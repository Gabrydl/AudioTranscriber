"""Speaker recognition: who said each sentence.

Accuracy measures
- Three independent voice-print models, scores fused:
    WeSpeaker ResNet293-LM (best WeSpeaker model on VoxCeleb), NVIDIA TitaNet-large, WeSpeaker CAM++-LM.
- Silence is cut out before a voice print is taken (pauses carry no voice information).
- A speaker is compared against a running average AND their best recent samples.
- Only confident sentences (long enough, clear match) update a speaker's voice print.
- Short or ambiguous sentences are shown with "?" instead of creating fake new speakers.
- Long sentences are checked for a change of speaker in the middle and split at the word boundary.
- You can correct any line (rename / "this is actually…" / merge); corrections teach the model.
- Voices are remembered between sessions (speakers.json, stored only on this PC).
"""
from __future__ import annotations

import json
import logging
import threading
from dataclasses import dataclass, field
from typing import Optional

import numpy as np

from .config import MODELS_DIR, ROOT

log = logging.getLogger("speakers")

SR = 16000
HF_REPO = "csukuangfj/speaker-embedding-models"
MODELS = {                                   # name -> (file, weight in the fused score)
    "r293": ("wespeaker_en_voxceleb_resnet293_LM.onnx", 0.45),
    "titanet": ("nemo_en_titanet_large.onnx", 0.30),
    "campp": ("wespeaker_en_voxceleb_CAM++_LM.onnx", 0.25),
}
WINDOW_MODEL = "campp"                       # fast model for detecting a speaker change mid-sentence
MAX_EMBED_S = 8.0                            # longer speech adds no accuracy, only time
SPEAKERS_FILE = ROOT / "speakers.json"
MAX_SAMPLES = 40


def _norm(v: np.ndarray) -> np.ndarray:
    v = np.asarray(v, np.float32)
    return v / (np.linalg.norm(v) + 1e-9)


def speech_only(audio: np.ndarray) -> np.ndarray:
    """Drop silent 20 ms frames so the voice print only contains voice."""
    f = 320
    n = audio.size - audio.size % f
    if n < f * 10:
        return audio
    frames = audio[:n].reshape(-1, f)
    db = 20 * np.log10(np.sqrt((frames ** 2).mean(axis=1)) + 1e-9)
    keep = db > max(db.max() - 30.0, -58.0)
    if keep.sum() < 15:
        return audio
    return frames[keep].reshape(-1)


# --------------------------------------------------------------------------- download
def download_model_file(fname: str, path, status, tries: int = 3):
    """Plain HTTPS download with progress, timeout and retries (no progress-bar libraries)."""
    import time
    import urllib.request
    url = f"https://huggingface.co/{HF_REPO}/resolve/main/{fname}"
    part = path.with_suffix(path.suffix + ".part")
    last_err = None
    for attempt in range(1, tries + 1):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "AudioTranscriber"})
            with urllib.request.urlopen(req, timeout=30) as r, open(part, "wb") as f:
                total = int(r.headers.get("Content-Length") or 0)
                done, t_last = 0, 0.0
                while True:
                    chunk = r.read(1 << 20)
                    if not chunk:
                        break
                    f.write(chunk)
                    done += len(chunk)
                    if time.time() - t_last > 0.5:
                        t_last = time.time()
                        pct = f"{done / total * 100:.0f}%" if total else f"{done / 1e6:.0f} MB"
                        status(f"downloading {pct} (one time)")
            if total and done != total:
                raise IOError(f"incomplete download ({done}/{total} bytes)")
            part.replace(path)
            log.info("Downloaded %s (%.1f MB)", fname, done / 1e6)
            return
        except Exception as e:
            last_err = e
            log.warning("Download %s attempt %d failed: %s", fname, attempt, e)
            status(f"download failed, retrying ({attempt}/{tries})…")
            time.sleep(2)
    raise last_err


