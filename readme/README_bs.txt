AudioTranscriber 1.6.0 - prepis i prevod govora uživo
=========================================================

ŠTA RADI
  Sluša aplikacije koje odabereš (npr. Discord), zapisuje šta svaka osoba kaže i uživo to prevodi na
  jezik koji odabereš. Prepoznavanje govora radi na ovom računaru. I prevod radi na ovom računaru ili,
  ako to uključiš, online preko Geminija. Bez naloga, ništa se ne snima na disk.

INSTALACIJA
  Pokreni Setup.exe. Prvi ekran pita jezik aplikacije (jezik Windowsa je već
  izabran). Instalacija sve priprema korak po korak (oko 8 GB, 10-20 minuta). Ako pronađe raniju
  kopiju, ponovo koristi njene modele, postavke i glasove. Zatim otvori AudioTranscriber s radne
  površine ili iz menija Start. Jezik aplikacije možeš promijeniti bilo kada dugmetom sa zastavom
  u lijevoj traci.

POČETAK
  1. Uđi u poziv na Discordu. Discord se pojavi pod "SLUŠAJ" (zelena tačka = reprodukuje zvuk).
  2. Klikni Pokreni. Svaka rečenica pojavi se s tim ko ju je rekao, vremenom, prevodom i onim
     šta se čulo.
  3. Talasni oblik pokazuje jačinu zvuka. "Auto" prati pozadinski šum svake osobe; povuci isprekidanu
     liniju da ga postaviš ručno.
  Dugme sa slušalicama pokraj Pokreni brzo mijenja jezike koji se slušaju.

PROZOR
  Lijeva traka: Uživo, Osobe, Riječi, Overlay, Zaključaj overlay, Očisti, zastava jezika, Postavke.
  Desno: kašnjenje, grafička kartica, memorija, redovi i osobe u pozivu.
  Klikni ime u bilo kojem redu da ga preimenuješ, ispraviš osobu, spojiš dvije osobe, nekoga
  ignorišeš ili odrediš jezik kojim uvijek govori. Svaki ispravak povećava tačnost.
  "POGOĐENO IZ KONTEKSTA" = riječi nisu bile jasne pa je prevodilac pogodio smisao.
  Sive riječi = prepoznavanje nije bilo sigurno u njih.

POSTAVKE (kategorije lijevo, rijetke opcije pod "Napredno")
  Prepoznavanje  model govora i gdje radi, jezici za prepoznavanje, prepoznavanje rečenica, riječi
                 koje treba znati (imena, pojmovi iz igara, sleng), pojmovi iz League of Legends.
  Prevod       grafička kartica (lokalno, bez interneta), Online - Gemini (besplatan ključ) ili
                 oboje: prvo online, grafička kartica kao rezerva. Dnevno besplatno ograničenje
                 Geminija resetuje se u 09:00 (talijansko vrijeme).
  Osobe          prepoznaj ko govori, pamti glasove, nauči jezik svake osobe, spisak poznatih osoba
                 (Ctrl/Shift + klik za odabir više njih, Delete da ih zaboraviš).
  Discord        imena i ko govori izravno iz aplikacije Discord na ovom računaru (bez bota),
                 postavlja se jednom preko "Kako to postaviti" (oko 2 minute); pokretanje i
                 zaustavljanje zajedno s tvojim pozivima.
  Overlay i prikaz  izvorni tekst, tekst overlaya, veličina, neprovidnost, automatsko skrivanje, prečaci.
  Aplikacija     jezik aplikacije, pokretanje s Windowsom, pouzdanost, izvoz, verzija.

OVERLAY
  Prozirni okvir iznad igre (prozorski način ili bez okvira; ne u ekskluzivnom cijelom ekranu).
  Povuci ga mišem da ga pomjeriš; prije igranja ga zaključaj (katanac ili Ctrl+Alt+L).
  Zaključan propušta klikove do igre i nestaje nakon nekoliko sekundi tišine.

PREČACI (rade i u igrama)
  Ctrl+Alt+S pokreni / zaustavi   Ctrl+Alt+P pauza / nastavi      Ctrl+Alt+C kopiraj zadnji prevod
  Ctrl+Alt+O overlay uklj. / isklj.   Ctrl+Alt+L zaključaj / otključaj overlay

AŽURIRANJA
  Pri otvaranju aplikacija traži noviju verziju, tiho je preuzme i ponovo se pokrene s njom (ako
  upravo slušaš, čim klikneš Zaustavi). Postavke, glasovi, prijava na Discord i modeli ostaju.

POPRAVAK I DEINSTALACIJA
  Popravak: Postavke > Aplikacije > AudioTranscriber > Izmijeni ili ponovo pokreni instalaciju i
  izaberi Popravi. Preuzima samo ono šta nedostaje; postavke i glasovi ostaju.
  Deinstalacija: Postavke > Aplikacije > AudioTranscriber > Deinstaliraj. Pita treba li izbrisati
  i modele i tvoje postavke (oko 8 GB). Ollama je poseban program s vlastitim programom za deinstalaciju.

PRIVATNOST
  Glasovi, imena, postavke, ključevi i prijava na Discord ostaju samo na ovom računaru. S uključenim
  Geminijem tekst svake rečenice (ne zvuk) šalje se Googleu radi prevoda.

FAJLOVI
  AudioTranscriber.exe  aplikacija          Setup.exe     popravka         Uninstall.exe  uklanjanje
  app\                  program             models\       modeli govora i glasova
  ollama_models\        modeli prevoda    transcripts\  samo kad klikneš Izvezi
  settings.json         tvoje postavke      speakers.json sačuvani glasovi  setup.log   zapisnik instalacije
