"""Glavni prozor: traka (Zalijepi / format / Preuzmi), red preuzimanja sa sličicama, meni."""

import contextlib
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
    QApplication, QComboBox, QFileDialog, QFrame, QHBoxLayout, QInputDialog, QLabel, QMainWindow,
    QMenu, QMessageBox, QProgressDialog, QPushButton, QScrollArea, QStackedWidget, QVBoxLayout, QWidget,
)

from . import __version__
from .bridge import BridgeServer
from .browser import BrowserRequest
from .download import PROCESSING, DownloadResult, Progress, download
from .i18n import LANGUAGES, MESSAGE_EXISTS, get_language, pick_language, set_language, tr
from .icons import icon
from .jobs import DownloadQueue, ItemStatus, QueueItem
from .native_host import call_app, data_dir, find_running_app
from .native_messaging import install_native_host, uninstall_native_host
from .runtime import extension_dir, find_tool, mark_running
from .presets import DEFAULT_PRESET_KEY, PRESETS, get_preset, safe_folder_name
from .probe import ProbeResult, probe
from . import updater
from .widgets import LINK_COLOR, DropZone, QueueRow, display_message, set_state
from .ytdl import JS_RUNTIMES, error_message

_URL_PATTERN = re.compile(r"https?://[^\s<>\"']+", re.IGNORECASE)
MAX_THUMBNAIL_BYTES = 2 * 1024 * 1024

STYLE = f"""
QMainWindow, QWidget#central, QScrollArea, QWidget#rows, QWidget#dropZone {{ background: #ffffff; }}
QMenuBar {{ background: #ffffff; border-bottom: 1px solid #e6e6e6; padding: 2px 4px; }}
QMenuBar::item {{ padding: 4px 10px; background: transparent; }}
QMenuBar::item:selected {{ background: #eef3fb; }}
QLabel#cornerLink {{ padding-right: 10px; }}
QFrame#toolbar {{ background: #ffffff; border-bottom: 1px solid #e6e6e6; }}
QPushButton#pasteButton, QPushButton#downloadButton {{
    color: #ffffff; border: none; border-radius: 3px; padding: 0 18px; min-height: 32px; font-size: 10pt;
}}
QPushButton#pasteButton {{ background: #4caf50; }}
QPushButton#pasteButton:hover {{ background: #43a047; }}
QPushButton#pasteButton:pressed {{ background: #388e3c; }}
QPushButton#downloadButton {{ background: #1e88e5; }}
QPushButton#downloadButton:hover {{ background: #1976d2; }}
QPushButton#downloadButton:pressed {{ background: #1565c0; }}
QPushButton#downloadButton[state="stop"] {{ background: #e53935; }}
QPushButton#downloadButton[state="stop"]:hover {{ background: #d32f2f; }}
QPushButton#downloadButton:disabled {{ background: #a9cdf2; }}
QComboBox#presetCombo {{
    border: 1px solid #cfcfcf; border-radius: 3px; padding: 0 10px; min-height: 32px; background: #ffffff;
    font-size: 10pt;
}}
QComboBox#presetCombo:hover {{ border-color: #9fbfe8; }}
QComboBox#presetCombo::drop-down {{ border: none; width: 28px; }}
QComboBox#presetCombo::down-arrow {{ image: url("{(Path(__file__).parent / 'assets' / 'chevron-down.svg').as_posix()}"); width: 12px; height: 12px; }}
QComboBox#presetCombo QAbstractItemView {{ border: 1px solid #cfcfcf; selection-background-color: #e8f0fe; selection-color: #202124; }}
QLabel#warning {{ background: #fff4e5; color: #8a5300; padding: 6px 12px; border-bottom: 1px solid #f3d9b1; }}
QFrame#queueRow {{ background: #ffffff; border-bottom: 1px solid #ececec; }}
QFrame#queueRow:hover {{ background: #f7faff; }}
QLabel#rowTitle {{ color: #202124; font-size: 10pt; }}
QLabel#rowStatus {{ color: #7a7a7a; }}
QLabel#rowStatus[state="done"] {{ color: #2e7d32; }}
QLabel#rowStatus[state="failed"] {{ color: #c62828; }}
QProgressBar#rowProgress {{ background: #e3ecf8; border: none; border-radius: 2px; }}
QProgressBar#rowProgress::chunk {{ background: #1e88e5; border-radius: 2px; }}
QToolButton#rowAction {{ border: none; border-radius: 17px; background: transparent; }}
QToolButton#rowAction:hover {{ background: #e8f0fe; }}
QToolButton#rowRemove {{ border: none; border-radius: 10px; background: transparent; }}
QToolButton#rowRemove:hover {{ background: #eeeeee; }}
QLabel#dropTitle {{ color: #5f6368; font-size: 10pt; }}
QLabel#dropHint {{ color: #9aa0a6; }}
QStatusBar {{ background: #fafafa; border-top: 1px solid #e6e6e6; color: #666666; }}
QStatusBar QLabel {{ color: #666666; padding: 0 6px; }}
QScrollArea {{ border: none; }}
"""


