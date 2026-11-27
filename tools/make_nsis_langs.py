import re, shutil
from pathlib import Path
SRC = Path("/usr/share/nsis/Contrib/Language files")
DST = Path(__file__).resolve().parent.parent / "installer" / "nsis" / "lang"
DST.mkdir(exist_ok=True)
for f in DST.glob("*"): f.unlink()
# id, base file, native display name, LANGID override
LANGS = [("English","English","English",None),("Italian","Italian","Italiano",None),
 ("PortugueseBR","PortugueseBR","Português (Brasil)",None),("Portuguese","Portuguese","Português (Portugal)",None),
 ("Spanish","Spanish","Español (España)",None),("SpanishLatAm","Spanish","Español (Latinoamérica)",2058),
 ("German","German","Deutsch",None),("French","French","Français",None),
 ("Tagalog","English","Tagalog",1124),("Cebuano","English","Bisaya (Cebuano)",4096),
 ("Czech","Czech","Čeština",None),("Polish","Polish","Polski",None),
 ("Finnish","Finnish","Suomi",None),("Estonian","Estonian","Eesti",None),("Serbian","Serbian","Српски",None),
 ("Croatian","Croatian","Hrvatski",None),("Montenegrin","SerbianLatin","Crnogorski",11290),("Bosnian","Bosnian","Bosanski",None),
 ("Bulgarian","Bulgarian","Български",None),("Russian","Russian","Русский",None),("Greek","Greek","Ελληνικά",None)]

