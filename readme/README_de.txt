AudioTranscriber 1.6.0 - Live-Transkription und -Übersetzung von Sprache
========================================================================

WAS ES MACHT
  Es hört den Apps zu, die du auswählst (z. B. Discord), schreibt mit, was jede Person sagt, und
  übersetzt es live in die Sprache deiner Wahl. Die Spracherkennung läuft auf diesem PC. Die Übersetzung
  läuft ebenfalls auf diesem PC oder, wenn du es einschaltest, online mit Gemini. Kein Konto, nichts
  wird auf der Festplatte aufgezeichnet.

INSTALLATION
  Starte AudioTranscriber_Setup.exe. Der erste Bildschirm fragt nach der Sprache der App (deine
  Windows-Sprache ist schon ausgewählt). Das Setup richtet alles Schritt für Schritt ein (etwa 8 GB,
  10-20 Minuten). Wird eine frühere Kopie gefunden, werden ihre Modelle, Einstellungen und Stimmen
  wiederverwendet. Öffne AudioTranscriber dann über den Desktop oder das Startmenü. Die Sprache der App
  kannst du jederzeit über den Flaggen-Knopf in der linken Leiste ändern.

LOSLEGEN
  1. Tritt einem Discord-Anruf bei. Discord erscheint unter "ZUHÖREN BEI" (grüner Punkt = spielt Ton ab).
  2. Klicke auf Start. Jeder Satz erscheint mit Sprecher, Uhrzeit, Übersetzung und dem Gehörten.
  3. Die Welle zeigt die Lautstärke. "Auto" folgt dem Hintergrundrauschen jeder Person; ziehe die
     gestrichelte Linie, um sie selbst einzustellen.

DAS FENSTER
  Linke Leiste: Live, Personen, Wörter, Overlay, Overlay sperren, Leeren, Sprachflagge, Einstellungen.
  Rechts: Verzögerung, Grafikkarte, Speicher, Zeilen und die Leute im Anruf.
  Klicke auf einen Namen in einer Zeile, um ihn umzubenennen, die Person zu korrigieren, zwei Personen
  zusammenzulegen, jemanden zu ignorieren oder die Sprache festzulegen, die jemand immer spricht. Jede
  Korrektur macht es genauer.
  "AUS DEM KONTEXT ERRATEN" = die Wörter waren undeutlich und der Übersetzer hat den Sinn erraten.
  Graue Wörter = die Erkennung war sich bei ihnen nicht sicher.

EINSTELLUNGEN (Kategorien links, seltene Optionen unter "Erweitert")
  Erkennung    Sprachmodell und wo es läuft, zu erkennende Sprachen, Satzerkennung, Wörter, die es
               kennen soll (Namen, Spielbegriffe, Slang), Begriffe aus League of Legends.
  Übersetzung  Grafikkarte (lokal, offline), Online - Gemini (Gratis-Schlüssel) oder beides: zuerst
               online, die Grafikkarte als Reserve. Das tägliche Gratislimit von Gemini wird um 09:00
               (italienische Zeit) zurückgesetzt.
  Personen     erkennen, wer spricht, Stimmen merken, die Sprache jeder Person lernen, Liste bekannter
               Personen (Strg/Umschalt + Klick, um mehrere zu wählen, Entf, um sie zu vergessen).
  Discord      Namen und wer spricht direkt aus der Discord-App auf diesem PC (kein Bot), einmalig
               eingerichtet über "So richtest du es ein" (etwa 2 Minuten); Start/Stopp mit deinen Anrufen.
  Overlay & Anzeige  Originaltext, Overlay-Text, Größe, Deckkraft, automatisches Ausblenden, Tastenkürzel.
  App          Sprache der App, Start mit Windows, Zuverlässigkeit, Export, Version.

OVERLAY
  Ein durchsichtiger Kasten über dem Spiel (Fenster- oder randloser Modus; nicht exklusives Vollbild).
  "Overlay verschieben" entsperrt es, damit du es ziehen kannst; nach dem Loslassen sperrt es sich wieder.
  Gesperrt gehen Klicks ans Spiel durch und es blendet sich nach ein paar stillen Sekunden aus.

TASTENKÜRZEL (gehen auch in Spielen)
  Strg+Alt+S Start / Stopp        Strg+Alt+P Pause / weiter       Strg+Alt+C letzte Übersetzung kopieren
  Strg+Alt+O Overlay an / aus     Strg+Alt+L Overlay sperren / entsperren

UPDATES
  Beim Öffnen sucht die App nach einer neueren Version, lädt sie still herunter und startet damit neu
  (wenn du gerade zuhörst, sobald du auf Stopp klickst). Einstellungen, Stimmen, Discord-Anmeldung und
  Modelle bleiben erhalten.

REPARIEREN UND DEINSTALLIEREN
  Reparieren: Einstellungen > Apps > AudioTranscriber > Ändern, oder starte das Setup erneut und wähle
  Reparieren. Es lädt nur, was fehlt; Einstellungen und Stimmen bleiben.
  Deinstallieren: Einstellungen > Apps > AudioTranscriber > Deinstallieren. Es fragt, ob auch die Modelle
  und deine Einstellungen gelöscht werden sollen (etwa 8 GB). Ollama ist ein eigenes Programm mit
  eigenem Deinstallationsprogramm.

DATENSCHUTZ
  Stimmen, Namen, Einstellungen, Schlüssel und die Discord-Anmeldung bleiben nur auf diesem PC. Mit
  eingeschaltetem Gemini wird der Text jedes Satzes (nicht der Ton) zum Übersetzen an Google geschickt.

DATEIEN
  AudioTranscriber.exe  die App              Setup.exe     reparieren        Uninstall.exe  entfernen
  app\                  Programm             models\       Sprach- und Stimmmodelle
  ollama_models\        Übersetzungsmodelle  transcripts\  nur beim Exportieren
  settings.json         deine Einstellungen  speakers.json gespeicherte Stimmen   setup.log  Setup-Protokoll
