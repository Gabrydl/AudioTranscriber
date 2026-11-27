"""Transcription (faster-whisper) + context-aware correction/translation (local LLM via Ollama)."""
from __future__ import annotations

import glob
import json
import logging
import math
import os
import queue
import re
import site
import sys
import threading
import time
import urllib.request
from dataclasses import dataclass, field
from typing import Callable, Optional

import numpy as np

from .config import MODELS_DIR, LANGUAGES, ROOT

log = logging.getLogger("engine")


# --------------------------------------------------------------------------- CUDA DLLs
def setup_cuda_paths() -> None:
    """Make the pip-installed cuBLAS/cuDNN DLLs visible to CTranslate2 on Windows."""
    if sys.platform != "win32":
        return
    roots = list(site.getsitepackages()) + [site.getusersitepackages()]
    dirs = []
    for r in roots:
        dirs += glob.glob(os.path.join(r, "nvidia", "*", "bin"))
    for d in dirs:
        try:
            os.add_dll_directory(d)
        except Exception:
            pass
    if dirs:
        os.environ["PATH"] = os.pathsep.join(dirs) + os.pathsep + os.environ.get("PATH", "")


# --------------------------------------------------------------------------- data
@dataclass
class Line:
    id: int
    source: str
    lang: str
    text: str                  # raw Whisper text
    confidence: float          # 0..1
    t: float                   # when speech started
    asr_ms: int = 0
    marked: str = ""           # text with low-confidence words marked word(?)
    speaker_id: Optional[int] = None
    speaker_unsure: bool = False
    speaker_score: float = 0.0
    embs: dict = field(default_factory=dict, repr=False)   # voice print (for corrections)
    corrected: str = ""
    estimated: bool = False
    tr: dict = field(default_factory=dict)   # {"it": "...", "en": "..."}
    llm_ms: int = 0
    llm_first_ms: int = 0                    # time until the first Italian words appeared
    speaker_name: str = ""
    usual_lang: str = ""                     # the language this person usually speaks (learned)
    state: str = "transcribed"               # transcribed | streaming | done | llm-off | skipped


HALLUCINATIONS = [
    "thank you for watching", "thanks for watching", "subscribe", "sottotitoli", "amara.org",
    "untertitel", "legendas pela comunidade", "subtítulos realizados por", "napisy stworzone",
    "titulky vytvořil", "sous-titres réalisés", "ご視聴", "www.", ".com",
]


