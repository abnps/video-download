"""Pokretač bez konzole (pythonw). Koriste ga pokreni.bat i browser kad aplikacija nije pokrenuta."""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Preuzeti yt-dlp mora doći na red prije nego ga bilo koji modul uveze.
from videodl.ytdlp_update import activate  # noqa: E402

activate()

from videodl.gui import main  # noqa: E402

raise SystemExit(main())
