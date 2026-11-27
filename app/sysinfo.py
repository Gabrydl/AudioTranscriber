"""Live resource readout (GPU / VRAM / CPU / RAM) and global hotkeys."""
from __future__ import annotations

import ctypes
import logging
import os
import sys
import threading
from typing import Callable

import psutil

log = logging.getLogger("sys")


class ResourceMonitor:
    def __init__(self):
        self.proc = psutil.Process(os.getpid())
        self.nv = None
        try:
            import pynvml
            pynvml.nvmlInit()
            self.nv = pynvml
            self.h = pynvml.nvmlDeviceGetHandleByIndex(0)
            name = pynvml.nvmlDeviceGetName(self.h)
            self.gpu_name = name.decode() if isinstance(name, bytes) else name
        except Exception:
            self.gpu_name = "GPU"
        psutil.cpu_percent(None)

    def _ollama_rss(self) -> int:
        """Memory of the Ollama processes. Going through every process is slow on Windows, so the list of
        Ollama processes is only looked up again every 15 s; in between just their memory is read."""
        import time
        now = time.monotonic()
        if now - getattr(self, "_oll_at", -1e9) > 15:
            self._oll_at = now
            procs = []
            for p in psutil.process_iter(["name"]):
                n = (p.info["name"] or "").lower()
                if n.startswith("ollama") or "llama" in n:
                    procs.append(p)
            self._oll = procs
        total = 0
        for p in list(getattr(self, "_oll", [])):
            try:
                total += p.memory_info().rss
            except Exception:
                self._oll.remove(p)
        return total

    def sample(self) -> dict:
        d = {"cpu": psutil.cpu_percent(None)}
        try:
            d["app_ram"] = self.proc.memory_info().rss + self._ollama_rss()
        except Exception:
            d["app_ram"] = 0
        vm = psutil.virtual_memory()
        d["ram_used"], d["ram_total"] = vm.used, vm.total
        if self.nv:
            try:
                m = self.nv.nvmlDeviceGetMemoryInfo(self.h)
                u = self.nv.nvmlDeviceGetUtilizationRates(self.h)
                d["vram_used"], d["vram_total"], d["gpu"] = m.used, m.total, u.gpu
            except Exception:
                pass
        return d


class GlobalHotkeys(threading.Thread):
    """Win32 RegisterHotKey in its own message loop. Ctrl+Alt+<key>."""

    MOD_ALT, MOD_CONTROL, MOD_NOREPEAT = 0x1, 0x2, 0x4000
    WM_HOTKEY = 0x0312

    def __init__(self, bindings: dict[str, Callable[[], None]]):
        super().__init__(daemon=True)
        self.bindings = bindings

    def run(self):
        if sys.platform != "win32":
            return
        from ctypes import wintypes
        user32 = ctypes.windll.user32
        ids = {}
        for i, (key, cb) in enumerate(self.bindings.items(), start=1):
            if user32.RegisterHotKey(None, i, self.MOD_CONTROL | self.MOD_ALT | self.MOD_NOREPEAT, ord(key.upper())):
                ids[i] = cb
            else:
                log.warning("Hotkey Ctrl+Alt+%s already in use", key)
        msg = wintypes.MSG()
        while user32.GetMessageW(ctypes.byref(msg), None, 0, 0) != 0:
            if msg.message == self.WM_HOTKEY and msg.wParam in ids:
                try:
                    ids[msg.wParam]()
                except Exception:
                    log.exception("hotkey")


# ------------------------------------------------------------------ start with Windows (current user only)
RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"


def set_start_with_windows(on: bool, root) -> bool:
    if sys.platform != "win32":
        return False
    try:
        import winreg
        launcher = os.path.join(str(root), "AudioTranscriber.exe")
        if os.path.exists(launcher):
            cmd = f'"{launcher}" --tray'
        else:
            exe = os.path.join(str(root), ".venv", "Scripts", "pythonw.exe")
            main = os.path.join(str(root), "app", "main.py")
            cmd = f'"{exe}" "{main}" --tray'
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY, 0, winreg.KEY_SET_VALUE) as k:
            if on:
                winreg.SetValueEx(k, "AudioTranscriber", 0, winreg.REG_SZ, cmd)
            else:
                try:
                    winreg.DeleteValue(k, "AudioTranscriber")
                except FileNotFoundError:
                    pass
        return True
    except Exception:
        log.exception("start with Windows")
        return False


def keep_on_top(widget) -> None:
    """Some games pull themselves above 'always on top' windows: put the overlay back on top (no focus change)."""
    if sys.platform != "win32":
        return
    try:
        hwnd = int(widget.winId())
        HWND_TOPMOST, SWP_NOMOVE, SWP_NOSIZE, SWP_NOACTIVATE, SWP_SHOWWINDOW = -1, 0x2, 0x1, 0x10, 0x40
        ctypes.windll.user32.SetWindowPos(hwnd, HWND_TOPMOST, 0, 0, 0, 0, SWP_NOMOVE | SWP_NOSIZE | SWP_NOACTIVATE | SWP_SHOWWINDOW)
    except Exception:
        pass
