"""Interface language: tr("English text") returns the text in the chosen language.

The tables live in app/locales/<code>.txt, one line per text: "N|text". en.txt holds the English
originals with the same numbers, so every language is matched by number. A missing line falls back
to English. Line breaks inside a text are written as \\n.
"""
from __future__ import annotations

import locale
from pathlib import Path

HERE = Path(__file__).resolve().parent / "locales"

# code, name in its own language, flag
LANGS = [
    ("en", "English", "gb"),
    ("it", "Italiano", "it"),
    ("pt-BR", "Português (Brasil)", "br"),
    ("pt-PT", "Português (Portugal)", "pt"),
    ("es-ES", "Español (España)", "es"),
    ("es-419", "Español (Latinoamérica)", "latam"),
    ("de", "Deutsch", "de"),
    ("fr", "Français", "fr"),
    ("tl", "Tagalog", "ph"),
    ("ceb", "Bisaya (Cebuano)", "ph"),
    ("cs", "Čeština", "cz"),
    ("pl", "Polski", "pl"),
]
CODES = [c for c, _n, _f in LANGS]
NAMES = {c: n for c, n, _f in LANGS}
FLAGS = {c: f for c, _n, f in LANGS}

_cur = "en"
_table: dict[str, str] = {}


def _read(path: Path) -> dict[int, str]:
    out = {}
    try:
        for raw in path.read_text(encoding="utf-8").splitlines():
            if "|" not in raw:
                continue
            n, _, txt = raw.partition("|")
            if n.strip().isdigit():
                out[int(n)] = txt.replace("\\n", "\n")
    except FileNotFoundError:
        pass
    return out


def set_lang(code: str) -> str:
    """Load a language; unknown codes fall back to English. Returns the code in use."""
    global _cur, _table
    code = code if code in CODES else "en"
    _cur = code
    _table = {}
    if code != "en":
        en = _read(HERE / "en.txt")
        loc = _read(HERE / f"{code}.txt")
        _table = {en[n]: t for n, t in loc.items() if n in en and t.strip()}
    return code


def current() -> str:
    return _cur


def tr(text: str) -> str:
    return _table.get(text, text)


def windows_lang() -> str:
    """The Windows display language mapped to one of ours (English when there is no match)."""
    tag = ""
    try:
        import ctypes
        buf = ctypes.create_unicode_buffer(85)
        if ctypes.windll.kernel32.GetUserDefaultLocaleName(buf, 85):
            tag = buf.value
    except Exception:
        try:
            tag = (locale.getlocale()[0] or "")
        except Exception:
            tag = ""
    return match(tag)


def match(tag: str) -> str:
    t = (tag or "").replace("_", "-").lower()
    if t.startswith("pt"):
        return "pt-BR" if t in ("pt", "pt-br") else "pt-PT"
    if t.startswith("es"):
        return "es-ES" if t in ("es", "es-es") or t.startswith("es-es") else "es-419"
    if t.startswith("fil") or t.startswith("tl"):
        return "tl"
    if t.startswith("ceb"):
        return "ceb"
    base = t.split("-")[0]
    return base if base in CODES else "en"
