"""Glavni prozor: traka (Zalijepi / format / Preuzmi), red preuzimanja sa sličicama, meni."""

import contextlib
import dataclasses
import datetime
import os
import queue
import re
import shutil
import subprocess
import sys
import tempfile
import threading
import time
import urllib.request
from pathlib import Path

from PySide6.QtCore import QLocale, QObject, QPoint, QSettings, QSize, Qt, QTimer, QUrl, Signal, Slot
from PySide6.QtGui import (
    QAction, QActionGroup, QColor, QDesktopServices, QFont, QIcon, QImage, QKeySequence, QPalette, QPixmap,
)
from PySide6.QtWidgets import (
    QApplication, QComboBox, QDialog, QFileDialog, QFrame, QHBoxLayout, QInputDialog, QLabel, QListWidget,
    QListWidgetItem, QMainWindow,
    QLineEdit, QMenu, QMessageBox, QProgressDialog, QPushButton, QScrollArea, QStackedWidget, QSystemTrayIcon,
    QTabWidget, QTextBrowser, QVBoxLayout,
    QWidget,
)

from . import __version__
from .bridge import BridgeServer
from .browser import BrowserRequest
from .download import PROCESSING, DownloadResult, Progress, download
from .i18n import LANGUAGES, MESSAGE_EXISTS, decimal, MESSAGE_NOT_MEDIA, MESSAGE_RETRY, get_language, pick_language, set_language, tr
from .icons import icon
from .jobs import DownloadQueue, ItemStatus, QueueItem
from .native_host import call_app, data_dir, find_running_app
from .native_messaging import install_native_host, uninstall_native_host
from .runtime import extension_dir, find_tool, mark_running
from .presets import (
    DEFAULT_NAME_TEMPLATE, DEFAULT_PRESET_KEY, NAME_TEMPLATES, PRESETS, format_section, get_preset, parse_section, safe_folder_name,
    subtitle_languages,
)
from .probe import ProbeResult, probe
from . import changelog, convert, diagnostics, legal, store, support, theme, winshell
from . import updater, ytdlp_update
from .widgets import DropZone, QueueRow, display_message, format_size, set_state
from .ytdl import JS_RUNTIMES, error_message, is_network_error, is_obviously_not_media

_URL_PATTERN = re.compile(r"https?://[^\s<>\"']+", re.IGNORECASE)
MAX_THUMBNAIL_BYTES = 2 * 1024 * 1024

# Pucanje veze: koliko puta aplikacija sama ponavlja i koliko čeka između pokušaja.
MAX_AUTO_RETRIES = 3
AUTO_RETRY_DELAY_MS = 5000

# Ukupno ograničenje brzine u MB/s (0 = bez ograničenja); dijeli se na preuzimanja u toku.
RATE_CHOICES = (0, 1, 2, 5, 10)

# Koliko preuzimanja može ići istovremeno (Preuzimanja → Istovremeno).
PARALLEL_CHOICES = (1, 2, 3, 4)
DEFAULT_PARALLEL = 2



def default_output_dir() -> str:
    return str(Path.home() / "Videos" / "Video Download")


def format_speed(bytes_per_second: float) -> str:
    value = bytes_per_second / 1024
    for unit in ("KB/s", "MB/s", "GB/s"):
        if value < 1024 or unit == "GB/s":
            return decimal(f"{value:.1f} {unit}")
        value /= 1024
    raise AssertionError("nedostižno")


def format_eta(seconds: int) -> str:
    minutes, secs = divmod(int(seconds), 60)
    hours, minutes = divmod(minutes, 60)
    if hours:
        return f"{hours}:{minutes:02d}:{secs:02d}"
    if minutes:
        return f"{minutes}:{secs:02d}"
    return f"{secs} s"


def format_progress(progress: Progress) -> str:
    if progress.phase == PROCESSING:
        return f"{tr(progress.label)}…"
    parts = [tr("progress.downloading") + (f" ({tr(progress.label)})" if progress.label else "")]
    if progress.fraction is not None:
        parts.append(f"{progress.fraction:.0%}")
    if progress.speed:
        parts.append(format_speed(progress.speed))
    if progress.eta is not None:
        parts.append(tr("progress.eta", time=format_eta(progress.eta)))
    return " · ".join(parts)


def extract_urls(text: str) -> list[str]:
    urls = []
    for match in _URL_PATTERN.findall(text or ""):
        url = match.rstrip(".,;)")
        if url not in urls:
            urls.append(url)
    return urls


def missing_tools() -> list[str]:
    missing = []
    if not find_tool("ffmpeg"):
        missing.append("missing.ffmpeg")
    if not any(find_tool(name) for name in JS_RUNTIMES):
        missing.append("missing.js")
    return missing


def fetch_thumbnail(url: str) -> bytes | None:
    if not url.lower().startswith(("http://", "https://")):
        return None
    request = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(request, timeout=10) as response:
        return response.read(MAX_THUMBNAIL_BYTES)


def apply_theme(app: QApplication) -> None:
    """Paleta za trenutnu temu (theme.set_colors); dijalozi i meniji je preuzimaju."""
    app.setStyle("Fusion")
    app.setFont(QFont("Segoe UI", 9))
    palette = QPalette()
    k = theme.c
    for role, color in ((QPalette.ColorRole.Window, k("bg")), (QPalette.ColorRole.Base, k("bg")),
                        (QPalette.ColorRole.AlternateBase, k("alt_base")), (QPalette.ColorRole.Text, k("text")),
                        (QPalette.ColorRole.WindowText, k("text")), (QPalette.ColorRole.Button, k("button")),
                        (QPalette.ColorRole.ButtonText, k("text")), (QPalette.ColorRole.Highlight, "#1e88e5"),
                        (QPalette.ColorRole.HighlightedText, "#ffffff"), (QPalette.ColorRole.ToolTipBase, k("bg")),
                        (QPalette.ColorRole.ToolTipText, k("text")), (QPalette.ColorRole.Link, k("link")),
                        (QPalette.ColorRole.PlaceholderText, k("hint"))):
        palette.setColor(role, QColor(color))
    for role in (QPalette.ColorRole.Text, QPalette.ColorRole.WindowText, QPalette.ColorRole.ButtonText):
        palette.setColor(QPalette.ColorGroup.Disabled, role, QColor(k("hint")))
    app.setPalette(palette)


def system_prefers_dark() -> bool:
    app = QApplication.instance()
    if app is None:
        return False
    return app.styleHints().colorScheme() == Qt.ColorScheme.Dark


class ProbeJob(QObject):
    """Čita linkove u pozadinskoj niti. Signali se u glavnoj niti isporučuju redom."""

    # access: {"http_headers": ..., "cookies": ...} za sajt iz browsera, samo neprazni ključevi
    # preset: format koji je dodatak izričito tražio (dugme „Preuzmi kao MP3"), inače None
    probed = Signal(object, str, object, bool, object)  # ProbeResult, output_dir, access, odmah preuzmi, preset
    failed = Signal(str, str, str, object, object)  # link, poruka, output_dir, access, preset
    finished = Signal(int)  # id posla

    def __init__(self, job_id: int, urls: list[str], output_dir: str, probe_fn,
                 access: dict | None = None, auto_start: bool = False, preset: str | None = None,
                 probe_options: dict | None = None):
        super().__init__()
        self.job_id = job_id
        self._urls = urls
        self.urls = tuple(urls)
        self._output_dir = output_dir
        self._probe_fn = probe_fn
        self._access = {key: value for key, value in (access or {}).items() if value}
        self._auto_start = auto_start
        self._preset = preset
        self._probe_options = {key: value for key, value in (probe_options or {}).items() if value}
        self._cancel = threading.Event()

    def cancel(self) -> None:
        """Čitanje linka se ne može prekinuti usred posla, ali se rezultat više ne koristi."""
        self._cancel.set()

    def start(self) -> None:
        # daemon: čitanje linka se ne može prekinuti, a ne smije držati program pri zatvaranju
        threading.Thread(target=self._run, daemon=True).start()

    def _run(self) -> None:
        for url in self._urls:
            if self._cancel.is_set():
                break
            try:
                result = self._probe_fn(url, **self._access, **self._probe_options)
                if not self._cancel.is_set():
                    self.probed.emit(result, self._output_dir, self._access, self._auto_start, self._preset)
            except Exception as exc:  # granica radne niti
                if not self._cancel.is_set():
                    self.failed.emit(url, error_message(exc), self._output_dir, self._access, self._preset)
        self.finished.emit(self.job_id)


class DownloadJob(QObject):
    progress = Signal(int, object)  # id stavke, Progress
    finished = Signal(int, object)  # id stavke, DownloadResult

    def __init__(self, item: QueueItem, download_fn, options: dict | None = None):
        super().__init__()
        self.item_id = item.id
        self._args = (item.url, get_preset(item.preset_key), item.output_dir, item.subfolder)
        self._extra = {"http_headers": dict(item.http_headers), "filename_title": item.filename_title}
        if item.cookies:
            self._extra["cookies"] = item.cookies
        # Isječak, titlovi, sličica, brzina: samo ono što je uključeno.
        self._extra.update(options or {})
        self._download_fn = download_fn
        self._cancel = threading.Event()
        self._thread = threading.Thread(target=self._run, daemon=True)
        # Dok yt-dlp čita informacije o videu (prije prvog bajta) prekid ne djeluje,
        # pa se takav posao napušta: nijedan fajl još ne postoji.
        self.started = False

    def start(self) -> None:
        self._thread.start()

    def cancel(self) -> None:
        self._cancel.set()

    def join(self, timeout: float) -> None:
        self._thread.join(timeout)

    def _run(self) -> None:
        try:
            result = self._download_fn(*self._args, on_progress=self._report,
                                       cancel_event=self._cancel, **self._extra)
        except Exception as exc:  # granica radne niti
            result = DownloadResult(ItemStatus.FAILED, message=error_message(exc))
        self.finished.emit(self.item_id, result)

    def _report(self, progress: Progress) -> None:
        self.started = True
        self.progress.emit(self.item_id, progress)


