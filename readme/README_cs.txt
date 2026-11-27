AudioTranscriber 1.6.0 - živý přepis a překlad hlasu
====================================================

CO DĚLÁ
  Poslouchá aplikace, které vyberete (třeba Discord), zapisuje, co kdo říká, a živě to překládá do
  zvoleného jazyka. Rozpoznávání řeči běží na tomto PC. Překlad běží také na tomto PC, nebo online přes
  Gemini, pokud ho zapnete. Žádný účet, nic se neukládá na disk.

INSTALACE
  Spusťte Setup.exe. První obrazovka se zeptá na jazyk aplikace (jazyk Windows je už
  vybraný). Instalace vše připraví krok za krokem (asi 8 GB, 10-20 minut). Pokud najde starší kopii,
  použije znovu její modely, nastavení a hlasy. Pak otevřete AudioTranscriber z plochy nebo z nabídky
  Start. Jazyk aplikace můžete kdykoli změnit tlačítkem s vlajkou v levém pruhu.

ZAČÍNÁME
  1. Připojte se k hovoru na Discordu. Discord se objeví pod "POSLOUCHAT" (zelená tečka = hraje zvuk).
  2. Klikněte na Spustit. Každá věta se objeví s tím, kdo ji řekl, časem, překladem a tím, co zaznělo.
  3. Vlna ukazuje hlasitost. "Auto" sleduje šum v pozadí u každého člověka; tažením přerušované čáry
     ho nastavíte ručně.
  Tlačítko se sluchátky vedle Spustit jedním kliknutím přepne jazyky k rozpoznání.

OKNO
  Levý pruh: Živě, Lidé, Slova, Překryv, Zamknout překryv, Vymazat, vlajka jazyka, Nastavení.
  Vpravo: zpoždění, grafická karta, paměť, řádky a lidé v hovoru.
  Kliknutím na jméno v libovolném řádku ho můžete přejmenovat, opravit osobu, sloučit dva lidi, někoho
  ignorujete nebo nastavíte jazyk, kterým vždy mluví. Každá oprava zvyšuje přesnost.
  "ODHADNUTO Z KONTEXTU" = slova nebyla jasná a překladač odhadl smysl.
  Šedá slova = rozpoznávač si jimi nebyl jistý.

NASTAVENÍ (kategorie vlevo, méně časté volby pod "Pokročilé")
  Rozpoznávání  model řeči a kde běží, jazyky k rozpoznání, rozpoznávání vět, slova, která má znát
                (jména, herní výrazy, slang), výrazy z League of Legends.
  Překlad       grafická karta (lokálně, offline), Online - Gemini (klíč zdarma), nebo obojí: nejdřív
                online, grafická karta jako záloha. Denní limit zdarma u Gemini se nuluje v 09:00
                (italského času).
  Lidé          rozpoznávat, kdo mluví, pamatovat si hlasy, naučit se jazyk každého člověka, seznam
                známých lidí (Ctrl/Shift + klik pro výběr více, Delete pro zapomenutí).
  Discord       jména a kdo mluví přímo z aplikace Discord na tomto PC (žádný bot), nastavíte jednou
                přes "Jak to nastavit" (asi 2 minuty); spouštění a zastavení spolu s hovory.
  Překryv a zobrazení  původní text, text překryvu, velikost, průhlednost, automatické skrytí, zkratky.
  Aplikace      jazyk aplikace, spouštění s Windows, spolehlivost, export, verze.

PŘEKRYV
  Průhledné okénko nad hrou (v okně nebo bez okrajů; ne v exkluzivním režimu celé obrazovky).
  Přesuňte ho tažením myší; před hraním ho zamkněte (zámek nebo Ctrl+Alt+L).
  Zamčený propouští kliknutí do hry a po pár sekundách ticha zmizí.

KLÁVESOVÉ ZKRATKY (fungují i ve hrách)
  Ctrl+Alt+S spustit / zastavit   Ctrl+Alt+P pauza / pokračovat  Ctrl+Alt+C kopírovat poslední překlad
  Ctrl+Alt+O překryv zap / vyp    Ctrl+Alt+L zamknout / odemknout překryv

AKTUALIZACE
  Po otevření aplikace zkontroluje novější verzi, tiše ji stáhne a restartuje se do ní (pokud právě
  posloucháte, jakmile kliknete na Zastavit). Nastavení, hlasy, přihlášení do Discordu a modely zůstanou.

OPRAVA A ODINSTALACE
  Oprava: Nastavení > Aplikace > AudioTranscriber > Změnit, nebo spusťte instalaci znovu a zvolte
  Opravit. Stáhne jen to, co chybí; nastavení a hlasy zůstanou.
  Odinstalace: Nastavení > Aplikace > AudioTranscriber > Odinstalovat. Zeptá se, zda smazat i modely
  a vaše nastavení (asi 8 GB). Ollama je samostatný program s vlastním odinstalátorem.

SOUKROMÍ
  Hlasy, jména, nastavení, klíče a přihlášení do Discordu zůstávají jen na tomto PC. Se zapnutým Gemini
  se text každé věty (ne zvuk) posílá Googlu k překladu.

SOUBORY
  AudioTranscriber.exe  aplikace          Setup.exe     oprava           Uninstall.exe  odebrání
  app\                  program           models\       modely řeči a hlasů
  ollama_models\        modely překladu   transcripts\  jen při exportu
  settings.json         vaše nastavení    speakers.json uložené hlasy    setup.log      protokol instalace
