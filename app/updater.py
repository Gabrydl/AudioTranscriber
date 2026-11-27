"""Self-update from GitHub releases. Checks as soon as the app opens (in the background, never delays the window).

The release has one asset, AudioTranscriber.zip, with the program files only (no models, no .venv).
On "Update now": download, close the app, copy the new files over this folder (settings, voices, models, logs and
the Python environment are never touched), reinstall packages only if requirements.txt changed, start the app again
(through AudioTranscriber.exe).
"""
from __future__ import annotations

import json
import logging
from .i18n import tr
import os
import re
import subprocess
import sys
import tempfile
import threading
import urllib.request
from pathlib import Path

from .version import VERSION

log = logging.getLogger("updater")
REPO = "Gabrydl/AudioTranscriber"
ASSET = "AudioTranscriber.zip"
ROOT = Path(__file__).resolve().parent.parent
UA = {"User-Agent": "AudioTranscriber-updater", "Accept": "application/vnd.github+json"}


def _tuple(v: str):
    n = [int(x) for x in re.findall(r"\d+", v or "")][:3]
    return n + [0] * (3 - len(n))


def is_newer(a: str, b: str) -> bool:
    return _tuple(a) > _tuple(b)


def find_update():
    """(version, url) of a newer release, else None. Any error (offline, rate limit...) -> None."""
    if REPO.startswith("__"):
        return None
    try:
        req = urllib.request.Request(f"https://api.github.com/repos/{REPO}/releases/latest", headers=UA)
        with urllib.request.urlopen(req, timeout=15) as r:
            j = json.load(r)
        for a in j.get("assets", []):
            if a.get("name", "").lower() == ASSET.lower() and is_newer(j.get("tag_name", ""), VERSION):
                return ".".join(map(str, _tuple(j["tag_name"]))), a["browser_download_url"]
    except Exception as e:  # noqa: BLE001
        log.info("update check skipped: %s", e)
    return None


def _download(url: str, dest: Path, progress):
    req = urllib.request.Request(url, headers={"User-Agent": UA["User-Agent"]})
    with urllib.request.urlopen(req, timeout=30) as r, open(dest, "wb") as f:
        total = int(r.headers.get("Content-Length") or 0)
        got = 0
        while True:
            chunk = r.read(256 * 1024)
            if not chunk:
                break
            f.write(chunk)
            got += len(chunk)
            if total:
                progress(int(got * 100 / total))


def _launch_helper(zip_path: Path, restart: bool = True):
    """Waits for this process to end, unpacks the zip over ROOT (keeping user data) and restarts the app
    (restart=False: the user closed the app, so it stays closed after the update)."""
    tmp = zip_path.parent
    ps = tmp / "update.ps1"
    q = lambda s: "'" + str(s).replace("'", "''") + "'"  # noqa: E731
    ps.write_text("\r\n".join([
        "$ErrorActionPreference = 'Continue'",
        f"try {{ Wait-Process -Id {os.getpid()} -Timeout 60 }} catch {{}}",
        "Start-Sleep -Milliseconds 800",
        f"$tmp = {q(tmp)}; $zip = {q(zip_path)}; $dst = {q(ROOT)}",
        "$out = Join-Path $tmp 'x'; New-Item -ItemType Directory -Force -Path $out | Out-Null",
        "tar -xf $zip -C $out",
        "if ($LASTEXITCODE -ne 0) { Expand-Archive -Force -Path $zip -DestinationPath $out }",
        "$oldReq = if (Test-Path (Join-Path $dst 'requirements.txt')) { (Get-FileHash (Join-Path $dst 'requirements.txt')).Hash } else { '' }",
        "$src = if (Test-Path (Join-Path $out 'app')) { $out } else { (Get-ChildItem $out -Directory | Select-Object -First 1).FullName }",
        "robocopy $src $dst /E /XD .venv models ollama_models transcripts gpu __pycache__ installer /XF settings.json speakers.json speakers_before_discord.json discord_token.json *.log *.bat setup.ps1 /R:3 /W:1 /NFL /NDL /NJH /NJS /NP | Out-Null",
        "$newReq = (Get-FileHash (Join-Path $dst 'requirements.txt')).Hash",
        "$py = Join-Path $dst '.venv\\Scripts\\python.exe'",
        "if (($oldReq -ne $newReq) -and (Test-Path $py)) { & $py -m pip install -r (Join-Path $dst 'requirements.txt') | Out-Null }",
        "Get-ChildItem -LiteralPath $dst -Filter '*.bat' | Remove-Item -Force -ErrorAction SilentlyContinue",
        "$exe = Join-Path $dst 'AudioTranscriber.exe'",
        *([
            "if (Test-Path $exe) { Start-Process -FilePath $exe -WorkingDirectory $dst }",
            "else { Start-Process -FilePath (Join-Path $dst '.venv\\Scripts\\pythonw.exe') -ArgumentList ('\"' + (Join-Path $dst 'app\\main.py') + '\"') -WorkingDirectory $dst }",
        ] if restart else []),
        "Start-Sleep -Seconds 2",
        "Remove-Item -Recurse -Force $tmp -ErrorAction SilentlyContinue",
    ]), encoding="utf-8")
    subprocess.Popen(
        ["powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass", "-WindowStyle", "Hidden", "-File", str(ps)],
        creationflags=0x00000008 | 0x08000000,  # DETACHED_PROCESS | CREATE_NO_WINDOW
        close_fds=True,
    )


