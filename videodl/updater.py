"""Automatsko ažuriranje: posljednje izdanje sa javnog GitHub repoa izdanja (bez Qt-a).

Izdanje mora imati instaler `VideoDownload-Setup-<verzija>.exe` i uz njega
`VideoDownload-Setup-<verzija>.exe.sha256`. Instaler se pokreće tek kad se SHA-256 poklopi.
"""

import hashlib
import json
import os
import re
import subprocess
import sys
import threading
import urllib.request
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlsplit

from . import __version__

RELEASES_REPO = "npgamy/video-download-releases"
LATEST_RELEASE_API = f"https://api.github.com/repos/{RELEASES_REPO}/releases/latest"
INSTALLER_NAME = re.compile(r"^VideoDownload-Setup-(\d+(?:\.\d+){1,3})\.exe$")
CHECK_INTERVAL_SECONDS = 24 * 60 * 60
MAX_NOTES = 800

# Naziv jezika u [Languages] sekciji Inno Setup skripte.
INSTALLER_LANGUAGES = {"bs": "bosnian", "en": "english", "de": "german", "es": "spanish", "fr": "french"}


class UpdateError(Exception):
    """Greška ažuriranja; `key` je ključ prevoda kad postoji, inače tekst ide kakav jeste."""

    def __init__(self, message: str, key: str | None = None):
        super().__init__(message)
        self.key = key


@dataclass(frozen=True)
class Release:
    version: str
    notes: str
    installer_name: str
    installer_url: str
    checksum_url: str
    size: int


def parse_version(text: str) -> tuple[int, ...]:
    return tuple(int(part) for part in re.findall(r"\d+", text or "")[:4]) or (0,)


def is_newer(candidate: str, current: str = __version__) -> bool:
    return parse_version(candidate) > parse_version(current)


def is_installed_app() -> bool:
    return bool(getattr(sys, "frozen", False))


def releases_url() -> str:
    # VIDEODL_UPDATE_URL služi testovima (lokalni server umjesto GitHuba).
    return os.environ.get("VIDEODL_UPDATE_URL") or LATEST_RELEASE_API


def _check_url(url: str) -> str:
    parts = urlsplit(url)
    local = parts.hostname in ("127.0.0.1", "localhost")
    if parts.scheme == "https" or (parts.scheme == "http" and local):
        return url
    raise UpdateError(f"Nesiguran link za ažuriranje: {url}")


def _request(url: str) -> urllib.request.Request:
    return urllib.request.Request(_check_url(url), headers={
        "Accept": "application/vnd.github+json",
        "User-Agent": f"VideoDownload/{__version__}",
    })


def fetch_latest(url: str | None = None, opener=urllib.request.urlopen, timeout: float = 15) -> Release | None:
    with opener(_request(url or releases_url()), timeout=timeout) as response:
        data = json.loads(response.read(2 * 1024 * 1024).decode("utf-8"))
    if not isinstance(data, dict) or data.get("draft") or data.get("prerelease"):
        return None
    assets = {asset.get("name"): asset for asset in data.get("assets") or [] if isinstance(asset, dict)}
    for name, asset in assets.items():
        match = INSTALLER_NAME.match(name or "")
        checksum = assets.get(f"{name}.sha256")
        if match and checksum:
            notes = (data.get("body") or "").strip()
            return Release(
                version=match.group(1),
                notes=notes[:MAX_NOTES] + ("…" if len(notes) > MAX_NOTES else ""),
                installer_name=name,
                installer_url=asset.get("browser_download_url") or "",
                checksum_url=checksum.get("browser_download_url") or "",
                size=int(asset.get("size") or 0),
            )
    raise UpdateError("Release has no installer", key="update.no_asset")


def download_installer(release: Release, target_dir: Path, on_progress: Callable[[int, int], None] | None = None,
                       cancel: threading.Event | None = None, opener=urllib.request.urlopen,
                       timeout: float = 30) -> Path:
    with opener(_request(release.checksum_url), timeout=timeout) as response:
        expected = response.read(4096).decode("utf-8", "replace").split()
    if not expected or not re.fullmatch(r"[0-9a-fA-F]{64}", expected[0]):
        raise UpdateError("Checksum file is invalid", key="update.checksum")

    target_dir.mkdir(parents=True, exist_ok=True)
    final = target_dir / release.installer_name
    partial = final.with_suffix(".part")
    digest = hashlib.sha256()
    done = 0
    try:
        with opener(_request(release.installer_url), timeout=timeout) as response, partial.open("wb") as file:
            total = int(response.headers.get("Content-Length") or release.size or 0)
            while True:
                if cancel is not None and cancel.is_set():
                    raise UpdateError("Cancelled")
                chunk = response.read(256 * 1024)
                if not chunk:
                    break
                file.write(chunk)
                digest.update(chunk)
                done += len(chunk)
                if on_progress:
                    on_progress(done, total)
        if digest.hexdigest().lower() != expected[0].lower():
            raise UpdateError("SHA-256 mismatch", key="update.checksum")
        os.replace(partial, final)
    finally:
        if partial.exists():
            partial.unlink()
    return final


def launch_installer(path: Path, language: str) -> subprocess.Popen:
    """Tiha instalacija preko postojeće; instaler zatvara i ponovo pokreće aplikaciju."""
    return subprocess.Popen([
        str(path), "/SILENT", "/SUPPRESSMSGBOXES", "/NORESTART", "/CLOSEAPPLICATIONS",
        f"/LANG={INSTALLER_LANGUAGES.get(language, 'english')}", "/update=1",
    ], close_fds=True)