def default_output_dir() -> str:
    return str(Path.home() / "Videos" / "Video Download")


def format_speed(bytes_per_second: float) -> str:
    value = bytes_per_second / 1024
    for unit in ("KB/s", "MB/s", "GB/s"):
        if value < 1024 or unit == "GB/s":
            return f"{value:.1f} {unit}".replace(".", ",")
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
    # Izgled je namjerno svijetao i isti bez obzira na temu Windowsa.
    app.setStyle("Fusion")
    app.setFont(QFont("Segoe UI", 9))
    palette = QPalette()
    for role, color in ((QPalette.ColorRole.Window, "#ffffff"), (QPalette.ColorRole.Base, "#ffffff"),
                        (QPalette.ColorRole.AlternateBase, "#f5f5f5"), (QPalette.ColorRole.Text, "#202124"),
                        (QPalette.ColorRole.WindowText, "#202124"), (QPalette.ColorRole.Button, "#f3f3f3"),
                        (QPalette.ColorRole.ButtonText, "#202124"), (QPalette.ColorRole.Highlight, "#1e88e5"),
                        (QPalette.ColorRole.HighlightedText, "#ffffff"), (QPalette.ColorRole.ToolTipBase, "#ffffff"),
                        (QPalette.ColorRole.ToolTipText, "#202124"), (QPalette.ColorRole.Link, LINK_COLOR)):
        palette.setColor(role, QColor(color))
    app.setPalette(palette)


class ProbeJob(QObject):
    """Čita linkove u pozadinskoj niti. Signali se u glavnoj niti isporučuju redom."""

    # access: {"http_headers": ..., "cookies": ...} za sajt iz browsera, samo neprazni ključevi
    probed = Signal(object, str, object, bool)  # ProbeResult, output_dir, access, odmah preuzmi
    failed = Signal(str, str, str, object)  # link, poruka, output_dir, access
    finished = Signal(int)  # id posla

    def __init__(self, job_id: int, urls: list[str], output_dir: str, probe_fn,
                 access: dict | None = None, auto_start: bool = False):
        super().__init__()
        self.job_id = job_id
        self._urls = urls
        self._output_dir = output_dir
        self._probe_fn = probe_fn
        self._access = {key: value for key, value in (access or {}).items() if value}
        self._auto_start = auto_start

    def start(self) -> None:
        # daemon: čitanje linka se ne može prekinuti, a ne smije držati program pri zatvaranju
        threading.Thread(target=self._run, daemon=True).start()

    def _run(self) -> None:
        for url in self._urls:
            try:
                result = self._probe_fn(url, **self._access)
                self.probed.emit(result, self._output_dir, self._access, self._auto_start)
            except Exception as exc:  # granica radne niti
                self.failed.emit(url, error_message(exc), self._output_dir, self._access)
        self.finished.emit(self.job_id)


