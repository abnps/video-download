"""Windows dodaci prozoru preko ctypes-a: napredak na dugmetu u traci zadataka i tamna naslovna traka.

Na drugim sistemima i u testovima (offscreen) sve je tiho bez efekta; greška Windowsa ovdje
nikad ne smije srušiti program.
"""

import ctypes
import sys
from ctypes import wintypes

# ITaskbarList3 (shobjidl.h)
_CLSID_TASKBAR_LIST = "{56FDF344-FD6D-11d0-958A-006097C9A090}"
_IID_ITASKBAR_LIST3 = "{ea1afb91-9e28-4b86-90e9-9e9f8a5eefaf}"
_CLSCTX_INPROC_SERVER = 0x1
# Redni brojevi metoda u vtable: IUnknown (0–2), HrInit 3, …, SetProgressValue 9, SetProgressState 10.
_HR_INIT, _SET_PROGRESS_VALUE, _SET_PROGRESS_STATE = 3, 9, 10

NO_PROGRESS, INDETERMINATE, NORMAL, ERROR, PAUSED = 0x0, 0x1, 0x2, 0x4, 0x8
_SCALE = 1000

_DWMWA_USE_IMMERSIVE_DARK_MODE = 20


class _GUID(ctypes.Structure):
    _fields_ = [("Data1", wintypes.DWORD), ("Data2", wintypes.WORD), ("Data3", wintypes.WORD),
                ("Data4", ctypes.c_ubyte * 8)]


def _guid(text: str) -> _GUID:
    guid = _GUID()
    ctypes.oledll.ole32.CLSIDFromString(ctypes.c_wchar_p(text), ctypes.byref(guid))
    return guid


def _native_window(widget) -> int | None:
    """HWND prozora ili None kad nije pravi Windows prozor (drugi sistem, offscreen testovi)."""
    if sys.platform != "win32":
        return None
    from PySide6.QtGui import QGuiApplication

    if QGuiApplication.platformName() != "windows":
        return None
    try:
        return int(widget.winId())
    except (RuntimeError, TypeError, ValueError):
        return None


class TaskbarProgress:
    """Napredak na dugmetu programa u traci zadataka (kao pri kopiranju fajlova u Exploreru)."""

    def __init__(self, widget):
        self._widget = widget
        self._pointer = None
        self._failed = False
        self._state = None
        self._value = None

    def _call(self, index: int, argtypes: tuple, *args) -> bool:
        pointer = self._get()
        if pointer is None:
            return False
        vtable = ctypes.cast(ctypes.cast(pointer, ctypes.POINTER(ctypes.c_void_p))[0],
                             ctypes.POINTER(ctypes.c_void_p))
        function = ctypes.WINFUNCTYPE(ctypes.c_long, ctypes.c_void_p, *argtypes)(vtable[index])
        return function(pointer, *args) >= 0

    def _get(self):
        if self._pointer is not None or self._failed:
            return self._pointer
        try:
            ole32 = ctypes.oledll.ole32
            # Qt je COM već pokrenuo u glavnoj niti; ponovni poziv je bezopasan.
            ctypes.windll.ole32.CoInitializeEx(None, 0x2)
            pointer = ctypes.c_void_p()
            ole32.CoCreateInstance(ctypes.byref(_guid(_CLSID_TASKBAR_LIST)), None, _CLSCTX_INPROC_SERVER,
                                   ctypes.byref(_guid(_IID_ITASKBAR_LIST3)), ctypes.byref(pointer))
            self._pointer = pointer
            if not self._call(_HR_INIT, ()):
                raise OSError("HrInit")
        except (OSError, AttributeError, ValueError):
            self._pointer = None
            self._failed = True  # npr. stariji Windows ili sistem bez trake zadataka
        return self._pointer

    def set(self, fraction: float | None, state: int = NORMAL) -> None:
        """`fraction` 0..1; None znači „radi, ali procenat nije poznat" (zeleno klizanje)."""
        hwnd = _native_window(self._widget)
        if hwnd is None:
            return
        if fraction is None and state == NORMAL:
            state = INDETERMINATE
        if state != self._state:
            self._call(_SET_PROGRESS_STATE, (wintypes.HWND, ctypes.c_int), hwnd, state)
            self._state = state
            self._value = None
        if fraction is not None and state != NO_PROGRESS:
            value = round(max(0.0, min(1.0, fraction)) * _SCALE)
            if value != self._value:
                self._call(_SET_PROGRESS_VALUE, (wintypes.HWND, ctypes.c_ulonglong, ctypes.c_ulonglong),
                           hwnd, value, _SCALE)
                self._value = value

    def clear(self) -> None:
        self.set(None, NO_PROGRESS)


def set_dark_title_bar(widget, dark: bool) -> None:
    """Naslovna traka prozora prati temu programa (Windows 10 20H1+ / 11)."""
    hwnd = _native_window(widget)
    if hwnd is None:
        return
    value = ctypes.c_int(1 if dark else 0)
    try:
        ctypes.windll.dwmapi.DwmSetWindowAttribute(wintypes.HWND(hwnd), _DWMWA_USE_IMMERSIVE_DARK_MODE,
                                                   ctypes.byref(value), ctypes.sizeof(value))
    except (OSError, AttributeError):
        pass
