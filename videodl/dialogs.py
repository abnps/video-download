"""Pomoćni prozori glavnog prozora: istorija, podrška, ugovori, šta je novo, uputstvo za dodatak."""

import datetime
import os
import shutil
import subprocess
import sys
from PySide6.QtCore import QUrl, Qt, Signal
from PySide6.QtGui import QDesktopServices, QPixmap
from PySide6.QtWidgets import QApplication, QCheckBox, QComboBox, QDialog, QHBoxLayout, QLabel, QLineEdit, QListWidget, QListWidgetItem, QPushButton, QTabWidget, QTextBrowser, QVBoxLayout
from pathlib import Path
from . import __version__, changelog, legal, parental, store
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
        from . import support  # bez kružnog uvoza pri učitavanju

        self.kofi_link = QLabel(tr("support.other", card=f'<a href="{support.STRIPE_URL}">{tr("support.card")}</a>',
                                   kofi=f'<a href="{support.KOFI_URL}">Ko-fi</a>'))
        self.kofi_link.setObjectName("supportNote")
        self.kofi_link.setOpenExternalLinks(True)
        layout.addWidget(self.kofi_link)

class AchievementDialog(QDialog):
    """Čestitka za dostignuće (ili više njih odjednom). Ne blokira rad; poruka i dugme za prilog samo kad je
    dozvoljeno (nije „Već sam podržao", najviše jednom dnevno)."""

    support_clicked = Signal()

    def __init__(self, headline: str, lines: list[str], show_support: bool, parent=None):
        super().__init__(parent)
        self.setWindowTitle(tr("achievement.title"))
        self.setFixedWidth(440)  # poruka za prilog se lomi u dva reda umjesto jednog dugog
        layout = QVBoxLayout(self)
        self.headline = QLabel(headline)
        font = self.headline.font()
        font.setPointSizeF(font.pointSizeF() * 1.6)
        font.setBold(True)
        self.headline.setFont(font)
        self.headline.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.headline.setWordWrap(True)
        layout.addWidget(self.headline)
        self.message = QLabel("\n".join([*lines, tr("achievement.thanks")]))
        self.message.setWordWrap(True)
        self.message.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.message)
        # Poruka za prilog uz čestitku (Ahmed 19.10.2026), ali ne i kad je korisnik kliknuo „Već sam podržao".
        self.support_note = QLabel(tr("achievement.support"))
        self.support_note.setWordWrap(True)
        self.support_note.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.support_note.setObjectName("supportNote")
        self.support_note.setVisible(show_support)
        layout.addWidget(self.support_note)
        buttons = QHBoxLayout()
        self.support_button = QPushButton(tr("support.link"))
        self.support_button.setObjectName("supportButton")
        self.support_button.clicked.connect(self.support_clicked)
        self.support_button.clicked.connect(self.accept)
        self.support_button.setVisible(show_support)
        self.ok_button = QPushButton(tr("achievement.ok"))
        self.ok_button.setDefault(True)
        self.ok_button.clicked.connect(self.accept)
        buttons.addWidget(self.support_button)
        buttons.addStretch(1)
        buttons.addWidget(self.ok_button)
        layout.addLayout(buttons)


def milestone_line(count: int) -> str:
    return tr(f"achievement.{count}" if count <= 500 else "achievement.big")


class AchievementsListDialog(QDialog):
    """Pomoć → Moja dostignuća: osvojena i neosvojena, ukupan broj preuzimanja."""

    def __init__(self, state, downloads: int, milestone_shown: int, parent=None):
        super().__init__(parent)
        from . import achievements, support  # bez kružnog uvoza pri učitavanju

        self.setWindowTitle(tr("menu.achievements").rstrip("…"))
        self.resize(520, 600)
        layout = QVBoxLayout(self)
        earned = [m for m in support.MILESTONES if m <= milestone_shown]
        total = len(support.MILESTONES) + len(achievements.BADGES)
        self.summary = QLabel(tr("achievements.summary", earned=len(earned) + len(state.earned), total=total,
                                 downloads=downloads, size=format_size(state.total_bytes)))
        self.summary.setWordWrap(True)
        layout.addWidget(self.summary)
        self.list = QListWidget()
        self.list.setSelectionMode(QListWidget.SelectionMode.NoSelection)  # samo za čitanje
        self.list.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        rows = []
        for count in support.MILESTONES:
            rows.append(("🏆", tr("achievements.count_name", count=count), tr("achievements.count_desc", count=count),
                         count <= milestone_shown, None))
        for key, icon in achievements.BADGES:
            rows.append((icon, tr(f"badge.{key}"), tr(f"badge.{key}.desc"), key in state.earned,
                         state.earned.get(key)))
        rows.sort(key=lambda row: not row[3])  # osvojena prva, inače istim redom
        for icon, name, desc, done, when in rows:
            if done:
                status = (tr("achievements.earned_on",
                             date=datetime.date.fromtimestamp(when).strftime("%d.%m.%Y")) if when else "")
                text = f"{icon}  {name}\n      {desc}" + (f"  ·  {status}" if status else "")
            else:
                text = f"🔒  {name}\n      {desc}  ·  {tr('achievements.locked')}"
            item = QListWidgetItem(text)
            if not done:
                item.setForeground(self.palette().placeholderText())
            self.list.addItem(item)
        layout.addWidget(self.list, 1)
        note = QLabel(tr("achievements.local"))
        note.setWordWrap(True)
        note.setObjectName("supportNote")
        layout.addWidget(note)
        buttons = QHBoxLayout()
        buttons.addStretch(1)
        self.close_button = QPushButton(tr("achievements.close"))
        self.close_button.clicked.connect(self.accept)
        buttons.addWidget(self.close_button)
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

