"""Jedan postupak pokretanja za sve ulaze (pokreni.pyw, python -m videodl, spakovani program).

Redoslijed je bitan: poziv iz browsera (native messaging host) ne smije učitavati Qt ni yt-dlp, a preuzeta
nova verzija yt-dlp-a mora se aktivirati PRIJE nego je bilo koji modul uveze.
"""

import sys


def run(argv: list[str] | None = None) -> int:
    argv = sys.argv if argv is None else argv
    from .native_host import is_browser_launch

    if is_browser_launch(argv):
        from .native_host import main as host_main

        return host_main()

    from .ytdlp_update import activate

    activate()

    from .gui import main

    return main()
