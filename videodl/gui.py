"""Glavni prozor: unos linkova, izbor formata i foldera, red preuzimanja."""

import contextlib
import os
import shutil
import subprocess
import sys
import threading
from pathlib import Path

from PySide6.QtCore import QObject, QSettings, Qt, QUrl, Signal, Slot
from PySide6.QtGui import QColor, QDesktopServices, QIcon
from PySide6.QtWidgets import (
    QAbstractItemView, QApplication, QComboBox, QFileDialog, QGridLayout, QHBoxLayout, QHeaderView,
    QLabel, QLineEdit, QMainWindow, QMessageBox, QProgressBar, QPushButton, QTableWidget,
    QTableWidgetItem, QVBoxLayout, QWidget,
)

from . import __version__
from .bridge import BridgeServer
from .browser import BrowserRequest
from .download import PROCESSING, DownloadResult, Progress, download
from .native_host import call_app, data_dir, find_running_app
from .native_messaging import PROJECT_ROOT, install_native_host
from .jobs import DownloadQueue, ItemStatus, QueueItem
from .presets import DEFAULT_PRESET_KEY, PRESETS, get_preset, safe_folder_name
from .probe import ProbeResult, probe
from .ytdl import JS_RUNTIMES, error_message

COL_TITLE, COL_FORMAT, COL_STATUS, COL_PROGRESS = range(4)
PROGRESS_MAX = 1000

STATUS_TEXT = {
    ItemStatus.WAITING: "Čeka",
    ItemStatus.ACTIVE: "Pokreće se…",
    ItemStatus.DONE: "Završeno",
    ItemStatus.FAILED: "Greška",
    ItemStatus.CANCELLED: "Otkazano",
}
STATUS_COLOR = {
    ItemStatus.DONE: QColor("#2e7d32"),
    ItemStatus.FAILED: QColor("#c62828"),
}


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


def missing_tools() -> list[str]:
    missing = []
    if not shutil.which("ffmpeg"):
        missing.append("ffmpeg (bez njega nema spajanja videa i zvuka ni MP3/M4A)")
    if not any(shutil.which(name) for name in JS_RUNTIMES):
        missing.append("Node.js ili Deno (YouTube bez njih često ne radi)")
    return missing


class ProbeJob(QObject):
    """Čita linkove u pozadinskoj niti. Signali se u glavnoj niti isporučuju redom."""

    probed = Signal(object, str, str, object)  # ProbeResult, preset_key, output_dir, zaglavlja
    failed = Signal(str, str)  # link, poruka
    finished = Signal(int)  # id posla

    def __init__(self, job_id: int, urls: list[str], preset_key: str, output_dir: str, probe_fn,
                 http_headers: dict[str, str] | None = None):
        super().__init__()
        self.job_id = job_id
        self._urls = urls
        self._preset_key = preset_key
        self._output_dir = output_dir
        self._probe_fn = probe_fn
        self._http_headers = dict(http_headers or {})

    def start(self) -> None:
        # daemon: čitanje linka se ne može prekinuti, a ne smije držati program pri zatvaranju
        threading.Thread(target=self._run, daemon=True).start()

    def _run(self) -> None:
        for url in self._urls:
            try:
                result = self._probe_fn(url, http_headers=self._http_headers)
                self.probed.emit(result, self._preset_key, self._output_dir, self._http_headers)
            except Exception as exc:  # granica radne niti
                self.failed.emit(url, error_message(exc))
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


