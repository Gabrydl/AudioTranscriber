"""Instant translations for very short, common voice-chat phrases ("gg", "ok", "wait", "go go").

These lines skip the translator completely, so they appear at once. Only used when the WHOLE line is one
of these phrases; anything longer still goes through the translator.
"""
from __future__ import annotations

import re
import unicodedata
from typing import Optional

# meaning -> translation per target language
MEANINGS = {
    "gg":       {"en": "GG", "it": "GG"},
    "ok":       {"en": "Okay", "it": "Ok"},
    "yes":      {"en": "Yes", "it": "Sì"},
    "no":       {"en": "No", "it": "No"},
    "thanks":   {"en": "Thanks", "it": "Grazie"},
    "wait":     {"en": "Wait", "it": "Aspetta"},
    "go":       {"en": "Go!", "it": "Vai!"},
    "gogo":     {"en": "Go, go!", "it": "Vai, vai!"},
    "letsgo":   {"en": "Let's go!", "it": "Andiamo!"},
    "nice":     {"en": "Nice!", "it": "Bella!"},
    "sorry":    {"en": "Sorry", "it": "Scusa"},
    "help":     {"en": "Help!", "it": "Aiuto!"},
    "back":     {"en": "Back!", "it": "Indietro!"},
    "run":      {"en": "Run!", "it": "Scappa!"},
    "careful":  {"en": "Careful!", "it": "Attento!"},
    "lol":      {"en": "LOL", "it": "LOL"},
    "hello":    {"en": "Hi", "it": "Ciao"},
    "bye":      {"en": "Bye", "it": "Ciao"},
    "goodgame": {"en": "Good game", "it": "Bella partita"},
    "wp":       {"en": "Well played", "it": "Ben giocato"},
}

# heard (normalized, any language) -> meaning
HEARD = {
    "gg": "gg", "ggwp": "goodgame", "goodgame": "goodgame", "wellplayed": "wp", "wp": "wp",
    "ok": "ok", "okay": "ok", "okey": "ok", "oke": "ok", "vale": "ok", "dale": "ok", "beleza": "ok", "tabom": "ok",
    "taok": "ok", "dobrze": "ok", "dobra": "ok", "okej": "ok", "dobre": "ok", "jasne": "ok", "dacord": "ok",
    "daccord": "ok", "alles klar": "ok", "allesklar": "ok", "passt": "ok", "sige": "ok", "cool": "ok",
    "yes": "yes", "yeah": "yes", "yep": "yes", "ja": "yes", "si": "yes", "sim": "yes", "tak": "yes",
    "ano": "yes", "jo": "yes", "oui": "yes", "ouais": "yes", "oo": "yes", "opo": "yes",
    "no": "no", "nope": "no", "nein": "no", "nao": "no", "nie": "no", "ne": "no", "non": "no", "hindi": "no",
    "thanks": "thanks", "thank you": "thanks", "thankyou": "thanks", "thx": "thanks", "ty": "thanks",
    "danke": "thanks", "gracias": "thanks", "obrigado": "thanks", "obrigada": "thanks", "valeu": "thanks",
    "merci": "thanks", "dzieki": "thanks", "dziekuje": "thanks", "diky": "thanks", "dekuji": "thanks",
    "salamat": "thanks",
    "wait": "wait", "warte": "wait", "wart mal": "wait", "wartmal": "wait", "espera": "wait",
    "esperen": "wait", "espera ai": "wait", "esperaai": "wait", "attends": "wait", "attendez": "wait",
    "czekaj": "wait", "pockej": "wait", "teka": "wait", "sandali": "wait",
    "go": "go", "los": "go", "vai": "go", "vamos": "letsgo", "bora": "letsgo", "vamo": "letsgo",
    "allez": "go", "dalej": "go", "jdeme": "letsgo", "tara": "letsgo", "go go": "gogo", "gogo": "gogo",
    "go go go": "gogo", "gogogo": "gogo", "lets go": "letsgo", "letsgo": "letsgo", "los los": "gogo",
    "loslos": "gogo", "vamos vamos": "letsgo", "allez allez": "gogo",
    "nice": "nice", "geil": "nice", "boa": "nice", "bien": "nice", "buena": "nice", "super": "nice",
    "top": "nice", "fajnie": "nice", "pekne": "nice",
    "sorry": "sorry", "sry": "sorry", "my bad": "sorry", "mybad": "sorry", "sorri": "sorry",
    "perdon": "sorry", "desculpa": "sorry", "entschuldigung": "sorry", "pardon": "sorry",
    "przepraszam": "sorry", "promin": "sorry", "pasensya": "sorry",
    "help": "help", "hilfe": "help", "ayuda": "help", "ajuda": "help", "socorro": "help", "aide": "help",
    "pomocy": "help", "pomoc": "help", "tulong": "help",
    "back": "back", "zuruck": "back", "zurueck": "back", "atras": "back", "volta": "back", "recule": "back",
    "run": "run", "lauf": "run", "corre": "run", "corran": "run", "fuja": "run", "cours": "run",
    "uciekaj": "run", "utikej": "run", "takbo": "run",
    "careful": "careful", "vorsicht": "careful", "cuidado": "careful", "attention": "careful",
    "uwaga": "careful", "pozor": "careful", "ingat": "careful",
    "lol": "lol", "haha": "lol", "hahaha": "lol", "jaja": "lol", "jajaja": "lol", "kkk": "lol",
    "kkkk": "lol", "kkkkk": "lol", "xd": "lol",
    "hello": "hello", "hi": "hello", "hey": "hello", "hallo": "hello", "hola": "hello", "ola": "hello",
    "oi": "hello", "salut": "hello", "czesc": "hello", "ahoj": "hello", "kumusta": "hello",
    "bye": "bye", "tschuss": "bye", "tschuess": "bye", "adios": "bye", "tchau": "bye", "nara": "bye",
}


