"""Zajedničke yt-dlp postavke, logger i čitljive poruke o greškama."""

import re

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


def reject_live(info: dict, *, incomplete: bool = False) -> None:
    """yt-dlp `match_filter`: prekida prije početka preuzimanja kad se ispostavi da je prenos uživo."""
    if is_live(info):
        raise LiveStreamError("Live stream")


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
    from .i18n import MESSAGE_DRM, MESSAGE_LIVE

    if message in (MESSAGE_DRM, MESSAGE_LIVE):
        return False
    if re.search(r"http error 4\d\d|unsupported url|private|members[- ]only|sign in|age", message, re.IGNORECASE):
        return False
    return bool(_NETWORK_ERROR.search(message or ""))


def error_message(exc: BaseException) -> str:
    from .i18n import MESSAGE_DRM, MESSAGE_LIVE

    # yt-dlp izuzetak iz match_filter-a ponekad umota u DownloadError.
    seen = exc
    while seen is not None:
        if isinstance(seen, LiveStreamError):
            return MESSAGE_LIVE
        wrapped = getattr(seen, "exc_info", None)
        seen = seen.__cause__ or seen.__context__ or (wrapped[1] if wrapped and wrapped[1] is not seen else None)
    text = str(exc).strip() or exc.__class__.__name__
    # yt-dlp za DRM sajtove vraća dugačku englesku poruku; prikaz je preveden (i18n „error.drm").
    if "[DRM]" in text or "DRM protection" in text:
        return MESSAGE_DRM
    # Jedan red: poruka stoji u redu liste i u statusnoj traci.
    return " ".join(_ERROR_PREFIX.sub("", text).split())
