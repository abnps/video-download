"""Otvaranje fajlova i foldera: Explorer na Windowsu, Finder na Macu, podrazumijevani player."""

import os
import subprocess
import sys
from PySide6.QtCore import QUrl
from PySide6.QtGui import QDesktopServices


def reveal(path: str, platform: str = sys.platform, popen=subprocess.Popen) -> None:
    """Otvara Explorer/Finder: fajl je označen, a za folder se otvara sam folder."""
    if not path or not os.path.exists(path):
        return
    if os.path.isfile(path):
        if platform == "win32":
            popen(f'explorer /select,"{os.path.normpath(path)}"')
            return
        if platform == "darwin":
            popen(["open", "-R", path])  # Finder s označenim fajlom
            return
    QDesktopServices.openUrl(QUrl.fromLocalFile(path))


def play_file(path: str) -> None:
    """Otvara preuzeti fajl u podrazumijevanom playeru (Filmovi i TV, VLC…)."""
    QDesktopServices.openUrl(QUrl.fromLocalFile(path))
