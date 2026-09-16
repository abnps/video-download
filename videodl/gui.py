"""Glavni prozor: traka (Zalijepi / format / Preuzmi), red preuzimanja sa sličicama, meni."""

import contextlib
import os
import queue
import re
import shutil
import subprocess
import sys
import threading
import urllib.request
from pathlib import Path

from PySide6.QtCore import QObject, QPoint, QSettings, QSize, Qt, QUrl, Signal, Slot
from PySide6.QtGui import (
    QAction, QActionGroup, QColor, QDesktopServices, QFont, QIcon, QImage, QKeySequence, QPalette, QPixmap,
)
from PySide6.QtWidgets import (
    QApplication, QComboBox, QFileDialog, QFrame, QHBoxLayout, QInputDialog, QLabel, QMainWindow,
    QMenu, QMessageBox, QPushButton, QScrollArea, QStackedWidget, QVBoxLayout, QWidget,
)

from . import __version__
from .bridge import BridgeServer
from .browser import BrowserRequest
from .download import PROCESSING, DownloadResult, Progress, download
from .icons import icon
from .jobs import DownloadQueue, ItemStatus, QueueItem
from .native_host import call_app, data_dir, find_running_app
from .native_messaging import PROJECT_ROOT, install_native_host
from .presets import DEFAULT_PRESET_KEY, PRESETS, get_preset, safe_folder_name
from .probe import ProbeResult, probe
from .widgets import LINK_COLOR, DropZone, QueueRow, set_state
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
        return f"{progress.label}…"
    parts = ["Preuzimanje" + (f" ({progress.label})" if progress.label else "")]
    if progress.fraction is not None:
        parts.append(f"{progress.fraction:.0%}")
    if progress.speed:
        parts.append(format_speed(progress.speed))
    if progress.eta is not None:
        parts.append(f"još {format_eta(progress.eta)}")
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
    if not shutil.which("ffmpeg"):
        missing.append("ffmpeg (bez njega nema spajanja videa i zvuka ni MP3/M4A)")
    if not any(shutil.which(name) for name in JS_RUNTIMES):
        missing.append("Node.js ili Deno (YouTube bez njih često ne radi)")
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

    probed = Signal(object, str, object, bool)  # ProbeResult, output_dir, zaglavlja, odmah preuzmi
    failed = Signal(str, str, str, object)  # link, poruka, output_dir, zaglavlja
    finished = Signal(int)  # id posla

    def __init__(self, job_id: int, urls: list[str], output_dir: str, probe_fn,
                 http_headers: dict[str, str] | None = None, auto_start: bool = False):
        super().__init__()
        self.job_id = job_id
        self._urls = urls
        self._output_dir = output_dir
        self._probe_fn = probe_fn
        self._http_headers = dict(http_headers or {})
        self._auto_start = auto_start

    def start(self) -> None:
        # daemon: čitanje linka se ne može prekinuti, a ne smije držati program pri zatvaranju
        threading.Thread(target=self._run, daemon=True).start()

    def _run(self) -> None:
        for url in self._urls:
            try:
                result = self._probe_fn(url, http_headers=self._http_headers)
                self.probed.emit(result, self._output_dir, self._http_headers, self._auto_start)
            except Exception as exc:  # granica radne niti
                self.failed.emit(url, error_message(exc), self._output_dir, self._http_headers)
        self.finished.emit(self.job_id)


class DownloadJob(QObject):
    progress = Signal(int, object)  # id stavke, Progress
    finished = Signal(int, object)  # id stavke, DownloadResult

    def __init__(self, item: QueueItem, download_fn):
        super().__init__()
        self.item_id = item.id
        self._args = (item.url, get_preset(item.preset_key), item.output_dir, item.subfolder)
        self._extra = {"http_headers": dict(item.http_headers), "filename_title": item.filename_title}
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


