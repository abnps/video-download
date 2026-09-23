"""Čitanje informacija o linku bez preuzimanja: jedan video ili plejlista."""

from collections.abc import Callable, Iterator
from dataclasses import dataclass

from yt_dlp import YoutubeDL

from .browser import Cookie, cookie_file
from .ytdl import LiveStreamError, base_options, is_live

# Kanal -> tabovi (Videos, Shorts...) -> videi: dva nivoa ugnježdavanja su dovoljna.
MAX_NESTING = 2

_PLAYLIST_TYPES = ("playlist", "multi_video")

Extractor = Callable[[str], dict]


@dataclass(frozen=True)
class Entry:
    url: str
    title: str
    thumbnail: str | None = None
    duration: float | None = None


@dataclass(frozen=True)
class ProbeResult:
    title: str
    entries: tuple[Entry, ...]
    is_playlist: bool


def probe(url: str, extract: Extractor | None = None, logger=None,
          http_headers: dict[str, str] | None = None, cookies: tuple[Cookie, ...] = (),
          whole_playlist: bool = False) -> ProbeResult:
    """`whole_playlist`: link videa koji je u plejlisti (watch?v=…&list=…) daje cijelu plejlistu."""
    extract = extract or _make_extractor(logger, http_headers, cookies, whole_playlist)
    info = extract(url)
    title = _title(info, url)
    if info.get("_type") not in _PLAYLIST_TYPES:
        if is_live(info):
            raise LiveStreamError("Live stream")
        return ProbeResult(title, (_entry(info, info.get("webpage_url") or url),), is_playlist=False)
    skipped = []
    entries = tuple(_flatten(info, extract, depth=0, skipped=skipped))
    if skipped and not entries:
        raise LiveStreamError("Live stream")  # npr. tab „Live" kanala: sve stavke su prenosi uživo
    return ProbeResult(title, entries, is_playlist=True)


def _flatten(info: dict, extract: Extractor, depth: int, skipped: list) -> Iterator[Entry]:
    for entry in info.get("entries") or ():
        if not entry:
            continue
        if is_live(entry):
            skipped.append(entry)  # prenos uživo u plejlisti ili kanalu se preskače
            continue
        entry_url = entry.get("url") or entry.get("webpage_url")
        if not entry_url:
            continue
        if _is_nested_playlist(entry) and depth < MAX_NESTING:
            nested = extract(entry_url)
            if nested.get("_type") in _PLAYLIST_TYPES:
                yield from _flatten(nested, extract, depth + 1, skipped)
                continue
        yield _entry(entry, entry_url)


def _is_nested_playlist(entry: dict) -> bool:
    if entry.get("_type") in _PLAYLIST_TYPES:
        return True
    # Na YouTube kanalu stavke plejliste su tabovi (YoutubeTab), ne videi.
    return entry.get("_type") == "url" and str(entry.get("ie_key") or "").endswith("Tab")


def _title(info: dict, fallback: str) -> str:
    return info.get("title") or info.get("id") or fallback


def _entry(info: dict, url: str) -> Entry:
    duration = info.get("duration")
    return Entry(url, _title(info, url), pick_thumbnail(info),
                 float(duration) if isinstance(duration, (int, float)) and duration > 0 else None)


def pick_thumbnail(info: dict) -> str | None:
    """Najmanja sličica koja je još dovoljno oštra za red u listi (širine 160+ px)."""
    thumbnails = [t for t in info.get("thumbnails") or () if isinstance(t, dict) and t.get("url")]
    sized = [t for t in thumbnails if (t.get("width") or 0) >= 160]
    if sized:
        return min(sized, key=lambda t: t["width"])["url"]
    if thumbnails:
        return thumbnails[-1]["url"]  # yt-dlp ih ređa od najlošije ka najboljoj
    return info.get("thumbnail")


def _make_extractor(logger, http_headers: dict[str, str] | None, cookies: tuple[Cookie, ...],
                    whole_playlist: bool = False) -> Extractor:
    def extract(url: str) -> dict:
        opts = base_options(logger)
        opts["extract_flat"] = "in_playlist"
        if whole_playlist:
            opts["noplaylist"] = False
        if http_headers:
            opts["http_headers"] = dict(http_headers)
        # Kolačići prijave postoje na disku samo dok traje ovo jedno čitanje.
        with cookie_file(cookies) as cookiefile:
            if cookiefile:
                opts["cookiefile"] = cookiefile
            with YoutubeDL(opts) as ydl:
                return ydl.extract_info(url, download=False)

    return extract
