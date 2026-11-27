"""Per-process loopback capture written directly against WASAPI (ctypes + comtypes).

Uses ActivateAudioInterfaceAsync("VAD\\Process_Loopback") – the same API OBS uses for
"Application Audio Capture". Works on Windows 10 2004 (build 19041) and newer, including
Windows 10 22H2. Captures the target process AND its child processes (Discord plays voice
from a child process, so we pass the root Discord.exe PID).

Delivers 16 kHz mono float32 to the callback (Windows does the resampling for us).
"""
from __future__ import annotations

import ctypes
import logging
import threading
from ctypes import POINTER, Structure, byref, c_int, c_longlong, c_uint32, c_uint64, c_ushort, c_ulong, c_void_p, c_wchar_p
from typing import Callable, Optional

import numpy as np

log = logging.getLogger("wasapi")

if not hasattr(ctypes, "windll"):        # imported on non-Windows (tests)
    raise ImportError("WASAPI loopback is Windows-only")

import comtypes                                       # noqa: E402
from comtypes import GUID, HRESULT, IUnknown, COMMETHOD, COMObject  # noqa: E402
from ctypes.wintypes import DWORD, HANDLE, WORD, BYTE  # noqa: E402

VT_BLOB = 65
AUDIOCLIENT_ACTIVATION_TYPE_PROCESS_LOOPBACK = 1
PROCESS_LOOPBACK_MODE_INCLUDE_TARGET_PROCESS_TREE = 0
AUDCLNT_SHAREMODE_SHARED = 0
AUDCLNT_STREAMFLAGS_LOOPBACK = 0x00020000
AUDCLNT_STREAMFLAGS_EVENTCALLBACK = 0x00040000
AUDCLNT_STREAMFLAGS_SRC_DEFAULT_QUALITY = 0x08000000
AUDCLNT_STREAMFLAGS_AUTOCONVERTPCM = 0x80000000
AUDCLNT_BUFFERFLAGS_SILENT = 0x2
WAVE_FORMAT_PCM = 1


class WAVEFORMATEX(Structure):
    _fields_ = [("wFormatTag", WORD), ("nChannels", WORD), ("nSamplesPerSec", DWORD),
                ("nAvgBytesPerSec", DWORD), ("nBlockAlign", WORD), ("wBitsPerSample", WORD), ("cbSize", WORD)]


class PROCESS_LOOPBACK_PARAMS(Structure):
    _fields_ = [("TargetProcessId", DWORD), ("ProcessLoopbackMode", c_int)]


class AUDIOCLIENT_ACTIVATION_PARAMS(Structure):
    _fields_ = [("ActivationType", c_int), ("ProcessLoopbackParams", PROCESS_LOOPBACK_PARAMS)]


class PROPVARIANT_BLOB(Structure):
    _fields_ = [("vt", c_ushort), ("r1", c_ushort), ("r2", c_ushort), ("r3", c_ushort),
                ("cbSize", c_ulong), ("pBlobData", c_void_p)]


class IAudioClient(IUnknown):
    _iid_ = GUID("{1CB9AD4C-DBFA-4c32-B178-C2F568A703B2}")
    _methods_ = [
        COMMETHOD([], HRESULT, "Initialize", (["in"], DWORD, "ShareMode"), (["in"], DWORD, "StreamFlags"),
                  (["in"], c_longlong, "hnsBufferDuration"), (["in"], c_longlong, "hnsPeriodicity"),
                  (["in"], POINTER(WAVEFORMATEX), "pFormat"), (["in"], POINTER(GUID), "AudioSessionGuid")),
        COMMETHOD([], HRESULT, "GetBufferSize", (["out"], POINTER(c_uint32), "n")),
        COMMETHOD([], HRESULT, "GetStreamLatency", (["out"], POINTER(c_longlong), "l")),
        COMMETHOD([], HRESULT, "GetCurrentPadding", (["out"], POINTER(c_uint32), "p")),
        COMMETHOD([], HRESULT, "IsFormatSupported", (["in"], DWORD, "m"), (["in"], POINTER(WAVEFORMATEX), "f"),
                  (["out"], POINTER(POINTER(WAVEFORMATEX)), "c")),
        COMMETHOD([], HRESULT, "GetMixFormat", (["out"], POINTER(POINTER(WAVEFORMATEX)), "f")),
        COMMETHOD([], HRESULT, "GetDevicePeriod", (["out"], POINTER(c_longlong), "a"), (["out"], POINTER(c_longlong), "b")),
        COMMETHOD([], HRESULT, "Start"),
        COMMETHOD([], HRESULT, "Stop"),
        COMMETHOD([], HRESULT, "Reset"),
        COMMETHOD([], HRESULT, "SetEventHandle", (["in"], HANDLE, "h")),
        COMMETHOD([], HRESULT, "GetService", (["in"], POINTER(GUID), "riid"), (["out"], POINTER(POINTER(IUnknown)), "ppv")),
    ]