# --------------------------------------------------------------------------- embeddings
class Embedder:
    """Wraps the sherpa-onnx voice-print models (CPU – runs in parallel with Whisper on the GPU)."""

    def __init__(self, status=lambda m: None):
        from concurrent.futures import ThreadPoolExecutor
        self.status = status
        self.ext: dict = {}
        self._locks = {k: threading.Lock() for k in MODELS}
        self._pool = ThreadPoolExecutor(max_workers=len(MODELS), thread_name_prefix="emb")

    def load(self):
        import sherpa_onnx
        d = MODELS_DIR / "speaker"
        d.mkdir(parents=True, exist_ok=True)
        for key, (fname, _) in MODELS.items():
            path = d / fname
            try:
                if not path.exists():
                    download_model_file(fname, path, lambda m, k=key: self.status(f"voice model {k}: {m}"))
                cfg = sherpa_onnx.SpeakerEmbeddingExtractorConfig(model=str(path), num_threads=3, provider="cpu")
                self.ext[key] = sherpa_onnx.SpeakerEmbeddingExtractor(cfg)
            except Exception as e:
                log.exception("voice model %s", key)
                self.status(f"voice model {key} unavailable ({str(e)[:60]}) – using the others")
        if not self.ext:
            raise RuntimeError("no voice model could be loaded")
        log.info("Speaker models loaded: %s", list(self.ext))
        self.status(f"speaker recognition ready ({len(self.ext)} voice models)")

    def unload(self):
        self.ext = {}
        self._pool.shutdown(wait=False)

    def _one(self, key: str, audio: np.ndarray) -> np.ndarray:
        ex = self.ext[key]
        with self._locks[key]:
            st = ex.create_stream()
            st.accept_waveform(sample_rate=SR, waveform=audio.astype(np.float32))
            st.input_finished()
            return _norm(np.array(ex.compute(st), np.float32))

    def embed(self, audio: np.ndarray, keys=None) -> dict:
        """All models in parallel (one CPU thread group each)."""
        audio = speech_only(audio)
        cap = int(MAX_EMBED_S * SR)
        if audio.size > cap:                       # keep the middle part
            start = (audio.size - cap) // 2
            audio = audio[start:start + cap]
        keys = list(keys or self.ext)
        futs = {k: self._pool.submit(self._one, k, audio) for k in keys}
        return {k: f.result() for k, f in futs.items()}

    def _windows(self, audio: np.ndarray) -> list:
        out, win, hop, t = [], 1.5, 0.5, 0.0
        dur = audio.size / SR
        while t + win <= dur + 1e-6:
            seg = audio[int(t * SR): int((t + win) * SR)]
            if np.sqrt(np.mean(seg ** 2)) > 1e-3:
                out.append((t, t + win, self._one(WINDOW_MODEL, seg)))
            t += hop
        return out

    def analyze(self, audio: np.ndarray) -> dict:
        """Whole-sentence voice print + sliding windows (for detecting a speaker change mid-sentence).
        Windows are computed at the same time as the big models, so they add no delay."""
        out = {"embs": {}, "windows": []}
        win_result = []
        th = None
        if audio.size / SR >= 2.2:
            th = threading.Thread(target=lambda: win_result.extend(self._windows(audio)), daemon=True)
            th.start()
        out["embs"] = self.embed(audio)
        if th:
            th.join()
            out["windows"] = win_result
        return out