class ThumbnailLoader(QObject):
    """Sličice se preuzimaju u nekoliko pozadinskih niti; QImage je bezbjedan van glavne niti."""

    loaded = Signal(str, QImage)
    WORKERS = 3

    def __init__(self, fetch):
        super().__init__()
        self._fetch = fetch
        self._requests: queue.Queue[str] = queue.Queue()
        self._started = False

    def request(self, url: str) -> None:
        if not self._started:
            self._started = True
            for _ in range(self.WORKERS):
                threading.Thread(target=self._work, daemon=True).start()
        self._requests.put(url)

    def _work(self) -> None:
        while True:
            url = self._requests.get()
            try:
                data = self._fetch(url)
            except Exception:  # sličica nije bitna; bez nje ostaje zamjenska slika
                continue
            image = QImage()
            if data and image.loadFromData(data):
                self.loaded.emit(url, image)


class UpdateCheckJob(QObject):
    finished = Signal(object, object, bool)  # Release | None, greška | None, ručna provjera

    def __init__(self, fetch, manual: bool):
        super().__init__()
        self._fetch = fetch
        self._manual = manual

    def start(self) -> None:
        threading.Thread(target=self._run, daemon=True).start()

    def _run(self) -> None:
        try:
            self.finished.emit(self._fetch(), None, self._manual)
        except Exception as exc:  # granica radne niti
            self.finished.emit(None, exc, self._manual)


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


class ConvertJob(QObject):
    """MP4 → MP3 u pozadinskoj niti; prozor ostaje upotrebljiv."""

    progress = Signal(int, object)  # id stavke, udio 0..1 ili None
    finished = Signal(int, object, str)  # id stavke, putanja MP3 ili None, poruka greške

    def __init__(self, item_id: int, source: str, duration: float | None, convert_fn):
        super().__init__()
        self.item_id = item_id
        self._source = source
        self._duration = duration
        self._convert_fn = convert_fn
        self._cancel = threading.Event()
        self._thread = threading.Thread(target=self._run, daemon=True)

    def start(self) -> None:
        self._thread.start()

    def cancel(self) -> None:
        self._cancel.set()

    def join(self, timeout: float) -> None:
        self._thread.join(timeout)

    def _run(self) -> None:
        try:
            path = self._convert_fn(self._source, on_progress=lambda f: self.progress.emit(self.item_id, f),
                                    cancel_event=self._cancel, duration=self._duration)
            self.finished.emit(self.item_id, path, "")
        except Exception as exc:  # granica radne niti
            self.finished.emit(self.item_id, None, str(exc) or exc.__class__.__name__)


class YtdlpUpdateJob(QObject):
    """Provjera i preuzimanje yt-dlp-a u pozadinskoj niti (mreža ne smije blokirati prozor)."""

    finished = Signal(object, object, bool)  # verzija | None, greška | None, ručna provjera

    def __init__(self, manual: bool, fetch=None, install=None):
        super().__init__()
        self._manual = manual
        self._fetch = fetch or ytdlp_update.fetch_latest
        self._install = install or ytdlp_update.install

    def start(self) -> None:
        threading.Thread(target=self._run, daemon=True).start()

    def _run(self) -> None:
        try:
            release = self._fetch()
            self.finished.emit(self._install(release) if release else None, None, self._manual)
        except Exception as exc:  # granica radne niti
            self.finished.emit(None, exc, self._manual)


class UpdateDownloadJob(QObject):
    progress = Signal(int, int)  # preuzeto, ukupno (bajtova)
    finished = Signal(object, object)  # Path | None, greška | None

    def __init__(self, release, target_dir: Path, download_fn=None):
        super().__init__()
        self._release = release
        self._target_dir = target_dir
        self._download_fn = download_fn or updater.download_installer
        self._cancel = threading.Event()

    @property
    def cancelled(self) -> bool:
        return self._cancel.is_set()

    def cancel(self) -> None:
        self._cancel.set()

    def start(self) -> None:
        threading.Thread(target=self._run, daemon=True).start()

    def _run(self) -> None:
        try:
            path = self._download_fn(self._release, self._target_dir, on_progress=self.progress.emit, cancel=self._cancel)
            self.finished.emit(path, None)
        except Exception as exc:  # granica radne niti
            self.finished.emit(None, exc)


def update_error_text(error: BaseException) -> str:
    key = getattr(error, "key", None)
    return tr(key) if key else error_message(error)


