"""Zajedničke yt-dlp postavke, logger i čitljive poruke o greškama."""

import re

# YouTube traži JavaScript runtime za rješavanje zaštite linkova. yt-dlp sam
# uključuje samo Deno; Node dodajemo jer je češće već instaliran.
JS_RUNTIMES = ("deno", "node")

_ERROR_PREFIX = re.compile(r"^(?:ERROR:\s*)+")


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
    return {
        "quiet": True,
        "noprogress": True,
        "color": "no_color",
        "noplaylist": True,
        "js_runtimes": {name: {} for name in JS_RUNTIMES},
        "logger": logger or YdlLogger(),
    }


DRM_MESSAGE = "Video je zaštićen DRM-om (npr. Netflix, Apple TV+, Disney+) i ne može se preuzeti."


def error_message(exc: BaseException) -> str:
    text = str(exc).strip() or exc.__class__.__name__
    # yt-dlp za DRM sajtove vraća dugačku englesku poruku sa savjetima za prijavu greške.
    if "[DRM]" in text or "DRM protection" in text:
        return DRM_MESSAGE
    # Jedan red: poruka stoji u redu liste i u statusnoj traci.
    return " ".join(_ERROR_PREFIX.sub("", text).split())
