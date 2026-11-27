# AudioTranscriber

Windows app that listens to another app (Discord by default), transcribes what people say and translates it live into the language you pick. Speech recognition runs locally (Whisper). Translation runs on your graphics card (Ollama), online with Google's Gemini API, or both (online first, local as backup).

## What it does
- Live transcription + translation of an app's audio (Discord, games, browsers…), with an in-game overlay
- Recognises Portuguese, Spanish, German, Tagalog, Bisaya (Cebuano), French, English, Czech and Polish (and more)
- Knows who is talking: by voice, and with **Discord names** through Discord's local RPC connection (no bot)
- Learns the language each person usually speaks; League of Legends terms kept as they are
- Voice detector for sentence cutting, noise removal for bad microphones (CPU or graphics card)
- Instant translations for short phrases ("gg", "ok", "wait")
- Carbon Pro dark UI with Settings split into categories, global hotkeys, auto start when a Discord call begins
- Interface in 12 languages: English, Italiano, Português (Brasil / Portugal), Español (España / Latinoamérica), Deutsch, Français, Tagalog, Bisaya, Čeština, Polski. The installer asks (Windows language preselected); the flag button in the app switches it later
- Updates itself from this repo's releases when it opens (settings, voices and models are kept)

## Install
Build the installer (`installer/nsis/AudioTranscriber.nsi`, NSIS 3) or run from source with Python 3.11:
```
pip install -r requirements.txt
python -m app.main
```
The installer sets up Python, the packages, CUDA libraries, Ollama and the models by itself.

## Discord names (optional)
Settings › Discord › *How to set it up*. You create your own Discord application, paste its Client ID and Client Secret and click Authorize in Discord. The secret and the login stay on your PC (`settings.json`, `discord_token.json`) and are never uploaded (see `.gitignore`).

## Translating the interface
Texts live in `app/locales/<language>.txt` (`number|text`, matched to `en.txt` by number) and `readme/README_<language>.txt`; installer texts in `installer/nsis/strings_src.py`. `tools/check_translations.py` asks Gemini (your own key, on your PC) to review them.

## Privacy
Voice prints, names, logs and settings stay on your PC. If you use it in calls, let people know their voice is being transcribed.
