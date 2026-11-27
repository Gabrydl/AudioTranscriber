"""Montenegrin (Latin, ijekavian) text -> Serbian (Cyrillic, ekavian). Brand names, codes, keys stay Latin."""
import re, sys
EKAV = [("rijetke","retke"),("Bisaya","Бисаја"),("prepisuje","transkribuje"),("uspjel","uspel"),("promijenjen","promenjen"),("premješten","premešten"),("Osvježi","Osveži"),("Prijeđi","Pređi"),("zahtjeva","zahteva"),("provjeravaju","proveravaju"),("nVrijedi","nVaži"),("Kasnije","Kasnije"),("nijesu","nisu"),("djelovi","delovi"),("Provjeri","Proveri"),("provjeri","proveri"),("provjerava","proverava"),("Provjera","Provera"),("provjera","provera"),("provjeru","proveru"),("Cijeli zapisnik","Ceo zapisnik"),("Izmijeni","Izmeni"),("izmijeni","izmeni"),("promijeniti","promeniti"),("Završna provjera","Završna provera"),("lijepi","lepi"),("vjerovatno","verovatno"),("zamijeni","zameni"),("Pamti","Pamti"),("nijedan","nijedan"),("Njemački","Nemački"),("njemačk","nemačk"),("bijelu","belu"),("Vrijeme","Vreme"),("vrijeme","vreme"),("Vrijedi","Važi"),("vrijedi","važi"),
 ("sljedeć","sledeć"),("riječi","reči"),("riječ","reč"),("Riječi","Reči"),("uvijek","uvek"),("Uvijek","Uvek"),
 ("Lijevo","Levo"),("Lijevi","Levi"),("lijevoj","levoj"),("lijevo","levo"),("lijevi","levi"),
 ("cijeli chat","ceo čet"),("cijelom","celom"),("cijeli","ceo"),("cijelu","celu"),
 ("promijene","promene"),("promijeni","promeni"),("promjenu","promenu"),("promjena","promena"),("Promjena","Promena"),
 ("Primijeni","Primeni"),("primijenjena","primenjena"),("Miješano","Mešano"),("Umjesto","Umesto"),("umjesto","umesto"),
 ("Ovdje","Ovde"),("ovdje","ovde"),("gdje","gde"),("Gdje","Gde"),("dolje","dole"),("uspjelo","uspelo"),("uspio","uspeo"),
 ("dijelim","delim"),("podijeli","podeli"),("Nalijepi","Nalepi"),("nalijepi","nalepi"),("smije","sme"),
 ("obavještenja","obaveštenja"),("Odaberi","Izaberi"),("odaberi","izaberi"),("odabrane","izabrane"),("Odabrane","Izabrane"),
 ("odabrane","izabrane"),("odabranih","izabranih"),("odabere","izabere"),("odabir","izbor"),("odabrani","izabrani"),
 ("Zadnji","Poslednji"),("zadnji","poslednji"),("Zadnja","Poslednja"),("Pomakni","Pomeri"),("pomicanje","pomeranje"),
 ("Mijenja","Menja"),("mijenja","menja"),("krivom","pogrešnom"),("krivo","pogrešno"),("dvije","dve"),("Dvije","Dve"),
 ("nijedan","nijedan"),("Bjezi","Beži"),("bježi","beži"),("vidjeti","videti"),("cijel","cel"),("prelaz","prelaz"),
 ("pretvara","pretvara"),("Uklanjanje","Uklanjanje"),("svijet","svet"),("mjesto","mesto"),("pjesm","pesm"),
 ("razumjeti","razumeti"),("vrijednost","vrednost"),("nesigurno","nesigurno"),("potrošeno","potrošeno"),
 ("Oboje označeno","Oba označena"),("Oboje:","Oba:"),("sljedeće","sledeće"),("slijed","sled"),("pjeva","peva"),
 ("ljevoj","levoj"),("Kad ","Kada "),("kad ","kada "),("Prepis","Transkripcija"),("prepisa","transkripcije"),("prepis","transkripcija"),
 ("preko gumba","preko dugmeta"),("ponovo pokreće","ponovo pokreće"),("Gotovo","Gotovo")]
