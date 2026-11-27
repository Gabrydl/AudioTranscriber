"""Settings, paths and constants for AudioTranscriber."""
from __future__ import annotations

import json
import os
from dataclasses import dataclass, field, asdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent          # G:\AudioTranscriber
MODELS_DIR = ROOT / "models"                            # Whisper models
TRANSCRIPTS_DIR = ROOT / "transcripts"                  # only used by "Export"
SETTINGS_FILE = ROOT / "settings.json"
LOG_FILE = ROOT / "audiotranscriber.log"

# Keep every big download on G:, never on C:
os.environ.setdefault("HF_HOME", str(MODELS_DIR / "hf"))
os.environ.setdefault("HF_HUB_DISABLE_SYMLINKS_WARNING", "1")

# Languages Whisper is allowed to pick from (Whisper codes)
LANGUAGES = {
    "pt": "Portuguese",
    "es": "Spanish",
    "de": "German",
    "tl": "Tagalog",
    "fr": "French",
    "en": "English",
    "cs": "Czech",
    "pl": "Polish",
    "it": "Italian",
    "ceb": "Bisaya (Cebuano)",
}
DEFAULT_LANGS = ["pt", "es", "de", "tl", "fr", "en", "cs", "pl", "ceb"]
# languages Whisper has no token for: recognised with the closest one, then labelled by their own words
WHISPER_CODE = {"ceb": "tl"}
AUSTRONESIAN = ("tl", "id", "ms", "jw", "su", "haw", "mi")   # where Whisper puts Bisaya speech

WHISPER_MODELS = {
    "large-v3": "max accuracy · ~3 GB VRAM (1.7 GB next to gemma3:12b) · slower",
    "large-v3-turbo": "fast and very good · ~1.6 GB VRAM",
    "medium": "good · ~1.5 GB",
    "small": "light · ~0.8 GB",
    "base": "tiny · ~0.3 GB",
}

LLM_MODELS = {
    "gemma3:4b": "Recommended – best multilingual (≈3.5–4 GB VRAM)",
    "qwen2.5:3b": "Lighter (≈2.5 GB VRAM)",
    "gemma3:12b": "Highest quality – slower: 5–15 s per translation on 8 GB cards (≈8 GB, partly on the CPU)",
}

# Where the models run (Settings > "Run on")
COMPUTE_MODES = {
    "gpu": "GPU – everything on the graphics card (fastest)",
    "mix": "Mix – graphics card + CPU (for models bigger than the card)",
    "cpu": "CPU only – no graphics card (slow)",
}

# old presets (no longer shown)
PROFILES = {
    "Max quality": dict(whisper_model="large-v3", whisper_device="cuda", llm_model="gemma3:12b", llm_on_gpu=True),
    "Quality":   dict(whisper_model="large-v3", whisper_device="cuda", llm_model="gemma3:4b",  llm_on_gpu=True),
    "Gaming":    dict(whisper_model="small",          whisper_device="cuda", llm_model="qwen2.5:3b", llm_on_gpu=True),
    "CPU only":  dict(whisper_model="small",          whisper_device="cpu",  llm_model="qwen2.5:3b", llm_on_gpu=False),
}