def looks_hallucinated(text: str) -> bool:
    t = text.lower().strip()
    if len(t) < 2:
        return True
    if any(h in t for h in HALLUCINATIONS) and len(t) < 90:
        return True
    words = re.findall(r"\w+", t)
    if len(words) >= 6 and len(set(words)) <= max(2, len(words) // 5):   # "la la la la la la"
        return True
    return False


# --------------------------------------------------------------------------- bad-mic cleanup
_HP_SOS = None

# Neural noise removal (DPDFNet, a DeepFilterNet model, run by sherpa-onnx on the CPU) for really noisy
# mics only. Tested against the old filter on noisy speech: fewer recognition errors at low SNR, but on
# clean or mildly noisy audio no cleanup at all is best for Whisper - so it is used only below ~7 dB SNR.
DENOISE_FILE = "dpdfnet8.onnx"
DENOISE_URL = "https://github.com/k2-fsa/sherpa-onnx/releases/download/speech-enhancement-models/" + DENOISE_FILE
_DN = {"model": None, "tried": False, "lock": threading.Lock(), "downloading": False}


def denoise_path():
    return MODELS_DIR / "denoise" / DENOISE_FILE


def _download_denoiser():
    if _DN["downloading"]:
        return
    _DN["downloading"] = True

    def run():
        path = denoise_path()
        tmp = path.with_suffix(".part")
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            req = urllib.request.Request(DENOISE_URL, headers={"User-Agent": "AudioTranscriber"})
            with urllib.request.urlopen(req, timeout=60) as r, open(tmp, "wb") as f:
                while True:
                    b = r.read(1 << 20)
                    if not b:
                        break
                    f.write(b)
            os.replace(tmp, path)
            _DN["tried"] = False                       # load it at the next noisy sentence
            log.info("Noise removal model downloaded")
        except Exception as e:
            log.warning("Noise removal model download failed: %s", e)
        finally:
            _DN["downloading"] = False
    threading.Thread(target=run, daemon=True, name="denoise-dl").start()


def _denoiser():
    if _DN["model"] is not None or _DN["tried"]:
        return _DN["model"]
    with _DN["lock"]:
        if _DN["model"] is not None or _DN["tried"]:
            return _DN["model"]
        _DN["tried"] = True
        try:
            import sherpa_onnx
            if not hasattr(sherpa_onnx, "OfflineSpeechDenoiserDpdfNetModelConfig"):
                log.info("sherpa-onnx too old for neural noise removal - using the simple filter")
                return None
            path = denoise_path()
            if not path.is_file():
                _download_denoiser()
                return None
            m = sherpa_onnx.OfflineSpeechDenoiserModelConfig(num_threads=max(2, min(4, (os.cpu_count() or 4) // 2)))
            m.dpdfnet.model = str(path)
            _DN["model"] = sherpa_onnx.OfflineSpeechDenoiser(sherpa_onnx.OfflineSpeechDenoiserConfig(model=m))
            log.info("Neural noise removal ready (%s)", DENOISE_FILE)
        except Exception:
            log.exception("noise removal model")
            _DN["model"] = None
    return _DN["model"]


GPU_SHERPA_DIR = ROOT / "gpu" / "sherpa"            # GPU build of sherpa-onnx, installed apart by Setup


class _GpuDenoiser:
    """Noise removal on the graphics card in a helper process (app/denoise_gpu.py). Any problem -> None,
    and the CPU is used instead."""

    def __init__(self):
        self.proc = None
        self.failed = False
        self.lock = threading.Lock()

    def available(self, settings) -> bool:
        if self.failed or not getattr(settings, "denoise_gpu", True):
            return False
        if getattr(settings, "compute", "gpu") == "cpu" or getattr(settings, "whisper_device", "cuda") != "cuda":
            return False
        return GPU_SHERPA_DIR.is_dir() and denoise_path().is_file()

    def _start(self):
        import subprocess
        exe = sys.executable
        if exe.lower().endswith("pythonw.exe"):
            exe = exe[:-len("pythonw.exe")] + "python.exe"
        script = os.path.join(os.path.dirname(os.path.abspath(__file__)), "denoise_gpu.py")
        flags = 0x08000000 if sys.platform == "win32" else 0
        self.proc = subprocess.Popen([exe, "-u", script, str(GPU_SHERPA_DIR), str(denoise_path())],
                                     stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                                     creationflags=flags)
        first = [b""]
        t = threading.Thread(target=lambda: first.__setitem__(0, self.proc.stdout.readline()), daemon=True)
        t.start()
        t.join(90)
        msg = first[0].decode(errors="replace").strip()
        if not msg.startswith("READY"):
            raise RuntimeError(msg or "no answer")
        info = json.loads(msg[6:] or "{}")
        if info.get("ms_per_3s", 9999) > 700:          # that is CPU speed: the card isn't really used
            raise RuntimeError(f"not on the graphics card ({info})")
        log.info("Noise removal on the GPU (%s)", info)

    def __call__(self, x: np.ndarray) -> Optional[np.ndarray]:
        import struct
        with self.lock:
            if self.failed:
                return None
            try:
                if self.proc is None or self.proc.poll() is not None:
                    self._start()
                self.proc.stdin.write(struct.pack("<I", x.size) + x.astype(np.float32).tobytes())
                self.proc.stdin.flush()
                (n,) = struct.unpack("<I", self.proc.stdout.read(4))
                return np.frombuffer(self.proc.stdout.read(n * 4), np.float32).copy()
            except Exception as e:
                log.warning("GPU noise removal unavailable (%s) - using the CPU", e)
                self.failed = True
                self.stop()
                return None

    def stop(self):
        try:
            if self.proc is not None:
                self.proc.kill()
        except Exception:
            pass
        self.proc = None


_GPU_DN = _GpuDenoiser()
_DN_SETTINGS = [None]


def neural_denoise(x: np.ndarray, sr: int = 16000) -> Optional[np.ndarray]:
    st = _DN_SETTINGS[0]
    if st is not None and denoise_path().is_file() and _GPU_DN.available(st):
        y = _GPU_DN(x)
        if y is not None:
            y = y[: x.size]
            if y.size < x.size:
                y = np.pad(y, (0, x.size - y.size))
            return (0.8 * y + 0.2 * x).astype(np.float32)
    dn = _denoiser()
    if dn is None:
        return None
    try:
        with _DN["lock"]:
            y = np.asarray(dn(x.astype(np.float32), sr).samples, np.float32)
        y = y[: x.size]
        if y.size < x.size:
            y = np.pad(y, (0, x.size - y.size))
        return (0.8 * y + 0.2 * x).astype(np.float32)   # a little of the original keeps consonants clear
    except Exception:
        log.exception("neural denoise")
        return None


def enhance(audio: np.ndarray, sr: int = 16000) -> np.ndarray:
    """Make cheap/noisy/quiet/clipping microphones easier for Whisper.

    1. 80 Hz high-pass  – removes hum, desk thumps, breathing rumble
    2. spectral gating  – reduces steady hiss / fan / bad-mic static (kept mild so voices stay natural)
    3. loudness levelling – quiet mics are boosted, loud/clipping ones tamed with a soft limiter
    """
    global _HP_SOS
    from scipy.signal import butter, sosfiltfilt
    x = audio.astype(np.float32)
    if x.size < 1600:
        return x
    if _HP_SOS is None:
        _HP_SOS = butter(4, 80, btype="highpass", fs=sr, output="sos")
    x = sosfiltfilt(_HP_SOS, x).astype(np.float32)
    # Noise removal only when there really is steady noise under the voice: on clean audio
    # (Discord already removes most noise) it blurs consonants and Whisper mishears words.
    fr = x[: x.size - x.size % 320].reshape(-1, 320)
    lv = 20 * np.log10(np.sqrt((fr ** 2).mean(axis=1) + 1e-12))
    snr = float(np.percentile(lv, 90) - np.percentile(lv, 15)) if lv.size >= 10 else 99.0
    done = False
    if snr < 12.0:                                     # very noisy (about 7 dB SNR or worse): neural cleanup
        y = neural_denoise(x, sr)
        if y is not None:
            x, done = y, True
    if snr < 25.0 and not done:
        try:
            import noisereduce as nr
            x = nr.reduce_noise(y=x, sr=sr, stationary=True, prop_decrease=0.45 if snr > 15 else 0.6,
                                n_std_thresh_stationary=1.5, n_jobs=1).astype(np.float32)
        except Exception:
            pass
    # level to about -20 dBFS RMS (measured on the loud part only)
    frames = x[: x.size - x.size % 320].reshape(-1, 320)
    rms = np.sqrt((frames ** 2).mean(axis=1) + 1e-12)
    loud = rms[rms >= np.percentile(rms, 60)]
    level = float(np.mean(loud)) if loud.size else float(np.mean(rms))
    gain = min(0.1 / max(level, 1e-5), 30.0)          # at most +30 dB for very quiet mics
    x = x * gain
    x = np.tanh(x * 1.2) / np.tanh(1.2)                # soft limiter, no hard clipping
    return x.astype(np.float32)


def mark_uncertain(segments, thr: float = 0.45) -> str:
    """Text for the LLM where low-confidence words are marked like this: word(?)"""
    out = []
    for s in segments:
        if not getattr(s, "words", None):
            out.append(s.text.strip())
            continue
        for w in s.words:
            t = w.word.strip()
            if t:
                out.append(f"{t}(?)" if w.probability < thr else t)
    return " ".join(out)


# --------------------------------------------------------------------------- Whisper
class Transcriber:
    def __init__(self, settings, status: Callable[[str], None]):
        self.s = settings
        _DN_SETTINGS[0] = settings
        self.status = status
        self.model = None
        self.device = settings.whisper_device
        self.model_name = settings.whisper_model          # may become lighter while running (lag fallback)
        self._last_lang: dict[str, str] = {}
        self._last_text: dict[str, str] = {}

    def _make(self, device: str, compute: str, **kw):
        from faster_whisper import WhisperModel
        name = self.model_name
        try:      # model already on disk -> skip the online check (faster start, works offline)
            return WhisperModel(name, device=device, compute_type=compute, download_root=str(MODELS_DIR),
                                local_files_only=True, **kw)
        except Exception:
            self.status(f"Downloading '{name}' (one time)…")
            return WhisperModel(name, device=device, compute_type=compute, download_root=str(MODELS_DIR), **kw)

    def load(self):
        MODELS_DIR.mkdir(parents=True, exist_ok=True)
        if self.model_name in BACKGROUND_MODELS and not whisper_on_disk(self.model_name):
            # big model not downloaded yet: start now with the fast one, fetch the big one in the background
            start_background_download(self.model_name, self.status)
            self.model_name = BACKGROUND_MODELS[self.model_name]
        name = self.model_name
        self.status(f"loading '{name}'…")
        t0 = time.time()
        if self.device == "cuda":
            try:
                setup_cuda_paths()
                # full precision (float16, as stored on disk): the most accurate way to run every model.
                # With the big translator, Whisper uses int8 weights (1.7 instead of 3 GB, almost the same
                # accuracy) so more of the translator fits on the graphics card.
                big = (getattr(self.s, "llm_enabled", True) and self.s.llm_model in BIG_LLMS
                       and getattr(self.s, "compute", "gpu") != "cpu")
                self.model = self._make("cuda", "int8_float16" if big else "float16")
                list(self.model.transcribe(np.zeros(16000, np.float32), language="en", beam_size=1)[0])
                log.info("Whisper %s loaded on GPU in %.1fs", name, time.time() - t0)
                self.status(f"'{name}' ready on GPU ({time.time() - t0:.1f}s)")
                return
            except Exception as e:
                log.exception("CUDA load failed")
                self.status(f"GPU failed ({str(e)[:80]}) – falling back to CPU")
                self.device = "cpu"
        self.model = self._make("cpu", "int8", cpu_threads=max(2, (os.cpu_count() or 4) - 2))
        log.info("Whisper %s loaded on CPU in %.1fs", name, time.time() - t0)
        self.status(f"'{name}' ready on CPU ({time.time() - t0:.1f}s)")

    def unload(self):
        """Free VRAM/RAM (called on Stop)."""
        self.model = None
        import gc
        gc.collect()

    def pick_language(self, audio: np.ndarray, source: str, prior_fn=None) -> tuple[str, float]:
        """Language of this clip. prior_fn() -> {lang: share} of the person who is probably talking
        (learned from their earlier lines): short or unclear clips are then read in that person's usual
        language instead of a wrong guess, while a clear switch to another language still wins."""
        allowed = [l for l in self.s.languages if l in LANGUAGES] or ["en"]
        self.skipped_detect = False
        if len(allowed) == 1:
            return allowed[0], 1.0
        quick = None
        if prior_fn is not None and getattr(self.s, "auto_speaker_lang", True):
            try:
                quick = prior_fn(True)                 # known right away (Discord says who is talking)
            except Exception:
                log.exception("language prior")
        if quick and quick.get("__force__") and str(quick["__force__"]) in LANGUAGES:
            self.last_lang_prob = 1.0
            return str(quick["__force__"]), 1.0
        if quick and getattr(self.s, "fast_lang", True) and quick.get("__n__", 0) >= 6:
            top = max(((l, v) for l, v in quick.items() if l in allowed), key=lambda x: x[1], default=None)
            if top and top[1] >= 0.9:
                # this person (known from Discord) practically always speaks this language: skip the
                # separate language pass (a whole extra run of Whisper's encoder). If the sentence then
                # comes out badly, transcribe() checks the language after all.
                self.skipped_detect = True
                self.last_lang_prob = top[1]
                return top[0], top[1]
        _, _, probs = self.model.detect_language(audio)
        pm = {l: p for l, p in probs if l in allowed}
        total = sum(pm.values()) or 1e-9
        pm = {l: p / total for l, p in pm.items()}
        det = max(pm, key=pm.get) if pm else allowed[0]
        prior = quick
        if prior is None and prior_fn is not None and getattr(self.s, "auto_speaker_lang", True):
            try:
                prior = prior_fn(False)
            except Exception:
                log.exception("language prior")
        if prior and prior.get("__force__") and str(prior["__force__"]) in LANGUAGES:
            self.last_lang_prob = pm.get(prior["__force__"], 0.0)
            return str(prior["__force__"]), 1.0
        if prior:
            k = len(allowed)
            mixed = {l: pm.get(l, 0.0) * ((float(prior.get(l, 0.0)) + 0.05) / (1 + 0.05 * k)) ** 0.5 for l in allowed}
            tot = sum(mixed.values()) or 1e-9
            mixed = {l: v / tot for l, v in mixed.items()}
            best = max(mixed, key=mixed.get)
            if best != det:
                log.info("language: heard %s (%.2f) -> %s, this person's usual language", det, pm.get(det, 0), best)
            self.last_lang_prob = pm.get(best, 0.0)
            return best, mixed[best]
        best = det
        last = self._last_lang.get(source)
        # short/ambiguous clips: stick with the language this app was just speaking
        if last and last in pm and pm[best] < 0.55 and pm[last] > 0.2:
            best = last
        self.last_lang_prob = pm.get(best, 0.0)
        return best, pm.get(best, 0.0)

    def vocabulary(self) -> str:
        words = [w.strip() for w in (self.s.vocabulary or []) if str(w).strip()][:80]
        if getattr(self.s, "league_terms", True):
            try:
                from .glossary import hotwords
                have = {w.lower() for w in words}
                words += [w for w in hotwords() if w.lower() not in have]
            except Exception:
                log.exception("League terms")
        out, size = [], 0
        for w in words:                     # Whisper only reads ~200 tokens of hints: your own words come first
            if size + len(w) + 2 > 650:
                break
            out.append(w)
            size += len(w) + 2
        return ", ".join(out)

    def transcribe(self, audio: np.ndarray, source: str, force_lang: Optional[str] = None,
                   cleaned: bool = False, prior_fn=None) -> Optional[tuple]:
        if self.s.enhance_audio and not cleaned:
            try:
                audio = enhance(audio)
            except Exception:
                log.exception("enhance")
        # 0.3 s of silence on both sides: Whisper often drops the first/last word when speech touches the edge
        pad = np.zeros(4800, np.float32)
        audio = np.concatenate([pad, audio.astype(np.float32), pad])
        lang = force_lang if force_lang in LANGUAGES else self.pick_language(audio, source, prior_fn)[0]
        prompt = None          # previous sentences are NOT passed in: Whisper copied old words into new lines
        vocab = self.vocabulary()
        kw = {}
        if vocab:
            kw["hotwords"] = vocab                     # names and game terms the user added
        try:
            segs, _info = self.model.transcribe(
                audio, language=lang, task="transcribe",
                beam_size=8 if self.device == "cuda" else 2, best_of=5, patience=2.0,   # weighs more alternatives
                vad_filter=True, vad_parameters=dict(min_silence_duration_ms=500, threshold=0.3, speech_pad_ms=400),
                condition_on_previous_text=False, initial_prompt=prompt, word_timestamps=True,
                temperature=[0.0, 0.2, 0.4], no_speech_threshold=0.6,
                hallucination_silence_threshold=2.0,      # drops invented text over long silent parts
                **kw,
            )
        except TypeError:                              # older faster-whisper without hotwords
            p2 = (f"{vocab}. " + (prompt or "")).strip() if vocab else prompt
            segs, _info = self.model.transcribe(
                audio, language=lang, task="transcribe",
                beam_size=8 if self.device == "cuda" else 2, best_of=5, patience=2.0,
                vad_filter=True, vad_parameters=dict(min_silence_duration_ms=500, threshold=0.3, speech_pad_ms=400),
                condition_on_previous_text=False, initial_prompt=p2, word_timestamps=True,
                temperature=[0.0, 0.2, 0.4], no_speech_threshold=0.6,
            )
        segs = list(segs)
        keep = [s for s in segs if not (s.no_speech_prob > 0.6 and s.avg_logprob < -0.8)
                and not (s.compression_ratio > 2.6 and s.avg_logprob < -0.5)]      # looping / repeated text
        text = " ".join(s.text.strip() for s in keep).strip()
        if not text or looks_hallucinated(text):
            return None
        conf = math.exp(sum(s.avg_logprob for s in keep) / len(keep))
        if getattr(self, "skipped_detect", False) and force_lang is None and conf < 0.5:
            # the usual language didn't fit this sentence well: check the language after all
            self.skipped_detect = False
            try:
                _, _, probs = self.model.detect_language(audio)
                allowed = [l for l in self.s.languages if l in LANGUAGES]
                pm = {l: p for l, p in probs if l in allowed}
                det = max(pm, key=pm.get) if pm else lang
                if det != lang and pm.get(det, 0) / (sum(pm.values()) or 1) > 0.6:
                    log.info("usual language %s didn't fit (conf %.2f) - heard %s", lang, conf, det)
                    r2 = self.transcribe(audio[4800:-4800], source, force_lang=det, cleaned=True)
                    if r2 and r2[2] > conf:
                        return r2
            except Exception:
                log.exception("language re-check")
        self._last_text[source] = text[-200:]
        words = [(max(0.0, w.start - 0.3), max(0.0, w.end - 0.3), w.word, w.probability)   # undo the padding
                 for sg in keep for w in (sg.words or [])]
        return lang, text, conf, mark_uncertain(keep), words


# --------------------------------------------------------------------------- background model download
BACKGROUND_MODELS = {"large-v3": "large-v3-turbo"}     # big model -> what to use while it downloads
_BG = {"thread": None, "status": None}
_BG_SIZE = {"large-v3": 3.09e9}


def whisper_on_disk(name: str) -> bool:
    try:
        from faster_whisper.utils import download_model
        download_model(name, local_files_only=True, cache_dir=str(MODELS_DIR))
        return True
    except Exception:
        return False


def _downloaded_bytes(name: str) -> int:
    total = 0
    for d in MODELS_DIR.glob(f"models--*--faster-whisper-{name}"):
        for f in (d / "blobs").glob("*"):
            try:
                total += f.stat().st_size
            except OSError:
                pass
    return total


def start_background_download(name: str, status) -> None:
    """Download a Whisper model while the app keeps working; progress goes to the status line."""
    _BG["status"] = status                     # always report to the newest session
    th = _BG["thread"]
    if th is not None and th.is_alive():
        return

    def report(msg):
        try:
            if _BG["status"]:
                _BG["status"](msg)
        except Exception:
            pass

    def run():
        from faster_whisper.utils import download_model
        done = threading.Event()

        def ticker():
            while not done.wait(3.0):
                got = _downloaded_bytes(name) / 1e9
                report(f"using turbo · downloading {name} in the background: {got:.1f} / {_BG_SIZE.get(name, 3e9) / 1e9:.1f} GB")
        threading.Thread(target=ticker, daemon=True).start()
        for attempt in range(1, 4):
            try:
                download_model(name, cache_dir=str(MODELS_DIR))
                done.set()
                log.info("Background download of %s finished", name)
                report(f"{name} downloaded – press Stop and Start to use it")
                return
            except Exception as e:
                log.warning("Background download of %s, attempt %d: %s", name, attempt, e)
                time.sleep(5)
        done.set()
        report(f"{name} could not be downloaded – staying on turbo (check the connection)")

    log.info("Starting background download of %s", name)
    _BG["thread"] = threading.Thread(target=run, daemon=True, name="model-download")
    _BG["thread"].start()


# --------------------------------------------------------------------------- LLM (Ollama)
_LOAD_LOCK = threading.Lock()         # one translator load at a time (quick Stop/Start or switching piled them up)
EXTRA_LLMS = ("gemma3:12b",)
BIG_LLMS = ("gemma3:12b",)            # pushed fully onto the graphics card (falls back to a GPU+CPU split)          # also downloaded (in the background) so they can be picked any time
_LLM_BG: dict = {"status": None}

SYSTEM_PROMPT = """You are a live interpreter for a gaming / Discord voice chat.
The input is speech-to-text output. It often has errors because many speakers have bad
microphones (noise, muffled, clipping, low volume, accents): misheard words, wrong homophones,
cut-off words, wrong language label. Words the recogniser was unsure about are marked word(?).

Translate ONLY "new_line". "recent_conversation" is just background to understand unclear words:
never copy, repeat or translate anything from it, and never add words that are not in new_line.
Work out what the speaker of new_line most likely MEANT (stay close to the sounds, never invent),
and translate exactly that - same length and content as new_line.
Natural spoken style; keep names, game terms and slang (slang -> equivalent slang).

League of Legends terms listed in "game_terms" (champions, summoner spells, items, runes, objectives,
slang): if new_line really uses one, write it EXACTLY as its "term" in both "tr" and "corrected" - the
English game name, never translated or adapted, even when the player said a localized name
(e.g. "destello" -> Flash, "hex flash" -> Hexflash, "filo infinito" -> Infinity Edge). Translate the rest
of the sentence normally. Ignore any game_terms that don't fit what was said.
"game_terms" also lists the user's own names/words, and unsure words(?) that only SOUND like a known
name ("flesh(?)" -> Flash): use such a term only if it makes sense in the sentence.
If "speaker_usually_speaks" is given, this person normally talks in that language: a short line labelled
otherwise may really be that language, misheard.

Reply with JSON only, keys in EXACTLY this order:
{"tr": "%s translation", "corrected": "what they most likely said, in the spoken language", "estimated": true if you had to fix or guess words else false, "lang": "real ISO code of the spoken language", "skip": true only if it is just noise, filler (uh, hm), song lyrics or a subtitle hallucination like "thanks for watching"}"""


TARGET_NAMES = {"en": "English", "it": "Italian", "pt": "Portuguese", "es": "Spanish", "de": "German",
                "fr": "French", "tl": "Tagalog", "cs": "Czech", "pl": "Polish"}


def target_of(settings) -> str:
    t = str(getattr(settings, "target", "en") or "en").lower()
    return t if t in TARGET_NAMES else "en"


def system_prompt(target: str) -> str:
    return SYSTEM_PROMPT.replace('"%s translation"', f'"{TARGET_NAMES[target]} translation"')


_KEY_RE_CACHE: dict = {}


def partial_json_string(buf: str, key: str) -> Optional[str]:
    """Read the (possibly unfinished) string value of `key` from a JSON text that is still being streamed."""
    rx = _KEY_RE_CACHE.get(key)
    if rx is None:
        rx = _KEY_RE_CACHE[key] = re.compile(r'"%s"\s*:\s*"' % re.escape(key))
    m = rx.search(buf)
    if not m:
        return None
    out, i, esc = [], m.end(), False
    while i < len(buf):
        c = buf[i]
        if esc:
            out.append({"n": "\n", "t": "\t", '"': '"', "\\": "\\", "/": "/"}.get(c, c))
            esc = False
        elif c == "\\":
            esc = True
        elif c == '"':
            break
        else:
            out.append(c)
        i += 1
    return "".join(out)


_GENERATION = [0]          # bumped on every Start; an old Stop's unload is skipped if a new Start happened


def find_ollama() -> Optional[str]:
    import shutil
    from pathlib import Path
    cands = [shutil.which("ollama")]
    for root in ("G:\\Ollama", os.path.expandvars(r"%LOCALAPPDATA%\Programs\Ollama"), r"C:\Program Files\Ollama"):
        cands.append(str(Path(root) / "ollama.exe"))
    return next((c for c in cands if c and os.path.exists(c)), None)


def _user_env(name: str) -> Optional[str]:
    """Read a user environment variable from the registry (setx values the app may not have inherited)."""
    try:
        import winreg
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, "Environment") as k:
            return winreg.QueryValueEx(k, name)[0]
    except Exception:
        return None


class Translator:
    def __init__(self, settings, status: Callable[[str], None]):
        self.s = settings
        self.status = status
        self.available = False

    def _req(self, path: str, payload: Optional[dict] = None, timeout: float = 120):
        url = self.s.ollama_url.rstrip("/") + path
        data = json.dumps(payload).encode() if payload is not None else None
        req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
        return urllib.request.urlopen(req, timeout=timeout)

    def _options(self) -> dict:
        o = {"temperature": 0.2, "num_ctx": 2048, "num_predict": 260}
        mode = getattr(self.s, "compute", "gpu")
        if mode == "cpu" or not self.s.llm_on_gpu:
            o["num_gpu"] = 0                      # processor only
        elif mode == "mix":
            o["num_gpu"] = 20                     # about half of the model on the card: leaves room for games
        # "gpu": Ollama puts on the card everything that really fits (forcing more made Windows move it
        # into normal RAM, which is much slower), anything left runs on the processor
        return o

    def gpu_share(self) -> str:
        """How much of the loaded model sits in graphics memory (from Ollama's /api/ps)."""
        try:
            with self._req("/api/ps", timeout=4) as r:
                for m in json.load(r).get("models", []):
                    if m.get("name", "").split(":latest")[0] == self.s.llm_model or m.get("model") == self.s.llm_model:
                        size, vram = m.get("size") or 0, m.get("size_vram") or 0
                        if size:
                            pct = round(vram / size * 100)
                            return f"GPU {pct}%" + (f" / CPU {100 - pct}%" if pct < 100 else "") + f", {vram / 1e9:.1f} GB on the card"
        except Exception:
            pass
        return "GPU" if self.s.llm_on_gpu else "CPU"

    def _tags(self, timeout=4):
        with self._req("/api/tags", timeout=timeout) as r:
            return json.load(r)

    def start_ollama(self) -> bool:
        """Ollama isn't running -> start it hidden and wait until it answers."""
        exe = find_ollama()
        if not exe:
            log.warning("Ollama executable not found")
            return False
        import subprocess
        env = dict(os.environ)
        models = _user_env("OLLAMA_MODELS")
        if models:
            env["OLLAMA_MODELS"] = models
        self.status("starting Ollama…")
        log.info("Starting Ollama: %s", exe)
        flags = 0x08000000 if sys.platform == "win32" else 0          # CREATE_NO_WINDOW
        subprocess.Popen([exe, "serve"], env=env, creationflags=flags,
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        for _ in range(40):                                          # up to ~20 s
            time.sleep(0.5)
            try:
                self._tags(timeout=1)
                return True
            except Exception:
                pass
        return False

    def ensure(self) -> bool:
        try:
            tags = self._tags()
        except Exception:
            if not self.start_ollama():
                self.available = False
                log.warning("Ollama not reachable at %s", self.s.ollama_url)
                self.status("Ollama not running – transcription only (translation off)")
                return False
            tags = self._tags()
        names = {m.get("name", "") for m in tags.get("models", [])}
        want = self.s.llm_model
        if want not in names and f"{want}:latest" not in names:
            self.status(f"Downloading translation model {want} (one time)…")
            try:
                with self._req("/api/pull", {"model": want, "name": want, "stream": True}, timeout=3600) as r:
                    last = 0.0
                    for raw in r:
                        ev = json.loads(raw or b"{}")
                        tot, done = ev.get("total"), ev.get("completed")
                        if tot and done and time.time() - last > 0.5:
                            last = time.time()
                            self.status(f"Downloading {want}: {done / tot * 100:.0f}%  ({tot / 1e9:.1f} GB)")
            except Exception as e:
                self.status(f"Could not download {want}: {e}")
                self.available = False
                return False
        self.available = True
        for extra in EXTRA_LLMS:
            if extra != want and extra not in names:
                self._pull_in_background(extra)
        return True

    def _pull_in_background(self, model: str):
        """Download another translator model while the current one keeps working (progress in the status line)."""
        _LLM_BG["status"] = self.status
        th = _LLM_BG.get(model)
        if th is not None and th.is_alive():
            return

        def run():
            def say(m):
                try:
                    _LLM_BG["status"](m)
                except Exception:
                    pass
            try:
                with self._req("/api/pull", {"model": model, "name": model, "stream": True}, timeout=7200) as r:
                    last = 0.0
                    for raw in r:
                        ev = json.loads(raw or b"{}")
                        tot, done = ev.get("total"), ev.get("completed")
                        if tot and done and time.time() - last > 3:
                            last = time.time()
                            say(f"{self.s.llm_model} ready · downloading {model} in the background: "
                                f"{done / 1e9:.1f} / {tot / 1e9:.1f} GB")
                log.info("Background download of %s finished", model)
                say(f"{model} downloaded – choose it in Settings > Translator model")
            except Exception as e:
                log.warning("Background download of %s failed: %s", model, e)
                say(f"{model} could not be downloaded – it will retry next Start")

        th = threading.Thread(target=run, daemon=True, name=f"pull-{model}")
        _LLM_BG[model] = th
        th.start()

    def loaded_now(self) -> bool:
        """Is this model already in memory (e.g. still there from the last Start)?"""
        try:
            with self._req("/api/ps", timeout=3) as r:
                names = {m.get("name", "") for m in json.load(r).get("models", [])}
            return self.s.llm_model in names or f"{self.s.llm_model}:latest" in names
        except Exception:
            return False

    def load(self):
        """Load the model into VRAM now (empty prompt = load only) and prime the prompt cache.
        Only one load runs at a time; an already loaded model is just reused."""
        with _LOAD_LOCK:
            if self.cancelled():
                return
            if self.loaded_now():
                share = self.gpu_share()
                log.info("LLM %s already loaded (%s)", self.s.llm_model, share)
                self.status(f"{self.s.llm_model} ready ({share})")
                return
            self._load_locked()

    def cancelled(self) -> bool:
        return False                              # replaced by the engine: True after Stop

    def _load_locked(self):
        t0 = time.time()
        self.status(f"loading {self.s.llm_model}…")
        try:
            with self._req("/api/generate", {"model": self.s.llm_model, "prompt": "", "keep_alive": "30m",
                                             "options": self._options()}, timeout=300) as r:
                r.read()
        except Exception as e:
            if getattr(self.s, "compute", "gpu") != "gpu" or getattr(self, "_gpu_fallback", False):
                raise
            # doesn't fit entirely on the card: let Ollama split it between graphics card and processor
            log.warning("%s does not fit fully on the GPU (%s) - using a GPU+CPU split", self.s.llm_model, e)
            self.status(f"{self.s.llm_model} doesn't fit fully on the card – splitting it with the CPU…")
            self._gpu_fallback = True
            with self._req("/api/generate", {"model": self.s.llm_model, "prompt": "", "keep_alive": "30m",
                                             "options": self._options()}, timeout=300) as r:
                r.read()
        try:   # one tiny request so the system prompt is already processed/cached
            self.translate_stream(Line(0, "warmup", "en", "ok", 1.0, time.time()), [], lambda *_: None,
                                  target_of(self.s))
        except Exception:
            pass
        share = self.gpu_share()
        log.info("LLM %s loaded in %.1fs (%s)", self.s.llm_model, time.time() - t0, share)
        self.status(f"{self.s.llm_model} ready ({share}, {time.time() - t0:.1f}s)")

    def unload(self, generation: Optional[int] = None):
        time.sleep(1.5)                                   # let a quick Stop->Start cancel this
        if generation is not None and generation != _GENERATION[0]:
            log.info("Skip unloading %s (a new Start happened)", self.s.llm_model)
            return
        try:
            with self._req("/api/generate", {"model": self.s.llm_model, "keep_alive": 0}, timeout=10) as r:
                r.read()
            log.info("Unloaded %s from VRAM", self.s.llm_model)
        except Exception:
            pass

    def translate_stream(self, line: Line, context: list[Line], on_partial: Callable[[str], None],
                         target: str = "it") -> dict:
        ctx = [{"speaker": c.speaker_name, "lang": c.lang, "text": c.corrected or c.text} for c in context]
        vocab = [w.strip() for w in (self.s.vocabulary or []) if str(w).strip()][:80]
        terms = []
        try:
            from .glossary import find
            # also the user's own words, and unsure words that SOUND like a known name ("flesh(?)" -> Flash)
            terms = find(line.marked or line.text, vocab=vocab, league=getattr(self.s, "league_terms", True))
        except Exception:
            log.exception("glossary")
        user = json.dumps({
            **({"names_and_terms_that_may_appear": vocab} if vocab else {}),
            **({"game_terms": terms} if terms else {}),
            "recent_conversation": ctx,
            "new_line": {"speaker": line.speaker_name, "lang_label": line.lang, "lang_name": LANGUAGES.get(line.lang, line.lang),
                         **({"speaker_usually_speaks": LANGUAGES.get(line.usual_lang, line.usual_lang)}
                            if line.usual_lang and line.usual_lang != line.lang else {}),
                         "asr_text": line.marked or line.text,
                         "asr_confidence": round(line.confidence, 2)},
        }, ensure_ascii=False)
        payload = {
            "model": self.s.llm_model, "stream": True, "format": "json", "keep_alive": "30m",
            "options": self._options(),
            "messages": [{"role": "system", "content": system_prompt(target)},
                         {"role": "user", "content": user}],
        }
        buf = ""
        last = None
        with self._req("/api/chat", payload, timeout=120) as r:
            for raw in r:
                if not raw.strip():
                    continue
                ev = json.loads(raw)
                buf += ev.get("message", {}).get("content", "")
                cur = partial_json_string(buf, "tr")
                if cur != last:
                    last = cur
                    on_partial(cur or "")
                if ev.get("done"):
                    break
        try:
            return json.loads(buf)
        except json.JSONDecodeError:
            m = re.search(r"\{.*\}", buf, re.S)
            try:
                return json.loads(m.group(0)) if m else {}
            except Exception:
                return {"tr": last or ""}


# --------------------------------------------------------------------------- Engine
class Engine:
    """Created on Start, destroyed on Stop (models are loaded/unloaded with it).
    Callbacks are invoked from worker threads."""

    def __init__(self, settings, on_status, on_line, on_update, on_metrics, on_ready=None, registry=None):
        self.s = settings
        self.registry = registry
        self.discord = None                      # DiscordVoice (names + who is talking), set by the window
        self.embedder = None
        self._spk_ready = threading.Event()
        self._pool = None
        self.on_status, self.on_line, self.on_update, self.on_metrics = on_status, on_line, on_update, on_metrics
        self.on_ready = on_ready or (lambda: None)
        self.asr_q: "queue.Queue" = queue.Queue()
        self.llm_q: "queue.Queue" = queue.Queue()
        self.history: list[Line] = []
        self._next_id = 1
        self._stop = threading.Event()
        self.transcriber = Transcriber(settings, lambda m: on_status("asr", m))
        self.translator = Translator(settings, lambda m: on_status("llm", m))
        self.translator.cancelled = lambda: self._stop.is_set()       # a stopped session doesn't load anything
        self._reviving = False
        self._last_revive = 0.0
        self._asr_ready = threading.Event()
        self._llm_ready = threading.Event()
        self.paused = False
        self._recent_ms: list[int] = []
        self._lag_hits = 0

    # lighter models, in order, when transcription can't keep up
    LIGHTER = {"large-v3": "large-v3-turbo", "large-v3-turbo": "small", "medium": "small", "small": "base"}

    def _check_lag(self, ms: int):
        """Too slow for several sentences in a row (or the queue keeps growing) -> lighter Whisper model."""
        if not self.s.auto_lighter:
            return
        self._recent_ms = (self._recent_ms + [ms])[-4:]
        slow = len(self._recent_ms) >= 4 and sum(self._recent_ms) / 4 > self.s.lag_limit_s * 1000
        backlog = self.asr_q.qsize() >= 4
        self._lag_hits = self._lag_hits + 1 if (slow or backlog) else 0
        nxt = self.LIGHTER.get(self.transcriber.model_name)
        if self._lag_hits < 2 or not nxt:
            return
        old = self.transcriber.model_name
        self.on_status("asr", f"lagging ({sum(self._recent_ms) / max(1, len(self._recent_ms)) / 1000:.1f}s) – switching {old} → {nxt}…")
        log.info("Lag fallback: %s -> %s", old, nxt)
        try:
            self.transcriber.unload()
            self.transcriber.model_name = nxt
            self.transcriber.load()
            self.on_metrics("model_switch", 1)
        except Exception:
            log.exception("lag fallback")
            self.transcriber.model_name = old
            self.transcriber.load()
        self._recent_ms, self._lag_hits = [], 0

    def start(self, first_id: int = 1):
        _GENERATION[0] += 1
        self._gen = _GENERATION[0]
        self._next_id = first_id
        self._stop.clear()
        threading.Thread(target=self._asr_loop, daemon=True, name="asr").start()
        threading.Thread(target=self._llm_loop, daemon=True, name="llm").start()
        threading.Thread(target=self._spk_load, daemon=True, name="spk").start()
        threading.Thread(target=self._wait_ready, daemon=True, name="ready").start()

    def _spk_load(self):
        try:
            if self.s.speakers_enabled and self.registry is not None:
                from concurrent.futures import ThreadPoolExecutor
                from .speakers import Embedder
                emb = Embedder(lambda m: self.on_status("spk", m))
                emb.load()
                self.embedder = emb
                self._pool = ThreadPoolExecutor(max_workers=1, thread_name_prefix="voiceprint")
        except Exception as e:
            log.exception("speaker model load")
            self.on_status("spk", f"speaker recognition unavailable: {str(e)[:100]}")
            self.embedder = None
        finally:
            self._spk_ready.set()

    def _wait_ready(self):
        # speaker models load in the background – they never block listening/translating
        self._asr_ready.wait()
        self._llm_ready.wait()
        if not self._stop.is_set():
            self.on_ready()

    def stop(self):
        """Stop and free GPU memory (Whisper + Ollama model)."""
        self._stop.set()
        self.asr_q.put(None)
        self.llm_q.put(None)
        self._asr_ready.set()
        self._llm_ready.set()
        self._spk_ready.set()
        threading.Thread(target=self.translator.unload, args=(self._gen,), daemon=True).start()
        if self._pool:
            self._pool.shutdown(wait=False)
        self.embedder = None

    @property
    def next_id(self) -> int:
        return self._next_id

    def submit(self, utt):
        if self.paused:
            return
        while self.asr_q.qsize() > 6:          # GPU far behind -> drop oldest, stay live
            try:
                self.asr_q.get_nowait()
            except queue.Empty:
                break
        self.asr_q.put(utt)

    # ---------------------------------------------------------------- workers
    def _asr_loop(self):
        try:
            self.transcriber.load()
        except Exception as e:
            log.exception("Whisper load failed")
            self.on_status("asr", f"failed to load: {e}")
            return
        finally:
            self._asr_ready.set()
        while not self._stop.is_set():
            utt = self.asr_q.get()
            if utt is None or self._stop.is_set():
                break
            t0 = time.time()
            emb, pool = self.embedder, self._pool
            fut = pool.submit(emb.analyze, utt.audio) if (emb and pool) else None   # runs on CPU while Whisper uses the GPU
            prior_fn = self._prior_fn(fut, utt)
            try:
                res = self.transcriber.transcribe(utt.audio, utt.source, prior_fn=prior_fn)
            except Exception as e:
                log.exception("transcribe")
                self.on_status("asr", f"transcription error: {e}")
                continue
            analysis = None
            if fut is not None:
                try:
                    analysis = fut.result(timeout=10)
                except Exception:
                    log.exception("voice print")
            ms = int((time.time() - t0) * 1000)
            self.on_metrics("asr_ms", ms)
            if not res or self._stop.is_set():
                self._check_lag(ms)
                continue
            lang, text, conf, marked, words = res
            parts = self._split_by_speaker(utt.audio, text, marked, words, analysis, emb)
            if len(parts) > 1 and self.registry is not None:
                for a, b in zip(parts, parts[1:]):
                    self.registry.note_different(a["embs"], b["embs"])
            prev_sid = None
            for part in parts:
                line = Line(self._next_id, utt.source, lang, part["text"], conf, utt.started + part["t0"],
                            asr_ms=ms, marked=part["marked"])
                self._next_id += 1
                m = None
                dc = self.discord
                in_call = dc is not None and dc.connected and dc.channel_id and self.registry is not None
                if in_call:
                    t0, t1 = utt.started + part["t0"], utt.started + part.get("t1", utt.audio.size / 16000)
                    uid = dc.dominant(t0, t1)
                    if uid:                                        # Discord: exactly this person was talking
                        m = self.registry.assign_discord(uid, dc.members().get(uid) or {}, part["embs"],
                                                         part["speech_s"])
                    elif part["embs"]:
                        talking = [u for u, f in dc.who(t0, t1).items() if f >= 0.15]
                        if talking:                                # several at once: decide by voice among them
                            m = self.registry.identify_among(part["embs"], talking)
                if (m is not None or part["embs"]) and self.registry is not None:
                    excl = {prev_sid} if (len(parts) > 1 and prev_sid is not None) else set()
                    if m is None and in_call:
                        # only people who are in this call
                        members = dc.members()
                        excl |= {sp.id for sp in self.registry.all() if sp.discord_id and sp.discord_id not in members}
                    if m is None:
                        m = self.registry.identify(part["embs"], part["speech_s"], exclude=excl or None)
                    prev_sid = m.speaker_id
                    line.speaker_id, line.speaker_unsure, line.speaker_score = m.speaker_id, m.unsure, m.score
                    line.speaker_name = self.registry.name(m.speaker_id)
                    line.usual_lang = self.registry.lang_of(m.speaker_id) or self.registry.usual_lang(m.speaker_id)
                    line.embs = part["embs"]
                    self._recheck_recent(line)
                    if self.registry.is_ignored(m.speaker_id) and not m.unsure:
                        continue                                   # a person the user chose to ignore
                    lock = self.registry.lang_of(m.speaker_id)
                    if lock and lock != lang and len(parts) == 1 and not m.unsure:
                        # this person always speaks one language: listen again in that language
                        try:
                            r2 = self.transcriber.transcribe(utt.audio, utt.source, force_lang=lock)
                            if r2:
                                line.lang, line.text, line.confidence, line.marked = r2[0], r2[1], r2[2], r2[3]
                        except Exception:
                            log.exception("forced-language transcription")
                self.on_line(line)
                quick_tr = None
                if getattr(self.s, "instant_phrases", True) and line.confidence >= 0.45:
                    try:
                        from .phrases import lookup
                        quick_tr = lookup(line.text, target_of(self.s), line.lang)
                    except Exception:
                        log.exception("phrases")
                if quick_tr is not None:                   # "gg", "ok", "wait"...: no translator needed
                    line.tr = {target_of(self.s): quick_tr}
                    line.corrected = line.text
                    line.state = "done"
                    self.on_update(line)
                    self._remember(line)
                    continue
                if self.s.llm_enabled and not self.translator.available:
                    self._revive_llm()
                if self.s.llm_enabled and (self.translator.available or self._reviving):
                    self.llm_q.put(line)
                else:
                    line.state = "llm-off"
                    self.on_update(line)
                    self._remember(line)
            self._check_lag(int((time.time() - t0) * 1000))
        self.transcriber.unload()

    def _prior_fn(self, fut, utt):
        """For the language choice: who is talking? Discord knows at once; otherwise wait for the voice print
        (computed on the CPU while Whisper detects the language on the GPU). Returns that person's usual
        languages. quick=True: only what is known without waiting."""
        def fn(quick=False):
            if self.registry is None:
                return None
            sid = None
            dc = self.discord
            if dc is not None and dc.connected and dc.channel_id:
                sid = self.registry.by_discord(dc.dominant(utt.started, utt.started + utt.audio.size / 16000))
            if sid is None:
                if quick or fut is None:
                    return None
                try:
                    analysis = fut.result(timeout=4)
                except Exception:
                    return None
                sid = self.registry.guess((analysis or {}).get("embs", {}))
            if sid is None:
                return None
            lock = self.registry.lang_of(sid)
            if lock:
                return {"__force__": lock}
            return self.registry.lang_prior(sid)
        return fn

    def _recheck_recent(self, newest: Line):
        """Lines from the last 2 minutes that were shown with "?" are checked again: as people keep
        talking their voice prints get better, so an early guess is corrected on screen."""
        recent = getattr(self, "_spk_recent", [])
        recent = [l for l in recent if newest.t - l.t <= 120.0]
        for l in recent:
            if not l.speaker_unsure or not l.embs:
                continue
            r = self.registry.recheck(l.embs, l.speaker_id)
            if r is None:
                continue
            sid, score = r
            changed = sid != l.speaker_id
            l.speaker_id, l.speaker_score, l.speaker_unsure = sid, score, False
            l.speaker_name = self.registry.name(sid)
            if changed:
                log.info("line %d re-assigned to %s (%.2f)", l.id, l.speaker_name, score)
            self.on_update(l)
        recent.append(newest)
        self._spk_recent = recent[-60:]

    @staticmethod
    def _words_text(words) -> tuple[str, str]:
        text = "".join(w[2] for w in words).strip()
        marked = " ".join((f"{w[2].strip()}(?)" if w[3] < 0.45 else w[2].strip()) for w in words if w[2].strip())
        return text, marked

    def _split_by_speaker(self, audio, text, marked, words, analysis, emb) -> list[dict]:
        """One sentence -> one or two parts (if the voice changes in the middle)."""
        speech_s = (words[-1][1] - words[0][0]) if words else audio.size / 16000
        whole = {"text": text, "marked": marked, "t0": 0.0, "t1": audio.size / 16000, "speech_s": speech_s,
                 "embs": (analysis or {}).get("embs", {})}
        if not analysis or not analysis.get("windows") or len(words) < 4 or emb is None:
            return [whole]
        from .speakers import find_speaker_changes
        groups, rest = [], list(words)
        for t in find_speaker_changes(analysis["windows"]):
            left = [w for w in rest if (w[0] + w[1]) / 2 < t]
            right = [w for w in rest if (w[0] + w[1]) / 2 >= t]
            if len(left) >= 2 and len(right) >= 2:
                groups.append(left)
                rest = right
        if not groups:
            return [whole]
        groups.append(rest)
        # cut at the silence between the words around each change
        bounds = [0.0] + [(g[-1][1] + n[0][0]) / 2 for g, n in zip(groups, groups[1:])] + [audio.size / 16000]
        parts = []
        for ws, a, b in zip(groups, bounds, bounds[1:]):
            seg = audio[int(a * 16000): int(b * 16000)]
            try:
                embs = emb.embed(seg)
            except Exception:
                embs = whole["embs"]
            tx, mk = self._words_text(ws)
            parts.append({"text": tx, "marked": mk, "t0": a, "t1": b, "speech_s": ws[-1][1] - ws[0][0], "embs": embs})
        log.info("speaker changes inside sentence at %s", ", ".join(f"{b:.2f}s" for b in bounds[1:-1]))
        return parts

    def _llm_loop(self):
        try:
            if self.s.llm_enabled and self.translator.ensure() and not self._stop.is_set():
                self.translator.load()
            elif self.s.llm_enabled:
                log.warning("Translator not available at start")
        except Exception as e:
            log.exception("LLM load")
            self.on_status("llm", f"failed to load: {str(e)[:120]}")
            self.translator.available = False
        finally:
            self._llm_ready.set()
        while not self._stop.is_set():
            line = self.llm_q.get()
            if line is None or self._stop.is_set():
                break
            # translator being (re)started? wait up to 30 s for it
            waited = 0.0
            while self._reviving and waited < 30 and not self._stop.is_set():
                time.sleep(0.25)
                waited += 0.25
            if not self.translator.available:
                line.state = "llm-off"
                self.on_update(line)
                self._remember(line)
                continue
            t0 = time.time()
            last_emit = [0.0]
            tgt = target_of(self.s)                       # read per line: the toggle works while running

            def partial(txt, line=line, tgt=tgt):
                line.tr = {tgt: txt}
                line.state = "streaming"
                now = time.time()
                if now - last_emit[0] > 0.05:          # max ~20 UI updates/s
                    last_emit[0] = now
                    if not line.llm_first_ms and txt:
                        line.llm_first_ms = int((now - t0) * 1000)
                    self.on_update(line)
            data = None
            for attempt in (1, 2):
                try:
                    # only what was said just before (last 20 s, max 3 lines) - older talk confused it
                    ctx = [h for h in self.history if h.state != "skipped" and line.t - h.t <= 20.0][-3:]
                    data = self.translator.translate_stream(line, ctx, partial, tgt)
                    break
                except Exception as e:
                    log.warning("translate attempt %d failed: %s", attempt, e)
                    if attempt == 1:
                        # Ollama closed or crashed -> start it again and retry this line once
                        self.on_status("llm", "translator stopped – restarting Ollama…")
                        self.translator.available = False
                        self._last_revive = 0.0
                        self._revive_llm()
                        waited = 0.0
                        while self._reviving and waited < 30 and not self._stop.is_set():
                            time.sleep(0.25)
                            waited += 0.25
                        if not self.translator.available:
                            break
            if data is None:
                self.on_status("llm", "translation unavailable – Ollama could not be started")
                line.state = "llm-off"
                self.on_update(line)
                self._remember(line)
                continue
            heard = len(line.text.split())
            if data and len(str(data.get("tr") or "").split()) > heard * 2 + 5:
                # translation much longer than what was said -> it mixed in older lines: redo without context
                log.info("translation too long for the heard text - retrying without context")
                try:
                    data = self.translator.translate_stream(line, [], partial, tgt) or data
                except Exception:
                    pass
            line.llm_ms = int((time.time() - t0) * 1000)
            self.on_metrics("llm_ms", line.llm_first_ms or line.llm_ms)
            if data.get("skip") is True:
                line.state = "skipped"
                self.on_update(line)
                continue
            line.corrected = str(data.get("corrected") or line.text).strip()
            heard_n, corr_n = len(line.text.split()), len(line.corrected.split())
            if corr_n > heard_n * 1.5 + 3:                 # grew a lot -> mixed in older lines: keep what was heard
                log.info("corrected text discarded (%d words vs %d heard)", corr_n, heard_n)
                line.corrected = line.text
            line.estimated = bool(data.get("estimated")) and line.corrected.lower() != line.text.lower()
            lang = str(data.get("lang") or line.lang).lower()[:2]
            if lang in LANGUAGES:
                line.lang = lang
            line.tr = {tgt: str(data.get("tr") or line.tr.get(tgt, "")).strip()}
            line.state = "done"
            self.on_update(line)
            self._remember(line)

    def _revive_llm(self):
        """Ollama missing/crashed mid-session -> restart it in the background (at most every 15 s)."""
        now = time.time()
        if not self.s.llm_enabled or self._reviving or now - self._last_revive < 15:
            return
        self._reviving, self._last_revive = True, now

        def run():
            try:
                log.info("Translator unavailable – (re)starting Ollama")
                if self.translator.ensure() and not self._stop.is_set():
                    self.translator.load()
            except Exception:
                log.exception("revive translator")
                self.translator.available = False
            finally:
                self._reviving = False
        threading.Thread(target=run, daemon=True, name="revive-llm").start()

    def switch_translator(self, model: str):
        """Change the translator while running: Whisper stays loaded, the old model leaves the
        graphics card and the new one is loaded (downloaded first if needed)."""
        old = self.s.llm_model
        if not model or model == old:
            return

        def run():
            try:
                try:
                    with self.translator._req("/api/generate", {"model": old, "keep_alive": 0}, timeout=15) as r:
                        r.read()
                    log.info("Unloaded %s (switching translator)", old)
                except Exception:
                    pass
                self.s.llm_model = model
                self.translator._gpu_fallback = False
                self.on_status("llm", f"switching to {model}…")
                if self.translator.ensure() and not self._stop.is_set():
                    self.translator.load()
            except Exception as e:
                log.exception("switch translator")
                self.on_status("llm", f"could not load {model}: {str(e)[:100]}")
        threading.Thread(target=run, daemon=True, name="switch-llm").start()

    def _remember(self, line: Line):
        if (self.registry is not None and line.speaker_id is not None and not line.speaker_unsure
                and line.state in ("done", "llm-off") and len(line.text.split()) >= 2):
            try:
                self.registry.note_lang(line.speaker_id, line.lang)
            except Exception:
                log.exception("note language")
        self.history.append(line)
        if len(self.history) > 500:
            self.history = self.history[-400:]
