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


def error_message(exc: BaseException) -> str:
    text = str(exc).strip() or exc.__class__.__name__
    return _ERROR_PREFIX.sub("", text)
