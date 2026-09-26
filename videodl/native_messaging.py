"""Registracija native messaging hosta za Chrome, Edge i Firefox, samo za trenutnog korisnika.

Windows: ključevi u HKCU. Mac: manifest u ~/Library/Application Support/<browser>/NativeMessagingHosts.

Uklanjanje: python -m videodl.native_messaging --uninstall
"""

import json
import shutil
import sys
from pathlib import Path

from . import native_host
from .runtime import HOST_EXE, PROJECT_ROOT, app_dir, is_frozen, user_data_base

# ID proizlazi iz javnog ključa ("key") u extension/manifest.json.
EXTENSION_ID = "jfgcekfmjipklibljeacchccmebppklp"
REGISTRY_PATHS = (
    rf"Software\Google\Chrome\NativeMessagingHosts\{native_host.HOST_NAME}",
    rf"Software\Microsoft\Edge\NativeMessagingHosts\{native_host.HOST_NAME}",
)
# Firefox: isti host, ali svoj manifest (allowed_extensions umjesto allowed_origins) i svoj ključ.
FIREFOX_EXTENSION_ID = "video-download@abnps.github.io"
FIREFOX_REGISTRY_PATHS = (rf"Software\Mozilla\NativeMessagingHosts\{native_host.HOST_NAME}",)

# Mac: folderi browsera u ~/Library/Application Support. Upisuje se samo za browser koji postoji
# (folder postoji); aplikacija registraciju ponavlja pri svakom pokretanju, pa kasnije instaliran browser
# dobije svoju pri sljedećem pokretanju.
MAC_CHROMIUM_DIRS = ("Google/Chrome", "Microsoft Edge", "Chromium", "BraveSoftware/Brave-Browser")
MAC_FIREFOX_DIR = "Mozilla"


def default_install_dir(platform: str = sys.platform) -> Path:
    # Namjerno ne prati VIDEODL_DATA_DIR: registracija je jedna za korisnika.
    return user_data_base(platform) / "VideoDownload" / "native-host"


def install_native_host(install_dir: Path | None = None, python_exe: str | None = None,
                        launch_command: list[str] | None = None, set_registry=None,
                        frozen_app_dir: Path | None = None, platform: str = sys.platform,
                        mac_support_dir: Path | None = None, host_executable: Path | None = None) -> Path:
    install_dir = Path(install_dir or default_install_dir(platform))
    install_dir.mkdir(parents=True, exist_ok=True)
    if frozen_app_dir is None and host_executable is None and is_frozen():
        if platform == "darwin":
            host_executable = Path(sys.executable).resolve()  # Mac: host je sama aplikacija
        else:
            frozen_app_dir = app_dir()

    if host_executable is not None:
        script = Path(host_executable)
    elif frozen_app_dir is not None:
        # Instalirana Windows verzija: host je poseban .exe pored aplikacije i sam zna gdje je aplikacija.
        script = Path(frozen_app_dir) / HOST_EXE
    else:
        launch_command = launch_command or [_sibling_exe("pythonw.exe"), str(PROJECT_ROOT / "pokreni.pyw")]
        shutil.copyfile(native_host.__file__, install_dir / "host.py")
        (install_dir / "host-config.json").write_text(
            json.dumps({"launch": launch_command}, ensure_ascii=False, indent=2), encoding="utf-8")
        if platform == "win32":
            python_exe = python_exe or _sibling_exe("python.exe")
            # .bat se čita u OEM kodnoj stranici: u njemu smije biti samo ASCII putanja.
            script = install_dir / "host.bat"
            script.write_bytes(f'@echo off\r\n"{_ascii_path(python_exe)}" "%~dp0host.py" %*\r\n'.encode("ascii"))
        else:
            python_exe = python_exe or sys.executable
            script = install_dir / "host.sh"
            script.write_text(f'#!/bin/sh\nexec "{python_exe}" "$(dirname "$0")/host.py" "$@"\n', encoding="utf-8")
            script.chmod(0o755)

    common = {"name": native_host.HOST_NAME, "description": "Video Download", "path": str(script), "type": "stdio"}
    manifest = install_dir / f"{native_host.HOST_NAME}.json"
    manifest.write_text(json.dumps({**common, "allowed_origins": [f"chrome-extension://{EXTENSION_ID}/"]},
                                   indent=2), encoding="utf-8")
    firefox = install_dir / f"{native_host.HOST_NAME}.firefox.json"
    firefox.write_text(json.dumps({**common, "allowed_extensions": [FIREFOX_EXTENSION_ID]}, indent=2),
                       encoding="utf-8")

    if platform == "win32":
        register = set_registry or _set_registry_default
        register(REGISTRY_PATHS, str(manifest))
        register(FIREFOX_REGISTRY_PATHS, str(firefox))
    elif platform == "darwin":
        for target, source in mac_manifest_targets(mac_support_dir, manifest, firefox):
            if target.parent.parent.is_dir():  # browser postoji
                target.parent.mkdir(exist_ok=True)
                shutil.copyfile(source, target)
    return manifest


def mac_manifest_targets(support_dir: Path | None, chrome_manifest: Path | None = None,
                         firefox_manifest: Path | None = None) -> list[tuple[Path, Path | None]]:
    """(gdje browser traži manifest, koji naš manifest ide tamo) za svaki podržani Mac browser."""
    support = Path(support_dir) if support_dir is not None else user_data_base("darwin")
    name = f"{native_host.HOST_NAME}.json"
    targets = [(support / folder / "NativeMessagingHosts" / name, chrome_manifest) for folder in MAC_CHROMIUM_DIRS]
    targets.append((support / MAC_FIREFOX_DIR / "NativeMessagingHosts" / name, firefox_manifest))
    return targets


def uninstall_native_host(install_dir: Path | None = None, platform: str = sys.platform,
                          mac_support_dir: Path | None = None) -> None:
    if platform == "win32":
        import winreg

        for subkey in REGISTRY_PATHS + FIREFOX_REGISTRY_PATHS:
            try:
                winreg.DeleteKey(winreg.HKEY_CURRENT_USER, subkey)
            except FileNotFoundError:
                pass
    elif platform == "darwin":
        for target, _source in mac_manifest_targets(mac_support_dir):
            try:
                target.unlink()
            except FileNotFoundError:
                pass
    shutil.rmtree(install_dir or default_install_dir(platform), ignore_errors=True)


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
