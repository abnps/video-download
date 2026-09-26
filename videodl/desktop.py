"""Otvaranje fajlova i foldera u Windowsu (Explorer, podrazumijevani player)."""

import os
import subprocess
import sys
from PySide6.QtCore import QUrl
from PySide6.QtGui import QDesktopServices


def reveal(path: str) -> None:
    """Otvara Explorer: fajl je označen, a za folder se otvara sam folder."""
    if not path or not os.path.exists(path):
        return
    if sys.platform == "win32" and os.path.isfile(path):
        subprocess.Popen(f'explorer /select,"{os.path.normpath(path)}"')
        return
    QDesktopServices.openUrl(QUrl.fromLocalFile(path))

def play_file(path: str) -> None:
    """Otvara preuzeti fajl u podrazumijevanom playeru (Filmovi i TV, VLC…)."""
    QDesktopServices.openUrl(QUrl.fromLocalFile(path))
