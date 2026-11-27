AudioTranscriber 1.6.0 - prijepis i prijevod govora uživo
=========================================================

ŠTO RADI
  Sluša aplikacije koje odabereš (npr. Discord), zapisuje što svaka osoba kaže i uživo to prevodi na
  jezik koji odabereš. Prepoznavanje govora radi na ovom računalu. I prijevod radi na ovom računalu ili,
  ako to uključiš, online preko Geminija. Bez računa, ništa se ne snima na disk.

INSTALACIJA
  Pokreni Setup.exe. Prvi zaslon pita jezik aplikacije (jezik Windowsa je već
  odabran). Instalacija sve priprema korak po korak (oko 8 GB, 10-20 minuta). Ako pronađe raniju
  kopiju, ponovno koristi njezine modele, postavke i glasove. Zatim otvori AudioTranscriber s radne
  površine ili iz izbornika Start. Jezik aplikacije možeš promijeniti bilo kada gumbom sa zastavom
  u lijevoj traci.

POČETAK
  1. Uđi u poziv na Discordu. Discord se pojavi pod "SLUŠAJ" (zelena točka = reproducira zvuk).
  2. Klikni Pokreni. Svaka rečenica pojavi se s tim tko ju je rekao, vremenom, prijevodom i onim
     što se čulo.
  3. Valni oblik pokazuje glasnoću. "Auto" prati pozadinski šum svake osobe; povuci isprekidanu
     liniju da ga postaviš ručno.
  Gumb sa slušalicama pokraj gumba Pokreni brzo mijenja jezike koji se slušaju.

PROZOR
  Lijeva traka: Uživo, Osobe, Riječi, Overlay, Zaključaj overlay, Očisti, zastava jezika, Postavke.
  Desno: kašnjenje, grafička kartica, memorija, retci i osobe u pozivu.
  Klikni ime u bilo kojem retku da ga preimenuješ, ispraviš osobu, spojiš dvije osobe, nekoga
  ignoriraš ili odrediš jezik kojim uvijek govori. Svaki ispravak povećava točnost.
  "POGOĐENO IZ KONTEKSTA" = riječi nisu bile jasne pa je prevoditelj pogodio smisao.
  Sive riječi = prepoznavanje nije bilo pouzdano za njih.

POSTAVKE (kategorije lijevo, rijetke opcije pod "Napredno")
  Prepoznavanje  model govora i gdje radi, jezici za prepoznavanje, prepoznavanje rečenica, riječi
                 koje treba znati (imena, pojmovi iz igara, sleng), pojmovi iz League of Legends.
  Prijevod       grafička kartica (lokalno, bez interneta), Online - Gemini (besplatan ključ) ili
                 oboje: prvo online, grafička kartica kao rezerva. Dnevno besplatno ograničenje
                 Geminija resetira se u 09:00 (talijansko vrijeme).
  Osobe          prepoznaj tko govori, pamti glasove, nauči jezik svake osobe, popis poznatih osoba
                 (Ctrl/Shift + klik za odabir više njih, Delete da ih zaboraviš).
  Discord        imena i tko govori izravno iz aplikacije Discord na ovom računalu (bez bota),
                 postavlja se jednom preko "Kako to postaviti" (oko 2 minute); pokretanje i
                 zaustavljanje zajedno s tvojim pozivima.
  Overlay i prikaz  izvorni tekst, tekst overlaya, veličina, neprozirnost, automatsko skrivanje, prečaci.
  Aplikacija     jezik aplikacije, pokretanje s Windowsom, pouzdanost, izvoz, verzija.

OVERLAY
  Prozirni okvir iznad igre (prozorski način ili bez okvira; ne u ekskluzivnom cijelom zaslonu).
  Povuci ga mišem da ga pomakneš; prije igranja ga zaključaj (lokot ili Ctrl+Alt+L).
  Zaključan propušta klikove do igre i nestaje nakon nekoliko sekundi tišine.

PREČACI (rade i u igrama)
  Ctrl+Alt+S pokreni / zaustavi   Ctrl+Alt+P pauza / nastavi      Ctrl+Alt+C kopiraj zadnji prijevod
  Ctrl+Alt+O overlay uklj. / isklj.   Ctrl+Alt+L zaključaj / otključaj overlay

AŽURIRANJA
  Pri otvaranju aplikacija traži noviju verziju, tiho je preuzme i ponovno se pokrene s njom (ako
  upravo slušaš, čim klikneš Zaustavi). Postavke, glasovi, prijava na Discord i modeli ostaju.

POPRAVAK I DEINSTALACIJA
  Popravak: Postavke > Aplikacije > AudioTranscriber > Izmijeni ili ponovno pokreni instalaciju i
  odaberi Popravi. Preuzima samo ono što nedostaje; postavke i glasovi ostaju.
  Deinstalacija: Postavke > Aplikacije > AudioTranscriber > Deinstaliraj. Pita treba li izbrisati
  i modele i tvoje postavke (oko 8 GB). Ollama je zaseban program s vlastitim deinstalacijskim programom.

PRIVATNOST
  Glasovi, imena, postavke, ključevi i prijava na Discord ostaju samo na ovom računalu. S uključenim
  Geminijem tekst svake rečenice (ne zvuk) šalje se Googleu radi prijevoda.

DATOTEKE
  AudioTranscriber.exe  aplikacija          Setup.exe     popravak         Uninstall.exe  uklanjanje
  app\                  program             models\       modeli govora i glasova
  ollama_models\        modeli prijevoda    transcripts\  samo kad klikneš Izvezi
  settings.json         tvoje postavke      speakers.json spremljeni glasovi  setup.log   zapisnik instalacije
