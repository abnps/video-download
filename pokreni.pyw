"""Pokretač bez konzole (pythonw). Koriste ga pokreni.bat, browser kad aplikacija nije pokrenuta i PyInstaller.

Sav redoslijed pokretanja (poziv iz browsera, aktiviranje preuzetog yt-dlp-a, prozor) je u videodl/launch.py,
isti i za `python -m videodl`.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from videodl.launch import run  # noqa: E402

raise SystemExit(run())
