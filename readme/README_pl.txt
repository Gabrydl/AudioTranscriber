AudioTranscriber 1.6.0 - transkrypcja i tłumaczenie głosu na żywo
=================================================================

CO ROBI
  Słucha wybranych aplikacji (np. Discorda), zapisuje, co mówi każda osoba, i tłumaczy to na żywo na
  wybrany język. Rozpoznawanie mowy działa na tym PC. Tłumaczenie też działa na tym PC albo online
  przez Gemini, jeśli je włączysz. Bez konta, nic nie jest nagrywane na dysk.

INSTALACJA
  Uruchom AudioTranscriber_Setup.exe. Pierwszy ekran pyta o język aplikacji (język Windows jest już
  wybrany). Instalator przygotowuje wszystko krok po kroku (około 8 GB, 10-20 minut). Jeśli znajdzie
  wcześniejszą kopię, użyje ponownie jej modeli, ustawień i głosów. Potem otwórz AudioTranscriber z
  pulpitu albo z menu Start. Język aplikacji możesz zmienić w każdej chwili przyciskiem z flagą na
  lewym pasku.

START
  1. Dołącz do rozmowy na Discordzie. Discord pojawia się w "SŁUCHAJ" (zielona kropka = gra dźwięk).
  2. Kliknij Start. Każde zdanie pojawia się z tym, kto je powiedział, godziną, tłumaczeniem i tym,
     co zostało usłyszane.
  3. Fala pokazuje głośność. "Auto" śledzi szum tła każdej osoby; przeciągnij przerywaną linię, aby
     ustawić go ręcznie.

OKNO
  Lewy pasek: Na żywo, Osoby, Słowa, Nakładka, Zablokuj nakładkę, Wyczyść, flaga języka, Ustawienia.
  Po prawej: opóźnienie, karta graficzna, pamięć, linie i osoby w rozmowie.
  Kliknij imię w dowolnej linii, aby zmienić nazwę, poprawić osobę, połączyć dwie osoby, kogoś
  ignorować albo ustalić język, którym zawsze mówi. Każda poprawka zwiększa dokładność.
  "ODGADNIĘTE Z KONTEKSTU" = słowa były niewyraźne i tłumacz odgadł sens.
  Szare słowa = rozpoznawanie nie było ich pewne.

USTAWIENIA (kategorie po lewej, rzadkie opcje w "Zaawansowane")
  Rozpoznawanie  model mowy i gdzie działa, języki do rozpoznawania, wykrywanie zdań, słowa do znania
                 (imiona, terminy z gier, slang), terminy z League of Legends.
  Tłumaczenie    karta graficzna (lokalnie, offline), Online - Gemini (darmowy klucz) albo oba:
                 najpierw online, karta graficzna jako zapas. Darmowy dzienny limit Gemini zeruje się
                 o 09:00 (czasu włoskiego).
  Osoby          rozpoznawanie, kto mówi, zapamiętywanie głosów, nauka języka każdej osoby, lista
                 znanych osób (Ctrl/Shift + klik, aby wybrać kilka, Delete, aby je zapomnieć).
  Discord        imiona i kto mówi prosto z aplikacji Discord na tym PC (bez bota), ustawiane raz
                 przez "Jak to ustawić" (około 2 minut); start i stop razem z twoimi rozmowami.
  Nakładka i wyświetlanie  tekst oryginalny, tekst nakładki, rozmiar, krycie, auto-ukrywanie, skróty.
  Aplikacja      język aplikacji, uruchamianie z Windows, niezawodność, eksport, wersja.

NAKŁADKA
  Przezroczyste okienko nad grą (tryb okna lub bez ramek; nie wyłączny pełny ekran).
  "Przesuń nakładkę" odblokowuje ją, aby można ją było przeciągnąć; po puszczeniu sama się blokuje.
  Zablokowana przepuszcza kliknięcia do gry i znika po kilku sekundach ciszy.

SKRÓTY (działają w grach)
  Ctrl+Alt+S start / stop         Ctrl+Alt+P pauza / wznów        Ctrl+Alt+C kopiuj ostatnie tłumaczenie
  Ctrl+Alt+O nakładka wł. / wył.  Ctrl+Alt+L zablokuj / odblokuj nakładkę

AKTUALIZACJE
  Przy otwarciu aplikacja szuka nowszej wersji, pobiera ją po cichu i uruchamia się w niej ponownie
  (jeśli akurat słuchasz, gdy tylko klikniesz Stop). Ustawienia, głosy, logowanie do Discorda i modele
  zostają.

NAPRAWA I ODINSTALOWANIE
  Naprawa: Ustawienia > Aplikacje > AudioTranscriber > Modyfikuj albo uruchom instalator ponownie i
  wybierz Napraw. Pobiera tylko to, czego brakuje; ustawienia i głosy zostają.
  Odinstalowanie: Ustawienia > Aplikacje > AudioTranscriber > Odinstaluj. Pyta, czy usunąć też modele
  i twoje ustawienia (około 8 GB). Ollama to osobny program z własnym deinstalatorem.

PRYWATNOŚĆ
  Głosy, imiona, ustawienia, klucze i logowanie do Discorda zostają tylko na tym PC. Z włączonym Gemini
  tekst każdego zdania (nie dźwięk) jest wysyłany do Google do przetłumaczenia.

PLIKI
  AudioTranscriber.exe  aplikacja           Setup.exe     naprawa         Uninstall.exe  usuwanie
  app\                  program             models\       modele mowy i głosów
  ollama_models\        modele tłumaczenia  transcripts\  tylko po kliknięciu Eksportuj
  settings.json         twoje ustawienia    speakers.json zapisane głosy  setup.log      dziennik instalacji
