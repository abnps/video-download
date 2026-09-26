"""Ažuriranje samog yt-dlp-a, nezavisno od verzije aplikacije (bez Qt-a).

YouTube i drugi sajtovi se često mijenjaju, a yt-dlp izlazi mnogo češće od ove aplikacije.
Novi yt-dlp se skida sa PyPI-ja (čist Python paket, `py3-none-any.whl`), provjerava po SHA-256
i raspakuje u folder podataka korisnika. `activate()` ga pri pokretanju stavlja ispred verzije
iz instalacije; ako s njim nešto nije u redu, ostaje ona iz paketa.

VIDEODL_YTDLP_URL (testovi) zamjenjuje PyPI drugim izvorom istog oblika.
"""

import hashlib
import importlib.machinery
import json
import os
import re
import shutil
import sys
import threading
import urllib.request
import zipfile
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlsplit

PYPI_URL = "https://pypi.org/pypi/yt-dlp/json"
WHEEL_NAME = re.compile(r"^yt_dlp-(\d+(?:\.\d+){1,3})-py3-none-any\.whl$")
CHECK_INTERVAL_SECONDS = 24 * 60 * 60
MAX_WHEEL_BYTES = 64 * 1024 * 1024
STORE_NAME = "yt-dlp"
BAD_SUFFIX = ".neispravna"  # oznaka verzije koja se nije mogla pokrenuti: ne preuzima se ponovo


class YtdlpUpdateError(Exception):
    """Greška ažuriranja yt-dlp-a; `key` je ključ prevoda kad postoji."""

    def __init__(self, message: str, key: str | None = None):
        super().__init__(message)
        self.key = key


@dataclass(frozen=True)
class YtdlpRelease:
    version: str
    url: str
    sha256: str
    size: int


def store_dir() -> Path:
    """Folder podataka korisnika (isti kao za bridge.json), van instalacije koju piše instaler."""
    override = os.environ.get("VIDEODL_DATA_DIR")
    base = Path(override) if override else Path(os.environ.get("LOCALAPPDATA")
                                                or Path.home() / "AppData" / "Local") / "VideoDownload"
    return base / STORE_NAME


def parse_version(text: str) -> tuple[int, ...]:
    return tuple(int(part) for part in re.findall(r"\d+", text or "")[:4]) or (0,)


def installed_versions() -> list[str]:
    """Raspakovane verzije u folderu podataka, od najnovije ka starijoj."""
    store = store_dir()
    found = [path.name for path in store.iterdir() if (path / "yt_dlp" / "version.py").is_file()] \
        if store.is_dir() else []
    return sorted(found, key=parse_version, reverse=True)


def activate() -> str | None:
    """Stavlja preuzeti yt-dlp ispred onog iz paketa. Zove se PRIJE prvog `import yt_dlp`.

    Verzija iz paketa se namjerno ne uvozi radi poređenja: prvi uvoz bi je fiksirao.
    Preuzima se samo ono što je novije od aktivne, pa je najnoviji folder uvijek pravi izbor.
    Nova verzija mora proći i pravu provjeru (napraviti `YoutubeDL` sa zavisnostima iz paketa);
    ako ne prođe, dobija oznaku da se više ne preuzima, a radi prethodna (posljednja ispravna).
    """
    if "yt_dlp" in sys.modules:
        return None  # prekasno: ostaje ono što je već uvezeno
    versions = installed_versions()
    for index, version in enumerate(versions):
        folder = store_dir() / version
        finder = _Finder(str(folder))
        sys.meta_path.insert(0, finder)  # ispred PyInstaller-ovog uvoznika iz paketa
        try:
            import yt_dlp.version

            if yt_dlp.version.__version__ == version:
                from yt_dlp import YoutubeDL

                YoutubeDL({"quiet": True, "no_warnings": True}).close()
                # Ostaju samo ova i jedna starija, ispravna, za povratak; sve ranije se briše.
                prune(keep=tuple(versions[index:index + 2]))
                return version
        except Exception:  # noqa: BLE001 - neispravno preuzimanje ne smije oboriti aplikaciju
            pass
        sys.meta_path.remove(finder)
        for name in [name for name in sys.modules if name == "yt_dlp" or name.startswith("yt_dlp.")]:
            del sys.modules[name]
        shutil.rmtree(folder, ignore_errors=True)
        _mark_bad(version)
    return None


def _mark_bad(version: str) -> None:
    try:
        (store_dir() / f"{version}{BAD_SUFFIX}").write_text("", encoding="utf-8")
    except OSError:
        pass


def is_marked_bad(version: str) -> bool:
    return (store_dir() / f"{version}{BAD_SUFFIX}").is_file()


class _Finder:
    """Uvozi paket `yt_dlp` iz zadatog foldera, i u .exe-u gdje je paket zapakovan."""

    def __init__(self, path: str):
        self._path = [path]

    def find_spec(self, name, path=None, target=None):
        if name != "yt_dlp" and not name.startswith("yt_dlp."):
            return None
        return importlib.machinery.PathFinder.find_spec(name, self._path if name == "yt_dlp" else path, target)


def active_version() -> str:
    """Verzija koja se stvarno koristi (preuzeta ako je aktivirana, inače iz paketa)."""
    try:
        import yt_dlp.version

        return yt_dlp.version.__version__
    except Exception:  # noqa: BLE001 - bez yt-dlp-a nema ni verzije
        return "0"