class IAudioCaptureClient(IUnknown):
    _iid_ = GUID("{C8ADBD64-E71E-48a0-A4DE-185C395CD317}")
    _methods_ = [
        COMMETHOD([], HRESULT, "GetBuffer", (["out"], POINTER(POINTER(BYTE)), "data"), (["out"], POINTER(c_uint32), "frames"),
                  (["out"], POINTER(DWORD), "flags"), (["out"], POINTER(c_uint64), "devpos"), (["out"], POINTER(c_uint64), "qpc")),
        COMMETHOD([], HRESULT, "ReleaseBuffer", (["in"], c_uint32, "frames")),
        COMMETHOD([], HRESULT, "GetNextPacketSize", (["out"], POINTER(c_uint32), "frames")),
    ]


class IActivateAudioInterfaceAsyncOperation(IUnknown):
    _iid_ = GUID("{72A22D78-CDE4-431D-B8CC-843A71199B6D}")
    _methods_ = [
        COMMETHOD([], HRESULT, "GetActivateResult", (["out"], POINTER(ctypes.c_long), "hr"),
                  (["out"], POINTER(POINTER(IUnknown)), "iface")),
    ]


class IActivateAudioInterfaceCompletionHandler(IUnknown):
    _iid_ = GUID("{41D949AB-9862-444A-80F6-C261334DA5EB}")
    _methods_ = [
        COMMETHOD([], HRESULT, "ActivateCompleted", (["in"], POINTER(IActivateAudioInterfaceAsyncOperation), "op")),
    ]


class IAgileObject(IUnknown):
    _iid_ = GUID("{94ea2b94-e9cc-49e0-c0ff-ee64ca8f5b90}")
    _methods_ = []


class _Handler(COMObject):
    _com_interfaces_ = [IActivateAudioInterfaceCompletionHandler, IAgileObject]

    def __init__(self):
        super().__init__()
        self.done = threading.Event()

    def IActivateAudioInterfaceCompletionHandler_ActivateCompleted(self, this, op):
        self.done.set()
        return 0


_kernel32 = ctypes.windll.kernel32
_kernel32.CreateEventW.restype = HANDLE
_kernel32.WaitForSingleObject.argtypes = [HANDLE, DWORD]
_kernel32.CloseHandle.argtypes = [HANDLE]


def _activate(pid: int):
    mmdev = ctypes.WinDLL("Mmdevapi.dll")
    fn = mmdev.ActivateAudioInterfaceAsync
    fn.argtypes = [c_wchar_p, POINTER(GUID), POINTER(PROPVARIANT_BLOB),
                   POINTER(IActivateAudioInterfaceCompletionHandler),
                   POINTER(POINTER(IActivateAudioInterfaceAsyncOperation))]
    fn.restype = HRESULT

    params = AUDIOCLIENT_ACTIVATION_PARAMS()
    params.ActivationType = AUDIOCLIENT_ACTIVATION_TYPE_PROCESS_LOOPBACK
    params.ProcessLoopbackParams.TargetProcessId = pid
    params.ProcessLoopbackParams.ProcessLoopbackMode = PROCESS_LOOPBACK_MODE_INCLUDE_TARGET_PROCESS_TREE
    pv = PROPVARIANT_BLOB()
    pv.vt = VT_BLOB
    pv.cbSize = ctypes.sizeof(params)
    pv.pBlobData = ctypes.cast(ctypes.pointer(params), c_void_p)

    handler = _Handler()
    hptr = handler.QueryInterface(IActivateAudioInterfaceCompletionHandler)
    op = POINTER(IActivateAudioInterfaceAsyncOperation)()
    iid = IAudioClient._iid_
    fn("VAD\\Process_Loopback", byref(iid), byref(pv), hptr, byref(op))
    if not handler.done.wait(8):
        raise TimeoutError("Audio activation timed out")
    hr, unk = op.GetActivateResult()
    if hr < 0:
        raise OSError(f"Process loopback activation failed (HRESULT 0x{hr & 0xFFFFFFFF:08X})")
    return unk.QueryInterface(IAudioClient)


