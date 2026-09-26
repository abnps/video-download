"""Automatsko ažuriranje sa GitHub izdanja (bez Qt-a).

Repo je javan, pa se posljednje izdanje čita i preuzima običnim HTTPS-om: korisniku ne treba
GitHub nalog ni `gh`. Ako GitHub odbije pristup (npr. repo ponovo privatan), a `gh` je
instaliran i prijavljen, koristi se on. Izdanje mora imati `VideoDownload-Setup-<verzija>.exe`,
`.exe.sha256` i potpisan opis `release.json` + `release.json.sig` (od v0.9.6): instaler se pokreće
tek kad je opis potpisan našim ključem i instaler mu odgovara (verzija, ime, veličina, SHA-256).
U aplikaciji nema tokena.

VIDEODL_UPDATE_URL (testovi) zamjenjuje GitHub lokalnim HTTP serverom sa istim JSON-om.
"""

import dataclasses
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.request
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlsplit

from . import __version__, release_signing

RELEASES_REPO = "abnps/video-download"
LATEST_URL = f"https://api.github.com/repos/{RELEASES_REPO}/releases/latest"
# Odgovori koji znače „bez prijave ne može" (privatan repo): tada ima smisla probati gh.
_NEEDS_LOGIN = (401, 403, 404)
INSTALLER_NAME = re.compile(r"^VideoDownload-Setup-(\d+(?:\.\d+){1,3})\.exe$")
# Mac (beta): disk image uz izdanje; program ga ne instalira sam nego otvara njegov link.
MAC_INSTALLER_NAME = re.compile(r"^VideoDownload-macOS-arm64-(\d+(?:\.\d+){1,3})\.dmg$")
PLATFORM = sys.platform  # testovi ga postavljaju da bi isti test važio na svakom sistemu
CHECK_INTERVAL_SECONDS = 24 * 60 * 60
MAX_NOTES = 800
_NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)  # prozor aplikacije ne smije bljeskati konzolom

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
    installer_url: str  # prazno kad se preuzima preko gh
    checksum_url: str
    size: int
    tag: str = ""
    manifest_url: str = ""  # potpisan opis izdanja (release.json)
    signature_url: str = ""  # njegov potpis (release.json.sig)


def parse_version(text: str) -> tuple[int, ...]:
    return tuple(int(part) for part in re.findall(r"\d+", text or "")[:4]) or (0,)


def is_newer(candidate: str, current: str = __version__) -> bool:
    return parse_version(candidate) > parse_version(current)


def is_installed_app() -> bool:
    return bool(getattr(sys, "frozen", False))


def can_self_install(platform: str | None = None) -> bool:
    """Samo Windows verzija sama preuzima i pokreće instaler; Mac otvara link za preuzimanje."""
    return (platform or PLATFORM) == "win32"


def parse_release(data) -> Release | None:
    if not isinstance(data, dict) or data.get("draft") or data.get("prerelease"):
        return None
    assets = {asset.get("name"): asset for asset in data.get("assets") or [] if isinstance(asset, dict)}
    pattern = INSTALLER_NAME if PLATFORM == "win32" else MAC_INSTALLER_NAME
    for name, asset in assets.items():
        match = pattern.match(name or "")
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
                tag=data.get("tag_name") or "",
                manifest_url=(assets.get(release_signing.MANIFEST_NAME) or {}).get("browser_download_url") or "",
                signature_url=(assets.get(release_signing.SIGNATURE_NAME) or {}).get("browser_download_url") or "",
            )
    if PLATFORM != "win32":
        return None  # izdanje bez Mac verzije: za ovaj sistem nema ništa novo
    raise UpdateError("Release has no installer", key="update.no_asset")