BRAND_INFL = [("Ollamu","Ollama"),("Ollame","Ollama"),("Ollamom","Ollama"),("Ollamu","Ollama")]
BRANDS = ["AudioTranscriber","Discord","Google","Windows","Riot","Gemini","Gemma","Whisper","Ollama","Hexflash","Flash-Lite","Flash","League","Legends","War","Thunder","Bismarck","Gabry","Client","Secret","Shift","Delete","Ctrl","Alt","LATAM","New","Application","Create","Reset","Redirects","Redirect","Add","Save","Changes","Authorize","Turbo","turbo","feed","feedu","overlay","overlaya","overlayu","online"]
LAT = {"lj":"љ","Lj":"Љ","LJ":"Љ","nj":"њ","Nj":"Њ","NJ":"Њ","dž":"џ","Dž":"Џ","DŽ":"Џ"}
ONE = dict(zip("abvgdđežzijklmnoprstćufhcčšABVGDĐEŽZIJKLMNOPRSTĆUFHCČŠ","абвгдђежзијклмнопрстћуфхцчшАБВГДЂЕЖЗИЈКЛМНОПРСТЋУФХЦЧШ"))
def cyr(w):
    out=""; i=0
    while i < len(w):
        if w[i:i+2] in LAT: out+=LAT[w[i:i+2]]; i+=2
        else: out+=ONE.get(w[i], w[i]); i+=1
    return out
TOKEN = re.compile(r"(\{[^}]*\}|<[^>]*>|https?://[^\s<]+|[\w.+/-]+\.(?:json|txt|com|exe|log|py)[\w./-]*|[A-Za-zčćžšđČĆŽŠĐ0-9_+/-]+(?:\.[0-9]+[A-Za-z0-9:]*)?)")
ACRO = {"GPU","CPU","VRAM","RAM","API","ID","GB","LATAM","OAuth2","GG","LOL","URL","JSON","HF","CUDA","PC"}
SPECIAL = {"feed":"фид","feedu":"фиду","feedom":"фидом","overlay":"оверлеј","overlaya":"оверлеја","overlayu":"оверлеју",
           "overlayom":"оверлејом","Overlay":"Оверлеј","online":"онлајн","Online":"Онлајн"}
def word(w):
    if re.fullmatch(r"\{[^}]*\}|<[^>]*>", w) or "://" in w or re.search(r"\.(json|txt|com|exe|log|py)", w):
        return w
    if w in SPECIAL:
        return SPECIAL[w]
    if "+" in w:
        return "+".join(x if len(x) == 1 else word(x) for x in w.split("+"))
    if "-" in w and w != "Flash-Lite":
        return "-".join(word(x) for x in w.split("-"))
    for b in BRANDS:
        if w == b:
            return w
        if w.startswith(b) and 0 < len(w) - len(b) <= 3 and b[0].isupper():
            return b + "-" + cyr(w[len(b):])
    if w in ACRO or re.search(r"\d", w) or "_" in w or w in ("px", "gg", "ok") or re.search(r"[qwxyQWXY]", w):
        return w
    return cyr(w)
def convert(text):
    for a,b in EKAV: text = text.replace(a,b)
    for a,b in BRAND_INFL: text = text.replace(a,b)
    # keep literal \n escapes
    parts = re.split(r"(\\n)", text)
    res=[]
    for p in parts:
        if p == "\\n": res.append(p); continue
        res.append(TOKEN.sub(lambda m: word(m.group(0)), p))
    return "".join(res)
if __name__ == "__main__":
    src, dst = sys.argv[1], sys.argv[2]
    lines = open(src, encoding="utf-8").read().splitlines()
    out = []
    for l in lines:
        if "|" in l and l.split("|",1)[0].isdigit():
            n, t = l.split("|",1); out.append(n+"|"+convert(t))
        else:
            out.append(convert(l))
    open(dst,"w",encoding="utf-8").write("\n".join(out)+"\n")
