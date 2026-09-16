"""Predefinisani formati preuzimanja i pretvaranje u yt-dlp opcije."""

import hashlib
import os
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlsplit

from yt_dlp.utils import sanitize_filename

from .ytdl import base_options

# .150B ograničava naslov na 150 bajtova da putanja ne pređe Windows limit.
OUTPUT_NAME = "%(title).150B [%(id)s].%(ext)s"

# Pri istoj rezoluciji prednost imaju H.264 i AAC: takav MP4 se pušta svuda.
_COMPATIBLE = ("fps", "vcodec:h264", "acodec:aac")


@dataclass(frozen=True)
class Preset:
    key: str
    label: str
    short_label: str
    format: str
    format_sort: tuple[str, ...] = ()
    merge_output_format: str | None = None
    audio_codec: str | None = None
    audio_quality: str | None = None

    @property
    def is_audio(self) -> bool:
        return self.audio_codec is not None


PRESETS: tuple[Preset, ...] = (
    Preset("best", "Video – najbolji kvalitet (MP4)", "MP4 najbolji", "bv*+ba/b",
           ("res", *_COMPATIBLE), "mp4"),
    Preset("1080p", "Video – do 1080p (MP4)", "MP4 1080p", "bv*+ba/b", ("res:1080", *_COMPATIBLE), "mp4"),
    Preset("720p", "Video – do 720p (MP4)", "MP4 720p", "bv*+ba/b", ("res:720", *_COMPATIBLE), "mp4"),
    Preset("480p", "Video – do 480p (MP4)", "MP4 480p", "bv*+ba/b", ("res:480", *_COMPATIBLE), "mp4"),
    Preset("mp3", "Samo zvuk – MP3", "MP3", "ba/b", audio_codec="mp3", audio_quality="192"),
    Preset("m4a", "Samo zvuk – M4A", "M4A", "ba/b", ("acodec:aac",), audio_codec="m4a"),
)

DEFAULT_PRESET_KEY = "best"


def get_preset(key: str) -> Preset:
    for preset in PRESETS:
        if preset.key == key:
            return preset
    raise KeyError(key)


def safe_folder_name(name: str, fallback: str = "Plejlista") -> str:
    cleaned = sanitize_filename(name or "").strip().rstrip(". ")
    return cleaned[:80].rstrip(". ") or fallback


def build_ydl_options(preset: Preset, output_dir: str, subfolder: str | None = None,
                      logger=None, *, http_headers: dict[str, str] | None = None,
                      filename_title: str | None = None, source_url: str | None = None,
                      cookiefile: str | None = None) -> dict:
    target_dir = Path(output_dir)
    if subfolder:
        target_dir /= safe_folder_name(subfolder)

    opts = base_options(logger)
    opts["format"] = preset.format
    opts["outtmpl"] = _escape(str(target_dir)) + os.sep + _output_name(filename_title, source_url)
    if http_headers:
        opts["http_headers"] = dict(http_headers)
    if cookiefile:
        opts["cookiefile"] = cookiefile
    if preset.format_sort:
        opts["format_sort"] = list(preset.format_sort)
    if preset.merge_output_format:
        opts["merge_output_format"] = preset.merge_output_format
    if preset.is_audio:
        extract = {"key": "FFmpegExtractAudio", "preferredcodec": preset.audio_codec}
        if preset.audio_quality:
            extract["preferredquality"] = preset.audio_quality
        opts["postprocessors"] = [extract]
        # Da yt-dlp prepozna već konvertovan fajl i ne preuzima ga ponovo.
        opts["final_ext"] = preset.audio_codec
    return opts


def _escape(text: str) -> str:
    # '%' u putanji ili naslovu yt-dlp bi čitao kao dio šablona.
    return text.replace("%", "%%")


def _output_name(filename_title: str | None, source_url: str | None) -> str:
    if not filename_title:
        return OUTPUT_NAME
    # Direktan tok (npr. index.m3u8) nema smislen naslov ni id, pa ime daje naslov
    # stranice, a kratki otisak putanje toka razlikuje različite videe istog naslova.
    title = sanitize_filename(filename_title).strip()[:120].rstrip(". ") or "Video"
    parts = urlsplit(source_url or "")
    fingerprint = hashlib.sha1(f"{parts.netloc}{parts.path}".encode("utf-8")).hexdigest()[:8]
    return f"{_escape(title)} [{fingerprint}].%(ext)s"