class DownloadJob(QObject):
    progress = Signal(int, object)  # id stavke, Progress
    finished = Signal(int, object)  # id stavke, DownloadResult

    def __init__(self, item: QueueItem, download_fn):
        super().__init__()
        self.item_id = item.id
        self._args = (item.url, get_preset(item.preset_key), item.output_dir, item.subfolder)
        self._extra = {"http_headers": dict(item.http_headers), "filename_title": item.filename_title}
        if item.cookies:
            self._extra["cookies"] = item.cookies
        self._download_fn = download_fn
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
            result = self._download_fn(*self._args, on_progress=self._report,
                                       cancel_event=self._cancel, **self._extra)
        except Exception as exc:  # granica radne niti
            result = DownloadResult(ItemStatus.FAILED, message=error_message(exc))
        self.finished.emit(self.item_id, result)

    def _report(self, progress: Progress) -> None:
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
                 thumbnail_fetch=fetch_thumbnail, update_fetch=None, check_updates_on_start: bool = False):
        super().__init__()
        self.browser_request.connect(self._on_browser_request)
        self.focus_requested.connect(self._bring_to_front)
        self._settings = settings if settings is not None else QSettings("VideoDownload", "VideoDownload")
        self._probe_fn = probe_fn
        self._download_fn = download_fn
        self._queue = DownloadQueue()
        self._rows: dict[int, QueueRow] = {}
        self._sizes: dict[int, int] = {}
        self._running = False  # „Preuzmi" je pokrenut: red se obrađuje dok ima stavki koje čekaju
        self._manual: list[int] = []  # pojedinačno pokrenute stavke (dugme u redu, browser)
        self._remove_when_done: set[int] = set()
        self._download_job: DownloadJob | None = None
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
        self.setStyleSheet(STYLE)
        self._update_fetch = update_fetch
        self._update_check_job = None
        self._build_menu()
        self._build_ui()
        self._load_settings()
        self.retranslate_ui()
        if check_updates_on_start:
            QTimer.singleShot(4000, lambda: self.check_for_updates(manual=False))

    # ---------- izgled ----------

    def _build_menu(self) -> None:
        menu = self.menuBar()
        self.file_menu = menu.addMenu("")
        self.paste_action = self.file_menu.addAction("", self._paste_from_clipboard)
        self.paste_action.setShortcut(QKeySequence.StandardKey.Paste)
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

        self.help_menu = menu.addMenu("")
        self.check_updates_action = self.help_menu.addAction("", lambda: self.check_for_updates(manual=True))
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
        self.help_menu.setTitle(tr("menu.help"))
        self.check_updates_action.setText(tr("menu.check_updates"))
        self.language_menu.setTitle(tr("menu.language"))
        for action in self.language_actions.actions():
            action.setChecked(action.data() == get_language())
        self.browser_help_action.setText(tr("menu.browser_help"))
        self.about_action.setText(tr("menu.about"))
        self.corner_link.setText(f'<a href="open" style="color:{LINK_COLOR}">{tr("corner.open_folder")}</a>')

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
        self.statusBar().setSizeGripEnabled(False)

    # ---------- podešavanja ----------

    def _load_settings(self) -> None:
        self.set_output_dir(self._settings.value("output_dir", default_output_dir(), type=str) or default_output_dir(),
                            save=False)
        preset_key = self._settings.value("preset_key", DEFAULT_PRESET_KEY, type=str)
        self.preset_combo.blockSignals(True)
        self.preset_combo.setCurrentIndex(max(self.preset_combo.findData(preset_key), 0))
        self.preset_combo.blockSignals(False)

    def _save_settings(self) -> None:
        self._settings.setValue("output_dir", self._output_dir)
        self._settings.setValue("preset_key", self.preset_combo.currentData())

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
        self.folder_label.setText(f'{tr("folder.label")} <a href="change" style="color:{LINK_COLOR}">{name}</a>')
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

    def _start_probe(self, urls: list[str], access: dict | None = None, auto_start: bool = False) -> None:
        job = ProbeJob(self._next_probe_id, urls, self._output_dir, self._probe_fn, access, auto_start)
        self._next_probe_id += 1
        job.probed.connect(self._on_probed)
        job.failed.connect(self._on_probe_failed)
        job.finished.connect(self._on_probe_finished)
        self._probe_jobs[job.job_id] = job
        self._set_status(tr("status.loading_one") if len(urls) == 1 else tr("status.loading_many", count=len(urls)))
        job.start()

    @Slot(object)
    def _on_browser_request(self, request: BrowserRequest) -> None:
        # Klik u browseru znači „preuzmi ovo sada", bez čekanja na dugme Preuzmi.
        access = {"http_headers": request.headers, "cookies": request.cookies}
        if request.media_url is None:
            self._start_probe([request.page_url], access, auto_start=True)
            return
        item = self._queue.add(request.media_url, request.page_title, self.preset_combo.currentData(),
                               self._output_dir, filename_title=request.page_title, **access)
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

    @Slot(object, str, object, bool)
    def _on_probed(self, result: ProbeResult, output_dir: str, access: dict, auto_start: bool) -> None:
        if not result.entries:
            self._set_status(tr("status.playlist_empty", title=result.title))
            return
        subfolder = result.title if result.is_playlist else None
        preset_key = self.preset_combo.currentData()
        for entry in result.entries:
            item = self._queue.add(entry.url, entry.title, preset_key, output_dir, subfolder,
                                   thumbnail=entry.thumbnail, duration=entry.duration, **access)
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

    @Slot(str, str, str, object)
    def _on_probe_failed(self, url: str, message: str, output_dir: str, access: dict) -> None:
        # Neuspio link ostaje vidljiv kao crveni red; „Pokušaj ponovo" ga daje yt-dlp-u direktno.
        item = self._queue.add(url, url, self.preset_combo.currentData(), output_dir, **access)
        item.status = ItemStatus.FAILED
        item.message = message
        self._append_row(item)
        self._refresh_row(item)
        self._set_status(tr("status.link_failed", message=display_message(message)))

    @Slot(int)
    def _on_probe_finished(self, job_id: int) -> None:
        job = self._probe_jobs.pop(job_id, None)
        if job is not None:
            job.deleteLater()

    # ---------- red preuzimanja ----------

    def _start_next(self) -> None:
        if self._download_job is not None:
            self._update_controls()
            return
        item = None
        while self._manual and item is None:
            candidate = self._queue.get(self._manual.pop(0))
            if candidate is not None and candidate.status == ItemStatus.WAITING:
                item = candidate
        if item is None and self._running:
            item = self._queue.next_waiting()
        if item is None:
            self._running = False
            self._update_controls()
            return

        item.status = ItemStatus.ACTIVE
        item.message = ""
        self._refresh_row(item)
        job = DownloadJob(item, self._download_fn)
        job.progress.connect(self._on_download_progress)
        job.finished.connect(self._on_download_finished)
        self._download_job = job
        self._update_controls()
        job.start()

    @Slot(int, object)
    def _on_download_progress(self, item_id: int, progress: Progress) -> None:
        item = self._queue.get(item_id)
        row = self._rows.get(item_id)
        if item is None or row is None or item.status != ItemStatus.ACTIVE:
            return
        row.show_progress(format_progress(progress), progress.fraction)

    @Slot(int, object)
    def _on_download_finished(self, item_id: int, result: DownloadResult) -> None:
        if self._download_job is not None and self._download_job.item_id == item_id:
            self._download_job.deleteLater()
            self._download_job = None
        item = self._queue.get(item_id)
        if item is not None:
            item.status = result.status
            item.filepath = result.filepath
            item.message = MESSAGE_EXISTS if result.already_existed else result.message
            if result.filepath and os.path.isfile(result.filepath):
                self._sizes[item_id] = os.path.getsize(result.filepath)
            if item_id in self._remove_when_done:
                self._remove_when_done.discard(item_id)
                self._remove_item(item_id)
            else:
                self._refresh_row(item)
        self._start_next()

    @Slot()
    def _toggle_running(self) -> None:
        if self._download_job is not None or self._running:
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

    @Slot()
    def _stop_all(self) -> None:
        self._running = False
        self._manual.clear()
        if self._download_job is not None:
            self._download_job.cancel()
            self._set_status(tr("status.stopping"))
        self._update_controls()

    @Slot(int)
    def _on_row_action(self, item_id: int) -> None:
        item = self._queue.get(item_id)
        if item is None:
            return
        if item.status == ItemStatus.ACTIVE:
            self._download_job.cancel()
            return
        if item.status == ItemStatus.DONE:
            reveal(item.filepath or _item_folder(item))
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
        if item.status == ItemStatus.ACTIVE:
            self._remove_when_done.add(item_id)
            self._download_job.cancel()
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
        chosen = menu.exec(position)
        if chosen is not None:
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
        busy = self._download_job is not None or self._running

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
        if self._download_job is not None:
            parts.append(tr("summary.active"))
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
        QMessageBox.information(self, tr("menu.browser_help"), tr("help.browser_text", folder=str(extension_dir())))

    @Slot()
    def _show_about(self) -> None:
        QMessageBox.about(self, tr("menu.about"), tr("about.text", version=__version__))

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
        if self._download_job is not None:
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
        if self._download_job is not None:
            answer = QMessageBox.question(
                self, tr("close.title"), tr("close.text"))
            if answer != QMessageBox.StandardButton.Yes:
                event.ignore()
                return
            self._running = False
            self._download_job.cancel()
            # Kratko sačekaj da se obrišu privremeni fajlovi prekinutog preuzimanja.
            self._download_job.join(timeout=10)
        self._save_settings()
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


def self_test(report_path: str) -> int:
    """Provjera paketa bez prozora: uvozi, alati i yt-dlp dodaci. Rezultat ide u JSON fajl."""
    import importlib.util
    import json

    import yt_dlp

    checks = {
        "version": __version__,
        "yt_dlp": yt_dlp.version.__version__,
        "ffmpeg": find_tool("ffmpeg"),
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
