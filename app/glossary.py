"""League of Legends terms (Riot's official names in en/pt/es/de/fr/pl/cs/it + common slang).

- hotwords(): short list given to Whisper so it spells common game words right (Flash, gank, Baron...).
- find(text): the game terms that probably appear in a sentence, including localized names and
  near-misses from the speech recogniser ("destello" -> Flash, "kaiser" -> Kai'Sa, "hex flash" -> Hexflash).
  These are passed to the translator, which keeps them as the English game term instead of translating.
Data: assets/league_terms.json (built from Riot Data Dragon).
"""
from __future__ import annotations

import difflib
import json
import logging
import re
import unicodedata
from typing import Optional

from .config import ROOT

log = logging.getLogger("glossary")
FILE = ROOT / "assets" / "league_terms.json"

_data: Optional[dict] = None
_exact: dict[str, str] = {}               # normalized surface form -> canonical term
_by_first: dict[str, list[str]] = {}      # first letter -> normalized forms (for fuzzy matching)
_max_words = 1


def _norm(s: str) -> str:
    s = unicodedata.normalize("NFKD", s.lower())
    s = "".join(c for c in s if not unicodedata.combining(c))
    return re.sub(r"[^a-z0-9]", "", s)


def _load() -> dict:
    global _data, _max_words
    if _data is not None:
        return _data
    try:
        _data = json.loads(FILE.read_text(encoding="utf-8"))
    except Exception:
        log.exception("League terms not available")
        _data = {"terms": [], "hotwords": []}
    for t in _data.get("terms", []):
        term = t["term"]
        for form in [term] + list(t.get("aliases", [])):
            n = _norm(form)
            if len(n) < 3 or n in _exact:
                continue
            _exact[n] = term
            _by_first.setdefault(n[0], []).append(n)
            _max_words = max(_max_words, min(4, len(form.split())))
    log.info("League terms loaded: %d terms, %d names", len(_data.get("terms", [])), len(_exact))
    return _data


def hotwords() -> list[str]:
    return list(_load().get("hotwords", []))


_SKEL_RULES = [("ph", "f"), ("ck", "k"), ("qu", "k"), ("c", "k"), ("q", "k"), ("z", "s"), ("w", "v"),
               ("y", "i"), ("x", "ks"), ("h", "")]


def _skel(n: str) -> str:
    """Rough "how it sounds" key: consonants only (spelling of vowels is what the recogniser gets wrong
    most on bad mics), similar letters merged. "flesh" -> "flsh" = "flash"."""
    for a, b in _SKEL_RULES:
        n = n.replace(a, b)
    if not n:
        return n
    out = n[0] + re.sub(r"[aeiou]", "", n[1:])
    return re.sub(r"(.)\1+", r"\1", out)


def _vocab_index(vocab) -> dict[str, str]:
    idx = {}
    for w in vocab or []:
        w = str(w).strip()
        n = _norm(w)
        if len(n) >= 3:
            idx.setdefault(n, w)
    return idx


def find(text: str, limit: int = 12, vocab=None, league: bool = True) -> list[dict]:
    """[{"heard": "destello", "term": "Flash"}, ...] for the game terms (and the user's own words) that
    probably appear in text. Words marked word(?) - the recogniser wasn't sure - are also matched by
    sound, more loosely ("flesh(?)" -> Flash), because those are the ones it usually got wrong."""
    _load()
    user = _vocab_index(vocab)
    league_exact = _exact if league else {}
    if not (league_exact or user) or not text:
        return []
    toks = re.findall(r"[\w'&.]+(?:\(\?\))?", text)
    unsure = [t.endswith("(?)") for t in toks]
    words = [t[:-3] if t.endswith("(?)") else t for t in toks]
    found: dict[str, str] = {}
    used = [False] * len(words)
    exact = dict(league_exact)
    exact.update(user)                                  # the user's own words win
    by_first: dict[str, list[str]] = {k: list(v) for k, v in _by_first.items()} if league else {}
    for n in user:
        by_first.setdefault(n[0], []).append(n)
    skel_index: dict[str, list[str]] = {}
    for n in list(user) + list(league_exact):                 # the user's own words are tried first
        k = _skel(n)
        if len(k) >= 3:
            skel_index.setdefault(k, []).append(n)
    max_words = max([_max_words] + [min(4, len(w.split())) for w in user.values()])

    def scan(mode: str):
        for n in range(max_words, 0, -1):              # longest phrases first ("Infinity Edge" before "Edge")
            for i in range(len(words) - n + 1):
                if len(found) >= limit or any(used[i:i + n]):
                    continue
                ws = words[i:i + n]
                if n > 1 and (len(ws[0]) <= 2 or len(ws[-1]) <= 2):
                    continue                            # don't glue little words ("e", "y") onto a name
                key = _norm(" ".join(ws))
                if len(key) < 3:
                    continue
                term = exact.get(key) if mode == "exact" else None
                if mode == "fuzzy" and len(key) >= 5:   # near-miss of a longer name (recogniser spelling)
                    cands = [c for c in by_first.get(key[0], []) if abs(len(c) - len(key)) <= 2]
                    mine = [c for c in cands if c in user]
                    best = (difflib.get_close_matches(key, mine, n=1, cutoff=0.78)       # the user's words first
                            or difflib.get_close_matches(key, cands, n=1, cutoff=0.84))
                    if best:
                        term = exact[best[0]]
                if mode == "sound" and all(unsure[i:i + n]) and len(key) >= 4:
                    same = skel_index.get(_skel(key)) or []
                    hit = None
                    if same:     # several names sound alike: the user's word, then the closest spelling
                        hit = max(same, key=lambda c: (c in user, difflib.SequenceMatcher(None, key, c).ratio()))
                    else:
                        cands = [c for c in by_first.get(key[0], []) if abs(len(c) - len(key)) <= 3]
                        best = difflib.get_close_matches(key, cands, n=1, cutoff=0.74)
                        hit = best[0] if best else None
                    if hit is not None:
                        term = exact[hit]
                if term is not None and term not in found.values():
                    found[" ".join(ws)] = term
                    for j in range(i, i + n):
                        used[j] = True

    scan("exact")        # exact names first (also localized ones)
    scan("fuzzy")        # then close misspellings
    scan("sound")        # then unsure words that sound like a known name
    return [{"heard": h, "term": t} for h, t in found.items()]