class MainWindow(QMainWindow):
    # Stižu iz niti lokalnog mosta; Qt ih isporučuje u glavnoj niti.
    browser_request = Signal(object)  # BrowserRequest
    focus_requested = Signal()

    def __init__(self, settings: QSettings | None = None, probe_fn=probe, download_fn=download,
                 thumbnail_fetch=fetch_thumbnail):
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

        self.setWindowTitle(f"Video Download {__version__}")
        self.setMinimumSize(640, 380)
        self.resize(820, 520)
        self.setAcceptDrops(True)
        self.setStyleSheet(STYLE)
        self._build_menu()
        self._build_ui()
        self._load_settings()
        self._update_controls()

    # ---------- izgled ----------

    def _build_menu(self) -> None:
        menu = self.menuBar()
        file_menu = menu.addMenu("&Fajl")
        self.paste_action = file_menu.addAction("Zalijepi link iz clipboarda", self._paste_from_clipboard)
        self.paste_action.setShortcut(QKeySequence.StandardKey.Paste)
        file_menu.addAction("Unesi linkove…", self._enter_links).setShortcut(QKeySequence("Ctrl+L"))
        file_menu.addSeparator()
        file_menu.addAction("Folder za preuzimanja…", self._choose_folder)
        file_menu.addAction("Otvori folder za preuzimanja", self._open_folder)
        file_menu.addSeparator()
        file_menu.addAction("Izlaz", self.close).setShortcut(QKeySequence("Ctrl+Q"))

        downloads = menu.addMenu("&Preuzimanja")
        self.start_action = downloads.addAction("Preuzmi sve", self._start_all)
        self.start_action.setShortcut(QKeySequence("F5"))
        self.stop_action = downloads.addAction("Zaustavi", self._stop_all)
        downloads.addSeparator()
        self.retry_failed_action = downloads.addAction("Ponovi neuspjele", self._retry_failed)
        self.clear_action = downloads.addAction("Očisti završene", self._clear_finished)
        self.remove_all_action = downloads.addAction("Ukloni sve sa liste", self._remove_all)

        help_menu = menu.addMenu("P&omoć")
        help_menu.addAction("Preuzimanje iz browsera", self._show_browser_help)
        help_menu.addAction("O programu", self._show_about)

        # Referenca se čuva: PySide ne preuzima vlasništvo, pa bi Python obrisao label.
        self.corner_link = QLabel(f'<a href="open" style="color:{LINK_COLOR}">Otvori folder</a>')
        self.corner_link.setObjectName("cornerLink")
        self.corner_link.linkActivated.connect(lambda _href: self._open_folder())
        menu.setCornerWidget(self.corner_link, Qt.Corner.TopRightCorner)

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
        self.paste_button = QPushButton("Zalijepi")
        self.paste_button.setObjectName("pasteButton")
        self.paste_button.setIcon(icon("plus"))
        self.paste_button.setIconSize(QSize(14, 14))
        self.paste_button.setToolTip("Dodaj link iz clipboarda (Ctrl+V)")
        self.paste_button.clicked.connect(self._paste_from_clipboard)
        bar.addWidget(self.paste_button)
        self.preset_combo = QComboBox()
        self.preset_combo.setObjectName("presetCombo")
        for preset in PRESETS:
            self.preset_combo.addItem(preset.label, preset.key)
        self.preset_combo.currentIndexChanged.connect(self._on_preset_changed)
        bar.addWidget(self.preset_combo, 1)
        self.download_button = QPushButton()
        self.download_button.setObjectName("downloadButton")
        self.download_button.setIconSize(QSize(14, 14))
        self.download_button.clicked.connect(self._toggle_running)
        bar.addWidget(self.download_button)
        layout.addWidget(toolbar)

        missing = missing_tools()
        self.warning_label = QLabel("Nije pronađeno: " + "; ".join(missing))
        self.warning_label.setObjectName("warning")
        self.warning_label.setWordWrap(True)
        self.warning_label.setVisible(bool(missing))
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
        name = Path(self._output_dir).name or self._output_dir
        self.folder_label.setText(f'Folder: <a href="change" style="color:{LINK_COLOR}">{name}</a>')
        self.folder_label.setToolTip(f"{self._output_dir}\nKlikni za promjenu")
        self.drop_zone.set_folder(self._output_dir)
        if save:
            self._save_settings()

    @Slot()
    def _choose_folder(self) -> None:
        folder = QFileDialog.getExistingDirectory(self, "Izaberi folder za preuzimanja", self._output_dir)
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
        self.add_links_from_text(QApplication.clipboard().text(), "U clipboardu nema linka. Kopiraj link videa pa klikni „Zalijepi“.")

    @Slot()
    def _enter_links(self) -> None:
        text, ok = QInputDialog.getMultiLineText(self, "Unesi linkove", "Linkovi videa ili plejlista (jedan po redu):")
        if ok:
            self.add_links_from_text(text, "Nije unesen nijedan link.")

    def add_links_from_text(self, text: str, empty_message: str = "Nema linka.") -> None:
        urls = extract_urls(text)
        if not urls:
            self._set_status(empty_message)
            return
        self._start_probe(urls)

    def dragEnterEvent(self, event) -> None:
        mime = event.mimeData()
        if mime.hasUrls() or mime.hasText():
            event.acceptProposedAction()

    def dropEvent(self, event) -> None:
        mime = event.mimeData()
        text = "\n".join(url.toString() for url in mime.urls()) if mime.hasUrls() else mime.text()
        self.add_links_from_text(text, "Prevučeni sadržaj nije link.")
        event.acceptProposedAction()

    def _start_probe(self, urls: list[str], http_headers: dict[str, str] | None = None,
                     auto_start: bool = False) -> None:
        job = ProbeJob(self._next_probe_id, urls, self._output_dir, self._probe_fn, http_headers, auto_start)
        self._next_probe_id += 1
        job.probed.connect(self._on_probed)
        job.failed.connect(self._on_probe_failed)
        job.finished.connect(self._on_probe_finished)
        self._probe_jobs[job.job_id] = job
        self._set_status("Učitavam informacije o linku…" if len(urls) == 1
                         else f"Učitavam informacije o {len(urls)} linka…")
        job.start()

    @Slot(object)
    def _on_browser_request(self, request: BrowserRequest) -> None:
        # Klik u browseru znači „preuzmi ovo sada", bez čekanja na dugme Preuzmi.
        if request.media_url is None:
            self._start_probe([request.page_url], request.headers, auto_start=True)
            return
        item = self._queue.add(request.media_url, request.page_title, self.preset_combo.currentData(),
                               self._output_dir, http_headers=request.headers,
                               filename_title=request.page_title)
        self._append_row(item)
        self._set_status(f"Iz browsera: {request.page_title}")
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
    def _on_probed(self, result: ProbeResult, output_dir: str, http_headers: dict[str, str],
                   auto_start: bool) -> None:
        if not result.entries:
            self._set_status(f"Plejlista „{result.title}“ nema dostupnih videa.")
            return
        subfolder = result.title if result.is_playlist else None
        preset_key = self.preset_combo.currentData()
        for entry in result.entries:
            item = self._queue.add(entry.url, entry.title, preset_key, output_dir, subfolder,
                                   http_headers=http_headers, thumbnail=entry.thumbnail, duration=entry.duration)
            self._append_row(item)
            if auto_start:
                self._manual.append(item.id)
        if result.is_playlist:
            self._set_status(f"Dodana plejlista „{result.title}“: {len(result.entries)} videa.")
        elif auto_start:
            self._set_status(f"Iz browsera: {result.title}")
        else:
            self._set_status(f"Dodano: {result.title}. Klikni „Preuzmi“.")
        self._start_next()

    @Slot(str, str, str, object)
    def _on_probe_failed(self, url: str, message: str, output_dir: str, http_headers: dict[str, str]) -> None:
        # Neuspio link ostaje vidljiv kao crveni red; „Pokušaj ponovo" ga daje yt-dlp-u direktno.
        item = self._queue.add(url, url, self.preset_combo.currentData(), output_dir, http_headers=http_headers)
        item.status = ItemStatus.FAILED
        item.message = message
        self._append_row(item)
        self._refresh_row(item)
        self._set_status(f"Link nije moguće učitati: {message}")

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
            item.message = "Već postoji" if result.already_existed else result.message
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
            self._set_status("Nema ništa za preuzimanje. Kopiraj link videa pa klikni „Zalijepi“.")
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
            self._set_status("Zaustavljam preuzimanje…")
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
            self._set_status("Fajl više ne postoji na disku.")
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
            self.download_button.setText("Zaustavi")
            self.download_button.setIcon(icon("stop"))
            self.download_button.setEnabled(True)
            set_state(self.download_button, "stop")
        else:
            self.download_button.setText("Preuzmi")
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
            parts.append("preuzimanje u toku")
        if waiting:
            parts.append(f"čeka: {waiting}")
        if done:
            parts.append(f"završeno: {done}")
        if failed:
            parts.append(f"neuspjelo: {failed}")
        self.summary_label.setText(" · ".join(parts))

    def _set_status(self, text: str) -> None:
        self.status_label.setText(text)

    # ---------- pomoć ----------

    @Slot()
    def _show_browser_help(self) -> None:
        QMessageBox.information(self, "Preuzimanje iz browsera", (
            "1. Otvori edge://extensions (ili chrome://extensions).\n"
            "2. Uključi „Developer mode“ i klikni „Load unpacked“.\n"
            f"3. Izaberi folder:\n   {PROJECT_ROOT / 'extension'}\n\n"
            "Na stranici pokreni video i klikni ikonu Video Download. "
            "Ako aplikacija nije pokrenuta, klik je sam pokreće.\n\n"
            "Video zaštićen DRM-om (Netflix, Disney+…) se ne može preuzeti."))

    @Slot()
    def _show_about(self) -> None:
        QMessageBox.about(self, "O programu", f"Video Download {__version__}\n\n"
                          "Lična aplikacija za preuzimanje videa i zvuka (yt-dlp, ffmpeg).")

    # ---------- zatvaranje ----------

    def closeEvent(self, event) -> None:
        if self._download_job is not None:
            answer = QMessageBox.question(
                self, "Preuzimanje u toku",
                "Preuzimanje je u toku. Prekinuti ga i zatvoriti program?")
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


def main() -> int:
    # Druga instanca samo podigne prozor prve (npr. dvoklik na pokreni.bat dok aplikacija radi).
    running = find_running_app()
    if running is not None:
        with contextlib.suppress(OSError):
            call_app(running, "POST", "/focus")
        return 0

    app = QApplication(sys.argv)
    app.setApplicationName("Video Download")
    app.setWindowIcon(QIcon(str(PROJECT_ROOT / "extension" / "icons" / "icon128.png")))
    apply_theme(app)
    window = MainWindow(settings=_settings())

    problems = []
    bridge = BridgeServer(window.browser_request.emit, window.focus_requested.emit)
    try:
        bridge.start()
    except OSError as exc:
        problems.append(f"veza sa browserom ne radi ({exc})")
    try:
        install_native_host()
    except OSError as exc:
        problems.append(f"registracija za browser nije uspjela ({exc})")
    if problems:
        window._set_status("Upozorenje: " + "; ".join(problems))

    window.show()
    try:
        return app.exec()
    finally:
        bridge.stop()
