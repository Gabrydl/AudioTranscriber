"""Discord names + who is talking, through Discord's own local connection (RPC over the desktop app's IPC pipe).

Nothing joins your servers: this talks to the Discord program on this PC, the same way stream overlays do.
It needs a Discord "application" made by the user (Client ID + Client Secret from discord.com/developers);
Discord only lets the app's owner use the voice scopes, which is exactly this case.

What it provides to the rest of the app:
  - members():           {user_id: {"display", "nick", "username"}} of the voice call you are in
  - who(t0, t1):         {user_id: share of [t0, t1] that this person was talking}, from Discord's speaking events
  - name(user_id):       the name to show (Settings: display name / server nickname / username)
Runs in one background thread; reconnects by itself when Discord restarts.
"""
from __future__ import annotations

import json
import logging
import os
import socket
import struct
import sys
import threading
import time
import urllib.parse
import urllib.request
import uuid
from collections import deque
from typing import Callable, Optional

from .config import ROOT

log = logging.getLogger("discord")
TOKEN_FILE = ROOT / "discord_token.json"
SCOPES = ["rpc", "rpc.voice.read", "identify"]
REDIRECTS = ["http://localhost", "http://localhost/", "http://127.0.0.1", None]   # whichever the app has registered
API = "https://discord.com/api/v10"

OP_HANDSHAKE, OP_FRAME, OP_CLOSE, OP_PING, OP_PONG = 0, 1, 2, 3, 4


class RpcError(Exception):
    def __init__(self, msg, code=None):
        super().__init__(msg)
        self.code = code


class _Pipe:
    """The IPC connection: a named pipe on Windows, a unix socket elsewhere (also used by the tests)."""

    def __init__(self):
        self.f = None
        self.sock = None
        last = None
        for i in range(10):
            try:
                if sys.platform == "win32":
                    self.f = open(rf"\\?\pipe\discord-ipc-{i}", "r+b", buffering=0)
                else:
                    base = os.environ.get("DISCORD_IPC_DIR") or os.environ.get("XDG_RUNTIME_DIR") or "/tmp"
                    s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
                    s.connect(os.path.join(base, f"discord-ipc-{i}"))
                    self.sock = s
                return
            except OSError as e:
                last = e
        raise ConnectionError(f"Discord is not running ({last})")

    def _read(self, n: int) -> bytes:
        buf = b""
        while len(buf) < n:
            chunk = self.f.read(n - len(buf)) if self.f else self.sock.recv(n - len(buf))
            if not chunk:
                raise ConnectionError("Discord closed the connection")
            buf += chunk
        return buf

    def send(self, op: int, payload: dict):
        data = json.dumps(payload).encode()
        raw = struct.pack("<II", op, len(data)) + data
        if self.f:
            self.f.write(raw)
            self.f.flush()
        else:
            self.sock.sendall(raw)

    def recv(self) -> tuple[int, dict]:
        op, n = struct.unpack("<II", self._read(8))
        body = self._read(n) if n else b"{}"
        try:
            return op, json.loads(body or b"{}")
        except Exception:
            return op, {}

    def close(self):
        for x in (self.f, self.sock):
            try:
                if x:
                    x.close()
            except Exception:
                pass


def _post_form(url: str, fields: dict, timeout=20) -> dict:
    data = urllib.parse.urlencode(fields).encode()
    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/x-www-form-urlencoded",
                                                          "User-Agent": "AudioTranscriber"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.load(r)
    except urllib.error.HTTPError as e:
        try:
            body = json.loads(e.read() or b"{}")
        except Exception:
            body = {}
        raise RpcError(body.get("error_description") or body.get("error") or str(e), e.code)


