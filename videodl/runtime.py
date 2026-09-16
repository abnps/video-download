"""Putanje i alati: razvoj (Python + PATH) ili instalirana verzija (PyInstaller + alati u paketu)."""

import shutil
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
APP_EXE = "VideoDownload.exe"
HOST_EXE = "videodl-host.exe"


def is_frozen() -> bool:
    return bool(getattr(sys, "frozen", False))


def app_dir() -> Path:
    """Folder instalirane aplikacije (pored VideoDownload.exe) ili korijen projekta u razvoju."""
    return Path(sys.executable).resolve().parent if is_frozen() else PROJECT_ROOT


def tools_dir() -> Path:
    return app_dir() / "tools"


def extension_dir() -> Path:
    return app_dir() / "extension"


def find_tool(name: str) -> str | None:
    """Alat iz paketa ima prednost; u razvoju se traži na PATH-u."""
    bundled = tools_dir() / f"{name}.exe"
    if bundled.is_file():
        return str(bundled)
    return shutil.which(name)


def ffmpeg_location() -> str | None:
    bundled = tools_dir() / "ffmpeg.exe"
    return str(tools_dir()) if bundled.is_file() else None


RUNNING_MUTEX = "VideoDownloadRunning"
_mutex_handle = None


def mark_running() -> None:
    """Imenovani mutex dok aplikacija radi; instaler pri ažuriranju čeka da nestane (CheckForMutexes)."""
    global _mutex_handle
    if sys.platform == "win32" and _mutex_handle is None:
        import ctypes

        _mutex_handle = ctypes.windll.kernel32.CreateMutexW(None, False, RUNNING_MUTEX)


def js_runtimes() -> dict:
    # yt-dlp sam uključuje samo Deno; Node iz paketa ili sa PATH-a rješava YouTube zaštitu.
    runtimes = {"deno": {}}
    node = find_tool("node")
    runtimes["node"] = {"path": node} if node else {}
    return runtimes
