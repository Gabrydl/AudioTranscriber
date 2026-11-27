AudioTranscriber 1.6.0 - live voice transcription and translation
=================================================================

WHAT IT DOES
  It listens to the apps you choose (like Discord), writes down what each person says and translates it
  live into the language you pick. Speech recognition runs on this PC. Translation runs on this PC too,
  or online with Gemini if you turn that on. No account, nothing is recorded to disk.

INSTALL
  Run Setup.exe. The first screen asks the language of the app (your Windows language
  is already selected). Setup installs everything step by step (about 8 GB, 10-20 minutes). If an
  earlier copy is found, its models, settings and voices are reused. Then open AudioTranscriber from the
  desktop or the Start menu. You can change the app language any time with the flag button in the
  left bar.

START
  1. Join a Discord call. Discord appears under "LISTEN TO" (green dot = playing audio).
  2. Press Start. Each sentence appears with who said it, the time, the translation and what was heard.
  3. The waveform shows the volume. "Auto" follows each person's background noise; drag the dashed
     line to set it by hand.
  The headphones button next to Start switches the languages to recognise in one click.

THE WINDOW
  Left bar: Live, People, Words to know, Overlay, Lock overlay, Clear, language flag, Settings.
  Right side: delay, graphics card, memory, lines and the people in the call.
  Click a name on any line to rename it, fix the person, merge two people, ignore someone or fix the
  language they always speak. Every correction makes it more accurate.
  "GUESSED FROM CONTEXT" = the words were unclear and the translator guessed the meaning.
  Grey words = the recogniser wasn't sure about them.

SETTINGS (categories on the left, rare options under "Advanced")
  Recognition  speech model and where it runs, languages to recognise, sentence detection,
               words to know (names, game terms, slang), League of Legends terms.
  Translation  graphics card (local, offline), Online - Gemini (free key), or both: online first,
               the graphics card as backup. The free daily Gemini limit resets at 09:00 (Italy).
  People       recognise who is speaking, remember voices, learn each person's language,
               list of known people (Ctrl/Shift + click to pick several, Delete to forget them).
  Discord      names and who is talking straight from the Discord app on this PC (no bot), set up once
               with "How to set it up" (about 2 minutes); start/stop together with your calls.
  Overlay & display  original text, overlay text, size, opacity, auto-hide, hotkeys.
  App          app language, start with Windows, reliability, export, version.

OVERLAY
  A see-through box on top of your game (windowed or borderless; not exclusive full screen).
  "Move overlay" unlocks it so you can drag it; it locks again by itself after you drop it.
  When locked, clicks go through to the game and it fades away after a few quiet seconds.

HOTKEYS (work inside games)
  Ctrl+Alt+S start / stop        Ctrl+Alt+P pause / resume       Ctrl+Alt+C copy the last translation
  Ctrl+Alt+O overlay on / off    Ctrl+Alt+L lock / unlock the overlay

UPDATES
  When the app opens it checks for a newer version, downloads it quietly and restarts on it (if you are
  listening, as soon as you press Stop). Settings, voices, Discord login and models are kept.

REPAIR AND UNINSTALL
  Repair: Settings > Apps > AudioTranscriber > Modify, or run the setup again and choose Repair.
  It downloads only what is missing; settings and voices are kept.
  Uninstall: Settings > Apps > AudioTranscriber > Uninstall. It asks whether to also delete the models
  and your settings (about 8 GB). Ollama is a separate program with its own uninstaller.

PRIVACY
  Voices, names, settings, keys and the Discord login stay on this PC only. With Gemini turned on, the
  text of each sentence (not the audio) is sent to Google to be translated.

FILES
  AudioTranscriber.exe  the app            Setup.exe     repair         Uninstall.exe  remove
  app\                  program            models\       speech and voice models
  ollama_models\        translator models  transcripts\  only when you press Export
  settings.json         your settings      speakers.json saved voices   setup.log      setup log
