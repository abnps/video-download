"""Zajedničke yt-dlp postavke, logger i čitljive poruke o greškama."""

import re
from pathlib import PurePosixPath
from urllib.parse import unquote, urlsplit

# YouTube traži JavaScript runtime za rješavanje zaštite linkova. yt-dlp sam
# uključuje samo Deno; Node dodajemo jer je češće već instaliran.
JS_RUNTIMES = ("deno", "node")

_ERROR_PREFIX = re.compile(r"^(?:ERROR:\s*)+")

# Prenos uživo nema kraja: preuzimanje bi trajalo dok traje prenos, a red bi stajao u nedogled.
LIVE_STATUSES = ("is_live", "is_upcoming")


class LiveStreamError(Exception):
    """Link je prenos uživo (ili najavljen prenos) i ne preuzima se."""


def is_live(info: dict) -> bool:
    return bool(info.get("is_live")) or info.get("live_status") in LIVE_STATUSES


class NotMediaError(Exception):
    """Link ne vodi na video ni audio (npr. .exe, .zip, .pdf ili obična stranica bez videa)."""


# Ekstenzije koje video/audio fajl smije imati kad server ne kaže tip sadržaja.
MEDIA_EXTENSIONS = frozenset((
    "mp4", "m4v", "mov", "mkv", "webm", "avi", "flv", "wmv", "mpg", "mpeg", "ts", "m2ts", "mts",
    "3gp", "3g2", "ogv", "mp3", "m4a", "m4b", "aac", "ogg", "oga", "opus", "wav", "flac", "wma",
    "aif", "aiff", "alac", "mka", "m3u8", "mpd", "f4m", "ism"))

# Fajlovi koji sigurno nisu video ni audio: odbijaju se bez ikakvog čitanja preko interneta.
NOT_MEDIA_EXTENSIONS = frozenset((
    "exe", "msi", "msix", "appx", "bat", "cmd", "ps1", "dll", "sys", "apk", "aab", "ipa", "dmg", "pkg",
    "deb", "rpm", "appimage", "iso", "img", "bin", "zip", "rar", "7z", "tar", "gz", "tgz", "bz2", "xz",
    "zst", "cab", "jar", "pdf", "doc", "docx", "xls", "xlsx", "ppt", "pptx", "odt", "ods", "odp", "rtf",
    "txt", "csv", "json", "xml", "epub", "jpg", "jpeg", "png", "gif", "bmp", "webp", "svg", "ico",
    "tif", "tiff", "heic", "psd", "torrent", "ttf", "otf", "woff", "woff2"))


def url_extension(url: str) -> str:
    """Ekstenzija posljednjeg dijela putanje linka (bez upita), malim slovima."""
    try:
        path = unquote(urlsplit(url).path)
    except ValueError:
        return ""
    return PurePosixPath(path).suffix.lower().lstrip(".")


def is_obviously_not_media(url: str) -> bool:
    return url_extension(url) in NOT_MEDIA_EXTENSIONS


def is_guessed_non_media(info: dict) -> bool:
    """yt-dlp za fajl koji server ne označi kao audio/video samo nagađa „možda je video"
    (`direct`, bez liste formata). Prihvata se samo ako ekstenzija zaista jeste video ili audio."""
    if not info.get("direct") or info.get("formats"):
        return False
    return str(info.get("ext") or "").lower() not in MEDIA_EXTENSIONS


def check_media(info: dict) -> None:
    if is_guessed_non_media(info):
        raise NotMediaError("Not a video or audio file")


def reject_live(info: dict, *, incomplete: bool = False) -> None:
    """yt-dlp `match_filter`: prekida prije početka preuzimanja kad se ispostavi da je prenos uživo
    ili da link uopšte nije video ni audio (npr. „Pokušaj ponovo" na linku za .exe)."""
    if is_live(info):
        raise LiveStreamError("Live stream")
    check_media(info)


class YdlLogger:
    """Hvata poruke yt-dlp-a umjesto ispisa u konzolu (GUI nema konzolu)."""

    def __init__(self):
        self.warnings: list[str] = []

    def debug(self, msg):
        pass

    def info(self, msg):
        pass

    def warning(self, msg):
        self.warnings.append(msg)
        del self.warnings[:-20]

    def error(self, msg):
        # Greška stiže i kao izuzetak; poruka se čita odatle.
        pass


def base_options(logger=None) -> dict:
    from .runtime import ffmpeg_location, js_runtimes

    options = {
        "quiet": True,
        "noprogress": True,
        "color": "no_color",
        "noplaylist": True,
        # Kratak prekid veze ne smije oboriti preuzimanje: yt-dlp sam ponavlja i nastavlja .part fajl.
        "retries": 10,
        "fragment_retries": 10,
        "extractor_retries": 3,
        "socket_timeout": 30,
        "continuedl": True,
        "js_runtimes": js_runtimes(),
        "logger": logger or YdlLogger(),
    }
    location = ffmpeg_location()
    if location:
        options["ffmpeg_location"] = location  # ffmpeg/ffprobe iz instaliranog paketa
    return options


# Poruke koje znače „veza je pukla ili server trenutno ne odgovara" (vrijedi pokušati ponovo).
_NETWORK_ERROR = re.compile(
    r"unable to download|timed out|timeout|connection|connection reset|network is unreachable|"
    r"remote end closed|temporary failure|name or service not known|getaddrinfo|"
    r"winerror 1005[1-4]|http error 5\d\d|read operation|incomplete|broken pipe",
    re.IGNORECASE)


def is_network_error(message: str) -> bool:
    """Greška zbog veze (vrijedi ponovo), za razliku od DRM-a, nepodržanog sajta ili 404."""
    from .i18n import MESSAGE_DRM, MESSAGE_LIVE, MESSAGE_NOT_MEDIA

    if message in (MESSAGE_DRM, MESSAGE_LIVE, MESSAGE_NOT_MEDIA):
        return False
    if re.search(r"http error 4\d\d|unsupported url|private|members[- ]only|sign in|age", message, re.IGNORECASE):
        return False
    return bool(_NETWORK_ERROR.search(message or ""))


def error_message(exc: BaseException) -> str:
    from yt_dlp.utils import UnsupportedError

    from .i18n import MESSAGE_DRM, MESSAGE_LIVE, MESSAGE_NOT_MEDIA

    # yt-dlp izuzetak iz match_filter-a ponekad umota u DownloadError.
    seen = exc
    while seen is not None:
        if isinstance(seen, LiveStreamError):
            return MESSAGE_LIVE
        # „Unsupported URL": obična stranica na kojoj yt-dlp nije našao ni video ni audio.
        if isinstance(seen, (NotMediaError, UnsupportedError)):
            return MESSAGE_NOT_MEDIA
        wrapped = getattr(seen, "exc_info", None)
        seen = seen.__cause__ or seen.__context__ or (wrapped[1] if wrapped and wrapped[1] is not seen else None)
    text = str(exc).strip() or exc.__class__.__name__
    # yt-dlp za DRM sajtove vraća dugačku englesku poruku; prikaz je preveden (i18n „error.drm").
    if "[DRM]" in text or "DRM protection" in text:
        return MESSAGE_DRM
    # Jedan red: poruka stoji u redu liste i u statusnoj traci.
    return " ".join(_ERROR_PREFIX.sub("", text).split())