class DiscordVoice:
    def __init__(self, settings, on_status: Callable[[str], None] = lambda m: None,
                 on_members: Callable[[], None] = lambda: None, on_connected: Callable[[dict], None] = lambda u: None):
        self.s = settings
        self.on_status = on_status
        self.on_members = on_members
        self.on_connected = on_connected
        self.connected = False
        self.me: dict = {}
        self.channel_id: Optional[str] = None
        self.channel_name = ""
        self._members: dict[str, dict] = {}
        self._speaking: dict[str, float] = {}               # user -> start time (still talking)
        self._done: deque = deque(maxlen=400)                # (user, start, end) of the last minutes
        self._lock = threading.Lock()
        self._stop = threading.Event()
        self._pipe: Optional[_Pipe] = None
        self._thread: Optional[threading.Thread] = None
        self._subs: list[tuple[str, dict]] = []
        self._pending: set = set()
        self._answers: dict = {}
        self.status = "off"

    # ------------------------------------------------------------------ public
    def start(self):
        if self._thread and self._thread.is_alive():
            return
        self._stop.clear()
        self._thread = threading.Thread(target=self._run, daemon=True, name="discord-rpc")
        self._thread.start()

    def stop(self):
        self._stop.set()
        if self._pipe:
            self._pipe.close()
        self.connected = False

    def restart(self):
        self.stop()
        if self._thread:
            self._thread.join(timeout=3)
        self.start()

    def members(self) -> dict[str, dict]:
        with self._lock:
            return {k: dict(v) for k, v in self._members.items()}

    def name(self, uid: str, names: Optional[dict] = None) -> str:
        n = names or self._members.get(uid) or {}
        return pick_name(n, getattr(self.s, "discord_name", "display"))

    def speaking_now(self) -> set:
        with self._lock:
            return set(self._speaking)

    def who(self, t0: float, t1: float, pad: float = 0.35) -> dict[str, float]:
        """Share of [t0, t1] each person was talking (Discord's own speaking light, a little padded because
        the light and the audio we hear are not perfectly in step)."""
        dur = max(0.2, t1 - t0)
        now = time.time()
        with self._lock:
            spans = list(self._done) + [(u, st, now) for u, st in self._speaking.items()]
        out: dict[str, float] = {}
        me = self.me.get("id")
        for u, a, b in spans:
            if u == me:
                continue
            ov = min(t1, b + pad) - max(t0, a - pad)
            if ov > 0:
                out[u] = out.get(u, 0.0) + ov
        return {u: min(1.0, v / dur) for u, v in out.items()}

    def dominant(self, t0: float, t1: float) -> Optional[str]:
        """The one person clearly talking during [t0, t1], or None (nobody / several at once)."""
        w = self.who(t0, t1)
        if not w:
            return None
        ranked = sorted(w.items(), key=lambda x: -x[1])
        best, share = ranked[0]
        second = ranked[1][1] if len(ranked) > 1 else 0.0
        dur = max(0.2, t1 - t0)
        # a sentence also holds a little lead-in and the closing pause, so "talking for a good part of it
        # and nobody else much" is enough
        return best if share * dur >= min(0.3, 0.25 * dur) and second <= share * 0.35 else None

    # ------------------------------------------------------------------ thread
    def _say(self, m: str):
        self.status = m
        try:
            self.on_status(m)
        except Exception:
            pass

    def _run(self):
        delay = 3.0
        while not self._stop.is_set():
            cid = str(getattr(self.s, "discord_client_id", "") or "").strip()
            if not getattr(self.s, "discord_enabled", False) or not cid:
                self._say("off")
                return
            try:
                self._session(cid)
                delay = 3.0
            except RpcError as e:
                log.warning("Discord: %s", e)
                self._say(f"Discord: {e}")
                delay = 15.0 if e.code in (4000, 5000, "auth") else 5.0
            except Exception as e:
                if not self._stop.is_set():
                    log.info("Discord connection: %s", e)
                    self._say("waiting for Discord…" if "not running" in str(e) else f"reconnecting… ({str(e)[:60]})")
            finally:
                self.connected = False
                if self._pipe:
                    self._pipe.close()
                    self._pipe = None
                with self._lock:
                    self._members.clear()
                    self._speaking.clear()
                    self.channel_id = None
            self._stop.wait(delay)
            delay = min(delay * 1.5, 20.0)

    def _session(self, cid: str):
        self._pipe = p = _Pipe()
        p.send(OP_HANDSHAKE, {"v": 1, "client_id": cid})
        op, msg = p.recv()
        if op == OP_CLOSE:
            raise RpcError(f"Discord refused the Client ID ({msg.get('message', 'invalid')}) - check it in Settings",
                           msg.get("code", 4000))
        token = self._token(cid)
        try:
            auth = self._cmd("AUTHENTICATE", {"access_token": token})
        except RpcError as e:
            log.info("stored token refused (%s) - authorizing again", e)
            _save_token(None)
            auth = self._cmd("AUTHENTICATE", {"access_token": self._token(cid)})
        self.me = (auth or {}).get("user") or {}
        self.connected = True
        log.info("Discord connected as %s", self.me.get("username"))
        try:
            self.on_connected(self.me)
        except Exception:
            log.exception("on_connected")
        self._cmd("SUBSCRIBE", {}, evt="VOICE_CHANNEL_SELECT")
        ch = self._cmd("GET_SELECTED_VOICE_CHANNEL", {})
        self._set_channel(ch)
        while not self._stop.is_set():
            self._handle(*p.recv())

    # ------------------------------------------------------------------ protocol
    def _cmd(self, cmd: str, args: dict, evt: Optional[str] = None, timeout: float = 600):
        nonce = str(uuid.uuid4())
        payload = {"cmd": cmd, "args": args, "nonce": nonce}
        if evt:
            payload["evt"] = evt
        self._pending.add(nonce)
        try:
            self._pipe.send(OP_FRAME, payload)
            end = time.time() + timeout
            while time.time() < end and not self._stop.is_set():
                msg = self._answers.pop(nonce, None)      # answered while a nested command was waiting
                if msg is None:
                    op, msg = self._pipe.recv()
                    n = msg.get("nonce") if op == OP_FRAME else None
                    if n and n != nonce and n in self._pending:
                        self._answers[n] = msg
                        continue
                    if n != nonce:
                        self._handle(op, msg)
                        continue
                if msg.get("evt") == "ERROR":
                    d = msg.get("data") or {}
                    raise RpcError(d.get("message", "error"), d.get("code"))
                return msg.get("data")
            raise ConnectionError(f"no answer to {cmd}")
        finally:
            self._pending.discard(nonce)

    def _handle(self, op: int, msg: dict):
        if op == OP_PING:
            self._pipe.send(OP_PONG, msg)
            return
        if op == OP_CLOSE:
            raise ConnectionError(msg.get("message", "closed by Discord"))
        if op != OP_FRAME or msg.get("cmd") != "DISPATCH":
            return
        evt, d = msg.get("evt"), msg.get("data") or {}
        now = time.time()
        if evt == "SPEAKING_START":
            u = str(d.get("user_id"))
            with self._lock:
                self._speaking.setdefault(u, now)
        elif evt == "SPEAKING_STOP":
            u = str(d.get("user_id"))
            with self._lock:
                st = self._speaking.pop(u, None)
                if st is not None:
                    self._done.append((u, st, now))
        elif evt in ("VOICE_STATE_CREATE", "VOICE_STATE_UPDATE"):
            self._add_member(d)
            self._changed()
        elif evt == "VOICE_STATE_DELETE":
            u = str((d.get("user") or {}).get("id"))
            with self._lock:
                self._members.pop(u, None)
                self._speaking.pop(u, None)
            self._changed()
        elif evt == "VOICE_CHANNEL_SELECT":
            cid = d.get("channel_id")
            ch = self._cmd("GET_CHANNEL", {"channel_id": cid}) if cid else None
            self._set_channel(ch)

    def _set_channel(self, ch: Optional[dict]):
        for evt, args in self._subs:                       # leave the old call
            try:
                self._cmd("UNSUBSCRIBE", args, evt=evt, timeout=10)
            except Exception:
                pass
        self._subs = []
        with self._lock:
            self._members.clear()
            self._speaking.clear()
            self.channel_id = (ch or {}).get("id")
            self.channel_name = (ch or {}).get("name") or ""
        if ch:
            for vs in ch.get("voice_states") or []:
                self._add_member(vs)
            for evt in ("VOICE_STATE_CREATE", "VOICE_STATE_UPDATE", "VOICE_STATE_DELETE",
                        "SPEAKING_START", "SPEAKING_STOP"):
                args = {"channel_id": ch["id"]}
                self._cmd("SUBSCRIBE", args, evt=evt, timeout=10)
                self._subs.append((evt, args))
            self._say(f"connected · {len(self._members)} in {self.channel_name or 'call'}")
        else:
            self._say("connected · not in a voice call")
        self._changed()

    def _add_member(self, vs: dict):
        u = vs.get("user") or {}
        uid = str(u.get("id") or "")
        if not uid or u.get("bot") or uid == str(self.me.get("id")):
            return
        names = {"display": u.get("global_name") or u.get("username") or "",
                 "nick": vs.get("nick") or u.get("global_name") or u.get("username") or "",
                 "username": u.get("username") or ""}
        with self._lock:
            self._members[uid] = names

    def _changed(self):
        if self.channel_id:
            self._say(f"connected · {len(self._members)} in {self.channel_name or 'call'}")
        try:
            self.on_members()
        except Exception:
            log.exception("on_members")

    # ------------------------------------------------------------------ OAuth
    def _token(self, cid: str) -> str:
        tok = _load_token()
        secret = str(getattr(self.s, "discord_client_secret", "") or "").strip()
        if tok and tok.get("client_id") == cid:
            if tok.get("expires_at", 0) - time.time() > 3600:
                return tok["access_token"]
            if tok.get("refresh_token") and secret:
                try:
                    return self._exchange(cid, secret, {"grant_type": "refresh_token",
                                                        "refresh_token": tok["refresh_token"]})
                except Exception as e:
                    log.info("token refresh failed (%s) - authorizing again", e)
        if not secret:
            raise RpcError("Client Secret missing - paste it in Settings > Discord", "auth")
        self._say("click “Authorize” in Discord…")
        try:
            data = self._cmd("AUTHORIZE", {"client_id": cid, "scopes": SCOPES}, timeout=300)
        except RpcError as e:
            if e.code == 5000:
                raise RpcError("access was not allowed in Discord", 5000)
            raise
        return self._exchange(cid, secret, {"grant_type": "authorization_code", "code": data["code"]})

    def _exchange(self, cid: str, secret: str, fields: dict) -> str:
        base = {"client_id": cid, "client_secret": secret, **fields}
        j, last = None, None
        for r in (REDIRECTS if "code" in fields else [None]):
            try:
                j = _post_form(API + "/oauth2/token", {**base, "redirect_uri": r} if r else base)
                break
            except RpcError as e:
                last = e
                if "redirect" not in str(e).lower():
                    break
        if j is None:
            hint = "add http://localhost under OAuth2 > Redirects" if last and "redirect" in str(last).lower() \
                else "check the Client Secret"
            raise RpcError(f"Discord login failed: {last} ({hint})", "auth")
        _save_token({"client_id": cid, "access_token": j["access_token"], "refresh_token": j.get("refresh_token"),
                     "expires_at": time.time() + float(j.get("expires_in", 604800))})
        return j["access_token"]


def pick_name(names: dict, kind: str) -> str:
    kind = kind if kind in ("display", "nick", "username") else "display"
    return (names.get(kind) or names.get("display") or names.get("username") or "").strip()


def _load_token() -> Optional[dict]:
    try:
        return json.loads(TOKEN_FILE.read_text(encoding="utf-8"))
    except Exception:
        return None


def _save_token(tok: Optional[dict]):
    try:
        if tok is None:
            TOKEN_FILE.unlink(missing_ok=True)
        else:
            TOKEN_FILE.write_text(json.dumps(tok), encoding="utf-8")
    except Exception:
        log.exception("save token")


def forget_login():
    _save_token(None)
