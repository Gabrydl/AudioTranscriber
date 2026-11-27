"""Streaming speech detector (Silero VAD, the same model faster-whisper ships with) for cutting sentences.

The volume gate alone can't tell a voice from a noisy mic, keyboard clicks or game sounds: noise above the
threshold kept sentences open until the 9 s limit, and loud clicks became fake sentences. This tells the gate
whether the sound is really a voice. Runs on the CPU, ~0.1 ms per 32 ms of audio.
"""
from __future__ import annotations

import glob
import logging
import os
from typing import Optional

import numpy as np

log = logging.getLogger("vad")
CHUNK = 512          # 32 ms at 16 kHz
CONTEXT = 64


def _model_path() -> Optional[str]:
    try:
        import faster_whisper
        d = os.path.join(os.path.dirname(faster_whisper.__file__), "assets")
        files = sorted(glob.glob(os.path.join(d, "silero_vad*.onnx")))
        return files[-1] if files else None
    except Exception:
        return None


class StreamingVAD:
    """feed(samples) -> latest speech probability (0..1). One per captured app."""

    def __init__(self):
        import onnxruntime
        path = _model_path()
        if not path:
            raise RuntimeError("Silero VAD model not found")
        o = onnxruntime.SessionOptions()
        o.inter_op_num_threads = 1
        o.intra_op_num_threads = 1
        o.log_severity_level = 4
        self.sess = onnxruntime.InferenceSession(path, providers=["CPUExecutionProvider"], sess_options=o)
        names = {i.name for i in self.sess.get_inputs()}
        if {"input", "h", "c"} <= names:            # faster-whisper's version
            self.kind = "hc"
            self.h = np.zeros((1, 1, 128), np.float32)
            self.c = np.zeros((1, 1, 128), np.float32)
        elif {"input", "state", "sr"} <= names:     # original Silero v5
            self.kind = "state"
            self.state = np.zeros((2, 1, 128), np.float32)
        else:
            raise RuntimeError(f"unknown VAD model inputs {names}")
        self.ctx = np.zeros(CONTEXT, np.float32)
        self.buf = np.zeros(0, np.float32)
        self.prob = 0.0
        log.info("VAD ready (%s, %s)", os.path.basename(path), self.kind)

    def reset(self):
        if self.kind == "hc":
            self.h[:] = 0
            self.c[:] = 0
        else:
            self.state[:] = 0
        self.ctx[:] = 0
        self.buf = np.zeros(0, np.float32)
        self.prob = 0.0

    def feed(self, x: np.ndarray) -> float:
        self.buf = np.concatenate([self.buf, x.astype(np.float32)])
        while self.buf.size >= CHUNK:
            ch, self.buf = self.buf[:CHUNK], self.buf[CHUNK:]
            inp = np.concatenate([self.ctx, ch])[None, :]
            if self.kind == "hc":
                out, self.h, self.c = self.sess.run(None, {"input": inp, "h": self.h, "c": self.c})
            else:
                out, self.state = self.sess.run(None, {"input": inp, "state": self.state,
                                                       "sr": np.array(16000, np.int64)})
            self.prob = float(np.asarray(out).reshape(-1)[-1])
            self.ctx = ch[-CONTEXT:]
        return self.prob


def make() -> Optional[StreamingVAD]:
    try:
        return StreamingVAD()
    except Exception as e:
        log.warning("speech detector unavailable (%s) - volume only", e)
        return None
