"""Setup steps run by Setup.exe (Install / Repair) with the app's own Python. No PowerShell.

    python -u setup_tasks.py reuse  <root>   take models, settings and voices from an earlier copy (hard links, no extra space)
    python -u setup_tasks.py cuda   <root>   NVIDIA GPU found -> CUDA 12 libraries for Whisper
    python -u setup_tasks.py ollama <root>   install/start Ollama, keep its models next to the app, pull gemma3:4b
    python -u setup_tasks.py models <root>   Whisper large-v3-turbo + the three voice recognition models
    python -u setup_tasks.py check  <root>   final check of every component

Every step can run again safely: it only downloads what is missing.
Output is plain ASCII lines (the installer shows them in its details list). Exit code 0 = ok.
"""
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

NO_WINDOW = 0x08000000
LLM = "gemma3:4b"
WHISPER = "large-v3"                    # max accuracy (default)
WHISPER_FAST = "large-v3-turbo"         # used automatically if large-v3 lags
SPEAKER_REPO = "csukuangfj/speaker-embedding-models"
SPEAKER_FILES = ("wespeaker_en_voxceleb_resnet293_LM.onnx", "nemo_en_titanet_large.onnx",
                 "wespeaker_en_voxceleb_CAM++_LM.onnx")
OLLAMA_URL = "http://127.0.0.1:11434"
SHERPA_GPU = "2.0.1+cuda12.cudnn9"         # matches the CUDA 12 / cuDNN 9 libraries Whisper already uses


def say(t: str = "") -> None:
    print(t.encode("ascii", "replace").decode(), flush=True)


class Fail(Exception):
    pass


# ------------------------------------------------------------------ helpers
def user_env(name: str):
    try:
        import winreg
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, "Environment") as k:
            return winreg.QueryValueEx(k, name)[0]
    except Exception:
        return None


def set_user_env(name: str, value: str) -> None:
    import ctypes
    import winreg
    with winreg.OpenKey(winreg.HKEY_CURRENT_USER, "Environment", 0, winreg.KEY_SET_VALUE) as k:
        winreg.SetValueEx(k, name, 0, winreg.REG_EXPAND_SZ, value)
    r = ctypes.c_ulong()                                   # tell Explorer / new programs about it
    ctypes.windll.user32.SendMessageTimeoutW(0xFFFF, 0x001A, 0, "Environment", 0x0002, 2000, ctypes.byref(r))


def run(cmd, env=None, quiet_prefixes=()) -> int:
    """Run a program, copy its output to the installer (spinners / repeated progress lines thinned out)."""
    p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, env=env, creationflags=NO_WINDOW)
    last = ["", 0.0]

    def emit(raw: bytes) -> None:
        line = "".join(c for c in raw.decode("utf-8", "replace") if c.isprintable())
        line = re.sub(r"\[[0-9;?]*[A-Za-z]", "", line).strip()
        if not line.strip(" -\\|/.") or line.startswith(quiet_prefixes):
            return
        now = time.time()
        if line[:22] == last[0] and now - last[1] < 4:
            return
        last[0], last[1] = line[:22], now
        say("    " + line)

    buf = b""
    while True:
        ch = p.stdout.read(1)
        if not ch:
            emit(buf)
            break
        if ch in (b"\r", b"\n"):
            emit(buf)
            buf = b""
        else:
            buf += ch
    return p.wait()


def link_tree(src: Path, dst: Path) -> int:
    """Copy src into dst without overwriting. Same drive: hard links (instant, no extra space)."""
    n = 0
    for f in src.rglob("*"):
        if not f.is_file():
            continue
        t = dst / f.relative_to(src)
        if t.exists():
            continue
        t.parent.mkdir(parents=True, exist_ok=True)
        try:
            os.link(f, t)
        except OSError:
            shutil.copy2(f, t)
        n += 1
    return n


def find_ollama():
    cands = [shutil.which("ollama")]
    drives = {Path(sys.executable).drive, "G:", "C:"}
    for d in drives:
        cands.append(f"{d}\\Ollama\\ollama.exe")
    cands += [os.path.expandvars(r"%LOCALAPPDATA%\Programs\Ollama\ollama.exe"), r"C:\Program Files\Ollama\ollama.exe"]
    return next((c for c in cands if c and os.path.exists(c)), None)


def ollama_up() -> bool:
    try:
        with urllib.request.urlopen(OLLAMA_URL + "/api/tags", timeout=2) as r:
            json.load(r)
        return True
    except Exception:
        return False


