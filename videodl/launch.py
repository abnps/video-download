"""Jedan postupak pokretanja za sve ulaze (pokreni.pyw, python -m videodl, spakovani program).

Redoslijed je bitan: poziv iz browsera (native messaging host) ne smije učitavati Qt ni yt-dlp, a preuzeta
nova verzija yt-dlp-a mora se aktivirati PRIJE nego je bilo koji modul uveze (u pozadini; ko ga treba,
prvo zove `ytdlp_update.ensure_ready()`).
"""

import sys


def run(argv: list[str] | None = None) -> int:
    argv = sys.argv if argv is None else argv
    from . import runtime
    from .native_host import is_browser_launch

    if runtime.is_frozen() and runtime.IS_LINUX:
        runtime.restore_system_env()

    if is_browser_launch(argv):
        from .native_host import main as host_main

        return host_main()

    from .ytdlp_update import start_background

    start_background()  # yt-dlp se aktivira i učitava paralelno s prozorom

    from .gui import main

    return main()
