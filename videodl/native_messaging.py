"""Registracija native messaging hosta za Chrome i Edge, samo za trenutnog korisnika (HKCU).

Uklanjanje: python -m videodl.native_messaging --uninstall
"""

import json
import os
import shutil
import sys
from pathlib import Path

from . import native_host

# ID proizlazi iz javnog ključa ("key") u extension/manifest.json.
EXTENSION_ID = "jfgcekfmjipklibljeacchccmebppklp"
PROJECT_ROOT = Path(__file__).resolve().parent.parent
REGISTRY_PATHS = (
    rf"Software\Google\Chrome\NativeMessagingHosts\{native_host.HOST_NAME}",
    rf"Software\Microsoft\Edge\NativeMessagingHosts\{native_host.HOST_NAME}",
)


def default_install_dir() -> Path:
    # Namjerno ne prati VIDEODL_DATA_DIR: registracija je jedna za korisnika.
    base = os.environ.get("LOCALAPPDATA") or str(Path.home() / "AppData" / "Local")
    return Path(base) / "VideoDownload" / "native-host"


def install_native_host(install_dir: Path | None = None, python_exe: str | None = None,
                        launch_command: list[str] | None = None, set_registry=None) -> Path:
    install_dir = Path(install_dir or default_install_dir())
    python_exe = python_exe or _sibling_exe("python.exe")
    launch_command = launch_command or [_sibling_exe("pythonw.exe"), str(PROJECT_ROOT / "pokreni.pyw")]

    install_dir.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(native_host.__file__, install_dir / "host.py")
    (install_dir / "host-config.json").write_text(
        json.dumps({"launch": launch_command}, ensure_ascii=False, indent=2), encoding="utf-8")
    # .bat se čita u OEM kodnoj stranici: u njemu smije biti samo ASCII putanja.
    script = install_dir / "host.bat"
    script.write_bytes(f'@echo off\r\n"{_ascii_path(python_exe)}" "%~dp0host.py" %*\r\n'.encode("ascii"))

    manifest = install_dir / f"{native_host.HOST_NAME}.json"
    manifest.write_text(json.dumps({
        "name": native_host.HOST_NAME,
        "description": "Video Download",
        "path": str(script),
        "type": "stdio",
        "allowed_origins": [f"chrome-extension://{EXTENSION_ID}/"],
    }, indent=2), encoding="utf-8")

    (set_registry or _set_registry_default)(REGISTRY_PATHS, str(manifest))
    return manifest


def uninstall_native_host(install_dir: Path | None = None) -> None:
    import winreg

    for subkey in REGISTRY_PATHS:
        try:
            winreg.DeleteKey(winreg.HKEY_CURRENT_USER, subkey)
        except FileNotFoundError:
            pass
    shutil.rmtree(install_dir or default_install_dir(), ignore_errors=True)


def _sibling_exe(name: str) -> str:
    candidate = Path(sys.executable).with_name(name)
    return str(candidate if candidate.exists() else sys.executable)


def _ascii_path(path: str) -> str:
    if path.isascii():
        return path
    import ctypes

    buffer = ctypes.create_unicode_buffer(32768)
    if ctypes.windll.kernel32.GetShortPathNameW(path, buffer, len(buffer)) and buffer.value.isascii():
        return buffer.value
    raise OSError(f"Putanja do Pythona ima znakove koje .bat fajl ne podržava: {path}")


def _set_registry_default(subkeys, value: str) -> None:
    import winreg

    for subkey in subkeys:
        with winreg.CreateKey(winreg.HKEY_CURRENT_USER, subkey) as key:
            winreg.SetValueEx(key, "", 0, winreg.REG_SZ, value)


if __name__ == "__main__":
    if "--uninstall" in sys.argv:
        uninstall_native_host()
        print("Registracija za browser je uklonjena.")
    else:
        print("Registrovano:", install_native_host())