class ProcessLoopback:
    """Runs its own MTA thread. on_audio(np.float32 mono 16 kHz)."""

    FORMATS = [(16000, 1), (48000, 2), (44100, 2)]

    def __init__(self, pid: int, on_audio: Callable[[np.ndarray, int], None]):
        self.pid = pid
        self.on_audio = on_audio
        self._stop = threading.Event()
        self._ready = threading.Event()
        self.error: Optional[BaseException] = None
        self.rate = 16000
        self._thread: Optional[threading.Thread] = None

    def start(self, timeout: float = 10.0):
        self._thread = threading.Thread(target=self._run, daemon=True, name=f"loopback-{self.pid}")
        self._thread.start()
        self._ready.wait(timeout)
        if self.error:
            raise self.error
        if not self._ready.is_set():
            raise TimeoutError("Loopback capture did not start")

    def stop(self):
        self._stop.set()
        if self._thread:
            self._thread.join(2)

    def _run(self):
        comtypes.CoInitializeEx(comtypes.COINIT_MULTITHREADED)
        evt = None
        try:
            client, fmt = None, None
            last_err = None
            for rate, ch in self.FORMATS:
                try:
                    client = _activate(self.pid)
                    fmt = WAVEFORMATEX(WAVE_FORMAT_PCM, ch, rate, rate * ch * 2, ch * 2, 16, 0)
                    client.Initialize(AUDCLNT_SHAREMODE_SHARED,
                                      AUDCLNT_STREAMFLAGS_LOOPBACK | AUDCLNT_STREAMFLAGS_EVENTCALLBACK |
                                      AUDCLNT_STREAMFLAGS_AUTOCONVERTPCM | AUDCLNT_STREAMFLAGS_SRC_DEFAULT_QUALITY,
                                      200000, 0, byref(fmt), None)
                    break
                except Exception as e:
                    last_err, client = e, None
                    log.warning("Format %s Hz/%s ch refused: %s", rate, ch, e)
            if client is None:
                raise last_err or OSError("No capture format accepted")
            self.rate, self.channels = fmt.nSamplesPerSec, fmt.nChannels
            evt = _kernel32.CreateEventW(None, False, False, None)
            client.SetEventHandle(evt)
            cap = client.GetService(byref(IAudioCaptureClient._iid_)).QueryInterface(IAudioCaptureClient)
            client.Start()
            log.info("Process loopback started for pid %s at %s Hz / %s ch", self.pid, self.rate, self.channels)
            self._ready.set()
            block = fmt.nBlockAlign
            while not self._stop.is_set():
                _kernel32.WaitForSingleObject(evt, 100)
                while True:
                    n = cap.GetNextPacketSize()
                    if not n:
                        break
                    data, frames, flags, _, _ = cap.GetBuffer()
                    if frames:
                        if flags & AUDCLNT_BUFFERFLAGS_SILENT:
                            pcm = np.zeros(frames * self.channels, np.int16)
                        else:
                            pcm = np.frombuffer(ctypes.string_at(data, frames * block), np.int16).copy()
                    cap.ReleaseBuffer(frames)
                    if frames:
                        x = pcm.astype(np.float32) / 32768.0
                        if self.channels > 1:
                            x = x.reshape(-1, self.channels).mean(axis=1)
                        self.on_audio(x, self.rate)
            client.Stop()
        except BaseException as e:   # noqa: BLE001
            log.exception("Loopback thread")
            self.error = e
            self._ready.set()
        finally:
            if evt:
                _kernel32.CloseHandle(evt)
            comtypes.CoUninitialize()