def fetch_latest(url: str | None = None, opener=urllib.request.urlopen, runner=subprocess.run,
                 timeout: float = 30) -> Release | None:
    """Posljednje izdanje; None kad izdanja još nema. HTTPS prvo, `gh` samo kao rezerva."""
    test_url = url or os.environ.get("VIDEODL_UPDATE_URL")
    try:
        with opener(_request(test_url or LATEST_URL), timeout=timeout) as response:
            return parse_release(json.loads(response.read(2 * 1024 * 1024).decode("utf-8")))
    except urllib.error.HTTPError as exc:
        if test_url or exc.code not in _NEEDS_LOGIN:
            raise UpdateError(f"HTTP {exc.code}") from exc
        http_error = exc
    except urllib.error.URLError as exc:
        # Nema mreže ili je GitHub nedostupan: gh bi pao iz istog razloga.
        raise UpdateError(str(exc.reason or exc)) from exc
    try:
        gh = gh_path()
    except UpdateError:
        if http_error.code == 404:
            return None  # javan repo bez ijednog izdanja izgleda isto kao privatan
        raise
    return _fetch_with_gh(gh, runner, timeout)


def _fetch_with_gh(gh: str, runner, timeout: float) -> Release | None:
    result = runner([gh, "api", f"repos/{RELEASES_REPO}/releases/latest"], capture_output=True,
                    text=True, encoding="utf-8", timeout=timeout, creationflags=_NO_WINDOW)
    if result.returncode != 0:
        if "Not Found" in (result.stderr or ""):
            return None  # još nema nijednog izdanja
        raise UpdateError(_gh_error(result.stderr))
    release = parse_release(json.loads(result.stdout))
    # GitHub i za privatni repo vraća browser_download_url, ali bez prijave daje 404:
    # u gh načinu se preuzima isključivo preko gh.
    return dataclasses.replace(release, installer_url="", checksum_url="", manifest_url="",
                               signature_url="") if release else None


def download_installer(release: Release, target_dir: Path, on_progress: Callable[[int, int], None] | None = None,
                       cancel: threading.Event | None = None, opener=urllib.request.urlopen,
                       popen=subprocess.Popen, timeout: float = 30) -> Path:
    target_dir.mkdir(parents=True, exist_ok=True)
    final = target_dir / release.installer_name
    checksum_file = target_dir / f"{release.installer_name}.sha256"
    manifest_file = target_dir / release_signing.MANIFEST_NAME
    signature_file = target_dir / release_signing.SIGNATURE_NAME
    extras = (checksum_file, manifest_file, signature_file)
    for stale in (final, *extras):
        stale.unlink(missing_ok=True)
    try:
        if release.installer_url:
            if not (release.manifest_url and release.signature_url):
                raise UpdateError("Release is not signed", key="update.unsigned")
            # Potpis se provjerava PRIJE preuzimanja velikog instalera.
            _fetch_small(release.manifest_url, manifest_file, opener, timeout)
            _fetch_small(release.signature_url, signature_file, opener, timeout)
            _verified_manifest(release, manifest_file, signature_file)
            _download_http(release, final, checksum_file, on_progress, cancel, opener, timeout)
        else:
            _download_gh(release, target_dir, final, on_progress, cancel, popen)
        _verify(final, checksum_file)
        manifest = _verified_manifest(release, manifest_file, signature_file)
        try:
            release_signing.check_installer(manifest, release.version, final)
        except release_signing.SignatureError as exc:
            raise UpdateError(str(exc), key="update.unsigned") from exc
    except BaseException:
        final.unlink(missing_ok=True)
        raise
    finally:
        for extra in extras:
            extra.unlink(missing_ok=True)
    return final


def launch_installer(path: Path, language: str) -> subprocess.Popen:
    """Tiha instalacija preko postojeće; instaler sačeka gašenje aplikacije i ponovo je pokrene."""
    return subprocess.Popen([
        str(path), "/SILENT", "/SUPPRESSMSGBOXES", "/NORESTART", "/CLOSEAPPLICATIONS",
        f"/LANG={INSTALLER_LANGUAGES.get(language, 'english')}", "/update=1",
    ], close_fds=True)


# ---------- gh ----------

