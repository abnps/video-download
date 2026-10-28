"""Putanje i alati: razvoj (Python + PATH) ili instalirana verzija (PyInstaller + alati u paketu).

Windows je glavni sistem; macOS i Linux (beta) koriste iste funkcije s drugim putanjama.
"""

import os
import shutil
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
IS_WINDOWS = sys.platform == "win32"
IS_MAC = sys.platform == "darwin"
IS_LINUX = sys.platform.startswith("linux")


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


def user_config_base(environ=os.environ, home: Path | None = None) -> Path:
    """Linux: XDG_CONFIG_HOME ili ~/.config (tu su browseri i QSettings)."""
    return Path(environ.get("XDG_CONFIG_HOME") or (Path(home) if home is not None else Path.home()) / ".config")


def app_dir() -> Path:
    """Folder instalirane aplikacije (pored VideoDownload.exe) ili korijen projekta u razvoju.
    Na Macu je to `Video Download.app/Contents/MacOS`."""
    return Path(sys.executable).resolve().parent if is_frozen() else PROJECT_ROOT


def bundle_dir() -> Path:
    """Gdje su alati i dodatak u paketu. Windows: pored .exe-a (build ih tamo kopira).
    Mac: PyInstaller ih stavlja u Contents/Frameworks (sys._MEIPASS), jer u Contents/MacOS smije biti samo kod.
    Linux: u _internal (sys._MEIPASS) unutar AppImage-a."""
    if is_frozen() and not IS_WINDOWS and hasattr(sys, "_MEIPASS"):
        return Path(sys._MEIPASS)
    return app_dir()


def linux_appimage(environ=os.environ) -> Path | None:
    """AppImage iz kojeg radi Linux verzija (AppImage ga upisuje u $APPIMAGE), inače None."""
    path = environ.get("APPIMAGE") if is_frozen() and IS_LINUX else None
    return Path(path) if path and os.path.isfile(path) else None


def restore_system_env(environ=os.environ) -> None:
    """Linux paket: PyInstaller usmjerava LD_LIBRARY_PATH na svoje biblioteke. Programi koje pokrećemo (xdg-open,
    browser, upravljač fajlova, node) moraju dobiti sistemske, inače znaju pući; staru vrijednost čuva u *_ORIG."""
    for name in ("LD_LIBRARY_PATH", "LD_PRELOAD"):
        original = environ.pop(f"{name}_ORIG", None)
        if original:
            environ[name] = original
        else:
            environ.pop(name, None)


LINUX_DESKTOP_ID = "io.github.abnps.videodownload"  # ime .desktop fajla i ikone (Wayland ga koristi kao app_id)


def _desktop_exec(path: Path) -> str:
    """Putanja za Exec= u .desktop fajlu: u navodnicima, s escape-om po Desktop Entry specifikaciji."""
    quoted = "".join("\\" + char if char in '"`$\\' else char for char in str(path))
    return '"' + quoted.replace("\\", "\\\\") + '"'


def install_linux_menu_entry(appimage: Path, icon: Path, data_home: Path | None = None) -> Path:
    """Linux „instalacija": prečica u meniju aplikacija i ikona za AppImage iz kojeg program radi. Osvježava se pri
    svakom pokretanju, pa prati i premješten fajl; ništa ne traži administratora."""
    base = Path(data_home) if data_home is not None else user_data_base()
    icons = base / "icons" / "hicolor" / "128x128" / "apps"
    icons.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(icon, icons / f"{LINUX_DESKTOP_ID}.png")
    entry = base / "applications" / f"{LINUX_DESKTOP_ID}.desktop"
    entry.parent.mkdir(parents=True, exist_ok=True)
    text = ("[Desktop Entry]\nType=Application\nName=Video Download\n"
            "Comment=Save videos as MP4 or audio as MP3\n"
            f"Exec={_desktop_exec(appimage)}\nIcon={LINUX_DESKTOP_ID}\nCategories=AudioVideo;Network;\n"
            f"Terminal=false\nStartupWMClass=VideoDownload\n")
    if not entry.is_file() or entry.read_text(encoding="utf-8") != text:
        entry.write_text(text, encoding="utf-8")
    return entry


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


def user_extension_dir(source: Path | None = None, target: Path | None = None) -> Path:
    """Folder dodatka za Chrome („Load unpacked"). Linux AppImage se pri svakom pokretanju otvara na drugoj
    privremenoj putanji (/tmp/.mount_…), pa Chrome dobija kopiju na stalnom mjestu, osvježenu pri pokretanju."""
    source = source or extension_dir()
    if target is None:
        if linux_appimage() is None:
            return source
        target = user_data_base() / "VideoDownload" / "extension"
    shutil.rmtree(target, ignore_errors=True)
    shutil.copytree(source, target)
    return target


_store_package: bool | None = None


def is_store_package() -> bool:
    """Program iz Microsoft Store paketa (MSIX): ima identitet paketa, a novu verziju donosi Store, ne mi."""
    global _store_package
    if _store_package is None:
        _store_package = False
        if IS_WINDOWS:
            import ctypes

            length = ctypes.c_uint32(0)
            try:
                # Bez paketa vraća APPMODEL_ERROR_NO_PACKAGE (15700); u paketu traži veći bafer (122).
                result = ctypes.windll.kernel32.GetCurrentPackageFullName(ctypes.byref(length), None)
                _store_package = result != 15700
            except (AttributeError, OSError):
                pass
    return _store_package


def bundled_tool(name: str) -> str | None:
    """Alat iz paketa programa (tools/), bez traženja po PATH-u."""
    bundled = tools_dir() / exe(name)
    return str(bundled) if bundled.is_file() else None


def find_tool(name: str) -> str | None:
    """Alat iz paketa ima prednost; u razvoju se traži na PATH-u."""
    return bundled_tool(name) or shutil.which(name)


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