# --------------------------------------------------------------------------- registry
@dataclass
class Speaker:
    id: int
    name: str
    samples: dict = field(default_factory=dict)       # model -> list[np.ndarray]
    lang: str = ""                                    # language lock ("" = detect every time)
    ignored: bool = False                             # lines from this voice are not shown
    self_scores: list = field(default_factory=list)   # how well this voice usually matches itself
    langs: list = field(default_factory=list)         # languages of this person's recent lines (learned automatically)
    discord_id: str = ""                              # linked Discord account (stays the same across sessions)
    discord_names: dict = field(default_factory=dict) # {"display", "nick", "username"} as Discord last reported
    name_custom: bool = False                         # the user typed this name: Discord names don't replace it

    def centroid(self, key: str) -> Optional[np.ndarray]:
        s = self.samples.get(key)
        return _norm(np.mean(s, axis=0)) if s else None

    def add(self, embs: dict):
        for k, v in embs.items():
            lst = self.samples.setdefault(k, [])
            lst.append(np.asarray(v, np.float32))
            if len(lst) > MAX_SAMPLES:
                del lst[0]

    def count(self) -> int:
        return max((len(v) for v in self.samples.values()), default=0)

    def note_score(self, sc: float):
        self.self_scores = (self.self_scores + [float(sc)])[-30:]

    def stats(self) -> Optional[tuple[float, float]]:
        if len(self.self_scores) < 5:
            return None
        return float(np.mean(self.self_scores)), float(np.std(self.self_scores))

    def new_threshold(self, new_t: float) -> float:
        """Below this it is someone else. Judged against how well this voice usually matches ITSELF:
        on Discord different people still score high, but clearly lower than a person scores with
        themselves."""
        st = self.stats()
        if st is None:
            return new_t
        m, sd = st
        return float(np.clip(m - max(2.5 * sd, 0.06), new_t, 0.9))

    def can_learn(self, score: float, match_t: float) -> bool:
        """Only clear matches go into the voice print, so it never becomes a blend of several people."""
        st = self.stats()
        if st is None:
            return score >= max(match_t + 0.1, 0.72)
        m, sd = st
        return score >= m - max(1.5 * sd, 0.04)

    def own_threshold(self, match_t: float, new_t: float) -> float:
        """Voices on a bad mic match themselves less well: accept them a bit lower (never below new_t)."""
        if len(self.self_scores) < 5:
            return match_t
        m, sd = float(np.mean(self.self_scores)), float(np.std(self.self_scores))
        return float(np.clip(min(match_t, m - 1.5 * sd), new_t + 0.03, match_t))


@dataclass
class Match:
    speaker_id: int
    score: float
    unsure: bool
    new: bool


