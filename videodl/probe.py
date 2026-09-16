"""Čitanje informacija o linku bez preuzimanja: jedan video ili plejlista."""

from collections.abc import Callable, Iterator
from dataclasses import dataclass

from yt_dlp import YoutubeDL

from .ytdl import base_options

# Kanal -> tabovi (Videos, Shorts...) -> videi: dva nivoa ugnježdavanja su dovoljna.
MAX_NESTING = 2

_PLAYLIST_TYPES = ("playlist", "multi_video")

Extractor = Callable[[str], dict]


@dataclass(frozen=True)
class Entry:
    url: str
    title: str


@dataclass(frozen=True)
class ProbeResult:
    title: str
    entries: tuple[Entry, ...]
    is_playlist: bool


def probe(url: str, extract: Extractor | None = None, logger=None,
          http_headers: dict[str, str] | None = None) -> ProbeResult:
    extract = extract or _make_extractor(logger, http_headers)
    info = extract(url)
    title = _title(info, url)
    if info.get("_type") not in _PLAYLIST_TYPES:
        entry = Entry(info.get("webpage_url") or url, title)
        return ProbeResult(title, (entry,), is_playlist=False)
    return ProbeResult(title, tuple(_flatten(info, extract, depth=0)), is_playlist=True)


def _flatten(info: dict, extract: Extractor, depth: int) -> Iterator[Entry]:
    for entry in info.get("entries") or ():
        if not entry:
            continue
        entry_url = entry.get("url") or entry.get("webpage_url")
        if not entry_url:
            continue
        if _is_nested_playlist(entry) and depth < MAX_NESTING:
            nested = extract(entry_url)
            if nested.get("_type") in _PLAYLIST_TYPES:
                yield from _flatten(nested, extract, depth + 1)
                continue
        yield Entry(entry_url, _title(entry, entry_url))


def _is_nested_playlist(entry: dict) -> bool:
    if entry.get("_type") in _PLAYLIST_TYPES:
        return True
    # Na YouTube kanalu stavke plejliste su tabovi (YoutubeTab), ne videi.
    return entry.get("_type") == "url" and str(entry.get("ie_key") or "").endswith("Tab")


def _title(info: dict, fallback: str) -> str:
    return info.get("title") or info.get("id") or fallback


def _make_extractor(logger, http_headers: dict[str, str] | None) -> Extractor:
    opts = base_options(logger)
    opts["extract_flat"] = "in_playlist"
    if http_headers:
        opts["http_headers"] = dict(http_headers)

    def extract(url: str) -> dict:
        with YoutubeDL(opts) as ydl:
            return ydl.extract_info(url, download=False)

    return extract