def download(url: str, dst: Path) -> None:
    say(f"    downloading {url}")
    req = urllib.request.Request(url, headers={"User-Agent": "AudioTranscriber-setup"})
    with urllib.request.urlopen(req, timeout=60) as r, open(dst, "wb") as f:
        total = int(r.headers.get("Content-Length") or 0)
        got, shown = 0, -10
        while True:
            b = r.read(1 << 20)
            if not b:
                break
            f.write(b)
            got += len(b)
            if total and got * 100 // total >= shown + 10:
                shown = got * 100 // total
                say(f"    {shown}%  ({got >> 20} / {total >> 20} MB)")


# ------------------------------------------------------------------ steps
def step_reuse(root: Path) -> None:
    cands = []
    om = user_env("OLLAMA_MODELS")
    if om:
        cands.append(Path(om).parent)
    drive = root.drive or "G:"
    progetti = Path(drive + "\\Progetti")
    if progetti.is_dir():
        cands += [p for p in progetti.iterdir() if p.is_dir() and "audiotranscriber" in p.name.lower()]
    prev = None
    for c in cands:
        try:
            if c.resolve() != root.resolve() and (c / "models").is_dir():
                prev = c
                break
        except OSError:
            pass
    if not prev:
        say("    No earlier copy found - everything will be downloaded")
        return
    say(f"    Found an earlier copy: {prev}")
    for d in ("models", "ollama_models"):
        if (prev / d).is_dir():
            n = link_tree(prev / d, root / d)
            say(f"    {d}: {n} files taken over")
    for f in ("settings.json", "speakers.json"):
        if (prev / f).is_file() and not (root / f).exists():
            shutil.copy2(prev / f, root / f)
            say(f"    {f} copied")
    say("    The earlier copy is untouched.")


def step_cuda(root: Path) -> None:
    smi = shutil.which("nvidia-smi") or (r"C:\Windows\System32\nvidia-smi.exe" if os.path.exists(r"C:\Windows\System32\nvidia-smi.exe") else None)
    if not smi:
        say("    No NVIDIA GPU found - choose the 'CPU only' profile in Settings.")
        return
    run([smi, "--query-gpu=name,memory.total,driver_version", "--format=csv,noheader"])
    code = run([sys.executable, "-m", "pip", "install", "--progress-bar", "off", "nvidia-cublas-cu12", "nvidia-cudnn-cu12==9.*",
                "nvidia-cuda-runtime-cu12", "nvidia-cufft-cu12"])
    if code != 0:
        say("    WARNING: the CUDA libraries could not be installed - Whisper will use the CPU (slower). Repair retries this.")
        return
    # noise removal on the graphics card: GPU build of sherpa-onnx in its own folder (the app keeps the normal one)
    gpu = root / "gpu" / "sherpa"
    if (gpu / "sherpa_onnx").is_dir():
        say("    GPU noise removal: already installed")
        return
    say("    GPU noise removal (sherpa-onnx CUDA build, about 250 MB)")
    tmp = root / "gpu" / "sherpa_new"
    shutil.rmtree(tmp, ignore_errors=True)
    code = run([sys.executable, "-m", "pip", "install", "--progress-bar", "off", "--target", str(tmp),
                "sherpa-onnx==" + SHERPA_GPU, "-f", "https://k2-fsa.github.io/sherpa/onnx/cuda.html"])
    if code == 0 and (tmp / "sherpa_onnx").is_dir():
        shutil.rmtree(gpu, ignore_errors=True)
        tmp.rename(gpu)
        say("    ok")
    else:
        shutil.rmtree(tmp, ignore_errors=True)
        say("    WARNING: GPU noise removal not installed - noisy mics are cleaned on the CPU instead.")


