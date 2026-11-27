"""Online translator: Google's Gemini API (free key from aistudio.google.com/apikey).

Same job as the local translator (fix misheard words + translate, same instructions and the same JSON answer),
just on Google's servers: faster and smarter than what fits on an 8 GB card. Used only when ticked in Settings;
with "both" ticked it goes first and the local translator takes over whenever it can't answer (no internet,
daily free limit reached, slow, key wrong).

Free plan: a daily number of requests per model (one request = one sentence). The count is kept here so the app
can show it; when Google answers "limit reached" the app switches to the local translator until the limit resets
(midnight Pacific time = 09:00 in Italy).
"""
from __future__ import annotations

import datetime as dt
import json
import logging
import re
import time
import urllib.error
import urllib.request

from .i18n import tr
from typing import Callable, Optional

log = logging.getLogger("online")
API = "https://generativelanguage.googleapis.com/v1beta/models/{model}:streamGenerateContent?alt=sse"

# model id -> (label, free requests per day as Google lists them for the free plan; shown as a guide only)
MODELS = {
    "gemma-4-31b-it": ("Gemma 4 31B – free", 14400),
    "gemini-flash-lite-latest": ("Gemini Flash-Lite – faster/smarter, small daily free limit", 1000),
    "gemini-flash-latest": ("Gemini Flash – smartest, very small daily free limit", 250),
}
DEFAULT_MODEL = "gemma-4-31b-it"
RETIRED = {"gemma-3-27b-it": "gemma-4-31b-it"}      # Google took Gemma 3 off the API


class OnlineUnavailable(Exception):
    pass


def _pacific_day() -> str:
    """Google's daily limits reset at midnight Pacific time (UTC-8, -7 in summer)."""
    now = dt.datetime.utcnow() - dt.timedelta(hours=8)
    return now.strftime("%Y-%m-%d")


class GeminiTranslator:
    def __init__(self, settings, build_user: Callable, system_prompt: Callable[[str], str],
                 status: Callable[[str], None] = lambda m: None):
        self.s = settings
        self.build_user = build_user
        self.system_prompt = system_prompt
        self.status = status
        self.blocked_until = 0.0
        self.block_reason = ""

    # ------------------------------------------------------------------ state
    def usable(self) -> bool:
        return bool(getattr(self.s, "translate_online", False) and str(getattr(self.s, "gemini_key", "")).strip()
                    and time.time() >= self.blocked_until)

    def used_today(self) -> int:
        return int(self.s.online_used or 0) if self.s.online_day == _pacific_day() else 0

    def _count(self):
        day = _pacific_day()
        if self.s.online_day != day:
            self.s.online_day, self.s.online_used = day, 0
        self.s.online_used = int(self.s.online_used or 0) + 1

    def _block(self, seconds: float, why: str):
        self.blocked_until = time.time() + seconds
        self.block_reason = why
        log.info("online translator paused for %.0f s: %s", seconds, why)
        local = bool(getattr(self.s, "translate_local", True))
        self.status("online: " + why + (" – " + tr("using the graphics card") if local else ""))

    # ------------------------------------------------------------------ request
    def translate_stream(self, line, context, on_partial, target: str) -> dict:
        from .engine import partial_json_string
        key = str(self.s.gemini_key or "").strip()
        model = str(self.s.gemini_model or DEFAULT_MODEL)
        model = RETIRED.get(model, model)
        user = self.build_user(line, context, target)
        sysp = self.system_prompt(target)
        if model.startswith("gemma"):
            # Gemma on the API takes no separate instructions: they go in front of the message
            body = {"contents": [{"role": "user", "parts": [{"text": sysp + "\n\n" + user}]}],
                    "generationConfig": {"temperature": 0.2, "maxOutputTokens": 300}}
        else:
            body = {"systemInstruction": {"parts": [{"text": sysp}]},
                    "contents": [{"role": "user", "parts": [{"text": user}]}],
                    "generationConfig": {"temperature": 0.2, "maxOutputTokens": 300,
                                         "responseMimeType": "application/json"}}
        req = urllib.request.Request(API.format(model=model), data=json.dumps(body).encode(),
                                     headers={"Content-Type": "application/json", "x-goog-api-key": key,
                                              "User-Agent": "AudioTranscriber"})
        buf, last = "", None
        t0 = time.time()
        try:
            with urllib.request.urlopen(req, timeout=float(getattr(self.s, "online_timeout_s", 10) or 10)) as r:
                self._count()
                for raw in r:
                    raw = raw.decode("utf-8", "replace").strip()
                    if not raw.startswith("data:"):
                        continue
                    ev = json.loads(raw[5:].strip() or "{}")
                    for c in ev.get("candidates") or []:
                        for p in (c.get("content") or {}).get("parts") or []:
                            if not p.get("thought"):
                                buf += p.get("text", "")
                    cur = partial_json_string(_strip_fence(buf), "tr")
                    if cur != last:
                        last = cur
                        on_partial(cur or "")
                    if time.time() - t0 > 15:
                        break
        except urllib.error.HTTPError as e:
            msg = ""
            try:
                msg = json.loads(e.read() or b"{}").get("error", {}).get("message", "")
            except Exception:
                pass
            if e.code == 429:
                if "day" in msg.lower() or "daily" in msg.lower() or "PerDay" in msg:
                    self._block(_seconds_to_reset(), tr("free daily limit reached (resets 09:00)"))
                else:
                    self._block(30, tr("too many requests per minute"))
            elif e.code in (400, 401, 403):
                self._block(600, tr("API key or model refused – check Settings"))
            else:
                self._block(20, tr("Google error {c}").format(c=e.code))
            raise OnlineUnavailable(f"{e.code} {msg[:120]}")
        except Exception as e:                                    # offline, timeout...
            self._block(20, tr("no answer (internet?)"))
            raise OnlineUnavailable(str(e))
        text = _strip_fence(buf)
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            m = re.search(r"\{.*\}", text, re.S)
            try:
                return json.loads(m.group(0)) if m else {"tr": last or ""}
            except Exception:
                return {"tr": last or ""}


def _strip_fence(t: str) -> str:
    t = t.strip()
    if t.startswith("```"):
        t = re.sub(r"^```(?:json)?\s*", "", t)
        t = re.sub(r"\s*```\s*$", "", t)
    return t


def _seconds_to_reset() -> float:
    now = dt.datetime.utcnow() - dt.timedelta(hours=8)
    nxt = (now + dt.timedelta(days=1)).replace(hour=0, minute=5, second=0, microsecond=0)
    return (nxt - now).total_seconds()
