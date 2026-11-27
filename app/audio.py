"""Per-application audio capture (WASAPI process loopback) + volume-based speech segmentation."""
from __future__ import annotations

import logging
import threading
import time
from collections import deque
from dataclasses import dataclass
from typing import Callable, Optional

import numpy as np

log = logging.getLogger("audio")

SR = 16000              # Whisper sample rate
FRAME = 480             # 30 ms frames at 16 kHz

# Apps that are offered even when they are not playing sound right now
KNOWN_APPS = [
    "Discord.exe", "DiscordPTB.exe", "DiscordCanary.exe", "Teams.exe", "ms-teams.exe",
    "Zoom.exe", "ts3client_win64.exe", "TeamSpeak.exe", "Telegram.exe", "WhatsApp.exe",
    "chrome.exe", "msedge.exe", "firefox.exe", "opera.exe", "brave.exe", "Spotify.exe", "vlc.exe",
]


@dataclass
class AppInfo:
    name: str          # e.g. "Discord.exe"
    pid: int           # root process of the tree (capture includes children)
    exe: str           # full path, used for the icon
    active: bool       # currently has an audio session

    @property
    def label(self) -> str:
        return self.name.rsplit(".", 1)[0]


def _root_of(proc):
    """Walk up while the parent has the same exe name (Discord, Chrome… run many processes)."""
    try:
        name = proc.name().lower()
        while True:
            parent = proc.parent()
            if parent is None or parent.name().lower() != name:
                return proc
            proc = parent
    except Exception:
        return proc


def list_audio_apps() -> list[AppInfo]:
    """Apps with an audio session, plus known voice/browser apps that are running."""
    import psutil

    apps: dict[str, AppInfo] = {}
    try:
        from pycaw.pycaw import AudioUtilities
        for s in AudioUtilities.GetAllSessions():
            p = s.Process
            if p is None:
                continue
            try:
                root = _root_of(p)
                key = root.name().lower()
                active = False
                try:
                    active = s.State == 1  # AudioSessionStateActive
                except Exception:
                    pass
                if key in apps:
                    apps[key].active |= active
                    continue
                apps[key] = AppInfo(root.name(), root.pid, root.exe(), active)
            except Exception:
                continue
    except Exception as e:  # pycaw missing / COM error
        log.warning("Audio session enumeration failed: %s", e)

    wanted = {n.lower() for n in KNOWN_APPS}
    for p in psutil.process_iter(["name"]):
        try:
            n = (p.info["name"] or "")
            if n.lower() in wanted and n.lower() not in apps:
                root = _root_of(p)
                apps[n.lower()] = AppInfo(root.name(), root.pid, root.exe(), False)
        except Exception:
            continue

    out = list(apps.values())
    out.sort(key=lambda a: (a.name.lower() not in ("discord.exe", "discordptb.exe", "discordcanary.exe"),
                            not a.active, a.name.lower()))
    return out


class Decimator48:
    """48 kHz mono float32 -> 16 kHz, streaming (keeps filter state between chunks)."""

    def __init__(self):
        from scipy.signal import firwin, lfilter_zi
        self.taps = firwin(95, 7600, fs=48000).astype(np.float64)
        self.zi = lfilter_zi(self.taps, 1.0) * 0.0
        self.phase = 0

    def __call__(self, x: np.ndarray) -> np.ndarray:
        from scipy.signal import lfilter
        if x.size == 0:
            return np.zeros(0, np.float32)
        y, self.zi = lfilter(self.taps, 1.0, x.astype(np.float64), zi=self.zi)
        out = y[self.phase::3]
        self.phase = (self.phase - len(x)) % 3
        return out.astype(np.float32)


class BlockResampler:
    """Any rate -> 16 kHz in 200 ms blocks (only used if Windows refuses 16/48 kHz)."""

    def __init__(self, rate: int):
        from math import gcd
        g = gcd(rate, SR)
        self.up, self.down = SR // g, rate // g
        self.block = rate // 5
        self.buf = np.zeros(0, np.float32)

    def __call__(self, x: np.ndarray) -> np.ndarray:
        from scipy.signal import resample_poly
        self.buf = np.concatenate([self.buf, x])
        outs = []
        while self.buf.size >= self.block:
            blk, self.buf = self.buf[:self.block], self.buf[self.block:]
            outs.append(resample_poly(blk, self.up, self.down).astype(np.float32))
        return np.concatenate(outs) if outs else np.zeros(0, np.float32)