class SpeakerRegistry:
    """Thread-safe store of known voices. Lives for the whole app session (not tied to Start/Stop)."""

    def __init__(self, settings):
        self.s = settings
        self.speakers: dict[int, Speaker] = {}
        self._next = 1
        # how alike two DIFFERENT people sound on these calls (measured on lines where the voice changed)
        self.impostor: list[float] = []
        self.lock = threading.RLock()
        if settings.remember_speakers:
            self.load()

    # ---------------- thresholds (slider "separation": 0 = merge more, 1 = split more)
    def thresholds(self) -> tuple[float, float]:
        sep = float(self.s.speaker_separation)
        match = 0.42 + 0.30 * sep          # >= match  -> confidently this speaker
        new = match - 0.10                  # <  new    -> a different, new speaker
        if len(self.impostor) >= 3:
            # Discord audio makes different people look alike: the "same person" bar must sit above
            # the similarity measured between people who really are different
            imp = float(np.percentile(self.impostor, 75)) + 0.06 * (sep - 0.5) * 2
            new = max(new, imp + 0.03)
            match = max(match, new + 0.08)
        return min(match, 0.92), min(new, 0.86)

    @staticmethod
    def similarity(a: dict, b: dict) -> float:
        total, wsum = 0.0, 0.0
        for k, v in a.items():
            if k in b:
                w = MODELS.get(k, ("", 1.0))[1]
                total += w * float(np.dot(v, b[k]))
                wsum += w
        return total / wsum if wsum else 0.0

    def note_different(self, a: dict, b: dict):
        """Two parts of one line where the voice changed: a sample of how alike different people score."""
        if a and b:
            with self.lock:
                self.impostor = (self.impostor + [self.similarity(a, b)])[-60:]

    # ---------------- scoring
    def _score(self, sp: Speaker, embs: dict) -> float:
        total, wsum = 0.0, 0.0
        for k, v in embs.items():
            c = sp.centroid(k)
            if c is None:
                continue
            samples = sp.samples[k]
            sims = sorted((float(np.dot(v, x)) for x in samples), reverse=True)[:3]
            sc = 0.6 * float(np.dot(v, c)) + 0.4 * float(np.mean(sims))
            w = MODELS.get(k, ("", 1.0))[1]
            total += w * sc
            wsum += w
        return total / wsum if wsum else -1.0

    def scores(self, embs: dict) -> list[tuple[int, float]]:
        with self.lock:
            out = [(sid, self._score(sp, embs)) for sid, sp in self.speakers.items()]
        return sorted(out, key=lambda x: -x[1])

    def identify(self, embs: dict, speech_s: float, exclude: Optional[set] = None) -> Match:
        """exclude: speakers this voice can't be (e.g. the person who spoke the other half of the line)."""
        match_t, new_t = self.thresholds()
        with self.lock:
            sc = [x for x in self.scores(embs) if not exclude or x[0] not in exclude]
            best_id, best = sc[0] if sc else (None, -1.0)
            second = sc[1][1] if len(sc) > 1 else -1.0
            reliable = speech_s >= 1.0
            log.info("speaker scores %s (dur %.1fs)", [(i, round(s, 3)) for i, s in sc[:4]], speech_s)
            # a new person only from a clear sentence (>= 1.5 s): short clips give shaky voice prints
            # and used to create fake extra speakers. A part of a line where the voice changed is
            # known to be someone else, so 1 s is enough there.
            need = 1.0 if exclude else 1.5
            bar = self.speakers[best_id].new_threshold(new_t) if best_id is not None else new_t
            if best_id is None or (best < bar and speech_s >= need):
                sp = self._create(embs)
                return Match(sp.id, 1.0, unsure=speech_s < need, new=True)
            sp = self.speakers[best_id]
            unsure = best < sp.own_threshold(match_t, new_t) or not reliable or (best - second) < 0.05
            if not unsure and speech_s >= 1.5 and sp.can_learn(best, match_t):
                sp.add(embs)                              # learn from clear matches only
                sp.note_score(best)
            return Match(best_id, best, unsure=unsure, new=False)

    def recheck(self, embs: dict, current: Optional[int]) -> Optional[tuple[int, float]]:
        """Re-score an earlier unsure line now that the voices are better known.
        Returns (speaker, score) when it is now a confident match, else None."""
        match_t, new_t = self.thresholds()
        with self.lock:
            sc = self.scores(embs)
            if not sc:
                return None
            best_id, best = sc[0]
            second = sc[1][1] if len(sc) > 1 else -1.0
            sp = self.speakers.get(best_id)
            if sp and best >= sp.own_threshold(match_t, new_t) and best - second >= 0.08:
                return best_id, best
        return None

    # ---------------- corrections from the UI
    def _create(self, embs: dict, name: str = "") -> Speaker:
        sid = self._next
        self._next += 1
        sp = Speaker(sid, name or f"Speaker {sid}")
        if embs:
            sp.add(embs)
        self.speakers[sid] = sp
        return sp

    def name(self, sid: Optional[int]) -> str:
        sp = self.speakers.get(sid) if sid is not None else None
        if not sp:
            return "?"
        if sp.discord_id and sp.discord_names and not sp.name_custom:
            from .discord_rpc import pick_name
            return pick_name(sp.discord_names, getattr(self.s, "discord_name", "display")) or sp.name
        return sp.name

    def rename(self, sid: int, name: str):
        with self.lock:
            if sid in self.speakers and name.strip():
                self.speakers[sid].name = name.strip()
                self.speakers[sid].name_custom = True
        self.save()

    def use_discord_name(self, sid: int):
        with self.lock:
            sp = self.speakers.get(sid)
            if sp:
                sp.name_custom = False
        self.save()

    # ---------------- Discord accounts
    def by_discord(self, uid: Optional[str]) -> Optional[int]:
        if not uid:
            return None
        for sp in self.speakers.values():
            if sp.discord_id == uid:
                return sp.id
        return None

    def discord_of(self, sid: Optional[int]) -> str:
        sp = self.speakers.get(sid) if sid is not None else None
        return sp.discord_id if sp else ""

    def update_discord_names(self, members: dict) -> bool:
        """Discord reported names for the people in the call: keep the saved ones up to date."""
        changed = False
        with self.lock:
            for sp in self.speakers.values():
                n = members.get(sp.discord_id) if sp.discord_id else None
                if n and n != sp.discord_names:
                    sp.discord_names = dict(n)
                    sp.name = n.get("display") or sp.name
                    changed = True
        if changed:
            self.save()
        return changed

    def assign_discord(self, uid: str, names: dict, embs: dict, speech_s: float) -> Match:
        """Discord says exactly this person was talking: use (or create) their speaker and learn the voice."""
        with self.lock:
            sid = self.by_discord(uid)
            new = sid is None
            if new:
                sp = self._create({}, (names or {}).get("display") or "")
                sp.discord_id = uid
                sp.discord_names = dict(names or {})
                sid = sp.id
                log.info("new Discord person %s (%s)", sp.discord_names.get("display"), uid)
            sp = self.speakers[sid]
            if names and names != sp.discord_names:
                sp.discord_names = dict(names)
            score = self._score(sp, embs) if (embs and sp.count()) else 1.0
            if embs and speech_s >= 1.0:
                sp.add(embs)                              # Discord is the truth: always learn from it
                if sp.count() > 1:
                    sp.note_score(score)
        self.save()
        return Match(sid, float(score), unsure=False, new=new)

    def identify_among(self, embs: dict, uids: list) -> Optional[Match]:
        """Several people (or nobody, per Discord) were talking: pick by voice among these accounts."""
        match_t, new_t = self.thresholds()
        with self.lock:
            cands = [(self.by_discord(u), u) for u in uids]
            scored = [(sid, self._score(self.speakers[sid], embs)) for sid, _ in cands
                      if sid is not None and self.speakers[sid].count()]
        if not scored:
            return None
        scored.sort(key=lambda x: -x[1])
        sid, best = scored[0]
        second = scored[1][1] if len(scored) > 1 else -1.0
        sp = self.speakers[sid]
        unsure = best < sp.own_threshold(match_t, new_t) or best - second < 0.05
        return Match(sid, best, unsure=unsure, new=False)

    def start_fresh(self, backup) -> int:
        """Discord names are on for the first time: the old voices are moved to a backup file."""
        n = len(self.speakers)
        try:
            if SPEAKERS_FILE.exists():
                SPEAKERS_FILE.replace(backup)
        except Exception:
            log.exception("backup speakers")
        with self.lock:
            self.speakers.clear()
            self._next = 1
            self.impostor = []
        self.save()
        return n

    def _remove_sample(self, sid: int, embs: dict):
        sp = self.speakers.get(sid)
        if not sp or not embs:
            return
        for k, v in embs.items():
            lst = sp.samples.get(k, [])
            for i, x in enumerate(lst):
                if np.allclose(x, v, atol=1e-6):
                    del lst[i]
                    break
        if sp.count() == 0 and not sp.discord_id:
            del self.speakers[sid]

    def reassign(self, embs: dict, from_id: Optional[int], to_id: int):
        """'This line is actually X' – moves the voice sample and teaches X."""
        with self.lock:
            if from_id is not None and from_id != to_id:
                self._remove_sample(from_id, embs)
            if to_id in self.speakers and embs:
                self.speakers[to_id].add(embs)
        self.save()

    def new_from(self, embs: dict, from_id: Optional[int], name: str = "") -> int:
        with self.lock:
            if from_id is not None:
                self._remove_sample(from_id, embs)
            sp = self._create(embs, name)
        self.save()
        return sp.id

    def merge(self, keep_id: int, drop_id: int):
        with self.lock:
            a, b = self.speakers.get(keep_id), self.speakers.get(drop_id)
            if not a or not b or a is b:
                return
            for k, lst in b.samples.items():
                for v in lst:
                    a.add({k: v})
            a.langs = (a.langs + b.langs)[-30:]
            del self.speakers[drop_id]
        self.save()

    # ---------------- automatic language per person
    def note_lang(self, sid: Optional[int], lang: str):
        """Remember which language this person just spoke (last 30 lines)."""
        if sid is None or not lang:
            return
        with self.lock:
            sp = self.speakers.get(sid)
            if sp is None:
                return
            sp.langs = (sp.langs + [lang])[-30:]
            n = len(sp.langs)
        if n % 5 == 0:
            self.save()

    def lang_prior(self, sid: Optional[int]) -> Optional[dict]:
        """{lang: share} of this person's recent lines, or None while there are fewer than 3."""
        sp = self.speakers.get(sid) if sid is not None else None
        if sp is None or len(sp.langs) < 3:
            return None
        out: dict = {}
        for l in sp.langs:
            out[l] = out.get(l, 0) + 1
        res = {l: c / len(sp.langs) for l, c in out.items()}
        res["__n__"] = len(sp.langs)
        return res

    def usual_lang(self, sid: Optional[int]) -> str:
        p = self.lang_prior(sid)
        if not p:
            return ""
        l, share = max(((k, v) for k, v in p.items() if not k.startswith("__")), key=lambda x: x[1])
        return l if share >= 0.7 else ""

    def guess(self, embs: dict) -> Optional[int]:
        """Who is probably talking (read-only, nothing is learned or created). Used before transcription
        to choose the language; the real identification happens afterwards."""
        if not embs:
            return None
        match_t, new_t = self.thresholds()
        sc = self.scores(embs)
        if not sc:
            return None
        best_id, best = sc[0]
        second = sc[1][1] if len(sc) > 1 else -1.0
        sp = self.speakers.get(best_id)
        if sp is None or best < sp.own_threshold(match_t, new_t) or best - second < 0.05:
            return None
        return best_id

    # ---------------- per-person options
    def lang_of(self, sid: Optional[int]) -> str:
        sp = self.speakers.get(sid) if sid is not None else None
        return sp.lang if sp else ""

    def set_lang(self, sid: int, lang: str):
        with self.lock:
            if sid in self.speakers:
                self.speakers[sid].lang = lang or ""
        self.save()

    def is_ignored(self, sid: Optional[int]) -> bool:
        sp = self.speakers.get(sid) if sid is not None else None
        return bool(sp and sp.ignored)

    def set_ignored(self, sid: int, on: bool):
        with self.lock:
            if sid in self.speakers:
                self.speakers[sid].ignored = bool(on)
        self.save()

    def unignore_all(self):
        with self.lock:
            for sp in self.speakers.values():
                sp.ignored = False
        self.save()

    def delete(self, sid: int):
        """Forget one voice (the others stay)."""
        with self.lock:
            self.speakers.pop(sid, None)
        self.save()

    def forget_all(self):
        with self.lock:
            self.speakers.clear()
            self._next = 1
            self.impostor = []
        try:
            SPEAKERS_FILE.unlink()
        except Exception:
            pass

    def all(self) -> list[Speaker]:
        with self.lock:
            return sorted(self.speakers.values(), key=lambda s: s.id)

    # ---------------- persistence (local file only)
    def save(self):
        if not self.s.remember_speakers:
            return
        with self.lock:
            data = {"next": self._next, "impostor": [round(x, 4) for x in self.impostor], "speakers": [
                {"id": sp.id, "name": sp.name, "lang": sp.lang, "ignored": sp.ignored,
                 "self_scores": [round(x, 4) for x in sp.self_scores], "langs": sp.langs,
                 "discord_id": sp.discord_id, "discord_names": sp.discord_names, "name_custom": sp.name_custom,
                 "samples": {k: [v.round(5).tolist() for v in lst] for k, lst in sp.samples.items()}}
                for sp in self.speakers.values()]}
        try:
            SPEAKERS_FILE.write_text(json.dumps(data), encoding="utf-8")
        except Exception:
            log.exception("save speakers")

    def load(self):
        try:
            data = json.loads(SPEAKERS_FILE.read_text(encoding="utf-8"))
        except Exception:
            return
        with self.lock:
            for d in data.get("speakers", []):
                sp = Speaker(int(d["id"]), d["name"],
                             {k: [np.asarray(v, np.float32) for v in lst] for k, lst in d["samples"].items()},
                             str(d.get("lang") or ""), bool(d.get("ignored")),
                             [float(x) for x in d.get("self_scores", [])],
                             [str(x) for x in d.get("langs", [])][-30:],
                             str(d.get("discord_id") or ""), dict(d.get("discord_names") or {}),
                             bool(d.get("name_custom")))
                if sp.count() or sp.discord_id:
                    self.speakers[sp.id] = sp
            self._next = max([data.get("next", 1)] + [s + 1 for s in self.speakers])
            self.impostor = [float(x) for x in data.get("impostor", [])][-60:]