def pending_version() -> str | None:
    """Preuzeta verzija koja čeka sljedeće pokretanje (novija od one koja sada radi)."""
    for version in installed_versions():
        if parse_version(version) > parse_version(active_version()):
            return version
    return None


def fetch_latest(url: str | None = None, opener=urllib.request.urlopen, timeout: float = 30) -> YtdlpRelease | None:
    """Posljednje izdanje sa PyPI-ja; None kad je već instalirano ono najnovije."""
    url = url or os.environ.get("VIDEODL_YTDLP_URL") or PYPI_URL
    with opener(_request(url), timeout=timeout) as response:
        data = json.loads(response.read(4 * 1024 * 1024).decode("utf-8"))
    version = str((data.get("info") or {}).get("version") or "")
    wheel = next((item for item in data.get("urls") or []
                  if isinstance(item, dict) and WHEEL_NAME.match(item.get("filename") or "")), None)
    if not version or not wheel:
        raise YtdlpUpdateError("PyPI nema wheel paket", key="ytdlp.no_asset")
    if parse_version(version) <= parse_version(active_version()) and not pending_version():
        return None
    if version in installed_versions():
        return None  # već preuzeto, primjenjuje se pri sljedećem pokretanju
    if is_marked_bad(version):
        return None  # ova verzija se kod nas već nije mogla pokrenuti; čeka se sljedeća
    return YtdlpRelease(version, wheel.get("url") or "", str((wheel.get("digests") or {}).get("sha256") or ""),
                        int(wheel.get("size") or 0))


def install(release: YtdlpRelease, on_progress: Callable[[int, int], None] | None = None,
            cancel: threading.Event | None = None, opener=urllib.request.urlopen, timeout: float = 60) -> str:
    """Preuzima i raspakuje wheel; vraća verziju koja će raditi od sljedećeg pokretanja."""
    if not re.fullmatch(r"[0-9a-fA-F]{64}", release.sha256):
        raise YtdlpUpdateError("PyPI nije dao SHA-256", key="ytdlp.checksum")
    store = store_dir()
    store.mkdir(parents=True, exist_ok=True)
    wheel = store / f"{release.version}.whl"
    target = store / release.version
    staging = store / f"{release.version}.novi"
    for stale in (wheel, staging):
        shutil.rmtree(stale, ignore_errors=True) if stale.is_dir() else stale.unlink(missing_ok=True)
    try:
        _download(release, wheel, on_progress, cancel, opener, timeout)
        _extract(wheel, staging)
        shutil.rmtree(target, ignore_errors=True)
        staging.rename(target)
    except BaseException:
        shutil.rmtree(staging, ignore_errors=True)
        raise
    finally:
        wheel.unlink(missing_ok=True)
    # Verzija koja upravo radi ostaje: program je koristi (i njene module učitava tek kad zatrebaju),
    # a ujedno je posljednja ispravna, za povratak ako nova ne prođe provjeru pri pokretanju.
    prune(keep=(release.version,))
    return release.version


def prune(keep: tuple[str, ...]) -> None:
    """Briše nepotrebne raspakovane verzije; aktivna (ona koja radi sada) se nikad ne briše."""
    keep = (*keep, active_version())
    for version in installed_versions():
        if version not in keep:
            shutil.rmtree(store_dir() / version, ignore_errors=True)


# ---------- interno ----------

def _request(url: str) -> urllib.request.Request:
    parts = urlsplit(url)
    local = parts.hostname in ("127.0.0.1", "localhost")
    if not (parts.scheme == "https" or (parts.scheme == "http" and local)):
        raise YtdlpUpdateError(f"Nesiguran link: {url}")
    from . import __version__

    return urllib.request.Request(url, headers={"User-Agent": f"VideoDownload/{__version__}"})


def _download(release: YtdlpRelease, wheel: Path, on_progress, cancel, opener, timeout) -> None:
    digest = hashlib.sha256()
    done = 0
    with opener(_request(release.url), timeout=timeout) as response, wheel.open("wb") as file:
        total = int(response.headers.get("Content-Length") or release.size or 0)
        while True:
            if cancel is not None and cancel.is_set():
                raise YtdlpUpdateError("Cancelled")
            chunk = response.read(256 * 1024)
            if not chunk:
                break
            done += len(chunk)
            if done > MAX_WHEEL_BYTES:
                raise YtdlpUpdateError("Paket je prevelik", key="ytdlp.failed")
            digest.update(chunk)
            file.write(chunk)
            if on_progress:
                on_progress(done, total)
    if digest.hexdigest().lower() != release.sha256.lower():
        raise YtdlpUpdateError("SHA-256 se ne poklapa", key="ytdlp.checksum")


def _extract(wheel: Path, staging: Path) -> None:
    """Raspakuje samo paket `yt_dlp`; imena van njega (npr. ../) se preskaču."""
    staging.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(wheel) as archive:
        members = [name for name in archive.namelist()
                   if (name == "yt_dlp/" or name.startswith("yt_dlp/")) and ".." not in Path(name).parts]
        archive.extractall(staging, members=members)
    if not (staging / "yt_dlp" / "version.py").is_file():
        raise YtdlpUpdateError("Paket nema yt_dlp", key="ytdlp.failed")