def start(qapp, window):
    """Call once after the main window exists. Checks GitHub in the background as soon as the app opens and
    updates by itself: the new version downloads quietly, then the app restarts on it – right away if nothing is
    being transcribed, otherwise as soon as you press Stop (or close the app). Settings, voices and models are kept."""
    if sys.platform != "win32":
        return
    from PySide6.QtCore import QObject, Signal, QTimer

    class Bridge(QObject):
        found = Signal(str, str)
        done = Signal(str)
        failed = Signal(str)

    b = Bridge()
    state = {"ver": "", "zip": None}

    def say(msg):
        try:
            window._on_status("upd", msg)
        except Exception:
            pass

    def busy() -> bool:
        return getattr(window, "state", "idle") != "idle"

    def on_found(ver, url):
        state["ver"] = ver
        say(tr("Downloading update {v}…").format(v=ver))
        tmp = Path(tempfile.mkdtemp(prefix="at-upd-"))
        zip_path = tmp / "update.zip"

        def work():
            try:
                _download(url, zip_path, lambda p: None)
                b.done.emit(str(zip_path))
            except Exception as e:  # noqa: BLE001
                b.failed.emit(str(e))
        threading.Thread(target=work, daemon=True).start()

    def apply_now():
        z = state.get("zip")
        if not z:
            return
        state["zip"] = None
        log.info("updating to %s", state["ver"])
        try:
            window.tray.showMessage("AudioTranscriber", tr("Updating to {v} – back in a few seconds").format(v=state['ver']), window.windowIcon(), 3000)
        except Exception:
            pass
        _launch_helper(Path(z))
        try:
            window.s.save()
            window.close()            # stops Discord, the overlay and the tray icon cleanly before the swap
        except Exception:
            pass
        qapp.quit()
        os._exit(0)  # the helper is waiting for this process to end

    def on_done(path):
        state["zip"] = path
        if not busy():
            say(tr("Update {v} ready – restarting…").format(v=state['ver']))
            QTimer.singleShot(1500, lambda: apply_now() if not busy() else None)
        else:
            say(tr("Update {v} ready – it installs when you press Stop").format(v=state['ver']))
        # wait for the end of the session (Stop) if it was running
        t = QTimer(window)
        t.timeout.connect(lambda: apply_now() if (state.get("zip") and not busy()) else None)
        t.start(3000)
        state["timer"] = t
        state["apply"] = apply_now                 # also used on close

    def on_failed(msg):
        log.warning("update download failed: %s", msg)
        say(tr("Update could not be downloaded – it retries next time the app opens"))

    b.found.connect(on_found)
    b.done.connect(on_done)
    b.failed.connect(on_failed)
    state["bridge"] = b  # keep alive
    window._updater_state = state

    def check():
        r = find_update()
        if r:
            b.found.emit(*r)
    threading.Thread(target=check, daemon=True).start()
