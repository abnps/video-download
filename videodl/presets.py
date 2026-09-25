"""Predefinisani formati preuzimanja i pretvaranje u yt-dlp opcije."""

import hashlib
import os
import re
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlsplit

from yt_dlp.utils import download_range_func, sanitize_filename

from .i18n import tr
from .ytdl import base_options, reject_live

# .150B ograničava naslov na 150 bajtova da putanja ne pređe Windows limit.
OUTPUT_NAME = "%(title).150B [%(id)s].%(ext)s"

# Šabloni imena fajla (Preuzimanja → Ime fajla). Dio ispred naslova ostaje prazan kad sajt ne da
# taj podatak (npr. video bez izvođača), pa ime nikad ne počinje sa „NA - ".
# Bez [id] u imenu dva različita videa istog naslova dobiju isto ime: drugi se tada smatra već preuzetim.
NAME_TEMPLATES = {
    "title_id": OUTPUT_NAME,
    "title": "%(title).150B.%(ext)s",
    "artist_title": "%(artist,creator&{} - |).80B%(title).150B.%(ext)s",
    "channel_title": "%(channel,uploader&{} - |).80B%(title).150B.%(ext)s",
    "date_title": "%(upload_date>%Y-%m-%d&{} |)s%(title).150B.%(ext)s",
}
DEFAULT_NAME_TEMPLATE = "title_id"

# Pri istoj rezoluciji prednost imaju H.264 i AAC: takav MP4 se pušta svuda.
_COMPATIBLE = ("fps", "vcodec:h264", "acodec:aac")


@dataclass(frozen=True)
class Preset:
    key: str
    format: str
    format_sort: tuple[str, ...] = ()
    merge_output_format: str | None = None
    audio_codec: str | None = None
    audio_quality: str | None = None

    @property
    def is_audio(self) -> bool:
        return self.audio_codec is not None

    @property
    def label(self) -> str:
        return tr(f"preset.{self.key}")

    @property
    def short_label(self) -> str:
        return tr(f"preset.{self.key}.short")


