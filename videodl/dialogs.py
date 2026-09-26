"""Pomoćni prozori glavnog prozora: istorija, podrška, ugovori, šta je novo, uputstvo za dodatak."""

import datetime
import os
import subprocess
import sys
from PySide6.QtCore import QUrl, Qt, Signal
from PySide6.QtGui import QDesktopServices, QPixmap
from PySide6.QtWidgets import QApplication, QComboBox, QDialog, QHBoxLayout, QLabel, QLineEdit, QListWidget, QListWidgetItem, QPushButton, QTabWidget, QTextBrowser, QVBoxLayout
from pathlib import Path
from . import __version__, changelog, legal, store
from .desktop import reveal
from .i18n import get_language, tr
from .widgets import format_size


class SupportDialog(QDialog):
    """Podsjetnik za dobrovoljni prilog: tri dugmeta, ništa se ne otključava ni blokira."""

    support_clicked = Signal()
    already_clicked = Signal()

    def __init__(self, text: str, parent=None):
        super().__init__(parent)
        self.setWindowTitle(tr("support.title"))
        self.setMinimumWidth(600)
        layout = QVBoxLayout(self)
        body = QHBoxLayout()
        texts = QVBoxLayout()
        message = QLabel(text)
        message.setWordWrap(True)
        texts.addWidget(message)
        note = QLabel(tr("support.voluntary"))
        note.setWordWrap(True)
        note.setObjectName("supportNote")
        texts.addWidget(note)
        texts.addStretch(1)
        body.addLayout(texts, 1)
        # Isti link kao dugme, za plaćanje telefonom (QR sa PayPal-a, provjeren da vodi na SUPPORT_URL).
        qr_column = QVBoxLayout()
        self.qr_label = QLabel()
        self.qr_label.setPixmap(QPixmap(str(Path(__file__).parent / "assets" / "support-qr.png")).scaled(
            150, 150, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
        self.qr_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        qr_column.addWidget(self.qr_label)
        self.qr_caption = QLabel(tr("support.qr"))
        self.qr_caption.setObjectName("supportNote")
        self.qr_caption.setAlignment(Qt.AlignmentFlag.AlignCenter)
        qr_column.addWidget(self.qr_caption)
        body.addLayout(qr_column)
        layout.addLayout(body)
        buttons = QHBoxLayout()
        self.support_button = QPushButton(tr("support.button"))
        self.support_button.setObjectName("supportButton")
        self.support_button.setDefault(True)
        self.support_button.clicked.connect(self.support_clicked)
        self.support_button.clicked.connect(self.accept)
        self.later_button = QPushButton(tr("support.later"))
        self.later_button.clicked.connect(self.reject)
        self.already_button = QPushButton(tr("support.already"))
        self.already_button.clicked.connect(self.already_clicked)
        self.already_button.clicked.connect(self.accept)
        buttons.addWidget(self.support_button)
        buttons.addStretch(1)
        buttons.addWidget(self.later_button)
        buttons.addWidget(self.already_button)
        layout.addLayout(buttons)

class LegalDialog(QDialog):
    """Pomoć → Ugovori i licence: isti tekstovi kao u instaleru, na jeziku aplikacije."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(tr("menu.legal").rstrip("…"))
        self.resize(680, 600)
        layout = QVBoxLayout(self)
        self.tabs = QTabWidget()
        language = get_language()
        for kind, key in legal.DOCUMENTS:
            self.tabs.addTab(self._text_view(legal.document_text(kind, language)), tr(key))
        folder = legal.licenses_dir()
        self.tabs.addTab(self._text_view(legal.notices_text(folder)), tr("legal.components"))
        layout.addWidget(self.tabs)
        buttons = QHBoxLayout()
        self.open_licenses_button = QPushButton(tr("legal.open_licenses"))
        self.open_licenses_button.clicked.connect(lambda: reveal(str(folder)))
        self.open_licenses_button.setEnabled(folder.is_dir())
        buttons.addWidget(self.open_licenses_button)
        buttons.addStretch(1)
        close_button = QPushButton(tr("history.close"))
        close_button.clicked.connect(self.accept)
        buttons.addWidget(close_button)
        layout.addLayout(buttons)

    @staticmethod
    def _text_view(text: str) -> QTextBrowser:
        view = QTextBrowser()
        view.setPlainText(text)
        return view

class WhatsNewDialog(QDialog):
    """Pomoć → Šta je novo: kratke bilješke po verzijama, na jeziku aplikacije."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(tr("menu.whats_new").rstrip("…"))
        self.resize(560, 480)
        layout = QVBoxLayout(self)
        self.current_label = QLabel(tr("whats_new.current", version=__version__))
        layout.addWidget(self.current_label)
        self.browser = QTextBrowser()
        self.browser.setOpenExternalLinks(False)
        self.browser.setHtml(changelog.to_html(get_language(), __version__))
        layout.addWidget(self.browser)
        close_button = QPushButton(tr("history.close"))
        close_button.clicked.connect(self.accept)
        buttons = QHBoxLayout()
        buttons.addStretch(1)
        buttons.addWidget(close_button)
        layout.addLayout(buttons)

HISTORY_KINDS = ("all", "video", "audio", "missing")

AUDIO_EXTENSIONS = frozenset((".mp3", ".m4a", ".aac", ".opus", ".ogg", ".oga", ".wav", ".flac", ".wma"))

def filter_history(entries, text: str = "", kind: str = "all") -> list:
    """Istorija po riječima iz naslova, linka ili imena fajla (sve riječi, bez obzira na velika slova)
    i po vrsti: video, zvuk ili fajl koji više ne postoji."""
    words = text.casefold().split()
    result = []
    for entry in entries:
        haystack = f"{entry.title} {entry.url} {os.path.basename(entry.filepath or '')}".casefold()
        if any(word not in haystack for word in words):
            continue
        audio = Path(entry.filepath or "").suffix.lower() in AUDIO_EXTENSIONS
        if kind == "video" and audio or kind == "audio" and not audio or kind == "missing" and entry.exists:
            continue
        result.append(entry)
    return result

SITE_URL = "https://abnps.github.io/video-download/"

# Stranica dodataka u browseru; otvara se pokretanjem browsera s tom adresom.
BROWSERS = (("msedge.exe", "edge://extensions", "help.open_edge"),
            ("chrome.exe", "chrome://extensions", "help.open_chrome"))

def browser_exe(name: str) -> str | None:
    """Putanja browsera iz „App Paths" registra (tako ga nalazi i Windows), ili None."""
    if sys.platform != "win32":
        return None
    import winreg

    for root in (winreg.HKEY_CURRENT_USER, winreg.HKEY_LOCAL_MACHINE):
        try:
            with winreg.OpenKey(root, rf"Software\Microsoft\Windows\CurrentVersion\App Paths\{name}") as key:
                path = winreg.QueryValue(key, None)
        except OSError:
            continue
        path = path.strip('"')
        if path and os.path.isfile(path):
            return path
    return None

class BrowserHelpDialog(QDialog):
    """Uputstvo za dodatak: koraci + dugmad koja rade teške dijelove (putanja, folder, stranica dodataka)."""

    def __init__(self, folder: str, parent=None, find_browser=browser_exe, launch=subprocess.Popen):
        super().__init__(parent)
        self._folder = folder
        self._launch = launch
        self.setWindowTitle(tr("menu.browser_help"))
        self.setMinimumWidth(560)
        layout = QVBoxLayout(self)
        text = QLabel(tr("help.browser_text", folder=folder))
        text.setWordWrap(True)
        text.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        layout.addWidget(text)

        row = QHBoxLayout()
        self.copy_button = QPushButton(tr("help.copy_path"))
        self.copy_button.clicked.connect(self._copy_path)
        row.addWidget(self.copy_button)
        self.folder_button = QPushButton(tr("help.open_folder"))
        self.folder_button.clicked.connect(lambda: reveal(self._folder))
        row.addWidget(self.folder_button)
        row.addStretch(1)
        layout.addLayout(row)

        browsers = QHBoxLayout()
        self.browser_buttons = {}
        for exe, url, key in BROWSERS:
            path = find_browser(exe)
            if not path:
                continue  # browser nije instaliran: bez dugmeta
            button = QPushButton(tr(key))
            button.clicked.connect(lambda _checked=False, path=path, url=url: self._open_extensions(path, url))
            browsers.addWidget(button)
            self.browser_buttons[exe] = button
        browsers.addStretch(1)
        layout.addLayout(browsers)

        self.note = QLabel()
        self.note.setObjectName("supportNote")
        layout.addWidget(self.note)
        bottom = QHBoxLayout()
        guide = QLabel(f'<a href="guide">{tr("help.guide_online")}</a>')
        guide.linkActivated.connect(lambda _href: QDesktopServices.openUrl(QUrl(self.guide_url())))
        bottom.addWidget(guide)
        bottom.addStretch(1)
        close_button = QPushButton(tr("history.close"))
        close_button.clicked.connect(self.accept)
        bottom.addWidget(close_button)
        layout.addLayout(bottom)

    @staticmethod
    def guide_url() -> str:
        return SITE_URL + ("bs/" if get_language() == "bs" else "") + "extension.html"

    def _copy_path(self) -> None:
        QApplication.clipboard().setText(self._folder)
        self.note.setText(tr("help.copied"))

    def _open_extensions(self, exe: str, url: str) -> None:
        try:
            self._launch([exe, url])
            self.note.setText(tr("help.opened"))
        except OSError:
            QApplication.clipboard().setText(url)
            self.note.setText(tr("help.open_failed", url=url))

class HistoryDialog(QDialog):
    """Šta je i kada preuzeto; fajl se može otvoriti u folderu i kad je red odavno obrisan."""

    def __init__(self, path: Path, parent=None):
        super().__init__(parent)
        self._path = path
        self.setWindowTitle(tr("history.title"))
        self.resize(680, 460)
        layout = QVBoxLayout(self)
        filters = QHBoxLayout()
        self.search = QLineEdit()
        self.search.setPlaceholderText(tr("history.search"))
        self.search.setClearButtonEnabled(True)
        self.search.textChanged.connect(self._apply_filter)
        filters.addWidget(self.search, 1)
        self.kind = QComboBox()
        for key in HISTORY_KINDS:
            self.kind.addItem(tr(f"history.kind.{key}"), key)
        self.kind.currentIndexChanged.connect(self._apply_filter)
        filters.addWidget(self.kind)
        layout.addLayout(filters)
        self.list = QListWidget()
        self.list.itemDoubleClicked.connect(self._open_selected)
        layout.addWidget(self.list)
        self.count_label = QLabel()
        self.count_label.setObjectName("supportNote")
        layout.addWidget(self.count_label)
        buttons = QHBoxLayout()
        self.open_button = QPushButton(tr("history.open"))
        self.open_button.clicked.connect(self._open_selected)
        self.clear_button = QPushButton(tr("history.clear"))
        self.clear_button.clicked.connect(self._clear)
        close_button = QPushButton(tr("history.close"))
        close_button.clicked.connect(self.accept)
        buttons.addWidget(self.open_button)
        buttons.addWidget(self.clear_button)
        buttons.addStretch(1)
        buttons.addWidget(close_button)
        layout.addLayout(buttons)
        self._fill()

    def _fill(self) -> None:
        self._entries = store.load_history(self._path)
        self._apply_filter()

    def _apply_filter(self, *_args) -> None:
        self.list.clear()
        entries = self._entries
        shown = filter_history(entries, self.search.text(), self.kind.currentData() or "all")
        for entry in shown:
            when = datetime.datetime.fromtimestamp(entry.finished_at).strftime("%d.%m.%Y %H:%M")
            size = format_size(entry.size) if entry.size else ""
            note = "" if entry.exists else f" — {tr('history.missing')}"
            row = QListWidgetItem(f"{when}   {entry.title}   {size}{note}")
            row.setData(Qt.ItemDataRole.UserRole, entry.filepath)
            row.setToolTip(entry.filepath or entry.url)
            self.list.addItem(row)
        self.list.setEnabled(bool(shown))
        self.open_button.setEnabled(bool(shown))
        self.clear_button.setEnabled(bool(entries))
        self.search.setEnabled(bool(entries))
        self.kind.setEnabled(bool(entries))
        if not entries:
            self.list.addItem(tr("history.empty"))
        elif not shown:
            self.list.addItem(tr("history.no_match"))
        self.count_label.setText(tr("history.count", shown=len(shown), total=len(entries)) if entries else "")

    def _open_selected(self) -> None:
        row = self.list.currentItem()
        path = row.data(Qt.ItemDataRole.UserRole) if row else None
        if path:
            reveal(path)

    def _clear(self) -> None:
        store.clear_history(self._path)
        self._fill()
