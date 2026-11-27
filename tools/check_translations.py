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
         "tl": "Tagalog (Filipino)", "ceb": "Cebuano (Bisaya)", "cs": "Czech", "pl": "Polish"}
MODEL = "gemini-flash-latest"          # smarter than Gemma for reviewing; a few calls only


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
            "generationConfig": {"temperature": 0.2, "responseMimeType": "application/json"}}
    req = urllib.request.Request(url, json.dumps(body).encode(), method="POST",
                                 headers={"Content-Type": "application/json", "x-goog-api-key": key})
    for attempt in range(4):
        try:
            with urllib.request.urlopen(req, timeout=120) as r:
                d = json.loads(r.read())
            return d["candidates"][0]["content"]["parts"][0]["text"]
        except urllib.error.HTTPError as e:
            if e.code in (429, 500, 503) and attempt < 3:
                time.sleep(20 * (attempt + 1))
                continue
            raise
    return "[]"


PROMPT = """You are a native {lang} speaker and a professional software localizer.
Below are user-interface texts of a Windows app (live voice transcription and translation for gamers,
used with Discord). Each item has the English original and the current {lang} translation.
Report ONLY items where the {lang} text is wrong, unnatural, ungrammatical, misleading, uses the wrong
regional variant, or is inconsistent with the other items. Keep placeholders like {{name}} exactly,
keep \\n line breaks and HTML tags exactly, keep product names (Discord, Gemini, Ollama, Whisper, GPU, CPU).
Do not report matters of taste. Answer with a JSON list: [{{"n": number, "fix": "corrected text", "why": "short reason in English"}}].
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
    s = json.loads((ROOT / "settings.json").read_text(encoding="utf-8"))
    key = (s.get("gemini_key") or "").strip()
    if not key:
        sys.exit("No Gemini key in settings.json")
    only = sys.argv[1:] or list(NAMES)
    en = read(ROOT / "app" / "locales" / "en.txt")
    en_readme = (ROOT / "readme" / "README_en.txt").read_text(encoding="utf-8")
    out_path = ROOT / "translation_check.json"
    report = json.loads(out_path.read_text(encoding="utf-8")) if out_path.exists() else {}
    for code in only:
        lang = NAMES[code]
        tr = read(ROOT / "app" / "locales" / f"{code}.txt")
        nums = sorted(tr)
        found = []
        for i in range(0, len(nums), 90):                        # a few calls per language
            items = "\n".join(json.dumps({"n": n, "en": en.get(n, ""), "tr": tr[n]}, ensure_ascii=False)
                              for n in nums[i:i + 90])
            try:
                found += json.loads(ask(key, PROMPT.format(lang=lang, items=items)))
            except Exception as e:
                found.append({"error": str(e)[:200]})
            time.sleep(4)
        rd = ROOT / "readme" / f"README_{code}.txt"
        rfound = []
        if rd.exists():
            try:
                rfound = json.loads(ask(key, README_PROMPT.format(lang=lang, en=en_readme,
                                                                  tr=rd.read_text(encoding="utf-8"))))
            except Exception as e:
                rfound = [{"error": str(e)[:200]}]
        report[code] = {"app": found, "readme": rfound}
        out_path.write_text(json.dumps(report, ensure_ascii=False, indent=1), encoding="utf-8")
        print(f"{code}: {len(found)} app lines, {len(rfound)} README lines to look at", flush=True)
    print("report:", out_path)


if __name__ == "__main__":
    main()
