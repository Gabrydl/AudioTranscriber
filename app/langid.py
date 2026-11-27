"""Bisaya (Cebuano) or Tagalog? Whisper has no Bisaya model, so Bisaya is recognised with the Tagalog one
(close relatives) and then told apart by the small everyday words each language uses and the other doesn't."""
from __future__ import annotations

import re
from typing import Optional

CEB = {"ug", "unsa", "unsaon", "dili", "naa", "wala", "kaayo", "nimo", "imo", "nako", "ako", "bitaw", "diay",
       "unya", "kini", "kana", "kadto", "adto", "gani", "ngano", "nganong", "asa", "kinsa", "ganahan", "gyud",
       "jud", "pud", "sad", "usab", "ra", "lagi", "atong", "ato", "nato", "ninyo", "inyo", "nila", "ila",
       "mao", "maoy", "kay", "karon", "ugma", "gahapon", "dayon", "dinhi", "diri", "didto", "nganha", "ingon",
       "sige", "intawon", "bayi", "lalaki", "uyab", "lami", "gutom", "kapoy", "hulat", "dagan", "tabang",
       "amping", "pila", "kanus-a", "kanusa", "ayaw", "basin", "tingali", "siguro", "nimo", "kaniya", "niya",
       "ani", "ana", "ingani", "ingana", "nindot", "pangit", "daghan", "gamay", "dako", "dula", "kuyog"}
TGL = {"ng", "hindi", "ito", "iyan", "iyon", "kasi", "talaga", "naman", "po", "opo", "bakit", "saan", "sino",
       "gusto", "meron", "mayroon", "dito", "doon", "diyan", "yung", "iyong", "ko", "mo", "niyo", "natin",
       "namin", "nila", "sila", "tayo", "kami", "kayo", "ngayon", "bukas", "kahapon", "sobra", "ganito",
       "ganyan", "paano", "kailan", "ilan", "huwag", "wag", "baka", "siguro", "ba", "pa", "na", "rin", "din",
       "lang", "muna", "tara", "takbo", "tulong", "ingat", "maganda", "pangit", "marami", "konti", "malaki",
       "laro", "sama", "ano", "anong"}
SHARED = CEB & TGL


def bisaya_or_tagalog(text: str, prior: Optional[str] = None) -> Optional[str]:
    """'ceb', 'tl' or None (can't tell). prior = the person's usual language, used when it's a tie."""
    words = re.findall(r"[a-zA-ZñÑ'-]+", (text or "").lower())
    if not words:
        return None
    c = sum(1 for w in words if w in CEB and w not in SHARED)
    t = sum(1 for w in words if w in TGL and w not in SHARED)
    if c > t:
        return "ceb"
    if t > c:
        return "tl"
    return prior if prior in ("ceb", "tl") else None