NLF = {
"Tagalog": {
"^SetupCaption":"Setup ng $(^Name)","^UninstallCaption":"Pag-uninstall ng $(^Name)",
"^DirSubCaption":": Folder ng Pag-install","^InstallingSubCaption":": Ini-install","^CompletedSubCaption":": Tapos na",
"^ConfirmSubCaption":": Kumpirmasyon","^UninstallingSubCaption":": Ina-uninstall","^UnCompletedSubCaption":": Tapos na",
"^BackBtn":"< &Bumalik","^NextBtn":"&Susunod >","^InstallBtn":"&I-install","^UninstallBtn":"&I-uninstall",
"^CancelBtn":"Kanselahin","^CloseBtn":"&Isara","^BrowseBtn":"&Mag-browse...","^ShowDetailsBtn":"Ipakita ang &detalye",
"^ClickNext":"I-click ang Susunod para magpatuloy.","^ClickInstall":"I-click ang I-install para simulan ang pag-install.",
"^ClickUninstall":"I-click ang I-uninstall para simulan ang pag-uninstall.","^Name":"Pangalan","^Completed":"Tapos na",
"^DirText":"Ii-install ng Setup ang $(^NameDA) sa folder na ito. Para mag-install sa ibang folder, i-click ang Mag-browse at pumili ng ibang folder. $_CLICK",
"^DirSubText":"Folder na paglalagyan","^DirBrowseText":"Piliin ang folder kung saan ii-install ang $(^NameDA):",
"^SpaceAvailable":"\"Bakanteng espasyo: \"","^SpaceRequired":"\"Kailangang espasyo: \"",
"^UninstallingText":"Ia-uninstall ang $(^NameDA) mula sa folder na ito. $_CLICK","^UninstallingSubText":"Ina-uninstall mula sa:",
"^CopyDetails":"Kopyahin ang Detalye sa Clipboard","^ErrorDecompressing":"May error sa pag-decompress ng data! Sira ba ang installer?",
},
"Cebuano": {
"^SetupCaption":"Setup sa $(^Name)","^UninstallCaption":"Pag-uninstall sa $(^Name)",
"^DirSubCaption":": Folder sa Pag-install","^InstallingSubCaption":": Gi-install","^CompletedSubCaption":": Human na",
"^ConfirmSubCaption":": Kumpirmasyon","^UninstallingSubCaption":": Gi-uninstall","^UnCompletedSubCaption":": Human na",
"^BackBtn":"< &Balik","^NextBtn":"&Sunod >","^InstallBtn":"&I-install","^UninstallBtn":"&I-uninstall",
"^CancelBtn":"Kanselaha","^CloseBtn":"&Sirad-i","^BrowseBtn":"&Pangita...","^ShowDetailsBtn":"Ipakita ang &detalye",
"^ClickNext":"I-click ang Sunod aron magpadayon.","^ClickInstall":"I-click ang I-install aron sugdan ang pag-install.",
"^ClickUninstall":"I-click ang I-uninstall aron sugdan ang pag-uninstall.","^Name":"Ngalan","^Completed":"Human na",
"^DirText":"I-install sa Setup ang $(^NameDA) niini nga folder. Aron i-install sa laing folder, i-click ang Pangita ug pagpili og laing folder. $_CLICK",
"^DirSubText":"Folder nga butangan","^DirBrowseText":"Pilia ang folder diin i-install ang $(^NameDA):",
"^SpaceAvailable":"\"Bakante nga espasyo: \"","^SpaceRequired":"\"Gikinahanglan nga espasyo: \"",
"^UninstallingText":"I-uninstall ang $(^NameDA) gikan niini nga folder. $_CLICK","^UninstallingSubText":"Gi-uninstall gikan sa:",
"^CopyDetails":"Kopyaha ang Detalye ngadto sa Clipboard","^ErrorDecompressing":"Adunay error sa pag-decompress sa data! Guba ba ang installer?",
}}
NSH = {
"Tagalog": {
"MUI_TEXT_WELCOME_INFO_TITLE":"Maligayang pagdating sa Setup ng $(^NameDA)",
"MUI_UNTEXT_WELCOME_INFO_TITLE":"Maligayang pagdating sa Pag-uninstall ng $(^NameDA)",
"MUI_TEXT_DIRECTORY_TITLE":"Piliin kung saan ii-install","MUI_TEXT_DIRECTORY_SUBTITLE":"Piliin ang folder kung saan ii-install ang $(^NameDA).",
"MUI_TEXT_INSTALLING_TITLE":"Ini-install","MUI_TEXT_INSTALLING_SUBTITLE":"Sandali lang habang ini-install ang $(^NameDA).",
"MUI_TEXT_FINISH_TITLE":"Tapos na ang pag-install","MUI_TEXT_FINISH_SUBTITLE":"Matagumpay na natapos ang Setup.",
"MUI_TEXT_ABORT_TITLE":"Naputol ang pag-install","MUI_TEXT_ABORT_SUBTITLE":"Hindi natapos nang maayos ang Setup.",
"MUI_UNTEXT_UNINSTALLING_TITLE":"Ina-uninstall","MUI_UNTEXT_UNINSTALLING_SUBTITLE":"Sandali lang habang ina-uninstall ang $(^NameDA).",
"MUI_UNTEXT_FINISH_TITLE":"Tapos na ang pag-uninstall","MUI_UNTEXT_FINISH_SUBTITLE":"Matagumpay na natapos ang pag-uninstall.",
"MUI_UNTEXT_ABORT_TITLE":"Naputol ang pag-uninstall","MUI_UNTEXT_ABORT_SUBTITLE":"Hindi natapos nang maayos ang pag-uninstall.",
"MUI_TEXT_FINISH_INFO_TITLE":"Tinatapos ang Setup ng $(^NameDA)","MUI_TEXT_FINISH_INFO_TEXT":"Naka-install na ang $(^NameDA) sa computer mo.$\\r$\\n$\\r$\\nI-click ang Tapusin para isara ang Setup.",
"MUI_UNTEXT_FINISH_INFO_TITLE":"Tinatapos ang Pag-uninstall ng $(^NameDA)","MUI_UNTEXT_FINISH_INFO_TEXT":"Na-uninstall na ang $(^NameDA) sa computer mo.$\\r$\\n$\\r$\\nI-click ang Tapusin para isara ang Setup.",
"MUI_TEXT_FINISH_RUN":"&Patakbuhin ang $(^NameDA)","MUI_TEXT_FINISH_SHOWREADME":"&Ipakita ang Readme","MUI_BUTTONTEXT_FINISH":"&Tapusin",
"MUI_UNTEXT_CONFIRM_TITLE":"I-uninstall ang $(^NameDA)","MUI_UNTEXT_CONFIRM_SUBTITLE":"Alisin ang $(^NameDA) sa computer mo.",
"MUI_TEXT_ABORTWARNING":"Sigurado ka bang gusto mong ihinto ang Setup ng $(^Name)?","MUI_UNTEXT_ABORTWARNING":"Sigurado ka bang gusto mong ihinto ang pag-uninstall ng $(^Name)?",
},
"Cebuano": {
"MUI_TEXT_WELCOME_INFO_TITLE":"Maayong pag-abot sa Setup sa $(^NameDA)",
"MUI_UNTEXT_WELCOME_INFO_TITLE":"Maayong pag-abot sa Pag-uninstall sa $(^NameDA)",
"MUI_TEXT_DIRECTORY_TITLE":"Pilia kung asa i-install","MUI_TEXT_DIRECTORY_SUBTITLE":"Pilia ang folder diin i-install ang $(^NameDA).",
"MUI_TEXT_INSTALLING_TITLE":"Gi-install","MUI_TEXT_INSTALLING_SUBTITLE":"Hulat kadiyot samtang gi-install ang $(^NameDA).",
"MUI_TEXT_FINISH_TITLE":"Human na ang pag-install","MUI_TEXT_FINISH_SUBTITLE":"Malampuson nga nahuman ang Setup.",
"MUI_TEXT_ABORT_TITLE":"Naputol ang pag-install","MUI_TEXT_ABORT_SUBTITLE":"Wala nahuman og maayo ang Setup.",
"MUI_UNTEXT_UNINSTALLING_TITLE":"Gi-uninstall","MUI_UNTEXT_UNINSTALLING_SUBTITLE":"Hulat kadiyot samtang gi-uninstall ang $(^NameDA).",
"MUI_UNTEXT_FINISH_TITLE":"Human na ang pag-uninstall","MUI_UNTEXT_FINISH_SUBTITLE":"Malampuson nga nahuman ang pag-uninstall.",
"MUI_UNTEXT_ABORT_TITLE":"Naputol ang pag-uninstall","MUI_UNTEXT_ABORT_SUBTITLE":"Wala nahuman og maayo ang pag-uninstall.",
"MUI_TEXT_FINISH_INFO_TITLE":"Gitapos ang Setup sa $(^NameDA)","MUI_TEXT_FINISH_INFO_TEXT":"Na-install na ang $(^NameDA) sa imong computer.$\\r$\\n$\\r$\\nI-click ang Humana aron sirad-an ang Setup.",
"MUI_UNTEXT_FINISH_INFO_TITLE":"Gitapos ang Pag-uninstall sa $(^NameDA)","MUI_UNTEXT_FINISH_INFO_TEXT":"Na-uninstall na ang $(^NameDA) sa imong computer.$\\r$\\n$\\r$\\nI-click ang Humana aron sirad-an ang Setup.",
"MUI_TEXT_FINISH_RUN":"&Padagana ang $(^NameDA)","MUI_TEXT_FINISH_SHOWREADME":"&Ipakita ang Readme","MUI_BUTTONTEXT_FINISH":"&Humana",
"MUI_UNTEXT_CONFIRM_TITLE":"I-uninstall ang $(^NameDA)","MUI_UNTEXT_CONFIRM_SUBTITLE":"Tangtanga ang $(^NameDA) sa imong computer.",
"MUI_TEXT_ABORTWARNING":"Sigurado ka nga gusto nimo hunongon ang Setup sa $(^Name)?","MUI_UNTEXT_ABORTWARNING":"Sigurado ka nga gusto nimo hunongon ang pag-uninstall sa $(^Name)?",
}}
for lid, base, native, langid in LANGS:
    nlf = (SRC / f"{base}.nlf").read_text(encoding="utf-8-sig").splitlines()
    nsh = (SRC / f"{base}.nsh").read_text(encoding="utf-8-sig")
    if langid is not None:   # Language ID is the line after "# Language ID"
        i = nlf.index("# Language ID"); nlf[i + 1] = str(langid)
    if lid in NLF:
        for i, l in enumerate(nlf):
            if l.startswith("# ^") and l[2:] in NLF[lid]:
                nlf[i + 1] = NLF[lid][l[2:]]
    for k, v in NSH.get(lid, {}).items():
        nsh, n = re.subn(r'(\$\{LangFileString\} ' + k + r' )"[^\n]*"', lambda m: m.group(1) + '"' + v + '"', nsh)
        assert n >= 1, (lid, k)
    nsh = re.sub(r'!insertmacro LANGFILE [^\n]*', f'!insertmacro LANGFILE "{lid}" "{lid}" "{native}" "{lid}"', nsh, 1)
    (DST / f"{lid}.nlf").write_text("﻿" + "\n".join(nlf) + "\n", encoding="utf-8")
    (DST / f"{lid}.nsh").write_text("﻿" + nsh, encoding="utf-8")
print("ok", len(LANGS))
