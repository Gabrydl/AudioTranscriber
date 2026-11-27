"""Noise removal on the graphics card, in a small helper process.

The GPU build of sherpa-onnx is installed apart from the normal one (folder gpu\\sherpa, by Setup), so the
speaker models keep using the normal CPU build in the app. This helper loads the GPU build, keeps the
noise-removal model on the card and cleans audio sent to it over a pipe. If anything here fails, the app
simply cleans on the CPU as before.

    python denoise_gpu.py <gpu_sherpa_dir> <model.onnx>
Protocol (stdin/stdout): first line "READY <json>" or "FAIL <reason>"; then per request
uint32 n + n float32 samples in, uint32 n + n float32 samples out.
"""
from __future__ import annotations

import glob
import json
import os
import site
import struct
import sys
import time


def _cuda_dlls():
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
    os.environ["PATH"] = os.pathsep.join(dirs) + os.pathsep + os.environ.get("PATH", "")


def main():
    out = sys.stdout.buffer
    inp = sys.stdin.buffer

    def line(t):
        out.write((t + "\n").encode())
        out.flush()

    try:
        gpu_dir, model = sys.argv[1], sys.argv[2]
        sys.path.insert(0, gpu_dir)
        _cuda_dlls()
        import numpy as np
        import sherpa_onnx
        m = sherpa_onnx.OfflineSpeechDenoiserModelConfig(num_threads=1, provider="cuda")
        m.dpdfnet.model = model
        dn = sherpa_onnx.OfflineSpeechDenoiser(sherpa_onnx.OfflineSpeechDenoiserConfig(model=m))
        test = (np.random.default_rng(0).standard_normal(16000 * 3) * 0.05).astype(np.float32)
        dn(test, 16000)                                    # warm-up (loads the model onto the card)
        t0 = time.time()
        dn(test, 16000)
        ms = (time.time() - t0) * 1000
        line("READY " + json.dumps({"version": getattr(sherpa_onnx, "__version__", "?"), "ms_per_3s": round(ms)}))
    except Exception as e:                                 # noqa: BLE001
        line("FAIL " + f"{type(e).__name__}: {e}"[:300])
        return
    while True:
        hdr = inp.read(4)
        if len(hdr) < 4:
            return
        (n,) = struct.unpack("<I", hdr)
        raw = inp.read(n * 4)
        x = np.frombuffer(raw, np.float32)
        try:
            y = np.asarray(dn(x, 16000).samples, np.float32)
        except Exception:                                  # noqa: BLE001
            y = x
        out.write(struct.pack("<I", y.size) + y.tobytes())
        out.flush()


if __name__ == "__main__":
    main()