def gh_path() -> str:
    found = shutil.which("gh")
    if not found:
        # Aplikacija pokrenuta iz Start menija ne mora imati isti PATH kao terminal.
        for candidate in (Path(os.environ.get("ProgramFiles", r"C:\Program Files")) / "GitHub CLI" / "gh.exe",
                          Path(os.environ.get("LOCALAPPDATA", "")) / "Programs" / "GitHub CLI" / "gh.exe"):
            if candidate.is_file():
                found = str(candidate)
                break
    if not found:
        raise UpdateError("GitHub CLI (gh) not found", key="update.no_gh")
    return found


def _gh_error(stderr: str | None) -> str:
    lines = [line.strip() for line in (stderr or "").splitlines() if line.strip()]
    return lines[-1] if lines else "gh"


def _download_gh(release: Release, target_dir: Path, final: Path, on_progress, cancel, popen) -> None:
    process = popen([gh_path(), "release", "download", release.tag, "--repo", RELEASES_REPO,
                     "--pattern", release.installer_name, "--pattern", f"{release.installer_name}.sha256",
                     "--pattern", release_signing.MANIFEST_NAME, "--pattern", release_signing.SIGNATURE_NAME,
                     "--dir", str(target_dir), "--clobber"],
                    stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, text=True, encoding="utf-8",
                    creationflags=_NO_WINDOW)
    while process.poll() is None:
        if cancel is not None and cancel.is_set():
            process.kill()
            process.wait()
            raise UpdateError("Cancelled")
        if on_progress and final.exists():
            on_progress(final.stat().st_size, release.size)
        time.sleep(0.3)
    if process.returncode != 0:
        raise UpdateError(_gh_error(process.stderr.read() if process.stderr else ""))
    if on_progress and final.exists():
        on_progress(final.stat().st_size, release.size)


# ---------- HTTP (testovi) ----------

def _request(url: str) -> urllib.request.Request:
    parts = urlsplit(url)
    local = parts.hostname in ("127.0.0.1", "localhost")
    if not (parts.scheme == "https" or (parts.scheme == "http" and local)):
        raise UpdateError(f"Nesiguran link za ažuriranje: {url}")
    headers = {"User-Agent": f"VideoDownload/{__version__}"}  # GitHub API odbija zahtjev bez njega
    if parts.hostname == "api.github.com":
        headers["Accept"] = "application/vnd.github+json"
    return urllib.request.Request(url, headers=headers)


def _download_http(release: Release, final: Path, checksum_file: Path, on_progress, cancel, opener, timeout) -> None:
    with opener(_request(release.checksum_url), timeout=timeout) as response:
        checksum_file.write_bytes(response.read(4096))
    partial = final.with_suffix(".part")
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
                done += len(chunk)
                if on_progress:
                    on_progress(done, total)
        os.replace(partial, final)
    finally:
        partial.unlink(missing_ok=True)


def _fetch_small(url: str, target: Path, opener, timeout: float) -> None:
    with opener(_request(url), timeout=timeout) as response:
        target.write_bytes(response.read(64 * 1024))


def _verified_manifest(release: Release, manifest_file: Path, signature_file: Path) -> dict:
    if not manifest_file.is_file() or not signature_file.is_file():
        raise UpdateError("Release is not signed", key="update.unsigned")
    try:
        manifest = release_signing.verify_manifest(manifest_file.read_bytes(),
                                                   signature_file.read_text(encoding="ascii", errors="replace"))
    except release_signing.SignatureError as exc:
        raise UpdateError(str(exc), key="update.unsigned") from exc
    if manifest.get("version") != release.version or manifest.get("installer") != release.installer_name:
        raise UpdateError("Signed manifest is for another release", key="update.unsigned")
    return manifest


def _verify(final: Path, checksum_file: Path) -> None:
    expected = checksum_file.read_text(encoding="utf-8", errors="replace").split() if checksum_file.exists() else []
    if not expected or not re.fullmatch(r"[0-9a-fA-F]{64}", expected[0]):
        raise UpdateError("Checksum file is invalid", key="update.checksum")
    digest = hashlib.sha256()
    with final.open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(chunk)
    if digest.hexdigest().lower() != expected[0].lower():
        raise UpdateError("SHA-256 mismatch", key="update.checksum")
