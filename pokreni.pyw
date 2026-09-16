"""Pokretač bez konzole (pythonw). Koriste ga pokreni.bat i browser kad aplikacija nije pokrenuta."""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from videodl.gui import main  # noqa: E402

raise SystemExit(main())