class MainWindow(QMainWindow):
    # Stižu iz niti lokalnog mosta; Qt ih isporučuje u glavnoj niti.
    browser_request = Signal(object)  # BrowserRequest
    focus_requested = Signal()

    def __init__(self, settings: QSettings | None = None, probe_fn=probe, download_fn=download,
                 thumbnail_fetch=fetch_thumbnail, update_fetch=None, check_updates_on_start: bool = False,
                 data_dir_path: Path | None = None, convert_fn=None):
        super().__init__()
        self.browser_request.connect(self._on_browser_request)
        self.focus_requested.connect(self._bring_to_front)
        self._settings = settings if settings is not None else QSettings("VideoDownload", "VideoDownload")
        self._probe_fn = probe_fn
        self._download_fn = download_fn
        self._convert_fn = convert_fn or convert.convert_to_mp3
        self._convert_jobs: dict[int, ConvertJob] = {}
        self._support = support.SupportState()
        self._support_dialog = None
        self._queue = DownloadQueue()
        self._rows: dict[int, QueueRow] = {}
        self._sizes: dict[int, int] = {}
        self._running = False  # „Preuzmi" je pokrenut: red se obrađuje dok ima stavki koje čekaju
        self._manual: list[int] = []  # pojedinačno pokrenute stavke (dugme u redu, browser)
        self._remove_when_done: set[int] = set()
        self._download_jobs: dict[int, DownloadJob] = {}  # stavka -> posao u toku
        self._probe_jobs: dict[int, ProbeJob] = {}
        self._next_probe_id = 1
        self._output_dir = default_output_dir()
        self._thumbnails = ThumbnailLoader(thumbnail_fetch)
        self._thumbnails.loaded.connect(self._on_thumbnail)
        self._thumbnail_cache: dict[str, QPixmap] = {}
        self._thumbnail_waiters: dict[str, list[int]] = {}

        set_language(self._settings.value("language", "", type=str) or pick_language(QLocale.system().name()))
        self.setWindowTitle(f"Video Download {__version__}")
        self.setMinimumSize(640, 380)
        self.resize(820, 520)
        self.setAcceptDrops(True)
        self._theme = theme.DEFAULT_THEME
        self._follows_system = False
        self._parallel = DEFAULT_PARALLEL
        self._subtitles = False
        self._thumbnail_cover = False
        self._whole_playlist = False
        self._rate_limit = 0
        self._name_template = DEFAULT_NAME_TEMPLATE
        self._probing: set[str] = set()  # linkovi koji se upravo čitaju
        # Grupa preuzimanja od pokretanja dok sve ne stane: napredak u traci zadataka i obavještenje.
        self._batch: dict[int, float] = {}  # stavka -> udio 0..1
        self._batch_stopped = False
        self._notify_done = True
        self._taskbar = winshell.TaskbarProgress(self)
        self._tray: QSystemTrayIcon | None = None
        self._notifier = self._show_notification
        self._errors: list[str] = []  # posljednje greške za izvještaj o problemu
        self._data_dir = Path(data_dir_path) if data_dir_path else data_dir()
        self._watch_clipboard = False
        # Tekst koji je clipboard već imao pri paljenju ne treba hvatati.
        self._last_clipboard = QApplication.clipboard().text() if QApplication.instance() else ""
        self._update_fetch = update_fetch
        self._update_check_job = None
        self._ytdlp_job = None
        self._build_menu()
        self._build_ui()
        self._load_settings()
        self.retranslate_ui()
        self._restore_queue()
        if check_updates_on_start:
            QTimer.singleShot(4000, lambda: self.check_for_updates(manual=False))
            # yt-dlp se mijenja češće od aplikacije; tiha provjera najviše jednom dnevno.
            QTimer.singleShot(9000, lambda: self.update_ytdlp(manual=False))

    # ---------- izgled ----------

    def _build_menu(self) -> None:
        menu = self.menuBar()
        self.file_menu = menu.addMenu("")
        self.paste_action = self.file_menu.addAction("", self._paste_from_clipboard)
        self.paste_action.setShortcut(QKeySequence.StandardKey.Paste)
        self.watch_clipboard_action = self.file_menu.addAction("", self.set_watch_clipboard)
        self.watch_clipboard_action.setCheckable(True)
        self.enter_links_action = self.file_menu.addAction("", self._enter_links)
        self.enter_links_action.setShortcut(QKeySequence("Ctrl+L"))
        self.file_menu.addSeparator()
        self.choose_folder_action = self.file_menu.addAction("", self._choose_folder)
        self.open_folder_action = self.file_menu.addAction("", self._open_folder)
        self.file_menu.addSeparator()
        self.exit_action = self.file_menu.addAction("", self.close)
        self.exit_action.setShortcut(QKeySequence("Ctrl+Q"))

        self.downloads_menu = menu.addMenu("")
        self.start_action = self.downloads_menu.addAction("", self._start_all)
        self.start_action.setShortcut(QKeySequence("F5"))
        self.stop_action = self.downloads_menu.addAction("", self._stop_all)
        self.downloads_menu.addSeparator()
        self.retry_failed_action = self.downloads_menu.addAction("", self._retry_failed)
        self.clear_action = self.downloads_menu.addAction("", self._clear_finished)
        self.remove_all_action = self.downloads_menu.addAction("", self._remove_all)
        self.history_action = self.downloads_menu.addAction("", self._show_history)
        self.downloads_menu.addSeparator()
        self.subtitles_action = self.downloads_menu.addAction(
            "", lambda checked: self._set_option("_subtitles", checked))
        self.subtitles_action.setCheckable(True)
        self.thumbnail_action = self.downloads_menu.addAction(
            "", lambda checked: self._set_option("_thumbnail_cover", checked))
        self.thumbnail_action.setCheckable(True)
        self.whole_playlist_action = self.downloads_menu.addAction(
            "", lambda checked: self._set_option("_whole_playlist", checked))
        self.whole_playlist_action.setCheckable(True)
        self.rate_menu = self.downloads_menu.addMenu("")
        self.rate_actions = QActionGroup(self)
        self.rate_actions.setExclusive(True)
        for value in RATE_CHOICES:
            action = self.rate_menu.addAction("")
            action.setCheckable(True)
            action.setData(value)
            action.triggered.connect(lambda _checked, rate=value: self._set_option("_rate_limit", rate))
            self.rate_actions.addAction(action)
        self.name_menu = self.downloads_menu.addMenu("")
        self.name_actions = QActionGroup(self)
        self.name_actions.setExclusive(True)
        for key in NAME_TEMPLATES:
            action = self.name_menu.addAction("")
            action.setCheckable(True)
            action.setData(key)
            action.triggered.connect(lambda _checked, value=key: self._set_option("_name_template", value))
            self.name_actions.addAction(action)
        self.downloads_menu.addSeparator()
        self.notify_action = self.downloads_menu.addAction(
            "", lambda checked: self._set_option("_notify_done", checked))
        self.notify_action.setCheckable(True)
        self.parallel_menu = self.downloads_menu.addMenu("")
        self.parallel_actions = QActionGroup(self)
        self.parallel_actions.setExclusive(True)
        for count in PARALLEL_CHOICES:
            action = self.parallel_menu.addAction(str(count))
            action.setCheckable(True)
            action.setData(count)
            action.triggered.connect(lambda _checked, value=count: self.set_parallel(value))
            self.parallel_actions.addAction(action)

        self.help_menu = menu.addMenu("")
        self.check_updates_action = self.help_menu.addAction("", lambda: self.check_for_updates(manual=True))
        self.whats_new_action = self.help_menu.addAction("", self._show_whats_new)
        self.update_ytdlp_action = self.help_menu.addAction("", lambda: self.update_ytdlp(manual=True))
        self.theme_menu = self.help_menu.addMenu("")
        self.theme_actions = QActionGroup(self)
        self.theme_actions.setExclusive(True)
        for name in theme.THEMES:
            action = self.theme_menu.addAction("")
            action.setCheckable(True)
            action.setData(name)
            action.triggered.connect(lambda _checked, value=name: self.set_theme(value))
            self.theme_actions.addAction(action)
        self.language_menu = self.help_menu.addMenu("")
        self.language_actions = QActionGroup(self)
        for code, name in LANGUAGES.items():
            action = QAction(name, self, checkable=True)
            action.setData(code)
            action.triggered.connect(lambda _checked=False, code=code: self.change_language(code))
            self.language_actions.addAction(action)
            self.language_menu.addAction(action)
        self.help_menu.addSeparator()
        self.browser_help_action = self.help_menu.addAction("", self._show_browser_help)
        self.report_action = self.help_menu.addAction("", self._save_report)
        self.legal_action = self.help_menu.addAction("", self._show_legal)
        self.support_action = self.help_menu.addAction("", lambda: self.show_support_dialog(automatic=False))
        self.about_action = self.help_menu.addAction("", self._show_about)

        # Referenca se čuva: PySide ne preuzima vlasništvo, pa bi Python obrisao label.
        self.corner_link = QLabel()
        self.corner_link.setObjectName("cornerLink")
        self.corner_link.linkActivated.connect(lambda _href: self._open_folder())
        menu.setCornerWidget(self.corner_link, Qt.Corner.TopRightCorner)

    def retranslate_ui(self) -> None:
        """Svi stalni tekstovi prozora; poziva se pri pokretanju i pri promjeni jezika."""
        self.file_menu.setTitle(tr("menu.file"))
        self.paste_action.setText(tr("menu.paste"))
        self.watch_clipboard_action.setText(tr("menu.watch_clipboard"))
        self.watch_clipboard_action.setChecked(self._watch_clipboard)
        self.enter_links_action.setText(tr("menu.enter_links"))
        self.choose_folder_action.setText(tr("menu.choose_folder"))
        self.open_folder_action.setText(tr("menu.open_folder"))
        self.exit_action.setText(tr("menu.exit"))
        self.downloads_menu.setTitle(tr("menu.downloads"))
        self.start_action.setText(tr("menu.start_all"))
        self.stop_action.setText(tr("menu.stop"))
        self.retry_failed_action.setText(tr("menu.retry_failed"))
        self.clear_action.setText(tr("menu.clear_finished"))
        self.remove_all_action.setText(tr("menu.remove_all"))
        self.history_action.setText(tr("menu.history"))
        self.subtitles_action.setText(tr("menu.subtitles"))
        self.thumbnail_action.setText(tr("menu.thumbnail"))
        self.whole_playlist_action.setText(tr("menu.whole_playlist"))
        self.rate_menu.setTitle(tr("menu.rate_limit"))
        for action in self.rate_actions.actions():
            value = action.data()
            action.setText(tr("rate.value", value=value) if value else tr("rate.none"))
        self._sync_option_actions()
        self.notify_action.setText(tr("menu.notify_done"))
        self.name_menu.setTitle(tr("menu.file_name"))
        for action in self.name_actions.actions():
            action.setText(tr(f"name.{action.data()}"))
        self.parallel_menu.setTitle(tr("menu.parallel"))
        for action in self.parallel_actions.actions():
            action.setChecked(action.data() == self._parallel)
        self.help_menu.setTitle(tr("menu.help"))
        self.check_updates_action.setText(tr("menu.check_updates"))
        self.whats_new_action.setText(tr("menu.whats_new"))
        self.update_ytdlp_action.setText(tr("menu.update_ytdlp"))
        self.theme_menu.setTitle(tr("menu.theme"))
        for action in self.theme_actions.actions():
            action.setText(tr(f"theme.{action.data()}"))
            action.setChecked(action.data() == self._theme)
        self.language_menu.setTitle(tr("menu.language"))
        for action in self.language_actions.actions():
            action.setChecked(action.data() == get_language())
        self.browser_help_action.setText(tr("menu.browser_help"))
        self.report_action.setText(tr("menu.report"))
        self.legal_action.setText(tr("menu.legal"))
        self.support_action.setText(tr("menu.support"))
        self.support_link.setText(f'<a href="support" style="color:{theme.c('support_link')};text-decoration:none">{tr("support.link")}</a>')
        self.support_banner_label.setText(tr("support.banner"))
        self.support_banner_button.setText(tr("support.button"))
        self.support_banner_later.setText(tr("support.later"))
        self.about_action.setText(tr("menu.about"))
        self.corner_link.setText(f'<a href="open" style="color:{theme.c("link")}">{tr("corner.open_folder")}</a>')

        self.paste_button.setText(tr("toolbar.paste"))
        self.paste_button.setToolTip(tr("toolbar.paste_tip"))
        current = self.preset_combo.currentData()
        self.preset_combo.blockSignals(True)
        for index in range(self.preset_combo.count()):
            self.preset_combo.setItemText(index, get_preset(self.preset_combo.itemData(index)).label)
        self.preset_combo.setCurrentIndex(max(self.preset_combo.findData(current), 0))
        self.preset_combo.blockSignals(False)
        missing = missing_tools()
        self.warning_label.setText(tr("warning.missing", items="; ".join(tr(key) for key in missing)))
        self.warning_label.setVisible(bool(missing))
        self.drop_zone.retranslate()
        self._update_folder_label()
        for item in self._queue.items():
            self._refresh_row(item)
        self._update_controls()

    def change_language(self, code: str) -> None:
        set_language(code)
        self._settings.setValue("language", get_language())
        self.retranslate_ui()

    def _build_ui(self) -> None:
        central = QWidget()
        central.setObjectName("central")
        layout = QVBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        toolbar = QFrame()
        toolbar.setObjectName("toolbar")
        bar = QHBoxLayout(toolbar)
        bar.setContentsMargins(14, 10, 14, 10)
        bar.setSpacing(8)
        self.paste_button = QPushButton()
        self.paste_button.setObjectName("pasteButton")
        self.paste_button.setIcon(icon("plus"))
        self.paste_button.setIconSize(QSize(14, 14))
        self.paste_button.clicked.connect(self._paste_from_clipboard)
        bar.addWidget(self.paste_button)
        self.preset_combo = QComboBox()
        self.preset_combo.setObjectName("presetCombo")
        for preset in PRESETS:
            self.preset_combo.addItem("", preset.key)
        self.preset_combo.currentIndexChanged.connect(self._on_preset_changed)
        bar.addWidget(self.preset_combo, 1)
        self.download_button = QPushButton()
        self.download_button.setObjectName("downloadButton")
        self.download_button.setIconSize(QSize(14, 14))
        self.download_button.clicked.connect(self._toggle_running)
        bar.addWidget(self.download_button)
        layout.addWidget(toolbar)

        self.warning_label = QLabel()
        self.warning_label.setObjectName("warning")
        self.warning_label.setWordWrap(True)
        layout.addWidget(self.warning_label)

        # Podsjetnik za dobrovoljni prilog: ništa ne blokira, „Kasnije" ga sakrije.
        self.support_banner = QFrame()
        self.support_banner.setObjectName("supportBanner")
        banner = QHBoxLayout(self.support_banner)
        banner.setContentsMargins(14, 8, 10, 8)
        self.support_banner_label = QLabel()
        self.support_banner_label.setWordWrap(True)
        banner.addWidget(self.support_banner_label, 1)
        self.support_banner_button = QPushButton()
        self.support_banner_button.setObjectName("supportButton")
        self.support_banner_button.clicked.connect(self._open_support)
        banner.addWidget(self.support_banner_button)
        self.support_banner_later = QPushButton()
        self.support_banner_later.clicked.connect(self._support_banner_later)
        banner.addWidget(self.support_banner_later)
        self.support_banner.hide()
        layout.addWidget(self.support_banner)

        self.stack = QStackedWidget()
        self.drop_zone = DropZone()
        self.drop_zone.paste_requested.connect(self._paste_from_clipboard)
        self.stack.addWidget(self.drop_zone)
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        rows = QWidget()
        rows.setObjectName("rows")
        self.rows_layout = QVBoxLayout(rows)
        self.rows_layout.setContentsMargins(0, 0, 0, 0)
        self.rows_layout.setSpacing(0)
        self.rows_layout.addStretch(1)
        self.scroll.setWidget(rows)
        self.stack.addWidget(self.scroll)
        layout.addWidget(self.stack, 1)
        self.setCentralWidget(central)

        self.status_label = QLabel()
        self.statusBar().addWidget(self.status_label, 1)
        self.summary_label = QLabel()
        self.statusBar().addPermanentWidget(self.summary_label)
        self.folder_label = QLabel()
        self.folder_label.linkActivated.connect(lambda _href: self._choose_folder())
        self.statusBar().addPermanentWidget(self.folder_label)
        self.support_link = QLabel()
        self.support_link.setObjectName("supportLink")
        self.support_link.linkActivated.connect(lambda _href: self._open_support())
        self.statusBar().addPermanentWidget(self.support_link)
        self.statusBar().setSizeGripEnabled(False)

    # ---------- podešavanja ----------

    def _load_settings(self) -> None:
        self.set_output_dir(self._settings.value("output_dir", default_output_dir(), type=str) or default_output_dir(),
                            save=False)
        self.set_watch_clipboard(self._settings.value("watch_clipboard", True, type=bool), save=False)
        self._support = support.SupportState(
            downloads=self._settings.value("support/downloads", 0, type=int),
            banner_next=self._settings.value("support/banner_next", support.BANNER_EVERY, type=int),
            last_dialog=self._settings.value("support/last_dialog", 0.0, type=float),
            snooze_until=self._settings.value("support/snooze_until", 0.0, type=float))
        self._subtitles = self._settings.value("subtitles", False, type=bool)
        self._thumbnail_cover = self._settings.value("thumbnail_cover", False, type=bool)
        self._whole_playlist = self._settings.value("whole_playlist", False, type=bool)
        self._notify_done = self._settings.value("notify_done", True, type=bool)
        name_template = self._settings.value("name_template", DEFAULT_NAME_TEMPLATE, type=str)
        self._name_template = name_template if name_template in NAME_TEMPLATES else DEFAULT_NAME_TEMPLATE
        name = self._settings.value("theme", theme.DEFAULT_THEME, type=str)
        self.set_theme(name if name in theme.THEMES else theme.DEFAULT_THEME, save=False)
        rate = self._settings.value("rate_limit", 0, type=int)
        self._rate_limit = rate if rate in RATE_CHOICES else 0
        parallel = self._settings.value("parallel", DEFAULT_PARALLEL, type=int)
        self._parallel = parallel if parallel in PARALLEL_CHOICES else DEFAULT_PARALLEL
        preset_key = self._settings.value("preset_key", DEFAULT_PRESET_KEY, type=str)
        self.preset_combo.blockSignals(True)
        self.preset_combo.setCurrentIndex(max(self.preset_combo.findData(preset_key), 0))
        self.preset_combo.blockSignals(False)

    def _save_settings(self) -> None:
        self._settings.setValue("output_dir", self._output_dir)
        self._settings.setValue("preset_key", self.preset_combo.currentData())
        self._settings.setValue("parallel", self._parallel)
        self._settings.setValue("subtitles", self._subtitles)
        self._settings.setValue("support/downloads", self._support.downloads)
        self._settings.setValue("support/banner_next", self._support.banner_next)
        self._settings.setValue("support/last_dialog", self._support.last_dialog)
        self._settings.setValue("support/snooze_until", self._support.snooze_until)
        self._settings.setValue("thumbnail_cover", self._thumbnail_cover)
        self._settings.setValue("whole_playlist", self._whole_playlist)
        self._settings.setValue("notify_done", self._notify_done)
        self._settings.setValue("name_template", self._name_template)
        self._settings.setValue("rate_limit", self._rate_limit)
        self._settings.setValue("theme", self._theme)
        self._settings.setValue("watch_clipboard", self._watch_clipboard)

    def _restore_queue(self) -> None:
        """Stavke koje su čekale pri zatvaranju (ili padu) vraćaju se u red, bez kolačića."""
        rows = store.load_queue(store.queue_path(self._data_dir))
        restored = 0
        for row in rows:
            if is_obviously_not_media(row["url"]):
                continue  # npr. kartica za .exe iz starije verzije: nema šta da se preuzme
            item = self._queue.add(row["url"], row.get("title") or row["url"],
                                   row.get("preset_key") or DEFAULT_PRESET_KEY,
                                   row.get("output_dir") or self._output_dir, row.get("subfolder"),
                                   http_headers=row.get("http_headers") or {},
                                   filename_title=row.get("filename_title"), thumbnail=row.get("thumbnail"),
                                   duration=row.get("duration"))
            item.custom_format = bool(row.get("custom_format"))
            section = row.get("section")
            if isinstance(section, (list, tuple)) and len(section) == 2:
                item.section = (float(section[0]), float(section[1]))
            self._append_row(item)
            restored += 1
        if restored:
            self._set_status(tr("status.queue_restored", count=restored))
        self._update_controls()

    def _save_queue(self) -> None:
        store.save_queue(self._queue.items(), store.queue_path(self._data_dir))

    # ---------- podrška (dobrovoljni prilog) ----------

    def _maybe_remind_support(self) -> None:
        now = time.time()
        if self._support.should_show_banner(now):
            self.support_banner.show()
        busy = bool(self._download_jobs) or self._running or bool(self._probe_jobs)
        if self._support.should_show_dialog(now, busy) and self._support_dialog is None:
            self.show_support_dialog(automatic=True)
        self._save_settings()

    @Slot()
    def _open_support(self) -> None:
        QDesktopServices.openUrl(QUrl(support.SUPPORT_URL))

    @Slot()
    def _support_banner_later(self) -> None:
        self._support.banner_later()
        self.support_banner.hide()
        self._save_settings()

    def show_support_dialog(self, automatic: bool) -> None:
        """Nije modalan za rad: preuzimanja teku dalje, a zatvaranje ništa ne mijenja u programu."""
        if automatic:
            self._support.dialog_shown(time.time())
        count = self._support.downloads
        text = tr("support.dialog_count", count=count) if count else tr("support.dialog_plain")
        dialog = SupportDialog(text, self)
        dialog.support_clicked.connect(self._open_support)
        dialog.already_clicked.connect(self._support_already)
        dialog.finished.connect(lambda _result: setattr(self, "_support_dialog", None))
        self._support_dialog = dialog
        dialog.open()

    @Slot()
    def _support_already(self) -> None:
        self._support.already_supported(time.time())
        self.support_banner.hide()
        self._save_settings()

    @Slot()
    def _show_legal(self) -> None:
        LegalDialog(self).exec()

    @Slot()
    def _show_whats_new(self) -> None:
        WhatsNewDialog(self).exec()

    @Slot()
    def _show_history(self) -> None:
        dialog = HistoryDialog(store.history_path(self._data_dir), self)
        dialog.exec()

    def set_watch_clipboard(self, enabled: bool, save: bool = True) -> None:
        """Kopiran link (Ctrl+C u browseru) sam ulazi u red; preuzimanje i dalje kreće na „Preuzmi"."""
        self._watch_clipboard = bool(enabled)
        self.watch_clipboard_action.setChecked(self._watch_clipboard)
        clipboard = QApplication.clipboard()
        if self._watch_clipboard:
            self._last_clipboard = clipboard.text()
            clipboard.dataChanged.connect(self._on_clipboard_change, Qt.ConnectionType.UniqueConnection)
        else:
            with contextlib.suppress(RuntimeError):
                clipboard.dataChanged.disconnect(self._on_clipboard_change)
        if save:
            self._save_settings()

    @Slot()
    def _on_clipboard_change(self) -> None:
        if not self._watch_clipboard:
            return
        text = QApplication.clipboard().text()
        if not text or text == self._last_clipboard:
            return
        self._last_clipboard = text
        known = {item.url for item in self._queue.items()}
        urls = [url for url in extract_urls(text) if url not in known]
        skipped = [url for url in urls if is_obviously_not_media(url)]
        urls = [url for url in urls if url not in skipped]
        if not urls:
            if skipped:
                self._set_status(tr("status.not_media", url=skipped[0]))
            return
        self._set_status(tr("status.clipboard_added", title=urls[0]))
        self._start_probe(urls)

    def _download_options(self, item: QueueItem) -> dict:
        options = {}
        if item.section:
            options["section"] = item.section
        if self._subtitles:
            options["subtitles"] = True
            options["subtitle_langs"] = subtitle_languages(get_language())
        if self._thumbnail_cover:
            options["thumbnail"] = True
        if self._name_template != DEFAULT_NAME_TEMPLATE:
            options["name_template"] = self._name_template
        if self._rate_limit:
            # Ukupno ograničenje se dijeli na preuzimanja koja mogu ići istovremeno.
            options["ratelimit"] = self._rate_limit * 1024 * 1024 // max(1, self._parallel)
        return options

    def _set_option(self, name: str, value) -> None:
        setattr(self, name, value)
        self._sync_option_actions()
        self._save_settings()

    def _sync_option_actions(self) -> None:
        self.subtitles_action.setChecked(self._subtitles)
        self.thumbnail_action.setChecked(self._thumbnail_cover)
        self.whole_playlist_action.setChecked(self._whole_playlist)
        self.notify_action.setChecked(self._notify_done)
        for action in self.name_actions.actions():
            action.setChecked(action.data() == self._name_template)
        for action in self.rate_actions.actions():
            action.setChecked(action.data() == self._rate_limit)

    def set_item_section(self, item_id: int, section: tuple[float, float] | None) -> None:
        item = self._queue.get(item_id)
        if item is None or item.status == ItemStatus.ACTIVE:
            return
        item.section = section
        self._sizes.pop(item_id, None)
        self._refresh_row(item)
        self._save_queue()

    def _ask_section(self, item_id: int) -> None:
        item = self._queue.get(item_id)
        if item is None:
            return
        text, ok = QInputDialog.getText(self, tr("section.title"), tr("section.prompt"),
                                        text=format_section(item.section))
        if not ok:
            return
        section = parse_section(text)
        if section is None:
            QMessageBox.warning(self, tr("section.title"), tr("section.invalid"))
            return
        self.set_item_section(item_id, section)

    def set_theme(self, name: str, save: bool = True) -> None:
        """Svijetla, tamna ili kao Windows; mijenja se odmah, bez ponovnog pokretanja."""
        self._theme = name if name in theme.THEMES else theme.DEFAULT_THEME
        dark = system_prefers_dark() if self._theme == "system" else self._theme == "dark"
        theme.set_colors(dark)
        app = QApplication.instance()
        if app is not None:
            apply_theme(app)
            # Samo „Kao Windows" prati promjenu teme u Windowsu dok program radi.
            follow = self._theme == "system"
            if follow != self._follows_system:
                signal = app.styleHints().colorSchemeChanged
                if follow:
                    signal.connect(self._on_system_scheme)
                else:
                    signal.disconnect(self._on_system_scheme)
                self._follows_system = follow
        self.setStyleSheet(theme.stylesheet())
        winshell.set_dark_title_bar(self, dark)
        for action in self.theme_actions.actions():
            action.setChecked(action.data() == self._theme)
        if hasattr(self, "drop_zone"):
            self.retranslate_ui()  # linkovi u tekstu nose svoju boju
            for item in self._queue.items():
                self._refresh_row(item)
            self.drop_zone.update()
        if save:
            self._save_settings()

    def _on_system_scheme(self, _scheme=None) -> None:
        if self._theme == "system":
            self.set_theme("system", save=False)

    def set_parallel(self, count: int) -> None:
        """Koliko preuzimanja ide istovremeno; veći broj ne znači uvijek brže (dijeli se veza)."""
        self._parallel = count if count in PARALLEL_CHOICES else DEFAULT_PARALLEL
        for action in self.parallel_actions.actions():
            action.setChecked(action.data() == self._parallel)
        self._save_settings()
        if self._running:
            self._start_next()

    @property
    def output_dir(self) -> str:
        return self._output_dir

    def set_output_dir(self, folder: str, save: bool = True) -> None:
        self._output_dir = os.path.normpath(folder)
        self._update_folder_label()
        self.drop_zone.set_folder(self._output_dir)
        if save:
            self._save_settings()

    def _update_folder_label(self) -> None:
        name = Path(self._output_dir).name or self._output_dir
        self.folder_label.setText(f'{tr("folder.label")} <a href="change" style="color:{theme.c("link")}">{name}</a>')
        self.folder_label.setToolTip(tr("folder.tip", path=self._output_dir))

    @Slot()
    def _choose_folder(self) -> None:
        folder = QFileDialog.getExistingDirectory(self, tr("dialog.choose_folder"), self._output_dir)
        if folder:
            self.set_output_dir(folder)

    @Slot(int)
    def _on_preset_changed(self, _index: int) -> None:
        self._save_settings()
        # Kao kod „izaberi format pa Preuzmi": izbor važi i za sve što još čeka.
        for item_id in self._queue.apply_preset_to_waiting(self.preset_combo.currentData()):
            self._refresh_row(self._queue.get(item_id))

    # ---------- dodavanje linkova ----------

    @Slot()
    def _paste_from_clipboard(self) -> None:
        self.add_links_from_text(QApplication.clipboard().text(), tr("status.clipboard_empty"))

    @Slot()
    def _enter_links(self) -> None:
        text, ok = QInputDialog.getMultiLineText(self, tr("dialog.enter_links_title"), tr("dialog.enter_links_label"))
        if ok:
            self.add_links_from_text(text, tr("status.no_links_entered"))

    def add_links_from_text(self, text: str, empty_message: str | None = None) -> None:
        urls = extract_urls(text)
        if not urls:
            self._set_status(empty_message or tr("status.no_link"))
            return
        self._start_probe(urls)

    def dragEnterEvent(self, event) -> None:
        mime = event.mimeData()
        if mime.hasUrls() or mime.hasText():
            event.acceptProposedAction()

    def dropEvent(self, event) -> None:
        mime = event.mimeData()
        text = "\n".join(url.toString() for url in mime.urls()) if mime.hasUrls() else mime.text()
        self.add_links_from_text(text, tr("status.drop_not_link"))
        event.acceptProposedAction()

    def _start_probe(self, urls: list[str], access: dict | None = None, auto_start: bool = False,
                     preset: str | None = None) -> None:
        # Isti link koji se upravo čita ne treba čitati dvaput (npr. hvatanje clipboarda pa „Zalijepi").
        urls = [url for url in urls if url not in self._probing]
        if not urls:
            return
        self._probing.update(urls)
        job = ProbeJob(self._next_probe_id, urls, self._output_dir, self._probe_fn, access, auto_start, preset,
                       {"whole_playlist": self._whole_playlist})
        self._next_probe_id += 1
        job.probed.connect(self._on_probed)
        job.failed.connect(self._on_probe_failed)
        job.finished.connect(self._on_probe_finished)
        self._probe_jobs[job.job_id] = job
        self._set_status(tr("status.loading_one") if len(urls) == 1 else tr("status.loading_many", count=len(urls)))
        self._update_controls()  # dugme postaje „Zaustavi" i dok traje čitanje linkova
        job.start()

    @Slot(object)
    def _on_browser_request(self, request: BrowserRequest) -> None:
        # Klik u browseru znači „preuzmi ovo sada", bez čekanja na dugme Preuzmi.
        access = {"http_headers": request.headers, "cookies": request.cookies}
        if request.media_url is None:
            self._start_probe([request.page_url], access, auto_start=True, preset=request.preset)
            return
        item = self._queue.add(request.media_url, request.page_title,
                               request.preset or self.preset_combo.currentData(),
                               self._output_dir, filename_title=request.page_title, **access)
        item.custom_format = bool(request.preset)  # izbor iz dodatka ne mijenja glavni format
        self._append_row(item)
        self._set_status(tr("status.from_browser", title=request.page_title))
        self._manual.append(item.id)
        self._start_next()

    @Slot()
    def _bring_to_front(self) -> None:
        if self.isMinimized():
            self.showNormal()
        self.show()
        self.raise_()
        self.activateWindow()

    @Slot(object, str, object, bool, object)
    def _on_probed(self, result: ProbeResult, output_dir: str, access: dict, auto_start: bool,
                   preset: str | None = None) -> None:
        if not result.entries:
            self._set_status(tr("status.playlist_empty", title=result.title))
            return
        subfolder = result.title if result.is_playlist else None
        preset_key = preset or self.preset_combo.currentData()
        for entry in result.entries:
            item = self._queue.add(entry.url, entry.title, preset_key, output_dir, subfolder,
                                   thumbnail=entry.thumbnail, duration=entry.duration, **access)
            item.custom_format = bool(preset)  # format tražen iz dodatka ostaje na toj stavci
            self._append_row(item)
            if auto_start:
                self._manual.append(item.id)
        if result.is_playlist:
            self._set_status(tr("status.playlist_added", title=result.title, count=len(result.entries)))
        elif auto_start:
            self._set_status(tr("status.from_browser", title=result.title))
        else:
            self._set_status(tr("status.added", title=result.title))
        self._start_next()

    @Slot(str, str, str, object, object)
    def _on_probe_failed(self, url: str, message: str, output_dir: str, access: dict,
                         preset: str | None = None) -> None:
        if message == MESSAGE_NOT_MEDIA:
            # Link na .exe, dokument ili običnu stranicu (kopiran, zalijepljen ili iz browsera):
            # nema šta da se preuzme, pa ni kartice; samo napomena u statusnoj traci.
            self._set_status(tr("status.not_media", url=url))
            return
        # Neuspio link ostaje vidljiv kao crveni red; „Pokušaj ponovo" ga daje yt-dlp-u direktno.
        item = self._queue.add(url, url, preset or self.preset_combo.currentData(), output_dir, **access)
        item.custom_format = bool(preset)
        item.status = ItemStatus.FAILED
        item.message = message
        self._append_row(item)
        self._refresh_row(item)
        self._note_error(message)
        self._set_status(tr("status.link_failed", message=display_message(message)))

    @Slot(int)
    def _on_probe_finished(self, job_id: int) -> None:
        job = self._probe_jobs.pop(job_id, None)
        if job is not None:
            self._probing.difference_update(job.urls)
            job.deleteLater()
        self._update_controls()

    # ---------- red preuzimanja ----------

    def _start_next(self) -> None:
        """Pokreće stavke dok ih u toku ne bude onoliko koliko je izabrano (Preuzimanja → Istovremeno)."""
        started = []
        while len(self._download_jobs) < self._parallel:
            item = None
            while self._manual and item is None:
                candidate = self._queue.get(self._manual.pop(0))
                if candidate is not None and candidate.status == ItemStatus.WAITING:
                    item = candidate
            if item is None and self._running:
                item = self._queue.next_waiting()
            if item is None:
                if not self._download_jobs:
                    self._running = False
                break
            item.status = ItemStatus.ACTIVE
            item.message = ""
            if not self._batch:
                self._batch_stopped = False
            self._batch[item.id] = 0.0
            self._refresh_row(item)
            job = DownloadJob(item, self._download_fn, self._download_options(item))
            job.progress.connect(self._on_download_progress)
            job.finished.connect(self._on_download_finished)
            self._download_jobs[item.id] = job
            started.append(job)
        self._update_controls()
        self._update_taskbar()
        for job in started:
            job.start()

    @Slot(int, object)
    def _on_download_progress(self, item_id: int, progress: Progress) -> None:
        item = self._queue.get(item_id)
        row = self._rows.get(item_id)
        if item is None or row is None or item.status != ItemStatus.ACTIVE:
            return
        audio = progress.label == "progress.audio" or get_preset(item.preset_key).is_audio
        row.show_progress(format_progress(progress), progress.fraction, "audio" if audio else "video")
        if progress.fraction is not None and item_id in self._batch:
            self._batch[item_id] = progress.fraction
            self._update_taskbar()

    @Slot(int, object)
    def _on_download_finished(self, item_id: int, result: DownloadResult) -> None:
        job = self._download_jobs.pop(item_id, None)
        if job is not None:
            job.deleteLater()
        item = self._queue.get(item_id)
        if item_id in self._batch:
            self._batch[item_id] = 1.0
        if item is not None and self._auto_retry(item, result):
            return
        if item is not None:
            item.status = result.status
            item.filepath = result.filepath
            item.message = MESSAGE_EXISTS if result.already_existed else result.message
            if result.status == ItemStatus.FAILED:
                self._note_error(result.message or "")
            if result.filepath and os.path.isfile(result.filepath):
                self._sizes[item_id] = os.path.getsize(result.filepath)
            if result.status == ItemStatus.DONE and result.filepath:
                store.append_history(item, store.history_path(self._data_dir), self._sizes.get(item_id))
                if not result.already_existed:
                    self._support.count_download()
            if item_id in self._remove_when_done:
                self._remove_when_done.discard(item_id)
                self._remove_item(item_id)
            else:
                self._refresh_row(item)
        self._save_queue()
        self._start_next()
        self._check_batch_done()
        self._maybe_remind_support()

    def _batch_fraction(self) -> float:
        waiting = 0
        if self._running:
            waiting = sum(1 for item in self._queue.items()
                          if item.status == ItemStatus.WAITING and item.id not in self._batch)
        total = len(self._batch) + waiting
        return sum(self._batch.values()) / total if total else 0.0

    def _update_taskbar(self) -> None:
        if self._batch and (self._download_jobs or self._running):
            self._taskbar.set(self._batch_fraction())

    def _check_batch_done(self) -> None:
        """Kad ništa više ne radi (ni ponovni pokušaj ne čeka): traka zadataka se čisti, stiže obavještenje."""
        if not self._batch or self._download_jobs or self._running:
            return
        items = [self._queue.get(item_id) for item_id in self._batch]
        if any(item is not None and item.status == ItemStatus.WAITING and item.message == MESSAGE_RETRY
               for item in items):
            return
        done = [item for item in items if item is not None and item.status == ItemStatus.DONE]
        failed = sum(1 for item in items if item is not None and item.status == ItemStatus.FAILED)
        stopped = self._batch_stopped
        self._batch.clear()
        self._taskbar.clear()
        if stopped or not self._notify_done or not (done or failed):
            return
        if self.isActiveWindow() and not self.isMinimized():
            return  # korisnik gleda u prozor: kartice već sve pokazuju
        if len(done) == 1 and not failed:
            title, body = tr("notify.done_one"), done[0].title
        else:
            title = tr("notify.done_many")
            body = tr("notify.summary", done=len(done), failed=failed) if failed else \
                tr("notify.summary_ok", done=len(done))
        QApplication.alert(self)  # dugme u traci zadataka zatreperi
        self._notifier(title, body)

    def _show_notification(self, title: str, body: str) -> None:
        if not QSystemTrayIcon.isSystemTrayAvailable():
            return
        if self._tray is None:
            self._tray = QSystemTrayIcon(self.windowIcon() or QApplication.windowIcon(), self)
            self._tray.setToolTip("Video Download")
            self._tray.messageClicked.connect(self._bring_to_front)
            self._tray.activated.connect(lambda _reason: self._bring_to_front())
        self._tray.show()
        self._tray.showMessage(title, body, QSystemTrayIcon.MessageIcon.Information, 8000)
        # Ikonica u sistemskoj traci treba samo za obavještenje; poslije se sklanja.
        QTimer.singleShot(15000, lambda: self._tray is not None and self._tray.hide())

    @Slot()
    def _toggle_running(self) -> None:
        if self._download_jobs or self._running or self._probe_jobs:
            self._stop_all()
        else:
            self._start_all()

    @Slot()
    def _start_all(self) -> None:
        if self._queue.next_waiting() is None:
            self._set_status(tr("status.nothing_to_download"))
            return
        self._running = True
        self._set_status("")
        self._start_next()

    def _cancel_active(self, item_id: int | None = None) -> bool:
        """Prekida jedno preuzimanje (ili sva). True kad je posao napušten jer još nije počeo."""
        jobs = [self._download_jobs[item_id]] if item_id in self._download_jobs else \
            (list(self._download_jobs.values()) if item_id is None else [])
        abandoned = False
        for job in jobs:
            job.cancel()
            if job.started:
                continue  # preuzimanje je počelo: nit sama prekida i briše svoje fajlove
            # Još se čitaju informacije o videu; na to se ne može uticati, pa se posao napušta.
            for signal in (job.progress, job.finished):
                with contextlib.suppress(RuntimeError):
                    signal.disconnect()
            self._download_jobs.pop(job.item_id, None)
            self._on_download_finished(job.item_id, DownloadResult(ItemStatus.CANCELLED))
            abandoned = True
        return abandoned

    def _cancel_probes(self) -> None:
        for job in list(self._probe_jobs.values()):
            job.cancel()
        self._probe_jobs.clear()

    def _auto_retry(self, item: QueueItem, result: DownloadResult) -> bool:
        """Veza pukne usred preuzimanja češće nego što se misli; stavka se sama vraća u red."""
        if result.status != ItemStatus.FAILED or not is_network_error(result.message or ""):
            return False
        if item.auto_retries >= MAX_AUTO_RETRIES or item.id in self._remove_when_done:
            return False
        item.auto_retries += 1
        item.status = ItemStatus.WAITING
        item.message = MESSAGE_RETRY
        self._refresh_row(item)
        self._set_status(tr("row.retrying"))
        QTimer.singleShot(AUTO_RETRY_DELAY_MS, lambda: self._retry_after_drop(item.id))
        self._update_controls()
        return True

    def _retry_after_drop(self, item_id: int) -> None:
        item = self._queue.get(item_id)
        if item is None or item.status != ItemStatus.WAITING or item.message != MESSAGE_RETRY:
            return  # u međuvremenu obrisano, ručno pokrenuto ili zaustavljeno
        self._manual.append(item_id)
        self._start_next()

    @Slot()
    def _stop_all(self) -> None:
        self._running = False
        self._manual.clear()
        for item in self._queue.items():
            if item.status == ItemStatus.WAITING and item.message == MESSAGE_RETRY:
                item.message = ""
                item.auto_retries = MAX_AUTO_RETRIES  # zaustavljeno ručno: bez daljeg ponavljanja
                self._refresh_row(item)
        self._cancel_probes()
        self._batch_stopped = True  # ručno zaustavljeno: bez obavještenja „sve je gotovo"
        if self._download_jobs:
            self._set_status(tr("status.stopping"))
            self._cancel_active()
        self._check_batch_done()
        self._update_controls()

    @Slot(int)
    def _on_row_action(self, item_id: int) -> None:
        item = self._queue.get(item_id)
        if item is None:
            return
        if item.status == ItemStatus.ACTIVE:
            self._cancel_active(item_id)
            return
        if item.status == ItemStatus.DONE:
            converted = item.convert_path if item.convert_path and os.path.isfile(item.convert_path) else None
            reveal(converted or item.filepath or _item_folder(item))
            return
        if item.status in (ItemStatus.FAILED, ItemStatus.CANCELLED):
            self._queue.retry(item_id)
            self._refresh_row(item)
        if self._running:
            self._queue.move_to_front(item_id)
        else:
            self._manual.append(item_id)
        self._start_next()

    @Slot(int)
    def _on_row_convert(self, item_id: int) -> None:
        item = self._queue.get(item_id)
        if item is None or item_id in self._convert_jobs or not convert.is_convertible(item.filepath):
            return
        item.convert_state, item.convert_message = "running", ""
        self._refresh_row(item)
        job = ConvertJob(item_id, item.filepath, item.duration, self._convert_fn)
        job.progress.connect(self._on_convert_progress)
        job.finished.connect(self._on_convert_finished)
        self._convert_jobs[item_id] = job
        job.start()

    @Slot(int, object)
    def _on_convert_progress(self, item_id: int, fraction) -> None:
        row = self._rows.get(item_id)
        if row is not None:
            percent = f" {round(fraction * 100)} %" if fraction is not None else ""
            row.show_progress(tr("row.converting") + percent, fraction, "audio")

    @Slot(int, object, str)
    def _on_convert_finished(self, item_id: int, path, error: str) -> None:
        job = self._convert_jobs.pop(item_id, None)
        if job is not None:
            job.deleteLater()
        item = self._queue.get(item_id)
        if item is None:
            return
        if path:
            item.convert_state, item.convert_path = "done", path
            mp3 = dataclasses.replace(item, filepath=path)
            store.append_history(mp3, store.history_path(self._data_dir), os.path.getsize(path))
        else:
            item.convert_state, item.convert_message = "failed", error
            self._note_error(error)
        row = self._rows.get(item_id)
        if row is not None:
            row.progress.hide()
        self._refresh_row(item)

    @Slot(int)
    def _on_row_play(self, item_id: int) -> None:
        item = self._queue.get(item_id)
        if item is None or not item.filepath or not os.path.isfile(item.filepath):
            self._set_status(tr("status.file_missing"))
            return
        play_file(item.filepath)

    @Slot(int)
    def _on_row_remove(self, item_id: int) -> None:
        item = self._queue.get(item_id)
        if item is None:
            return
        job = self._convert_jobs.pop(item_id, None)
        if job is not None:
            job.cancel()
        if item.status == ItemStatus.ACTIVE:
            self._remove_when_done.add(item_id)
            self._cancel_active(item_id)
            return
        self._remove_item(item_id)

    @Slot(int, QPoint)
    def _on_row_format(self, item_id: int, position: QPoint) -> None:
        item = self._queue.get(item_id)
        if item is None or item.status == ItemStatus.ACTIVE:
            return
        menu = QMenu(self)
        group = QActionGroup(menu)
        for preset in PRESETS:
            action = QAction(preset.label, menu, checkable=True)
            action.setChecked(preset.key == item.preset_key)
            action.setData(preset.key)
            group.addAction(action)
            menu.addAction(action)
        menu.addSeparator()
        section_action = menu.addAction(tr("row.section"))
        remove_section = menu.addAction(tr("row.section_remove")) if item.section else None
        chosen = menu.exec(position)
        if chosen is None:
            return
        if chosen is section_action:
            self._ask_section(item_id)
        elif chosen is remove_section:
            self.set_item_section(item_id, None)
        else:
            self.set_item_preset(item_id, chosen.data())

    def set_item_preset(self, item_id: int, preset_key: str) -> None:
        if self._queue.set_preset(item_id, preset_key):
            self._sizes.pop(item_id, None)
            self._refresh_row(self._queue.get(item_id))

    @Slot()
    def _retry_failed(self) -> None:
        for item in self._queue.items():
            if self._queue.retry(item.id):
                self._refresh_row(item)
                self._manual.append(item.id)
        self._start_next()

    @Slot()
    def _clear_finished(self) -> None:
        for item_id in self._queue.clear_finished():
            self._drop_row(item_id)
        self._update_controls()

    @Slot()
    def _remove_all(self) -> None:
        for item in self._queue.items():
            if item.status != ItemStatus.ACTIVE:
                self._remove_item(item.id)

    # ---------- redovi ----------

    def _append_row(self, item: QueueItem) -> None:
        row = QueueRow(item)
        row.action_clicked.connect(self._on_row_action)
        row.play_clicked.connect(self._on_row_play)
        row.convert_clicked.connect(self._on_row_convert)
        row.remove_clicked.connect(self._on_row_remove)
        row.format_clicked.connect(self._on_row_format)
        self._rows[item.id] = row
        self.rows_layout.insertWidget(self.rows_layout.count() - 1, row)
        if item.thumbnail:
            self._load_thumbnail(item.id, item.thumbnail)
        self._update_controls()

    def _refresh_row(self, item: QueueItem | None) -> None:
        if item is None:
            return
        row = self._rows.get(item.id)
        if row is not None:
            row.update_item(item, self._sizes.get(item.id))
        self._update_controls()

    def _remove_item(self, item_id: int) -> None:
        if self._queue.remove(item_id):
            self._drop_row(item_id)
        self._update_controls()

    def _drop_row(self, item_id: int) -> None:
        self._sizes.pop(item_id, None)
        row = self._rows.pop(item_id, None)
        if row is not None:
            self.rows_layout.removeWidget(row)
            row.deleteLater()

    def _load_thumbnail(self, item_id: int, url: str) -> None:
        cached = self._thumbnail_cache.get(url)
        if cached is not None:
            self._rows[item_id].thumbnail.set_pixmap(cached)
            return
        waiters = self._thumbnail_waiters.setdefault(url, [])
        waiters.append(item_id)
        if len(waiters) == 1:
            self._thumbnails.request(url)

    @Slot(str, QImage)
    def _on_thumbnail(self, url: str, image: QImage) -> None:
        pixmap = QPixmap.fromImage(image.scaled(192, 108, Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                                                Qt.TransformationMode.SmoothTransformation))
        self._thumbnail_cache[url] = pixmap
        for item_id in self._thumbnail_waiters.pop(url, []):
            row = self._rows.get(item_id)
            if row is not None:
                row.thumbnail.set_pixmap(pixmap)

    @Slot()
    def _open_folder(self) -> None:
        os.makedirs(self._output_dir, exist_ok=True)
        reveal(self._output_dir)

    # ---------- stanje ----------

    def _update_controls(self) -> None:
        items = self._queue.items()
        waiting = sum(item.status == ItemStatus.WAITING for item in items)
        done = sum(item.status == ItemStatus.DONE for item in items)
        failed = sum(item.status in (ItemStatus.FAILED, ItemStatus.CANCELLED) for item in items)
        # Čitanje linkova je takođe posao u toku: dugme mora nuditi „Zaustavi".
        busy = bool(self._download_jobs) or self._running or bool(self._probe_jobs)

        self.stack.setCurrentIndex(1 if items else 0)
        if busy:
            self.download_button.setText(tr("toolbar.stop"))
            self.download_button.setIcon(icon("stop"))
            self.download_button.setEnabled(True)
            set_state(self.download_button, "stop")
        else:
            self.download_button.setText(tr("toolbar.download"))
            self.download_button.setIcon(icon("download"))
            self.download_button.setEnabled(waiting > 0)
            set_state(self.download_button, "start")
        self.start_action.setEnabled(not busy and waiting > 0)
        self.stop_action.setEnabled(busy)
        self.retry_failed_action.setEnabled(failed > 0)
        self.clear_action.setEnabled(done > 0)
        self.remove_all_action.setEnabled(any(item.status != ItemStatus.ACTIVE for item in items))

        parts = []
        if self._download_jobs:
            parts.append(tr("summary.active", count=len(self._download_jobs)))
        if waiting:
            parts.append(tr("summary.waiting", count=waiting))
        if done:
            parts.append(tr("summary.done", count=done))
        if failed:
            parts.append(tr("summary.failed", count=failed))
        self.summary_label.setText(" · ".join(parts))

    def _set_status(self, text: str) -> None:
        self.status_label.setText(text)

    # ---------- pomoć ----------

    @Slot()
    def _show_browser_help(self) -> None:
        BrowserHelpDialog(str(extension_dir()), self).exec()

    def _note_error(self, message: str) -> None:
        if message:
            self._errors.append(f"{datetime.datetime.now():%H:%M:%S} {display_message(message)}")
            del self._errors[:-diagnostics.MAX_ERRORS]

    @Slot()
    def _save_report(self) -> None:
        """Jedan tekstualni fajl koji se može poslati: verzije, alati i posljednje greške."""
        suggestion = diagnostics.default_report_path(self._output_dir)
        chosen, _ = QFileDialog.getSaveFileName(self, tr("menu.report"), str(suggestion), "*.txt")
        if not chosen:
            return
        settings = {
            "jezik": get_language(),
            "folder": self._output_dir,
            "format": self.preset_combo.currentData(),
            "istovremeno": self._parallel,
            "hvatanje clipboarda": self._watch_clipboard,
            "stavki u redu": len(self._queue.items()),
        }
        try:
            Path(chosen).write_text(diagnostics.build_report(self._errors, settings), encoding="utf-8")
        except OSError as exc:
            self._set_status(tr("report.failed", error=exc))
            return
        self._set_status(tr("report.saved", path=chosen))
        reveal(chosen)

    @Slot()
    def _show_about(self) -> None:
        pending = ytdlp_update.pending_version()
        ytdlp = f"{ytdlp_update.active_version()} → {pending}" if pending else ytdlp_update.active_version()
        QMessageBox.about(self, tr("menu.about"), tr("about.text", version=__version__, ytdlp=ytdlp))

    # ---------- ažuriranje yt-dlp-a ----------

    def update_ytdlp(self, manual: bool) -> None:
        """Novi yt-dlp radi od sljedećeg pokretanja; tekući uvoz se ne može zamijeniti u hodu."""
        if self._ytdlp_job is not None:
            return
        if not manual:
            last = self._settings.value("last_ytdlp_check", 0.0, type=float)
            if time.time() - last < ytdlp_update.CHECK_INTERVAL_SECONDS:
                return
        self._settings.setValue("last_ytdlp_check", time.time())
        if manual:
            self._set_status(tr("ytdlp.checking"))
        job = YtdlpUpdateJob(manual)
        job.finished.connect(self._on_ytdlp_updated)
        self._ytdlp_job = job
        job.start()

    @Slot(object, object, bool)
    def _on_ytdlp_updated(self, version, error, manual: bool) -> None:
        self._ytdlp_job = None
        if error is not None:
            text = tr("ytdlp.failed", error=update_error_text(error))
            self._set_status(text)
            if manual:
                QMessageBox.warning(self, tr("menu.update_ytdlp"), text)
            return
        if version is None:
            if manual:
                QMessageBox.information(self, tr("menu.update_ytdlp"),
                                        tr("ytdlp.latest", version=ytdlp_update.active_version()))
            return
        text = tr("ytdlp.updated", version=version)
        self._set_status(text)
        if manual:
            QMessageBox.information(self, tr("menu.update_ytdlp"), text)

    # ---------- ažuriranje ----------

    def check_for_updates(self, manual: bool) -> None:
        if self._update_check_job is not None:
            return
        if not manual:
            last = self._settings.value("last_update_check", 0.0, type=float)
            if time.time() - last < updater.CHECK_INTERVAL_SECONDS:
                return
        self._settings.setValue("last_update_check", time.time())
        job = UpdateCheckJob(self._update_fetch or updater.fetch_latest, manual)
        job.finished.connect(self._on_update_checked)
        self._update_check_job = job
        job.start()

    @Slot(object, object, bool)
    def _on_update_checked(self, release, error, manual: bool) -> None:
        self._update_check_job = None
        if error is not None:
            if manual:
                QMessageBox.warning(self, tr("menu.check_updates"), tr("update.failed", error=update_error_text(error)))
            return
        if release is None or not updater.is_newer(release.version):
            if manual:
                QMessageBox.information(self, tr("menu.check_updates"), tr("update.latest", version=__version__))
            return
        answer = QMessageBox.question(self, tr("update.available_title"), tr(
            "update.available_text", new=release.version, current=__version__, notes=release.notes or "—"))
        if answer != QMessageBox.StandardButton.Yes:
            return
        if not updater.is_installed_app():
            QMessageBox.information(self, tr("update.available_title"), tr("update.dev_only", new=release.version))
            return
        if self._download_jobs:
            QMessageBox.information(self, tr("update.available_title"), tr("update.busy"))
            return
        self._install_update(release)

    def _install_update(self, release) -> None:
        dialog = QProgressDialog(tr("update.downloading"), tr("update.cancel"), 0, 100, self)
        dialog.setWindowTitle(tr("update.available_title"))
        dialog.setMinimumDuration(0)
        job = UpdateDownloadJob(release, Path(tempfile.gettempdir()) / "VideoDownload-update")
        dialog.canceled.connect(job.cancel)
        job.progress.connect(lambda done, total: dialog.setValue(int(done * 100 / total)) if total else None)

        def finished(path, error):
            dialog.close()
            job.deleteLater()
            if error is not None:
                if not job.cancelled:
                    QMessageBox.warning(self, tr("update.available_title"), tr("update.failed", error=update_error_text(error)))
                return
            updater.launch_installer(path, get_language())
            QApplication.quit()

        job.finished.connect(finished)
        self._update_download_job = job
        job.start()

    # ---------- zatvaranje ----------

    def closeEvent(self, event) -> None:
        if self._download_jobs:
            answer = QMessageBox.question(
                self, tr("close.title"), tr("close.text"))
            if answer != QMessageBox.StandardButton.Yes:
                event.ignore()
                return
            self._running = False
            jobs = list(self._download_jobs.values())
            for job in jobs:
                job.cancel()
            # Kratko sačekaj da se obrišu privremeni fajlovi prekinutih preuzimanja.
            for job in jobs:
                job.join(timeout=10)
        for job in list(self._convert_jobs.values()):
            job.cancel()
            job.join(timeout=5)
        self._save_settings()
        self._save_queue()
        self._taskbar.clear()
        if self._tray is not None:
            self._tray.hide()
        if self._follows_system:
            with contextlib.suppress(RuntimeError):
                QApplication.instance().styleHints().colorSchemeChanged.disconnect(self._on_system_scheme)
            self._follows_system = False
        # Prozor se gasi: signal clipboarda više ne smije stizati.
        with contextlib.suppress(RuntimeError):
            QApplication.clipboard().dataChanged.disconnect(self._on_clipboard_change)
        event.accept()