@dataclass
class Settings:
    whisper_model: str = "large-v3"
    whisper_device: str = "cuda"          # cuda | cpu
    llm_model: str = "gemma3:4b"
    llm_on_gpu: bool = True
    llm_enabled: bool = True
    ollama_url: str = "http://127.0.0.1:11434"
    languages: list = field(default_factory=lambda: list(DEFAULT_LANGS))
    targets: list = field(default_factory=lambda: ["it", "en"])   # old setting, not used any more
    target: str = "en"                    # the one language translations appear in: en | it

    # Volume gate
    auto_threshold: bool = True           # follow each app's noise floor (noisy mics)
    threshold_db: float = -45.0           # manual level that counts as "someone talking"
    silence_ms: int = 650                 # pause that closes a sentence
    max_utterance_s: float = 9.0          # force-cut long monologues
    min_utterance_s: float = 0.45

    # Bad-microphone handling
    enhance_audio: bool = True            # high-pass + noise reduction + loudness normalisation

    # Speaker recognition
    speakers_enabled: bool = True
    speaker_separation: float = 0.5       # 0 = merge more, 1 = split more
    remember_speakers: bool = True        # keep voice prints in speakers.json (this PC only)

    # Display
    show_original: bool = True
    context_lines: int = 6
    overlay_enabled: bool = False
    overlay_opacity: float = 0.82
    overlay_font: int = 15
    overlay_lines: int = 4
    overlay_geometry: list = field(default_factory=lambda: [80, 80, 720, 260])
    overlay_locked: bool = False
    last_apps: list = field(default_factory=lambda: ["Discord.exe"])

    # 1.1 – accuracy
    vocabulary: list = field(default_factory=list)   # names, game terms, slang the recogniser should know
    mark_unsure: bool = True              # unsure words shown in grey in the feed
    # 1.2 – recognition
    vad_cut: bool = True                  # speech detector decides where sentences start/end (not volume only)
    auto_speaker_lang: bool = True        # learn the language each person usually speaks and prefer it
    fast_lang: bool = True                # skip the separate language pass when the person's language is certain
    instant_phrases: bool = True          # "gg", "ok", "wait"...: translated at once, without the translator
    denoise_gpu: bool = True              # noise removal for bad mics on the graphics card (falls back to CPU)
    # 1.3 – Discord names (local RPC connection to the Discord app, with the user's own Discord application)
    discord_enabled: bool = False
    discord_client_id: str = ""
    discord_client_secret: str = ""
    discord_name: str = "display"         # display | nick | username
    discord_fresh_done: bool = False      # old voices were moved to speakers_before_discord.json once
    bisaya_added: bool = False            # 1.4.2: Bisaya added once to the recognised languages
    overlay_time: bool = True             # time stamp in front of each overlay line
    # 1.1 – control
    hotkeys_enabled: bool = True          # Ctrl+Alt+S start/stop · P pause · C copy · O overlay · L lock
    overlay_show_original: bool = False   # overlay: heard text above the translation
    overlay_autohide_s: int = 8           # overlay fades out after this many silent seconds (0 = never)
    overlay_text_opacity: float = 1.0
    # 1.1 – reliability
    device_recover: bool = True           # restart capture when headphones / output device change
    auto_lighter: bool = True             # switch to a lighter Whisper model when it lags
    lag_limit_s: float = 6.0
    # 1.1 – Discord
    auto_start: bool = False              # start listening when a Discord call starts
    auto_stop: bool = True                # ...and stop when it ends
    start_with_windows: bool = False
    quality_v2: bool = False
    league_terms: bool = True
    quality_v3: bool = False
    compute: str = ""
    fix_v4: bool = False                  # one-time reset of values changed by accidental scrolling                     # gpu | mix | cpu  ("" = derive from the old settings once)              # one-time switch to the automatic volume threshold             # League of Legends glossary: recognition hints + keep game terms untranslated              # one-time switch to the max-accuracy setup (large-v3)

    @classmethod
    def load(cls) -> "Settings":
        s = cls()
        try:
            data = json.loads(SETTINGS_FILE.read_text(encoding="utf-8"))
            for k, v in data.items():
                if hasattr(s, k):
                    setattr(s, k, v)
        except Exception:
            pass
        if not s.quality_v2:                  # one time: highest-quality speech model + matching lag limit
            if s.whisper_model in ("large-v3-turbo", "medium"):
                s.whisper_model = "large-v3"
            s.lag_limit_s = max(float(s.lag_limit_s or 0), 6.0)
            s.quality_v2 = True
            s.save()
        if s.compute not in ("gpu", "mix", "cpu"):
            s.compute = "cpu" if s.whisper_device == "cpu" else ("gpu" if s.llm_on_gpu else "mix")
            s.save()
        if not s.fix_v4:
            s.overlay_lines = max(int(s.overlay_lines or 4), 4)
            s.lag_limit_s = max(float(s.lag_limit_s or 6), 6.0)
            s.speaker_separation = max(float(s.speaker_separation), 0.5)
            s.silence_ms = 650
            s.auto_threshold = True
            s.fix_v4 = True
            s.save()
        if not s.quality_v3:
            s.auto_threshold = True
            s.quality_v3 = True
            s.save()
        return s

    def save(self) -> None:
        try:
            SETTINGS_FILE.write_text(json.dumps(asdict(self), indent=2), encoding="utf-8")
        except Exception:
            pass
