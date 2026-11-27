"""AudioTranscriber – live per-app voice transcription + translation."""
from __future__ import annotations

import logging
import sys
import traceback
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

# Started without a console (pythonw / desktop shortcut): sys.stdout/stderr are None and any
# library that prints a progress bar (model downloads) would crash. Send them to nowhere.
import os  # noqa: E402
if sys.stdout is None:
    sys.stdout = open(os.devnull, "w", encoding="utf-8")
if sys.stderr is None:
    sys.stderr = open(os.devnull, "w", encoding="utf-8")
os.environ.setdefault("HF_HUB_DISABLE_PROGRESS_BARS", "1")
os.environ.setdefault("HF_HUB_DISABLE_XET", "1")          # plain HTTPS downloads (more reliable)

from app.config import LOG_FILE  # noqa: E402  (also points HF cache to G:)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    handlers=[logging.FileHandler(LOG_FILE, encoding="utf-8"), logging.StreamHandler()],
)


def main():
    if sys.platform == "win32":
        try:
            import ctypes
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("AudioTranscriber.App")
        except Exception:
            pass

    from PySide6.QtWidgets import QApplication, QMessageBox
    from app.ui import MainWindow, app_icon

    app = QApplication(sys.argv)
    app.setApplicationName("AudioTranscriber")
    app.setWindowIcon(app_icon())

    # one copy only: opening it again just brings the running window to the front
    from PySide6.QtNetwork import QLocalServer, QLocalSocket
    key = "AudioTranscriber-" + os.environ.get("USERNAME", "user")
    if "--restart" in sys.argv:          # language switch: wait for the old window to close first
        import time
        for _ in range(40):
            p_ = QLocalSocket()
            p_.connectToServer(key)
            if not p_.waitForConnected(150):
                break
            p_.disconnectFromServer()
            time.sleep(0.25)
    probe = QLocalSocket()
    probe.connectToServer(key)
    if probe.waitForConnected(400):
        probe.write(b"tray" if "--tray" in sys.argv else b"show")
        probe.flush()
        probe.waitForBytesWritten(400)
        probe.disconnectFromServer()
        return 0
    QLocalServer.removeServer(key)
    server = QLocalServer()
    server.listen(key)

    def excepthook(t, v, tb):
        msg = "".join(traceback.format_exception(t, v, tb))
        logging.error("Unhandled:\n%s", msg)
        QMessageBox.critical(None, "AudioTranscriber – error", msg[-1500:])

    sys.excepthook = excepthook
    w = MainWindow()

    def bring_to_front():
        sock = server.nextPendingConnection()
        if sock is None:
            return
        sock.waitForReadyRead(300)
        if bytes(sock.readAll()) != b"tray":
            w.showNormal()
            w.raise_()
            w.activateWindow()
        sock.disconnectFromServer()
    server.newConnection.connect(bring_to_front)

    if getattr(w.s, "start_with_windows", False):   # keep the autostart entry pointing at this install
        try:
            from app.config import ROOT
            from app.sysinfo import set_start_with_windows
            set_start_with_windows(True, ROOT)
        except Exception:
            logging.exception("autostart entry")
    try:                               # looks for a newer GitHub release in the background, as soon as the app opens
        from app import updater
        updater.start(app, w)
    except Exception:
        logging.exception("update check could not start")
    if "--tray" in sys.argv:          # started with Windows: wait in the tray
        from app.i18n import tr
        w.tray.showMessage("AudioTranscriber", tr("Ready in the tray"), app_icon(), 1500)
    else:
        w.show()
    return app.exec()


if __name__ == "__main__":
    try:
        code = main()
    except Exception:
        logging.exception("AudioTranscriber could not start")
        code = 1
    # leave for sure: a thread stuck on the network or a pipe must never keep the closed app alive
    # (it would hold the single-copy lock, so a restart or the next start would find "it's already open")
    logging.shutdown()
    os._exit(code or 0)
