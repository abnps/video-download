"""Snimci programa za sajt (odjeljak „Funkcije"): 5 jezika, svijetla i tamna tema, trenutni izgled programa.

    python tools/site_screenshots.py

Isti prizor kao snimci za Microsoft Store (`store_screenshots.shoot`: izmišljeni naslovi, ništa se ne preuzima),
ali u veličini za sajt: prozor 860×470, snimljen u duploj oštrini (1720×940) da je jasan i na telefonu.
Pokrenuti poslije svake veće promjene izgleda programa.
"""

import os
import sys
from pathlib import Path

os.environ.setdefault("QT_SCALE_FACTOR", "2")  # dupla oštrina: isti raspored, dvostruko više piksela
sys.path.insert(0, str(Path(__file__).resolve().parent))

import store_screenshots  # noqa: E402  (postavlja offscreen, fontove i privremene podatke)

SITE_ASSETS = store_screenshots.PROJECT / "site" / "assets"


def main() -> int:
    from PySide6.QtWidgets import QApplication

    store_screenshots.SIZE = (860, 470)
    app = QApplication([])
    app.setStyle("Fusion")
    from videodl import gui, theme

    app.setStyleSheet(theme.stylesheet())
    window = gui.MainWindow()
    window.show()
    for lang in ("en", "bs", "de", "es", "fr"):
        for name in ("light", "dark"):
            shot = store_screenshots.shoot(window, app, lang, name, SITE_ASSETS)
            target = SITE_ASSETS / f"screenshot-{name}-{lang}.png"
            shot.replace(target)
            print(target)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