class MainWindow(QMainWindow):
    # Stižu iz niti lokalnog mosta; Qt ih isporučuje u glavnoj niti.
    browser_request = Signal(object)  # BrowserRequest
    focus_requested = Signal()

    def __init__(self, settings: QSettings | None = None, probe_fn=probe, download_fn=download):
        super().__init__()
        self.browser_request.connect(self._on_browser_request)
        self.focus_requested.connect(self._bring_to_front)
        self._settings = settings if settings is not None else QSettings("VideoDownload", "VideoDownload")
        self._probe_fn = probe_fn
        self._download_fn = download_fn
        self._queue = DownloadQueue()
        self._paused = False
        self._download_job: DownloadJob | None = None
        self._probe_jobs: dict[int, ProbeJob] = {}
        self._next_probe_id = 1

        self.setWindowTitle(f"Video Download {__version__}")
        self.resize(1000, 620)
        self._build_ui()
        self._load_settings()
        self._update_controls()

    # ---------- izgled ----------

    def _build_ui(self) -> None:
        central = QWidget()
        layout = QVBoxLayout(central)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)

        url_row = QHBoxLayout()
        self.url_edit = QLineEdit()
        self.url_edit.setPlaceholderText("Zalijepi link videa ili plejliste (može i više linkova odjednom)")
        self.url_edit.returnPressed.connect(self._add_urls)
        self.add_button = QPushButton("Dodaj")
        self.add_button.setDefault(True)
        self.add_button.clicked.connect(self._add_urls)
        url_row.addWidget(self.url_edit, 1)
        url_row.addWidget(self.add_button)
        layout.addLayout(url_row)

        options = QGridLayout()
        options.setColumnStretch(1, 1)
        options.addWidget(QLabel("Format:"), 0, 0)
        self.preset_combo = QComboBox()
        for preset in PRESETS:
            self.preset_combo.addItem(preset.label, preset.key)
        self.preset_combo.currentIndexChanged.connect(self._save_settings)
        format_row = QHBoxLayout()
        format_row.addWidget(self.preset_combo)
        format_row.addStretch(1)
        options.addLayout(format_row, 0, 1, 1, 3)
        options.addWidget(QLabel("Folder:"), 1, 0)
        self.folder_edit = QLineEdit()
        self.folder_edit.setReadOnly(True)
        options.addWidget(self.folder_edit, 1, 1)
        self.folder_button = QPushButton("Promijeni…")
        self.folder_button.clicked.connect(self._choose_folder)
        options.addWidget(self.folder_button, 1, 2)
        self.open_folder_button = QPushButton("Otvori folder")
        self.open_folder_button.clicked.connect(self._open_folder)
        options.addWidget(self.open_folder_button, 1, 3)
        layout.addLayout(options)

        self.warning_label = QLabel()
        self.warning_label.setWordWrap(True)
        self.warning_label.setStyleSheet("color: #c62828;")
        missing = missing_tools()
        self.warning_label.setText("Nije pronađeno: " + "; ".join(missing))
        self.warning_label.setVisible(bool(missing))
        layout.addWidget(self.warning_label)

        self.table = QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels(["Naziv", "Format", "Status", "Napredak"])
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(COL_TITLE, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(COL_FORMAT, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(COL_STATUS, QHeaderView.ResizeMode.Interactive)
        header.setSectionResizeMode(COL_PROGRESS, QHeaderView.ResizeMode.Fixed)
        self.table.setColumnWidth(COL_STATUS, 280)
        self.table.setColumnWidth(COL_PROGRESS, 140)
        self.table.verticalHeader().setVisible(False)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setWordWrap(False)
        self.table.itemSelectionChanged.connect(self._update_controls)
        self.table.cellDoubleClicked.connect(self._reveal_row)
        layout.addWidget(self.table, 1)

        buttons_row = QHBoxLayout()
        self.start_stop_button = QPushButton()
        self.start_stop_button.clicked.connect(self._toggle_running)
        self.retry_button = QPushButton("Ponovi")
        self.retry_button.clicked.connect(self._retry_selected)
        self.remove_button = QPushButton("Ukloni")
        self.remove_button.clicked.connect(self._remove_selected)
        self.clear_button = QPushButton("Očisti završene")
        self.clear_button.clicked.connect(self._clear_finished)
        for button in (self.start_stop_button, self.retry_button, self.remove_button, self.clear_button):
            buttons_row.addWidget(button)
        buttons_row.addSpacing(12)
        self.summary_label = QLabel()
        buttons_row.addWidget(self.summary_label, 1)
        layout.addLayout(buttons_row)

        self.status_label = QLabel()
        self.status_label.setWordWrap(True)
        layout.addWidget(self.status_label)

        self.setCentralWidget(central)

    # ---------- podešavanja ----------

    def _load_settings(self) -> None:
        output_dir = self._settings.value("output_dir", default_output_dir(), type=str)
        self.folder_edit.setText(output_dir or default_output_dir())
        preset_key = self._settings.value("preset_key", DEFAULT_PRESET_KEY, type=str)
        index = self.preset_combo.findData(preset_key)
        self.preset_combo.blockSignals(True)
        self.preset_combo.setCurrentIndex(max(index, 0))
        self.preset_combo.blockSignals(False)

    @Slot()
    def _save_settings(self) -> None:
        self._settings.setValue("output_dir", self.folder_edit.text())
        self._settings.setValue("preset_key", self.preset_combo.currentData())

    @Slot()
    def _choose_folder(self) -> None:
        folder = QFileDialog.getExistingDirectory(self, "Izaberi folder za preuzimanja",
                                                  self.folder_edit.text())
        if folder:
            self.folder_edit.setText(os.path.normpath(folder))
            self._save_settings()

    # ---------- dodavanje linkova ----------

    @Slot()
    def _add_urls(self) -> None:
        urls = self.url_edit.text().split()
        if not urls:
            return
        invalid = [url for url in urls if not url.lower().startswith(("http://", "https://"))]
        if invalid:
            self._set_status(f"Ovo nije link: {invalid[0]}")
            return
        self.url_edit.clear()
        self._start_probe(urls)

    def _start_probe(self, urls: list[str], http_headers: dict[str, str] | None = None) -> None:
        job = ProbeJob(self._next_probe_id, urls, self.preset_combo.currentData(),
                       self.folder_edit.text(), self._probe_fn, http_headers)
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
        if request.media_url is None:
            self._start_probe([request.page_url], request.headers)
            return
        # Direktan tok (MP4/HLS/DASH) nema šta da se čita unaprijed: odmah ide u red.
        item = self._queue.add(request.media_url, request.page_title, self.preset_combo.currentData(),
                               self.folder_edit.text(), http_headers=request.headers,
                               filename_title=request.page_title)
        self._append_row(item)
        self._set_status(f"Iz browsera: {request.page_title}")
        self._start_next()

    @Slot()
    def _bring_to_front(self) -> None:
        if self.isMinimized():
            self.showNormal()
        self.show()
        self.raise_()
        self.activateWindow()

    @Slot(object, str, str, object)
    def _on_probed(self, result: ProbeResult, preset_key: str, output_dir: str,
                   http_headers: dict[str, str]) -> None:
        if not result.entries:
            self._set_status(f"Plejlista „{result.title}“ nema dostupnih videa.")
            return
        subfolder = result.title if result.is_playlist else None
        for entry in result.entries:
            self._append_row(self._queue.add(entry.url, entry.title, preset_key, output_dir, subfolder,
                                             http_headers=http_headers))
        if result.is_playlist:
            self._set_status(f"Dodana plejlista „{result.title}“: {len(result.entries)} videa.")
        else:
            self._set_status(f"Dodano: {result.title}")
        self._start_next()

    @Slot(str, str)
    def _on_probe_failed(self, url: str, message: str) -> None:
        self._set_status(f"Link nije moguće učitati ({url}): {message}")

    @Slot(int)
    def _on_probe_finished(self, job_id: int) -> None:
        job = self._probe_jobs.pop(job_id, None)
        if job is not None:
            job.deleteLater()

    # ---------- red preuzimanja ----------

    def _start_next(self) -> None:
        if self._paused or self._download_job is not None:
            self._update_controls()
            return
        item = self._queue.next_waiting()
        if item is None:
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
        row = self._row_of(item_id)
        if item is None or item.status != ItemStatus.ACTIVE or row < 0:
            return
        self.table.item(row, COL_STATUS).setText(format_progress(progress))
        bar = self._bar(row)
        if progress.fraction is None:
            bar.setRange(0, 0)  # neodređeno trajanje (npr. ffmpeg obrada)
        else:
            bar.setRange(0, PROGRESS_MAX)
            bar.setValue(round(progress.fraction * PROGRESS_MAX))

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
            self._refresh_row(item)
        if self._paused:
            self._set_status("")
        self._start_next()

    @Slot()
    def _toggle_running(self) -> None:
        if self._paused:
            self._paused = False
            self._set_status("")
            self._start_next()
            return
        self._paused = True
        if self._download_job is not None:
            self._download_job.cancel()
            self._set_status("Zaustavljam preuzimanje…")
        self._update_controls()

    @Slot()
    def _retry_selected(self) -> None:
        for item_id in self._selected_ids():
            if self._queue.retry(item_id):
                self._refresh_row(self._queue.get(item_id))
        self._start_next()

    @Slot()
    def _remove_selected(self) -> None:
        for item_id in self._selected_ids():
            if self._queue.remove(item_id):
                self.table.removeRow(self._row_of(item_id))
        self._update_controls()

    @Slot()
    def _clear_finished(self) -> None:
        for item_id in self._queue.clear_finished():
            self.table.removeRow(self._row_of(item_id))
        self._update_controls()

    # ---------- tabela ----------

    def _append_row(self, item: QueueItem) -> None:
        row = self.table.rowCount()
        self.table.insertRow(row)
        title = QTableWidgetItem(item.title)
        title.setData(Qt.ItemDataRole.UserRole, item.id)
        title.setToolTip(item.url)
        self.table.setItem(row, COL_TITLE, title)
        self.table.setItem(row, COL_FORMAT, QTableWidgetItem(get_preset(item.preset_key).short_label))
        self.table.setItem(row, COL_STATUS, QTableWidgetItem())
        bar = QProgressBar()
        bar.setTextVisible(False)
        bar.setRange(0, PROGRESS_MAX)
        self.table.setCellWidget(row, COL_PROGRESS, bar)
        self._refresh_row(item)

    def _refresh_row(self, item: QueueItem) -> None:
        row = self._row_of(item.id)
        if row < 0:
            return
        status = self.table.item(row, COL_STATUS)
        if item.status == ItemStatus.FAILED:
            status.setText(f"Greška: {item.message}")
        elif item.status == ItemStatus.DONE and item.message:
            status.setText(item.message)
        else:
            status.setText(STATUS_TEXT[item.status])
        status.setToolTip(item.filepath or item.message)
        color = STATUS_COLOR.get(item.status)
        status.setData(Qt.ItemDataRole.ForegroundRole, color)

        bar = self._bar(row)
        if item.status == ItemStatus.ACTIVE:
            bar.setRange(0, 0)
        else:
            bar.setRange(0, PROGRESS_MAX)
            bar.setValue(PROGRESS_MAX if item.status == ItemStatus.DONE else 0)
        self._update_controls()

    def _row_of(self, item_id: int) -> int:
        for row in range(self.table.rowCount()):
            if self.table.item(row, COL_TITLE).data(Qt.ItemDataRole.UserRole) == item_id:
                return row
        return -1

    def _bar(self, row: int) -> QProgressBar:
        return self.table.cellWidget(row, COL_PROGRESS)

    def _selected_ids(self) -> list[int]:
        rows = sorted({index.row() for index in self.table.selectedIndexes()})
        return [self.table.item(row, COL_TITLE).data(Qt.ItemDataRole.UserRole) for row in rows]

    @Slot(int, int)
    def _reveal_row(self, row: int, _column: int) -> None:
        item = self._queue.get(self.table.item(row, COL_TITLE).data(Qt.ItemDataRole.UserRole))
        if item is not None:
            reveal(item.filepath or _item_folder(item))

    @Slot()
    def _open_folder(self) -> None:
        folder = self.folder_edit.text()
        os.makedirs(folder, exist_ok=True)
        reveal(folder)

    # ---------- stanje dugmadi ----------

    def _update_controls(self) -> None:
        items = self._queue.items()
        waiting = sum(item.status == ItemStatus.WAITING for item in items)
        done = sum(item.status == ItemStatus.DONE for item in items)
        failed = sum(item.status in (ItemStatus.FAILED, ItemStatus.CANCELLED) for item in items)
        active = self._download_job is not None

        if self._paused:
            self.start_stop_button.setText("Nastavi")
            self.start_stop_button.setEnabled(waiting > 0 and not active)
        else:
            self.start_stop_button.setText("Zaustavi")
            self.start_stop_button.setEnabled(active)

        selected = [self._queue.get(item_id) for item_id in self._selected_ids()]
        selected = [item for item in selected if item is not None]
        self.retry_button.setEnabled(any(
            item.status in (ItemStatus.FAILED, ItemStatus.CANCELLED) for item in selected))
        self.remove_button.setEnabled(any(item.status != ItemStatus.ACTIVE for item in selected))
        self.clear_button.setEnabled(done > 0)

        parts = []
        if active:
            parts.append("preuzimanje u toku")
        if waiting:
            parts.append(f"čeka: {waiting}")
        if done:
            parts.append(f"završeno: {done}")
        if failed:
            parts.append(f"neuspjelo/otkazano: {failed}")
        if self._paused and not active:
            parts.insert(0, "red je zaustavljen")
        self.summary_label.setText(" · ".join(parts))

    def _set_status(self, text: str) -> None:
        self.status_label.setText(text)

    # ---------- zatvaranje ----------

    def closeEvent(self, event) -> None:
        if self._download_job is not None:
            answer = QMessageBox.question(
                self, "Preuzimanje u toku",
                "Preuzimanje je u toku. Prekinuti ga i zatvoriti program?")
            if answer != QMessageBox.StandardButton.Yes:
                event.ignore()
                return
            self._paused = True
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
