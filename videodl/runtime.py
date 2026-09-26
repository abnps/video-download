"""Putanje i alati: razvoj (Python + PATH) ili instalirana verzija (PyInstaller + alati u paketu).

Windows je glavni sistem; macOS (beta) koristi iste funkcije s drugim putanjama.
"""

import os
import shutil
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
IS_WINDOWS = sys.platform == "win32"
IS_MAC = sys.platform == "darwin"


def exe(name: str) -> str:
    """Ime izvršnog fajla na ovom sistemu (`.exe` samo na Windowsu)."""
    return f"{name}.exe" if IS_WINDOWS else name


APP_EXE = exe("VideoDownload")
HOST_EXE = exe("videodl-host")


def is_frozen() -> bool:
    return bool(getattr(sys, "frozen", False))


def user_data_base(platform: str = sys.platform, environ=os.environ, home: Path | None = None) -> Path:
    """Folder u kojem program drži svoj folder podataka („VideoDownload"): na Windowsu %LOCALAPPDATA%,
    na Macu ~/Library/Application Support, drugdje XDG_DATA_HOME ili ~/.local/share."""
    home = Path(home) if home is not None else Path.home()
    if platform == "win32":
        return Path(environ.get("LOCALAPPDATA") or home / "AppData" / "Local")
    if platform == "darwin":
        return home / "Library" / "Application Support"
    return Path(environ.get("XDG_DATA_HOME") or home / ".local" / "share")


def app_dir() -> Path:
    """Folder instalirane aplikacije (pored VideoDownload.exe) ili korijen projekta u razvoju.
    Na Macu je to `Video Download.app/Contents/MacOS`."""
    return Path(sys.executable).resolve().parent if is_frozen() else PROJECT_ROOT


def bundle_dir() -> Path:
    """Gdje su alati i dodatak u paketu. Windows: pored .exe-a (build ih tamo kopira).
    Mac: PyInstaller ih stavlja u Contents/Frameworks (sys._MEIPASS), jer u Contents/MacOS smije biti samo kod."""
    if is_frozen() and IS_MAC and hasattr(sys, "_MEIPASS"):
        return Path(sys._MEIPASS)
    return app_dir()


def mac_app_bundle() -> Path | None:
    """`…/Video Download.app` instalirane Mac verzije, inače None."""
    if not (is_frozen() and IS_MAC):
        return None
    for parent in Path(sys.executable).resolve().parents:
        if parent.suffix == ".app":
            return parent
    return None


def tools_dir() -> Path:
    return bundle_dir() / "tools"


def extension_dir() -> Path:
    return bundle_dir() / "extension"


def find_tool(name: str) -> str | None:
    """Alat iz paketa ima prednost; u razvoju se traži na PATH-u."""
    bundled = tools_dir() / exe(name)
    if bundled.is_file():
        return str(bundled)
    return shutil.which(name)


def ffmpeg_location() -> str | None:
    bundled = tools_dir() / exe("ffmpeg")
    return str(tools_dir()) if bundled.is_file() else None


RUNNING_MUTEX = "VideoDownloadRunning"
_mutex_handle = None


def mark_running() -> None:
    """Imenovani mutex dok aplikacija radi; instaler pri ažuriranju čeka da nestane (CheckForMutexes).
    Samo Windows: na Macu nema instalera koji bi čekao."""
    global _mutex_handle
    if IS_WINDOWS and _mutex_handle is None:
        import ctypes

        _mutex_handle = ctypes.windll.kernel32.CreateMutexW(None, False, RUNNING_MUTEX)


def js_runtimes() -> dict:
    # yt-dlp sam uključuje samo Deno; Node iz paketa ili sa PATH-a rješava YouTube zaštitu.
    runtimes = {"deno": {}}
    node = find_tool("node")
    runtimes["node"] = {"path": node} if node else {}
    return runtimes
