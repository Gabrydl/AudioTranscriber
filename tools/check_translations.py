"""Asks Gemini to review the interface translations (app/locales) and the READMEs (readme/).

Run on the PC with the app's Python:   .venv\\Scripts\\python.exe tools\\check_translations.py
Uses the Gemini key from settings.json. Writes translation_check.json next to settings.json:
for each language, only the lines Gemini would change, with its suggestion and the reason.
Nothing is changed in the app; the report is only read back and applied by hand.
"""
from __future__ import annotations

import json
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
NAMES = {"it": "Italian", "pt-BR": "Brazilian Portuguese", "pt-PT": "European Portuguese",
         "es-ES": "Spanish (Spain)", "es-419": "Latin American Spanish", "de": "German", "fr": "French",
         "tl": "Tagalog (Filipino)", "ceb": "Cebuano (Bisaya)", "cs": "Czech", "pl": "Polish",
         "fi": "Finnish", "et": "Estonian", "sr": "Serbian (Cyrillic, ekavian)", "hr": "Croatian",
         "cnr": "Montenegrin (Latin script)", "bs": "Bosnian", "bg": "Bulgarian", "ru": "Russian", "el": "Greek"}
# first one Google answers is used (Gemma 3 was taken off the API; Gemma 4 has the big free allowance)
CANDIDATES = ["gemma-4-31b-it", "gemma-4-26b-a4b-it", "gemini-flash-lite-latest", "gemini-flash-latest"]
MODEL = CANDIDATES[0]


class Fatal(Exception):
    """Wrong key or model: no point going on with the other languages."""


def _err_text(e) -> str:
    try:
        return json.loads(e.read() or b"{}").get("error", {}).get("message", "")[:200]
    except Exception:
        return ""


def pick_model(key: str) -> str:
    for m in CANDIDATES:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{m}:generateContent"
        body = {"contents": [{"role": "user", "parts": [{"text": "Say OK."}]}]}
        req = urllib.request.Request(url, json.dumps(body).encode(), method="POST",
                                     headers={"Content-Type": "application/json", "x-goog-api-key": key})
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                r.read()
            return m
        except urllib.error.HTTPError as e:
            msg = _err_text(e)
            print(f"   {m}: {e.code} {msg}", flush=True)
            if e.code in (401, 403) or (e.code == 400 and "key" in msg.lower()):
                raise Fatal(f"the Gemini key was refused: {msg}")
            if e.code in (429, 503):          # exists, just busy or over today's limit: still usable later
                return m
        except Exception as e:
            print(f"   {m}: {e}", flush=True)
    raise Fatal("Google answered none of the models")


def read(p: Path) -> dict[int, str]:
    out = {}
    for raw in p.read_text(encoding="utf-8").splitlines():
        n, _, t = raw.partition("|")
        if n.strip().isdigit():
            out[int(n)] = t
    return out


def ask(key: str, prompt: str) -> str:
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL}:generateContent"
    body = {"contents": [{"role": "user", "parts": [{"text": prompt}]}],
            "generationConfig": {"temperature": 0.2}}
    req = urllib.request.Request(url, json.dumps(body).encode(), method="POST",
                                 headers={"Content-Type": "application/json", "x-goog-api-key": key})
    for attempt in range(6):
        try:
            with urllib.request.urlopen(req, timeout=300) as r:
                d = json.loads(r.read())
            return d["candidates"][0]["content"]["parts"][0]["text"]
        except urllib.error.HTTPError as e:
            msg = _err_text(e)
            if e.code in (429, 500, 503) and attempt < 5:
                print(f"   Google busy ({e.code} {msg[:80]}), waiting…", flush=True)
                time.sleep(30 * (attempt + 1))
                continue
            if e.code in (400, 401, 403, 404):
                raise Fatal(f"{e.code} {msg}")
            raise RuntimeError(f"{e.code} {msg}")
        except (TimeoutError, OSError):
            if attempt < 5:
                print("   no answer yet, retrying…", flush=True)
                time.sleep(15)
                continue
            raise
    return "[]"


def parse(text: str):
    """The JSON list in the answer (Gemma may wrap it in ```json fences or add a sentence)."""
    a, b = text.find("["), text.rfind("]")
    return json.loads(text[a:b + 1]) if a >= 0 and b > a else []