def _item_folder(item: QueueItem) -> str:
    folder = Path(item.output_dir)
    if item.subfolder:
        folder /= safe_folder_name(item.subfolder)
    return str(folder)


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


def _settings() -> QSettings:
    # VIDEODL_DATA_DIR odvaja podešavanja (npr. za testove) od korisnikovih u registry-ju.
    if os.environ.get("VIDEODL_DATA_DIR"):
        return QSettings(str(data_dir() / "settings.ini"), QSettings.Format.IniFormat)
    return QSettings("VideoDownload", "VideoDownload")


def _tool_version(path: str | None) -> str | None:
    """Prvi red `-version`: iz izvještaja se vidi koji je build ušao u paket."""
    if not path:
        return None
    try:
        result = subprocess.run([path, "-version"], capture_output=True, text=True, timeout=20,
                                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    except OSError:
        return None
    return (result.stdout.splitlines() or [""])[0][:120] or None


def self_test(report_path: str) -> int:
    """Provjera paketa bez prozora: uvozi, alati i yt-dlp dodaci. Rezultat ide u JSON fajl."""
    import importlib.util
    import json

    import yt_dlp

    checks = {
        "version": __version__,
        "yt_dlp": yt_dlp.version.__version__,
        "yt_dlp_store": str(ytdlp_update.store_dir()),
        "ffmpeg": find_tool("ffmpeg"),
        "ffmpeg_build": _tool_version(find_tool("ffmpeg")),
        "ffprobe": find_tool("ffprobe"),
        "node": find_tool("node"),
        "yt_dlp_ejs": importlib.util.find_spec("yt_dlp_ejs") is not None,
        "curl_cffi": importlib.util.find_spec("curl_cffi") is not None,
        "extension_manifest": (extension_dir() / "manifest.json").is_file(),
        "languages": sorted(LANGUAGES),
    }
    ok = all(checks[key] for key in ("ffmpeg", "ffprobe", "node", "yt_dlp_ejs", "curl_cffi", "extension_manifest"))
    checks["ok"] = ok
    Path(report_path).write_text(json.dumps(checks, indent=2), encoding="utf-8")
    return 0 if ok else 1


def main() -> int:
    args = sys.argv[1:]
    if args[:1] == ["--self-test"] and len(args) == 2:
        return self_test(args[1])
    if args[:1] == ["--uninstall-browser"]:
        # Deinstaler: ukloni registraciju za Chrome/Edge (HKCU) i generisane fajlove hosta.
        uninstall_native_host()
        return 0

    # Druga instanca samo podigne prozor prve (npr. dvoklik na pokreni.bat dok aplikacija radi).
    running = find_running_app()
    if running is not None:
        with contextlib.suppress(OSError):
            call_app(running, "POST", "/focus")
        return 0

    mark_running()
    app = QApplication(sys.argv)
    app.setApplicationName("Video Download")
    app.setWindowIcon(QIcon(str(extension_dir() / "icons" / "icon128.png")))
    apply_theme(app)
    window = MainWindow(settings=_settings(), check_updates_on_start=updater.is_installed_app())

    problems = []
    bridge = BridgeServer(window.browser_request.emit, window.focus_requested.emit)
    try:
        bridge.start()
    except OSError as exc:
        problems.append(tr("startup.bridge", error=exc))
    try:
        install_native_host()
    except OSError as exc:
        problems.append(tr("startup.register", error=exc))
    if problems:
        window._set_status(tr("startup.warning", problems="; ".join(problems)))

    window.show()
    try:
        return app.exec()
    finally:
        bridge.stop()