# --------------------------------------------------------------------------- change detection
def find_speaker_changes(windows: list, min_side: float = 1.0) -> list[float]:
    """All the points where the voice changes (a line can hold several turns, also A -> B -> A).

    For every possible moment, the ~1.5 s just before is compared with the ~1.5 s just after:
    a change is where both sides are self-consistent but clearly different from each other.
    """
    n = len(windows)
    if n < 4:
        return []
    E = np.stack([w[2] for w in windows])
    S = E @ E.T
    start, end = windows[0][0], windows[-1][1]
    cands = []
    for k in range(1, n):
        b = windows[k][0]                                   # boundary time
        if b - start < min_side or end - b < min_side:
            continue
        L = [i for i in range(n) if windows[i][1] <= b + 1e-6][-3:]  # windows entirely before b
        R = [i for i in range(n) if windows[i][0] >= b][:3]          # windows after b
        if not L or not R:
            continue
        def intra(ix):
            if len(ix) < 2:
                return 1.0
            m = S[np.ix_(ix, ix)]
            return (m.sum() - len(ix)) / (len(ix) ** 2 - len(ix))
        cross = float(S[np.ix_(L, R)].mean())
        gap = min(intra(L), intra(R)) - cross
        if cross < 0.75 and min(intra(L), intra(R)) > 0.45 and gap >= 0.15:
            cands.append((gap, b))
    # keep the strongest change in each neighbourhood (at least min_side apart)
    out = []
    for gap, b in sorted(cands, reverse=True):
        if all(abs(b - o) >= max(min_side, 1.5) for o in out):
            out.append(b)
    return sorted(out)


