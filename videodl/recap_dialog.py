"""Prozor „Tvoj oktobar u Video Downloadu" (Ahmed 2.11.2026): kartica s brojkama koja se može sačuvati ili kopirati
kao slika za dijeljenje. Na slici su samo brojke i adresa sajta, bez naslova videa; ništa se ne šalje."""

import os

from PySide6.QtCore import QLocale, Qt, Signal
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QApplication, QDialog, QFileDialog, QFrame, QHBoxLayout, QLabel, QPushButton, QVBoxLayout,
)

from .dialogs import SITE_URL
from .i18n import get_language, tr
from .pacing import NAMES, family_of
from .recap import Summary
from .widgets import format_size

LOCALES = {"bs": "bs_Latn_BA", "en": "en_GB", "de": "de_DE", "es": "es_ES", "fr": "fr_FR"}
CARD_STYLE = """
QFrame#recapCard { background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #5b3fd1, stop:1 #1e88e5);
                   border-radius: 14px; }
QFrame#recapCard QLabel { color: white; background: transparent; }
"""


def duration_text(seconds: float) -> str:
    minutes = int(round(seconds / 60))
    if minutes < 60:
        return tr("recap.minutes", minutes=minutes)
    hours, rest = divmod(minutes, 60)
    text = tr("recap.hours", hours=hours)
    return f"{text} {tr('recap.minutes', minutes=rest)}" if rest and hours < 10 else text


def period_title(summary: Summary) -> str:
    if summary.yearly:
        return tr("recap.title_year", year=summary.period)
    locale = QLocale(LOCALES.get(get_language(), "en_GB"))
    month = locale.standaloneMonthName(int(summary.period[5:7]), QLocale.FormatType.LongFormat)
    return tr("recap.title_month", month=month)


def weekday_name(index: int) -> str:
    return QLocale(LOCALES.get(get_language(), "en_GB")).standaloneDayName(index + 1, QLocale.FormatType.LongFormat)


class RecapDialog(QDialog):
    support_clicked = Signal()

    def __init__(self, summary: Summary, support_line: str, offer_support: bool, parent=None):
        super().__init__(parent)
        self.setWindowTitle(tr("recap.window"))
        self._summary = summary
        outer = QVBoxLayout(self)

        self.card = QFrame()
        self.card.setObjectName("recapCard")
        self.card.setStyleSheet(CARD_STYLE)
        self.card.setFixedWidth(440)
        box = QVBoxLayout(self.card)
        box.setContentsMargins(26, 22, 26, 18)
        box.setSpacing(8)
        self.title = QLabel(period_title(summary))
        font = QFont(self.title.font())
        font.setPointSize(font.pointSize() + 9)
        font.setBold(True)
        self.title.setFont(font)
        box.addWidget(self.title)
        self.stats = QLabel(tr("recap.stats", count=summary.count, size=format_size(summary.bytes),
                               time=duration_text(summary.seconds)))
        stats_font = QFont(self.stats.font())
        stats_font.setPointSize(stats_font.pointSize() + 3)
        stats_font.setBold(True)
        self.stats.setFont(stats_font)
        self.stats.setWordWrap(True)
        box.addWidget(self.stats)
        lines = []
        if summary.top_site:
            site = NAMES.get(family_of(f"https://{summary.top_site}")) or summary.top_site  # „YouTube", ne „youtube.com"
            lines.append(tr("recap.top_site", site=site))
        if summary.longest > 0:
            lines.append(tr("recap.longest", time=duration_text(summary.longest)))
        lines.append(tr("recap.busiest_day", day=weekday_name(summary.busiest_weekday)))
        self.details = QLabel("\n".join(lines))
        self.details.setWordWrap(True)
        box.addWidget(self.details)
        box.addSpacing(10)
        footer = QLabel(f"Video Download · {SITE_URL.removeprefix('https://').rstrip('/')}")
        footer_font = QFont(footer.font())
        footer_font.setPointSize(max(7, footer_font.pointSize() - 1))
        footer.setFont(footer_font)
        box.addWidget(footer)
        outer.addWidget(self.card, 0, Qt.AlignmentFlag.AlignHCenter)

        note = QLabel(tr("recap.private"))
        note.setObjectName("supportNote")
        note.setWordWrap(True)
        outer.addWidget(note)
        self.support_label = QLabel(support_line)
        self.support_label.setWordWrap(True)
        self.support_label.setVisible(bool(support_line))
        outer.addWidget(self.support_label)
        self.status = QLabel()
        self.status.setObjectName("supportNote")
        self.status.setWordWrap(True)
        self.status.hide()
        outer.addWidget(self.status)

        buttons = QHBoxLayout()
        self.save_button = QPushButton(tr("recap.save"))
        self.save_button.clicked.connect(self._save)
        buttons.addWidget(self.save_button)
        self.copy_button = QPushButton(tr("recap.copy"))
        self.copy_button.clicked.connect(self._copy)
        buttons.addWidget(self.copy_button)
        buttons.addStretch(1)
        self.support_button = QPushButton(tr("support.button"))
        self.support_button.setObjectName("supportButton")
        self.support_button.clicked.connect(self.support_clicked)
        self.support_button.setVisible(bool(support_line) and offer_support)
        buttons.addWidget(self.support_button)
        close = QPushButton(tr("card.close"))
        close.setDefault(True)
        close.clicked.connect(self.accept)
        buttons.addWidget(close)
        outer.addLayout(buttons)

    def image(self):
        return self.card.grab()

    def default_name(self) -> str:
        return f"video-download-{self._summary.period}.png"

    def _copy(self) -> None:
        QApplication.clipboard().setPixmap(self.image())
        self._say(tr("recap.copied"))

    def _save(self) -> None:
        folder = getattr(self.parent(), "output_dir", "") or os.path.expanduser("~")
        path, _filter = QFileDialog.getSaveFileName(self, tr("recap.save"), os.path.join(folder, self.default_name()),
                                                    "PNG (*.png)")
        if path and self.save_to(path):
            self._say(tr("recap.saved", path=path))

    def save_to(self, path: str) -> bool:
        return self.image().save(path, "PNG")

    def _say(self, text: str) -> None:
        self.status.setText(text)
        self.status.show()
