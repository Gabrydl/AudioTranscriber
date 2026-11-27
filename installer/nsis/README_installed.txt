AudioTranscriber 1.4.3 - live voice -> Italiano + English (100% local)
====================================================================

START
  Run AudioTranscriber_Setup.exe. It installs everything step by step and shows what it is doing:
  program files, Python, packages, CUDA libraries, Ollama + gemma3:4b, Whisper large-v3-turbo and
  the voice models (about 8 GB, 10-20 minutes). If an earlier copy of AudioTranscriber is found, its
  models, settings and voices are reused instead of downloaded again (no extra disk space on the same drive).
  Then open AudioTranscriber from the desktop or the Start menu.

  Opening it again while it is already running brings the window to the front.
  If the app ever can't start, it tells you why and offers Repair.

REPAIR
  Any of these: open AudioTranscriber and answer Yes to Repair / Settings > Apps > AudioTranscriber >
  Modify / run AudioTranscriber_Setup.exe again and choose Repair. It updates the program files,
  checks every component and downloads only what is missing. Settings and voices are kept.

  AudioTranscriber.exe --repair   open Repair
  AudioTranscriber.exe --debug    same app with a console window (or hold Shift while opening it)

UNINSTALL
  Settings > Apps > AudioTranscriber > Uninstall (or run the setup again and choose Uninstall).
  It asks whether to also delete the downloaded models and your settings (about 8 GB).
  Ollama is a separate program with its own uninstaller.

USE
  - The window (Carbon Pro look): left bar = Live, People, Words to know, Overlay, Lock overlay, Clear,
    Settings. Top: live waveform (drag the dashed line up/down to set the speech level), Auto, Pause,
    translation language, Start/Stop. Right: delay, GPU, memory, lines, and the people in the call.
  - Join a Discord call. Discord appears in "LISTEN TO" (green dot = playing audio).
    Tick one or more apps, press Start.
  - The waveform shows that app's volume. "Auto" follows the background noise of each
    speaker (good for bad mics). Drag the dashed line to set it by hand.
  - Each sentence shows: language, the text, Italian (IT) and English (EN).
    "~ ESTIMATED" = the words were unclear and the translator guessed the meaning
    from context. Hover the text to see what was actually heard.
  - Overlay button: transparent window on top of your game (windowed / borderless games;
    not exclusive full screen). When locked it fades away after a few quiet seconds.
  - Hotkeys (work inside games, can be switched off in Settings):
      Ctrl+Alt+S  start / stop          Ctrl+Alt+P  pause / resume
      Ctrl+Alt+C  copy the last translation
      Ctrl+Alt+O  overlay on/off
      Ctrl+Alt+L  lock overlay (clicks go through to the game) / unlock to move it
  - Speakers: each line shows who spoke (Speaker 1, 2...). Click the name to rename it
    ("Marco"), or fix it ("This is actually...", merge two). Corrections teach it.
    "?" = not sure (very short phrase or unclear voice). Voices are remembered next time
    (speakers.json, only on this PC) - "Forget all voices" in Settings deletes them.
  - Click a name: "Always speaks..." fixes the language of that person (fewer mistakes),
    "Ignore" hides that person. Settings > People shows everyone again.
  - Grey words = the recogniser wasn't sure about them. Unsure words that sound like a name or
    game term you know ("flesh" -> Flash, "Marko" -> Marco) are offered to the translator to fix.
  - Each person's language is learned after a few lines, so short or unclear sentences aren't heard
    in the wrong language (Settings > Speakers > "Learn each person's language").
  - Bisaya (Cebuano): Whisper has no Bisaya model, so it is heard with the Tagalog one and told apart
    from Tagalog by its everyday words (unsa, dili, naa, kaayo...). The translator is told it is Bisaya,
    so it fixes misspellings. Also as a translation language and in "Always speaks…" per person.
  - Updates itself: when the app opens it checks GitHub (Gabrydl/AudioTranscriber); a newer version
    downloads quietly and the app restarts on it (if you are transcribing, as soon as you press Stop).
    Settings, voices, Discord login and models are never touched.
  - Discord names (Settings > Discord names): the app reads who is in your call and who is talking from
    the Discord app on this PC (no bot). Each voice is linked to the Discord account, so names are right
    from the first sentence and the same people are recognised next time. Shown name: display name,
    server nickname or @username. Set up once: "How to set it up" in that section (about 2 minutes).
    Click a name to fix it; "Use the Discord name again" undoes a name you typed.
  - Settings > People list: Ctrl+click / Shift+click to pick several, then Delete or "Forget selected".
  - Short phrases ("gg", "ok", "wait", "vamos") appear at once, without the translator.
  - Noise removal for very bad mics runs on the graphics card when available (installed by Setup).
  - A voice detector decides where sentences start and end: noisy mics no longer keep a sentence
    open, clicks and game sounds don't become fake lines (Settings > Sentence detection).
  - Settings > Words to know: names, game terms, slang. They come out right more often.
  - Settings > Discord: start listening by itself when a call starts, stop when it ends,
    start with Windows (waits in the tray).
  - If you switch headphones or Discord restarts, capture reconnects by itself.
    If it lags, it switches to a lighter speech model (the timer chip turns amber/red when slow).
  - Settings: profiles (Quality / Gaming / CPU only), models, languages, overlay look,
    "Clean up audio" for bad microphones, Export .txt (saved in transcripts\).
  - Nothing is recorded to disk. Audio stays in memory only.

RESOURCES (RTX 2070 8 GB, i7-9700K)
  Quality  : Whisper turbo + gemma3:4b  ~ 5.5-6 GB VRAM, ~2 GB RAM, 1.5-3 s delay
  Gaming   : Whisper small + qwen2.5:3b ~ 3.5 GB VRAM, delay ~1.5-2.5 s
  CPU only : 0 VRAM, ~4 GB RAM, CPU spikes while someone talks, 4-8 s delay
  The GPU only works while someone is talking; it is idle in silence.
  Models load when you press Start (~5-10 s) and are freed when you press Stop.
  Speaker recognition: 3 voice models (~245 MB disk, ~600 MB RAM), run on the CPU in parallel with Whisper.

FILES
  AudioTranscriber.exe   start the app               Setup.exe       repair (copy of the installer)
  Uninstall.exe          removes the app             app\            program
  assets\                icons                       models\         Whisper + voice models
  ollama_models\         translator models           transcripts\    only when you press Export
  settings.json          your settings               setup.log       last setup / repair log
  audiotranscriber.log   app log