class ParentalDialog(QDialog):
    """Preuzimanja → Roditeljska zaštita: uključi/isključi blokadu 18+ i (opciono) postavi PIN."""

    def __init__(self, enabled: bool, parent=None):
        super().__init__(parent)
        self.setWindowTitle(tr("parental.title"))
        layout = QVBoxLayout(self)
        self.enabled_box = QCheckBox(tr("parental.enable"))
        self.enabled_box.setChecked(enabled)
        layout.addWidget(self.enabled_box)
        note = QLabel(tr("parental.note"))
        note.setWordWrap(True)
        layout.addWidget(note)
        self.pin = QLineEdit()
        self.pin.setEchoMode(QLineEdit.EchoMode.Password)
        self.pin.setPlaceholderText(tr("parental.pin"))
        self.pin.setMaxLength(8)
        self.repeat = QLineEdit()
        self.repeat.setEchoMode(QLineEdit.EchoMode.Password)
        self.repeat.setPlaceholderText(tr("parental.pin_repeat"))
        self.repeat.setMaxLength(8)
        layout.addWidget(self.pin)
        layout.addWidget(self.repeat)
        self.error = QLabel("")
        self.error.setObjectName("errorLabel")
        layout.addWidget(self.error)
        self.enabled_box.toggled.connect(self._sync)
        buttons = QHBoxLayout()
        buttons.addStretch(1)
        save = QPushButton(tr("parental.save"))
        save.setDefault(True)
        save.clicked.connect(self._accept)
        cancel = QPushButton(tr("adult.cancel"))
        cancel.clicked.connect(self.reject)
        buttons.addWidget(save)
        buttons.addWidget(cancel)
        layout.addLayout(buttons)
        self._sync()

    def _sync(self) -> None:
        on = self.enabled_box.isChecked()
        self.pin.setEnabled(on)
        self.repeat.setEnabled(on)

    def _accept(self) -> None:
        pin = self.chosen_pin()
        if pin and not parental.valid_pin(pin):
            self.error.setText(tr("parental.pin_invalid"))
        elif pin != (self.repeat.text().strip() if self.enabled_box.isChecked() else ""):
            self.error.setText(tr("parental.pin_mismatch"))
        else:
            self.accept()

    def chosen_enabled(self) -> bool:
        return self.enabled_box.isChecked()

    def chosen_pin(self) -> str:
        """Novi PIN ili "" (bez PIN-a); isključena zaštita nikad ne nosi PIN."""
        return self.pin.text().strip() if self.enabled_box.isChecked() else ""


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
# Discord zajednica (trajna pozivnica, ista kao na sajtu); otvara se samo u browseru na klik.
DISCORD_URL = "https://discord.gg/xZ7JNKSaKb"

# Dodatak iz prodavnica (Ahmed 27.10.2026): Edge i Firefox jednim klikom, sam se ažurira; Chrome ostaje ručno.
EDGE_ADDON_URL = "https://microsoftedge.microsoft.com/addons/detail/glikmhiifcloegaachgkhinigmnhnjpo"
FIREFOX_ADDON_URL = "https://addons.mozilla.org/firefox/addon/video-download-abnps/"
STORES = (("msedge.exe", EDGE_ADDON_URL, "help.install_edge"),
          ("firefox.exe", FIREFOX_ADDON_URL, "help.install_firefox"))
# Chrome: stranica dodataka se otvara pokretanjem browsera s tom adresom (iz programa je drugačije ne otvara).
CHROME = ("chrome.exe", "chrome://extensions")
# Mac: isti browseri u /Applications; izvršni fajl u paketu prima adresu kao i na Windowsu.
MAC_BROWSERS = {"msedge.exe": "Microsoft Edge.app/Contents/MacOS/Microsoft Edge",
                "chrome.exe": "Google Chrome.app/Contents/MacOS/Google Chrome",
                "firefox.exe": "Firefox.app/Contents/MacOS/firefox"}


# Linux: imena naredbi kako ih postavljaju paketi distribucija i proizvođača browsera.
LINUX_BROWSERS = {"msedge.exe": ("microsoft-edge", "microsoft-edge-stable"),
                  "chrome.exe": ("google-chrome", "google-chrome-stable", "chromium", "chromium-browser"),
                  "firefox.exe": ("firefox",)}


