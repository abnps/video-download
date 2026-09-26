"""Pokretač bez konzole (pythonw). Koriste ga pokreni.bat i browser kad aplikacija nije pokrenuta."""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Mac: browser pokreće ovaj isti program kao native messaging host (Windows ima poseban videodl-host.exe).
from videodl.native_host import is_browser_launch  # noqa: E402

if is_browser_launch(sys.argv):
    from videodl.native_host import main as host_main

    raise SystemExit(host_main())

# Preuzeti yt-dlp mora doći na red prije nego ga bilo koji modul uveze.
from videodl.ytdlp_update import activate  # noqa: E402

activate()

from videodl.gui import main  # noqa: E402

raise SystemExit(main())