PROMPT = """You are a native {lang} speaker and a professional software localizer.
Below are user-interface texts of a Windows app (live voice transcription and translation for gamers,
used with Discord). Each item has the English original and the current {lang} translation.
Report ONLY items where the {lang} text is wrong, unnatural, ungrammatical, misleading, uses the wrong
regional variant, or is inconsistent with the other items. Keep placeholders like {{name}} exactly,
keep \\n line breaks and HTML tags exactly, keep product names (Discord, Gemini, Ollama, Whisper, GPU, CPU).
Do not report matters of taste. Answer ONLY with a JSON list, nothing else: [{{"n": number, "fix": "corrected text", "why": "short reason in English"}}].
An empty list [] means everything is fine.

ITEMS:
{items}"""

README_PROMPT = """You are a native {lang} speaker and a professional software localizer. Below is the README
of a Windows app in English and its {lang} translation. Report ONLY real problems in the translation
(wrong meaning, unnatural or ungrammatical sentences, wrong regional variant). Answer with a JSON list:
[{{"line": "the current {lang} line", "fix": "corrected line", "why": "short reason in English"}}]. [] if fine.

ENGLISH:
{en}

{lang}:
{tr}"""


def main():
    for st in (sys.stdout, sys.stderr):           # a console that can't show "…" or Cyrillic must not crash it
        try:
            st.reconfigure(errors="replace")
        except Exception:
            pass
    s = json.loads((ROOT / "settings.json").read_text(encoding="utf-8"))
    key = (s.get("gemini_key") or "").strip()
    if not key:
        sys.exit("No Gemini key in settings.json")
    only = sys.argv[1:] or list(NAMES)
    en = read(ROOT / "app" / "locales" / "en.txt")
    en_readme = (ROOT / "readme" / "README_en.txt").read_text(encoding="utf-8")
    out_path = ROOT / "translation_check.json"
    report = {}
    if out_path.exists():
        try:
            report = json.loads(out_path.read_text(encoding="utf-8"))
        except Exception:
            report = {}
    # languages already checked without errors are skipped, so it can be stopped and started again
    only = [c for c in only if not (c in report and not any("error" in x for x in report[c]["app"]))]
    global MODEL
    try:
        MODEL = pick_model(key)
    except Fatal as e:
        input(f"Stopped: {e}\nPress Enter to close.")
        return
    print(f"using {MODEL}", flush=True)
    for code in only:
        lang = NAMES[code]
        tr = read(ROOT / "app" / "locales" / f"{code}.txt")
        nums = sorted(tr)
        found = []
        print(f"{code}: checking…", flush=True)
        for i in range(0, len(nums), 50):
            items = "\n".join(json.dumps({"n": n, "en": en.get(n, ""), "tr": tr[n]}, ensure_ascii=False)
                              for n in nums[i:i + 50])
            try:
                found += parse(ask(key, PROMPT.format(lang=lang, items=items)))
            except Fatal as e:
                input(f"Stopped: {e}\nPress Enter to close.")
                return
            except Exception as e:
                found.append({"error": str(e)[:200]})
            time.sleep(3)
        rd = ROOT / "readme" / f"README_{code}.txt"
        rfound = []
        if rd.exists():
            try:
                rfound = parse(ask(key, README_PROMPT.format(lang=lang, en=en_readme,
                                                             tr=rd.read_text(encoding="utf-8"))))
            except Exception as e:
                rfound = [{"error": str(e)[:200]}]
        report[code] = {"app": found, "readme": rfound}
        out_path.write_text(json.dumps(report, ensure_ascii=False, indent=1), encoding="utf-8")
        print(f"{code}: {len(found)} app lines, {len(rfound)} README lines to look at", flush=True)
    print("report:", out_path)
    input("Done. Press Enter to close.")


if __name__ == "__main__":
    try:
        main()
    except BaseException:
        import traceback
        err = traceback.format_exc()
        try:
            (ROOT / "translation_check_error.txt").write_text(err, encoding="utf-8")
        except Exception:
            pass
        print(err)
        try:
            input("Something went wrong (saved in translation_check_error.txt). Press Enter to close.")
        except Exception:
            time.sleep(60)
