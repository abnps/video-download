"""Samo čita Store vezu s browserom izvan MSIX paketa.

    python tools/check_store_browser_link.py
    python tools/check_store_browser_link.py --legacy

Prvi poziv je završna provjera poslije privatnog Store ažuriranja na 1.0.3.0
ili novije. Drugi provjerava kompatibilnost instalirane 1.0.2 verzije.
"""

import argparse
import json
import os
import re
import struct
import subprocess
import sys
from pathlib import Path

PROJECT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT))

from videodl import native_host, native_messaging  # noqa: E402

STORE_PACKAGE_NAME = "abnps.VideoDownloadbyabnps"
MAX_REPLY_BYTES = 64 * 1024


def version_parts(value: str) -> tuple[int, int, int, int]:
    if not re.fullmatch(r"\d+\.\d+\.\d+\.\d+", value):
        raise ValueError(f"Neispravna verzija Store paketa: {value!r}")
    return tuple(int(part) for part in value.split("."))


def installed_store_version() -> str:
    result = subprocess.run(
        ["powershell.exe", "-NoProfile", "-NonInteractive", "-Command",
         f"Get-AppxPackage -Name '{STORE_PACKAGE_NAME}' | Select-Object -First 1 -ExpandProperty Version"],
        capture_output=True, text=True, timeout=20,
    )
    value = result.stdout.strip()
    if result.returncode != 0 or not value:
        raise RuntimeError("Store paket nije pronađen za trenutnog korisnika")
    version_parts(value)
    return value


def registry_default(subkey: str) -> str:
    import winreg

    with winreg.OpenKey(winreg.HKEY_CURRENT_USER, subkey) as key:
        value, kind = winreg.QueryValueEx(key, "")
    if kind != winreg.REG_SZ or not isinstance(value, str):
        raise ValueError("(Default) nije REG_SZ putanja")
    return value


def manifest_problems(data: dict, host_name: str, alias: Path, browser: str) -> list[str]:
    issues = []
    if data.get("name") != host_name:
        issues.append("pogrešno ime hosta u JSON-u")
    if data.get("type") != "stdio":
        issues.append("pogrešan tip hosta u JSON-u")
    host_path = data.get("path")
    if not isinstance(host_path, str) or os.path.normcase(host_path) != os.path.normcase(str(alias)):
        issues.append("JSON ne pokazuje na stalni Store alias")
    if browser == "Firefox":
        if data.get("allowed_extensions") != [native_messaging.FIREFOX_EXTENSION_ID]:
            issues.append("pogrešan Firefox ID dodatka")
        if "allowed_origins" in data:
            issues.append("Firefox JSON sadrži Chromium dozvole")
    else:
        expected = [f"chrome-extension://{value}/" for value in native_messaging.CHROMIUM_EXTENSION_IDS]
        if data.get("allowed_origins") != expected:
            issues.append("pogrešni Chrome/Edge ID-jevi dodatka")
        if "allowed_extensions" in data:
            issues.append("Chromium JSON sadrži Firefox dozvole")
    return issues


def status_reply(raw: bytes) -> dict:
    if len(raw) < 4:
        raise ValueError("Host nije vratio dužinu odgovora")
    (length,) = struct.unpack("<I", raw[:4])
    if length > MAX_REPLY_BYTES or len(raw) != 4 + length:
        raise ValueError("Host je vratio neispravan uokvireni odgovor")
    reply = json.loads(raw[4:].decode("utf-8"))
    if not isinstance(reply, dict) or reply.get("ok") is not True:
        raise ValueError("Host nije potvrdio status upit")
    return reply


def check_alias(alias: Path) -> dict:
    if not alias.is_file():
        raise FileNotFoundError(f"Store alias ne postoji: {alias}")
    message = json.dumps({"action": "status"}).encode("utf-8")
    frame = struct.pack("<I", len(message)) + message
    result = subprocess.run(
        [str(alias), f"chrome-extension://{native_messaging.EXTENSION_ID}/"],
        input=frame, capture_output=True, timeout=25,
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
    )
    if result.returncode != 0 or result.stderr:
        raise RuntimeError(f"Store alias nije čisto odgovorio (izlaz {result.returncode})")
    return status_reply(result.stdout)


def check_browser(browser: str, branch: str, host_name: str, alias: Path, folder: Path) -> list[str]:
    subkey = rf"Software\{branch}\NativeMessagingHosts\{host_name}"
    filename = f"{host_name}{'.firefox' if browser == 'Firefox' else ''}.json"
    expected = folder / filename
    issues = []
    try:
        actual = registry_default(subkey)
    except (OSError, ValueError) as error:
        return [f"HKCU ključ nije čitljiv: {error}"]
    if os.path.normcase(os.path.normpath(actual)) != os.path.normcase(os.path.normpath(str(expected))):
        issues.append(f"HKCU ne pokazuje na očekivani JSON: {actual}")
    try:
        data = json.loads(expected.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            raise ValueError("JSON nije objekt")
    except (OSError, ValueError) as error:
        return issues + [f"JSON manifest nije čitljiv: {error}"]
    return issues + manifest_problems(data, host_name, alias, browser)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--legacy", action="store_true", help="provjeri staro ime hosta (Store 1.0.2 ili noviji)")
    args = parser.parse_args()
    if sys.platform != "win32":
        parser.error("Ova provjera radi samo na Windowsu")

    host_name = native_host.LEGACY_HOST_NAME if args.legacy else native_host.HOST_NAME
    minimum = "1.0.2.0" if args.legacy else "1.0.3.0"
    alias = native_messaging.store_host_alias()
    folder = native_messaging.default_install_dir("win32")
    failures = []
    try:
        installed = installed_store_version()
        if version_parts(installed) < version_parts(minimum):
            message = f"Store verzija {installed} je starija od potrebne {minimum}"
            failures.append(message)
            print(message)
        else:
            print(f"Store verzija: {installed} (OK)")
    except (OSError, RuntimeError, ValueError, subprocess.TimeoutExpired) as error:
        message = f"Store verzija: {error}"
        failures.append(message)
        print(message)

    for browser, branch in (("Chrome", r"Google\Chrome"), ("Edge", r"Microsoft\Edge"),
                            ("Firefox", "Mozilla")):
        issues = check_browser(browser, branch, host_name, alias, folder)
        print(f"{browser}: {'OK' if not issues else '; '.join(issues)}")
        failures.extend(f"{browser}: {issue}" for issue in issues)
    try:
        reply = check_alias(alias)
        print(f"Store alias: OK (status={reply.get('ok')})")
    except (OSError, RuntimeError, ValueError, subprocess.TimeoutExpired) as error:
        failures.append(f"Store alias: {error}")
        print(f"Store alias: {error}")

    if failures:
        print(f"NIJE SPREMNO: neuspjelih provjera: {len(failures)}.")
        return 1
    print(f"OSNOVNE PROVJERE PROŠLE za {host_name}; potvrdi i stvarni dodatak u browseru.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
