"""Napravi lokalizovane snimke stvarnih dijaloga dostignuća za sajt.

Podaci su izmišljeni primjeri; program se pokreće bez prozora i ne dira korisnička podešavanja.
"""

import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("QT_QPA_FONTDIR", "C:/Windows/Fonts")
os.environ["VIDEODL_DATA_DIR"] = tempfile.mkdtemp(prefix="videodl-dostignuca-")

from PySide6.QtGui import QFont  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

from videodl import achievements, i18n, theme  # noqa: E402
from videodl.dialogs import AchievementDialog, AchievementsListDialog  # noqa: E402

OUT = ROOT / "site" / "assets"
LANGUAGES = ("en", "bs", "de", "es", "fr")


def main() -> None:
    app = QApplication([])
    app.setStyle("Fusion")
    app.setFont(QFont("Segoe UI", 10))
    app.setStyleSheet(theme.stylesheet())
    OUT.mkdir(parents=True, exist_ok=True)
    for lang in LANGUAGES:
        i18n.set_language(lang)
        # Samo ilustracija: brojevi i osvojena dostignuća ne predstavljaju korisnika.
        state = achievements.AchievementState(
            earned={key: 0 for key in ("audio", "clip", "uhd", "browser", "sites5")},
            total_bytes=3 * achievements.GB,
        )
        listing = AchievementsListDialog(state, downloads=50, milestone_shown=50)
        listing.resize(520, 470)
        listing.show()
        app.processEvents()
        listing.grab().save(str(OUT / f"achievement-list-{lang}.png"))
        listing.close()

        badge = AchievementDialog(
            f"{achievements.ICONS['browser']} {i18n.tr('badge.browser')}",
            [i18n.tr("badge.browser.desc")],
            show_support=False,
        )
        badge.show()
        app.processEvents()
        badge.grab().save(str(OUT / f"achievement-toast-{lang}.png"))
        badge.close()


if __name__ == "__main__":
    main()