def step_ollama(root: Path) -> None:
    models = root / "ollama_models"
    models.mkdir(parents=True, exist_ok=True)
    if (user_env("OLLAMA_MODELS") or "").rstrip("\\").lower() != str(models).lower():
        set_user_env("OLLAMA_MODELS", str(models))
    say(f"    Translation models folder: {models}")

    exe = find_ollama()
    if not exe:
        target = (root.drive or "C:") + "\\Ollama"
        say(f"    Installing Ollama to {target}")
        tmp = Path(os.environ.get("TEMP", str(root))) / "OllamaSetup.exe"
        download("https://ollama.com/download/OllamaSetup.exe", tmp)
        subprocess.run([str(tmp), "/VERYSILENT", "/NORESTART", "/SUPPRESSMSGBOXES", f"/DIR={target}"], creationflags=NO_WINDOW)
        tmp.unlink(missing_ok=True)
        exe = find_ollama()
        if not exe:
            raise Fail("Ollama could not be installed. Install it from ollama.com, then run Repair.")
    say(f"    Ollama: {exe}")

    # restart it so it uses the folder above (a running copy may point somewhere else)
    for name in ("ollama app.exe", "ollama.exe"):
        subprocess.run(["taskkill", "/F", "/T", "/IM", name], capture_output=True, creationflags=NO_WINDOW)
    time.sleep(2)
    env = dict(os.environ, OLLAMA_MODELS=str(models))
    subprocess.Popen([exe, "serve"], env=env, creationflags=NO_WINDOW,
                     stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    for _ in range(40):
        time.sleep(1)
        if ollama_up():
            break
    else:
        raise Fail("Ollama did not start.")
    say(f"    Downloading {LLM} (skipped if already there)")
    if run([exe, "pull", LLM], env=env, quiet_prefixes=("pulling manifest",)) != 0:
        raise Fail(f"The translation model {LLM} could not be downloaded.")


def step_models(root: Path) -> None:
    mdir = root / "models"
    os.environ["HF_HOME"] = str(mdir / "hf")
    os.environ["HF_HUB_DISABLE_PROGRESS_BARS"] = "1"
    os.environ["HF_HUB_DISABLE_XET"] = "1"
    os.environ["HF_HUB_DISABLE_SYMLINKS_WARNING"] = "1"
    from faster_whisper import download_model
    for name, size in ((WHISPER, "about 3 GB"), (WHISPER_FAST, "about 1.6 GB")):
        say(f"    Whisper {name} ({size}, skipped if already there)")
        download_model(name, cache_dir=str(mdir))
        say("    ok")
    dn = mdir / "denoise" / "dpdfnet8.onnx"
    if not dn.is_file():
        say("    Noise removal model for bad microphones (about 15 MB)")
        dn.parent.mkdir(parents=True, exist_ok=True)
        try:
            download("https://github.com/k2-fsa/sherpa-onnx/releases/download/speech-enhancement-models/dpdfnet8.onnx",
                     dn.with_suffix(".part"))
            os.replace(dn.with_suffix(".part"), dn)
            say("    ok")
        except Exception as e:                      # noqa: BLE001
            say(f"    WARNING: not downloaded ({e}) - the app fetches it later by itself")
    say("    Voice recognition models (about 245 MB)")
    from huggingface_hub import hf_hub_download
    for f in SPEAKER_FILES:
        hf_hub_download(SPEAKER_REPO, f, local_dir=str(mdir / "speaker"))
        say(f"    {f} ok")


def step_check(root: Path) -> None:
    bad = []
    for mod in ("PySide6", "faster_whisper", "sherpa_onnx", "numpy", "scipy", "comtypes", "pycaw", "noisereduce"):
        try:
            __import__(mod)
        except Exception as e:                      # noqa: BLE001
            bad.append(f"{mod}: {e}")
    for name in (WHISPER, WHISPER_FAST):
        if not any(p.is_dir() for p in (root / "models").glob(f"*faster-whisper-{name}")):
            bad.append(f"Whisper {name} missing")
    for f in SPEAKER_FILES:
        if not (root / "models" / "speaker" / f).is_file():
            bad.append(f"voice model missing: {f}")
    if not find_ollama():
        bad.append("Ollama missing")
    if bad:
        for b in bad:
            say("    MISSING " + b)
        raise Fail("Some parts are still missing (see above).")
    say("    Everything is in place.")


STEPS = {"reuse": step_reuse, "cuda": step_cuda, "ollama": step_ollama, "models": step_models, "check": step_check}

if __name__ == "__main__":
    if len(sys.argv) < 3 or sys.argv[1] not in STEPS:
        say(__doc__)
        sys.exit(2)
    try:
        STEPS[sys.argv[1]](Path(sys.argv[2].rstrip("\\.").rstrip("\\") or sys.argv[2]))
    except Fail as e:
        say("ERROR: " + str(e))
        sys.exit(1)
    except Exception as e:                              # noqa: BLE001
        import traceback
        for line in traceback.format_exc().splitlines()[-6:]:
            say("    " + line)
        say(f"ERROR: {type(e).__name__}: {e}")
        sys.exit(1)
    sys.exit(0)