PRESETS: tuple[Preset, ...] = (
    Preset("best", "bv*+ba/b", ("res", *_COMPATIBLE), "mp4"),
    Preset("1080p", "bv*+ba/b", ("res:1080", *_COMPATIBLE), "mp4"),
    Preset("720p", "bv*+ba/b", ("res:720", *_COMPATIBLE), "mp4"),
    Preset("480p", "bv*+ba/b", ("res:480", *_COMPATIBLE), "mp4"),
    Preset("mp3", "ba/b", audio_codec="mp3", audio_quality="192"),
    Preset("m4a", "ba/b", ("acodec:aac",), audio_codec="m4a"),
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


def parse_section(text: str) -> tuple[float, float] | None:
    """„2:30-6:10", „1:02:03 – 1:05:00" ili „90-120" u sekunde; None ako nije ispravno."""
    parts = re.split(r"\s*[-–—]\s*", (text or "").strip())
    if len(parts) != 2:
        return None
    try:
        start, end = (_seconds(part) for part in parts)
    except ValueError:
        return None
    return (start, end) if 0 <= start < end else None


def format_section(section: tuple[float, float] | None) -> str:
    return "–".join(_clock(value) for value in section) if section else ""


def subtitle_languages(language: str) -> list[str]:
    """Jezici titlova po redu želje: jezik aplikacije (za bs i srodni hr, sr), pa engleski."""
    wanted = ["bs", "hr", "sr"] if language == "bs" else [language]
    return [code for code in wanted if code != "en"] + ["en"]


def pick_subtitles(info: dict, wanted: list[str]) -> list[str]:
    """Najviše dva titla: prvi dostupan na jeziku aplikacije (ili srodnom) i engleski.

    Ručno napravljeni imaju prednost; kad ih nema, uzimaju se automatski (YouTube ih ima za skoro
    svaki video, i prevedene). Ključevi su tačno onakvi kakve sajt nudi (npr. "en-GB")."""
    manual = [key for key in (info.get("subtitles") or {}) if key != "live_chat"]
    auto = [key for key in (info.get("automatic_captions") or {}) if not key.endswith("-orig")]
    auto += [key for key in (info.get("automatic_captions") or {}) if key.endswith("-orig")]  # zadnja opcija

    def first(codes: list[str]) -> str | None:
        for keys in (manual, auto):
            for code in codes:
                for key in keys:
                    if key == code or key.startswith(code + "-"):
                        return key
        return None

    own = [code for code in wanted if code != "en"]
    chosen = [first(own) if own else None, first(["en"]) if "en" in wanted else None]
    return [key for key in chosen if key]


def _seconds(text: str) -> float:
    pieces = text.split(":")
    if not 1 <= len(pieces) <= 3 or not all(re.fullmatch(r"\d+(?:[.,]\d+)?", piece) for piece in pieces):
        raise ValueError(text)
    total = 0.0
    for piece in pieces:
        total = total * 60 + float(piece.replace(",", "."))
    return total


def _clock(value: float) -> str:
    whole = int(value)
    hours, rest = divmod(whole, 3600)
    minutes, seconds = divmod(rest, 60)
    return f"{hours}:{minutes:02d}:{seconds:02d}" if hours else f"{minutes}:{seconds:02d}"


def build_ydl_options(preset: Preset, output_dir: str, subfolder: str | None = None,
                      logger=None, *, http_headers: dict[str, str] | None = None,
                      filename_title: str | None = None, source_url: str | None = None,
                      cookiefile: str | None = None, section: tuple[float, float] | None = None,
                      subtitles: bool = False, subtitle_langs: list[str] | None = None,
                      thumbnail: bool = False, ratelimit: int | None = None,
                      name_template: str | None = None) -> dict:
    target_dir = Path(output_dir)
    if subfolder:
        target_dir /= safe_folder_name(subfolder)

    opts = base_options(logger)
    opts["format"] = preset.format
    opts["outtmpl"] = _escape(str(target_dir)) + os.sep + _with_section(
        _output_name(filename_title, source_url, name_template), section)
    opts["match_filter"] = reject_live
    if http_headers:
        opts["http_headers"] = dict(http_headers)
    if cookiefile:
        opts["cookiefile"] = cookiefile
    if preset.format_sort:
        opts["format_sort"] = list(preset.format_sort)
    if preset.merge_output_format:
        opts["merge_output_format"] = preset.merge_output_format
    postprocessors = []
    if thumbnail:
        # Sličica postaje omot fajla (MP3 i MP4); jpg jer ga svi playeri prikazuju.
        opts["writethumbnail"] = True
        postprocessors.append({"key": "FFmpegThumbnailsConvertor", "format": "jpg", "when": "before_dl"})
    if preset.is_audio:
        extract = {"key": "FFmpegExtractAudio", "preferredcodec": preset.audio_codec}
        if preset.audio_quality:
            extract["preferredquality"] = preset.audio_quality
        postprocessors.append(extract)
        # Da yt-dlp prepozna već konvertovan fajl i ne preuzima ga ponovo.
        opts["final_ext"] = preset.audio_codec
    elif subtitles:
        # Titl ide i u MP4 i kao .srt pored videa: mnogi playeri (Windows Media Player, TV, telefon)
        # ugrađeni titl ne prikazuju sami, a .srt istog imena učitaju odmah. Ručni imaju prednost,
        # a automatski se uzimaju kad ručnih nema; tačne jezike bira download.pick_subtitles.
        opts["writesubtitles"] = True
        opts["writeautomaticsub"] = True
        opts["subtitleslangs"] = list(subtitle_langs or ["en"])
        opts["subtitlesformat"] = "srt/vtt/best"
        postprocessors.append({"key": "FFmpegSubtitlesConvertor", "format": "srt", "when": "before_dl"})
        postprocessors.append({"key": "FFmpegEmbedSubtitle", "already_have_subtitle": True})
    if thumbnail:
        postprocessors.append({"key": "EmbedThumbnail", "already_have_thumbnail": False})
    if postprocessors:
        opts["postprocessors"] = postprocessors
    if section:
        # Samo dio videa; rezovi na tačnom mjestu traže ponovno kodiranje oko ključnih kadrova.
        opts["download_ranges"] = download_range_func(None, [section])
        opts["force_keyframes_at_cuts"] = True
    if ratelimit:
        opts["ratelimit"] = int(ratelimit)
    return opts


def _escape(text: str) -> str:
    # '%' u putanji ili naslovu yt-dlp bi čitao kao dio šablona.
    return text.replace("%", "%%")


def _with_section(template: str, section: tuple[float, float] | None) -> str:
    """Isječak dobija svoje ime, da ne zamijeni cijeli video niti se s njim pomiješa."""
    if not section:
        return template
    label = format_section(section).replace(":", ".")
    return template.replace(".%(ext)s", f" ({label}).%(ext)s")


def _output_name(filename_title: str | None, source_url: str | None, name_template: str | None = None) -> str:
    if not filename_title:
        return NAME_TEMPLATES.get(name_template or DEFAULT_NAME_TEMPLATE, OUTPUT_NAME)
    # Direktan tok (npr. index.m3u8) nema smislen naslov ni id, pa ime daje naslov
    # stranice, a kratki otisak putanje toka razlikuje različite videe istog naslova.
    title = sanitize_filename(filename_title).strip()[:120].rstrip(". ") or "Video"
    parts = urlsplit(source_url or "")
    fingerprint = hashlib.sha1(f"{parts.netloc}{parts.path}".encode("utf-8")).hexdigest()[:8]
    return f"{_escape(title)} [{fingerprint}].%(ext)s"