def browser_exe(name: str, platform: str = sys.platform, applications: tuple[Path, ...] | None = None,
                which=shutil.which) -> str | None:
    """Putanja browsera: na Windowsu iz „App Paths" registra (tako ga nalazi i Windows),
    na Macu iz /Applications ili ~/Applications, na Linuxu iz PATH-a; None ako ga nema."""
    if platform.startswith("linux"):
        return next((found for command in LINUX_BROWSERS.get(name, ()) if (found := which(command))), None)
    if platform == "darwin":
        inside = MAC_BROWSERS.get(name)
        folders = applications or (Path("/Applications"), Path.home() / "Applications")
        for folder in folders if inside else ():
            if (folder / inside).is_file():
                return str(folder / inside)
        return None
    if platform != "win32":
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
    """Dodatak za browser: Edge i Firefox jednim klikom iz prodavnice, Chrome u tri numerisana koraka."""

    def __init__(self, folder: str, parent=None, find_browser=browser_exe, launch=subprocess.Popen,
                 open_url=lambda url: QDesktopServices.openUrl(QUrl(url))):
        super().__init__(parent)
        self._folder = folder
        self._launch = launch
        self._open_url = open_url
        self.setWindowTitle(tr("menu.browser_help"))
        self.setMinimumWidth(560)
        layout = QVBoxLayout(self)

        # 1) Edge i Firefox: zvanična stranica dodatka, otvorena baš u tom browseru (ako je instaliran).
        stores_title = QLabel(f"<b>{tr('help.stores_title')}</b>")
        layout.addWidget(stores_title)
        stores = QHBoxLayout()
        self.store_buttons = {}
        for exe, url, key in STORES:
            button = QPushButton(tr(key))
            path = find_browser(exe)
            button.clicked.connect(lambda _checked=False, path=path, url=url: self._open_store(path, url))
            stores.addWidget(button)
            self.store_buttons[exe] = button
        stores.addStretch(1)
        layout.addLayout(stores)
        stores_note = QLabel(tr("help.stores_note"))
        stores_note.setWordWrap(True)
        layout.addWidget(stores_note)

        # 2) Chrome: ručno, ali svaki korak ima svoje dugme ili jasnu radnju.
        layout.addSpacing(10)
        layout.addWidget(QLabel(f"<b>{tr('help.chrome_title')}</b>"))
        step1 = QHBoxLayout()
        step1.addWidget(QLabel(tr("help.chrome_step1")))
        self.copy_button = QPushButton(tr("help.copy_path"))
        self.copy_button.clicked.connect(self._copy_path)
        step1.addWidget(self.copy_button)
        step1.addStretch(1)
        layout.addLayout(step1)
        path_label = QLabel(folder)
        path_label.setObjectName("supportNote")
        path_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        path_label.setWordWrap(True)
        layout.addWidget(path_label)
        step2 = QHBoxLayout()
        step2.addWidget(QLabel(tr("help.chrome_step2")))
        self.browser_buttons = {}
        chrome_exe, chrome_url = CHROME
        chrome = find_browser(chrome_exe)
        if chrome:
            button = QPushButton(tr("help.open_chrome"))
            button.clicked.connect(lambda _checked=False: self._open_extensions(chrome, chrome_url))
            step2.addWidget(button)
            self.browser_buttons[chrome_exe] = button
        else:
            step2.addWidget(QLabel(f"<b>{chrome_url}</b>"))  # Chrome nije nađen: adresa za ručno otvaranje
        step2.addStretch(1)
        layout.addLayout(step2)
        step3 = QLabel(tr("help.chrome_step3"))
        step3.setWordWrap(True)
        layout.addWidget(step3)

        # 3) Kako se koristi (isto za sve browsere).
        layout.addSpacing(10)
        usage = QLabel(tr("help.usage"))
        usage.setWordWrap(True)
        layout.addWidget(usage)

        self.note = QLabel()
        self.note.setObjectName("supportNote")
        self.note.setWordWrap(True)
        layout.addWidget(self.note)
        bottom = QHBoxLayout()
        guide = QLabel(f'<a href="guide">{tr("help.guide_online")}</a>')
        guide.linkActivated.connect(lambda _href: self._open_url(self.guide_url()))
        bottom.addWidget(guide)
        bottom.addStretch(1)
        close_button = QPushButton(tr("history.close"))
        close_button.clicked.connect(self.accept)
        bottom.addWidget(close_button)
        layout.addLayout(bottom)

    @staticmethod
    def guide_url() -> str:
        # sajt ima svih 5 jezika: engleski u korijenu, ostali u svom podfolderu
        language = get_language()
        return SITE_URL + ("" if language == "en" else f"{language}/") + "extension.html"

    def _open_store(self, exe: str | None, url: str) -> None:
        """Stranica dodatka u prodavnici: u tom browseru ako je instaliran, inače u podrazumijevanom."""
        try:
            if exe:
                self._launch([exe, url])
            else:
                self._open_url(url)
            self.note.setText(tr("help.store_opened"))
        except OSError:
            self._open_url(url)
            self.note.setText(tr("help.store_opened"))

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