# words that mean something else in one language ("no" = "yeah" in Polish and Czech, "ja" = "I" in Polish)
BY_LANG = {"pl": {"no": "yes", "ja": None, "tak": "yes"}, "cs": {"no": "yes", "jo": "yes"},
           "es": {"ya": "ok"}, "tl": {"oo": "yes", "go": None},
           "ceb": {"oo": "yes", "o": "yes", "dili": "no", "sige": "ok", "sige sige": "ok", "hulat": "wait",
                   "hulat sa": "wait", "adto ta": "letsgo", "tara": "letsgo", "tabang": "help", "dagan": "run",
                   "amping": "careful", "kumusta": "hello", "babay": "bye", "salamat": "thanks", "nindot": "nice",
                   "pasayloa": "sorry", "go": None},
           "fi": {"kiitos": "thanks", "joo": "yes", "kylla": "yes", "ei": "no", "odota": "wait", "mennaan": "letsgo",
                  "moi": "hello", "hei": "hello", "anteeksi": "sorry", "apua": "help", "juokse": "run", "varo": "careful"},
           "et": {"aitah": "thanks", "jah": "yes", "jaa": "yes", "ei": "no", "oota": "wait", "oot": "wait",
                  "lahme": "letsgo", "tere": "hello", "vabandust": "sorry", "appi": "help", "jookse": "run"},
           "hr": {"hvala": "thanks", "da": "yes", "ne": "no", "cekaj": "wait", "idemo": "letsgo", "bok": "hello",
                  "oprosti": "sorry", "pomoc": "help", "bjezi": "run", "pazi": "careful"},
           "sr": {"hvala": "thanks", "da": "yes", "ne": "no", "cekaj": "wait", "idemo": "letsgo", "cao": "hello",
                  "izvini": "sorry", "pomoc": "help", "bezi": "run", "pazi": "careful"},
           "bs": {"hvala": "thanks", "da": "yes", "ne": "no", "cekaj": "wait", "idemo": "letsgo", "cao": "hello",
                  "izvini": "sorry", "pomoc": "help", "bjezi": "run", "pazi": "careful"},
           "cnr": {"hvala": "thanks", "da": "yes", "ne": "no", "cekaj": "wait", "idemo": "letsgo", "cao": "hello",
                   "izvini": "sorry", "pomoc": "help", "bjezi": "run", "pazi": "careful"}}


def _norm(text: str) -> str:
    t = unicodedata.normalize("NFKD", text.lower())
    t = "".join(c for c in t if not unicodedata.combining(c))
    t = re.sub(r"[^a-z' ]+", " ", t).replace("'", "")
    return re.sub(r"\s+", " ", t).strip()


def lookup(text: str, target: str, lang: str = "") -> Optional[str]:
    """The ready translation if the whole line is a common short phrase, else None."""
    n = _norm(text)
    if not n or len(n) > 24 or len(n.split()) > 3:
        return None
    special = BY_LANG.get(lang, {})
    if n in special:
        meaning = special[n]
    else:
        meaning = HEARD.get(n) or HEARD.get(n.replace(" ", ""))
    if meaning is None:
        return None
    tr = MEANINGS[meaning]
    return tr.get(target) or (tr["en"] if target == "en" else None)
