"""Pozadinski poslovi glavnog prozora (čitanje linka, preuzimanje, sličice, ažuriranja, pretvaranje u MP3).

Svaki radi u svojoj niti i javlja rezultat Qt signalom; prozor (gui.py) samo pokreće i prikazuje.
Izdvojeno iz gui.py bez promjene ponašanja (3.10.2026); gui.py ih i dalje izvozi pod istim imenima.
"""

import queue
import threading
from pathlib import Path

from PySide6.QtCore import QObject, Signal
from PySide6.QtGui import QImage

from . import updater, ytdlp_update
from .download import DownloadResult, Progress
from .i18n import tr
from .jobs import ItemStatus, QueueItem
from .presets import get_preset
from .ytdl import error_message


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

    def is_alive(self) -> bool:
        return self._thread.is_alive()

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

    def is_alive(self) -> bool:
        return self._thread.is_alive()

    @property
    def cancelled(self) -> bool:
        return self._cancel.is_set()

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