class Downsampler:
    """proc-tap format (48 kHz stereo float32 bytes) -> 16 kHz mono."""

    def __init__(self):
        self.dec = Decimator48()

    def __call__(self, pcm: bytes) -> np.ndarray:
        x = np.frombuffer(pcm, dtype=np.float32)
        if x.size < 2:
            return np.zeros(0, np.float32)
        x = x[: x.size - (x.size % 2)].reshape(-1, 2).mean(axis=1)
        return self.dec(x)


@dataclass
class Utterance:
    source: str
    audio: np.ndarray
    started: float       # wall clock
    peak_db: float


class AppCapture:
    """Captures one app, cuts its audio into utterances using the volume gate."""

    def __init__(self, app: AppInfo, settings, on_utterance: Callable[[Utterance], None],
                 on_level: Callable[[str, float, bool], None]):
        self.app = app
        self.s = settings
        self.on_utterance = on_utterance
        self.on_level = on_level
        self._cap = None
        self._native = None
        self._resamp = None
        self.backend = ""
        self._down = Downsampler()
        self._floor_hist = deque(maxlen=170)   # ~5 s of non-speech frame levels
        self._floor_count = 0
        self.threshold = settings.threshold_db
        self._buf = np.zeros(0, np.float32)
        self._lock = threading.Lock()
        self._pre = deque(maxlen=12)          # 360 ms pre-roll
        self._pre_p = deque(maxlen=12)
        self._speech: list[np.ndarray] = []
        self._probs: list[float] = []         # speech-detector probability of each frame in _speech
        self._voiced_ms = 0
        self._vad_hi = 0
        self._vad = None
        if getattr(settings, "vad_cut", True):
            from .vad import make
            self._vad = make()
        self._in_speech = False
        self._loud_run = 0
        self._quiet_ms = 0
        self._preroll_n = 0
        self._started = 0.0
        self._peak = -120.0
        self._last_level_emit = 0.0
        self.process_specific = True
        self.error: Optional[str] = None

    # ---- lifecycle -------------------------------------------------------
    def start(self):
        # 1) our own WASAPI process-loopback (works on Windows 10 2004+ and 11)
        try:
            from .wasapi_loopback import ProcessLoopback
            self._native = ProcessLoopback(self.app.pid, self._on_native)
            self._native.start()
            self.backend = "wasapi"
            log.info("Capturing %s (pid %s) via WASAPI process loopback", self.app.name, self.app.pid)
            return
        except Exception as e:
            log.warning("Native process loopback failed (%s) – trying proc-tap", e)
            self._native = None
        # 2) fallback: proc-tap library
        from proctap import ProcessAudioCapture
        self._cap = ProcessAudioCapture(self.app.pid, on_data=self._on_data, resample_quality="fast")
        try:
            self.process_specific = bool(self._cap._backend._native.is_process_specific())
        except Exception:
            self.process_specific = True
        self._cap.start()
        self.backend = "proctap"
        log.info("Capturing %s (pid %s) via proc-tap, process-specific=%s", self.app.name, self.app.pid, self.process_specific)

    def alive(self) -> bool:
        """False when the capture thread has died (device change, app restarted…)."""
        try:
            if self._native is not None:
                t = getattr(self._native, "_thread", None)
                return bool(t and t.is_alive())
            if self._cap is not None:
                return True
        except Exception:
            return True
        return False

    def stop(self):
        if self._native:
            try:
                self._native.stop()
            except Exception:
                pass
            self._native = None
        if self._cap:
            try:
                self._cap.stop()
            except Exception:
                pass
            self._cap = None
        with self._lock:
            self._flush(force=True)

    # ---- processing ------------------------------------------------------
    def _on_native(self, mono: np.ndarray, rate: int):
        if rate != SR:
            if self._resamp is None:
                self._resamp = Decimator48() if rate == 48000 else BlockResampler(rate)
            mono = self._resamp(mono)
        self._ingest(mono)

    def _on_data(self, pcm: bytes, _frames: int):
        self._ingest(self._down(pcm))

    def _ingest(self, mono: np.ndarray):
        if mono.size == 0:
            return
        with self._lock:
            self._buf = np.concatenate([self._buf, mono])
            while self._buf.size >= FRAME:
                frame, self._buf = self._buf[:FRAME], self._buf[FRAME:]
                self._process_frame(frame)

    def _process_frame(self, frame: np.ndarray):
        rms = float(np.sqrt(np.mean(frame * frame)) + 1e-9)
        db = 20.0 * np.log10(rms)
        if not self._in_speech:
            self._floor_hist.append(db)
        self._floor_count += 1
        if self.s.auto_threshold:
            if self._floor_count % 15 == 0 and len(self._floor_hist) > 20:
                floor = float(np.percentile(self._floor_hist, 20))
                # noisy mics raise the floor -> threshold follows it, always 12 dB above the hiss
                self.threshold = float(np.clip(floor + 12.0, -62.0, -22.0))
        else:
            self.threshold = self.s.threshold_db
        loud = db > self.threshold
        vad = self._vad
        p = vad.feed(frame) if vad is not None else 1.0
        if vad is not None:
            # quiet voice (bad/low mic) that the volume gate misses, but the detector is sure about
            self._vad_hi = self._vad_hi + 1 if (p >= 0.85 and db > self.threshold - 8.0) else 0
            # inside a sentence a clear voice a bit under the threshold (weaker words, bad mic) keeps it open
            voiced = (loud and p >= 0.3) or self._vad_hi >= 3 or (self._in_speech and p >= 0.6
                                                                    and db > self.threshold - 8.0)
        else:
            voiced = loud

        now = time.time()
        if now - self._last_level_emit > 0.05:
            self._last_level_emit = now
            self.on_level(self.app.name, db, self._in_speech, self.threshold)

        if not self._in_speech:
            self._pre.append(frame)
            self._pre_p.append(p)
            self._loud_run = self._loud_run + 1 if (loud or self._vad_hi >= 3) else 0
            # 60 ms above the threshold AND (with the detector) it really sounds like a voice:
            # clicks, game sounds and mic hiss no longer start a sentence
            if self._loud_run >= 2 and (vad is None or max(list(self._pre_p)[-4:]) >= 0.45):
                self._in_speech = True
                self._speech = list(self._pre)
                self._probs = list(self._pre_p)
                self._preroll_n = len(self._speech) - min(self._loud_run, len(self._speech))
                self._pre.clear()
                self._pre_p.clear()
                self._voiced_ms = 0
                self._quiet_ms = 0
                self._started = now - len(self._speech) * 0.03
                self._peak = db
            return

        self._speech.append(frame)
        self._probs.append(p)
        self._peak = max(self._peak, db)
        if p >= 0.5 and (loud or self._vad_hi >= 3):
            self._voiced_ms += 30
        # with the detector, steady noise above the threshold counts as a pause: the sentence closes
        # when the person stops talking, not when the 9 s limit is reached
        self._quiet_ms = 0 if voiced else self._quiet_ms + 30
        dur = len(self._speech) * 0.03
        if self._quiet_ms >= self.s.silence_ms:
            self._flush()
        elif dur >= self.s.max_utterance_s:
            self._flush(cut_at_quietest=True)

    def _flush(self, force: bool = False, cut_at_quietest: bool = False):
        if not self._speech:
            self._in_speech = False
            return
        frames = self._speech
        probs = self._probs if len(self._probs) == len(frames) else [1.0] * len(frames)
        carry: list[np.ndarray] = []
        carry_p: list[float] = []
        if cut_at_quietest and len(frames) > 60:
            # cut in the last 1.5 s where the detector is least sure it's a voice (= between words),
            # the quietest such frame, so words aren't chopped
            tail = frames[-50:]
            energies = np.array([float(np.mean(f * f)) for f in tail])
            pp = np.array(probs[-50:])
            score = pp + 0.3 * energies / (energies.max() + 1e-12)
            idx = len(frames) - 50 + int(np.argmin(score))
            frames, carry = frames[:idx + 1], frames[idx + 1:]
            carry_p = probs[idx + 1:]
        audio = np.concatenate(frames)
        speech_s = (len(frames) - self._preroll_n) * 0.03 - (self._quiet_ms / 1000.0 if not cut_at_quietest else 0)
        voiced_ok = self._vad is None or self._voiced_ms >= 210 or sum(1 for q in probs if q >= 0.5) * 0.03 >= 0.21
        if not voiced_ok:
            log.debug("%s: %.1fs of sound without a voice - skipped", self.app.name, speech_s)
        elif speech_s >= self.s.min_utterance_s or force and speech_s > 0.3:
            self.on_utterance(Utterance(self.app.name, audio, self._started, self._peak))
        self._preroll_n = 0
        self._voiced_ms = 0
        if carry:
            self._speech = carry
            self._probs = list(carry_p)
            self._started = time.time() - len(carry) * 0.03
            self._quiet_ms = 0
        else:
            self._speech = []
            self._probs = []
            self._in_speech = False
            self._loud_run = 0


def default_output_id() -> str:
    """Id of the Windows default playback device (changes when you switch headphones/speakers)."""
    try:
        from pycaw.pycaw import AudioUtilities
        dev = AudioUtilities.GetSpeakers()
        try:
            return str(dev.GetId())
        except Exception:
            return str(getattr(dev, "id", ""))
    except Exception:
        return ""