def find_speaker_change(windows: list, min_side: float = 1.0) -> Optional[float]:
    """Return the time where the voice changes inside one sentence, or None.

    windows: [(t0, t1, emb)] every 0.5 s. Tries every split point and keeps the one where the
    two sides are each self-consistent but clearly different from each other.
    """
    n = len(windows)
    if n < 4:
        return None
    E = np.stack([w[2] for w in windows])
    S = E @ E.T
    best, best_k = 0.0, None
    for k in range(1, n):
        left_t = windows[k - 1][1] - windows[0][0]
        right_t = windows[-1][1] - windows[k][0]
        if left_t < min_side or right_t < min_side:
            continue
        L, R = S[:k, :k], S[k:, k:]
        intra_l = (L.sum() - k) / max(k * k - k, 1) if k > 1 else 1.0
        intra_r = (R.sum() - (n - k)) / max((n - k) ** 2 - (n - k), 1) if n - k > 1 else 1.0
        cross = S[:k, k:].mean()
        gap = min(intra_l, intra_r) - cross
        # Discord audio (compressed, noise-suppressed) makes different voices look more alike,
        # so judge by how clearly the two halves differ, not by a fixed low similarity
        if cross < 0.50 and min(intra_l, intra_r) > 0.45 and gap >= 0.18 and gap > best:
            best, best_k = gap, k
    if best_k is None:
        return None
    # windows overlap: the change is around the start of window k + half the overlap
    return (windows[best_k][0] + windows[best_k - 1][1]) / 2.0
