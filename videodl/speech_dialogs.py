"""Prozori za titl iz govora (Ahmed 14.11.2026): preuzimanje modela s trakom napretka i pregled titla prije
upisa u sliku. Posao (preuzimanje, upis) radi u svojoj niti; prozor samo prikazuje napredak i nudi „Otkaži".

Svuda piše da titl pravi računar i da može imati grešaka (Ahmed: „Dodaj opise da model može da pravi greške").
"""

import os
import threading
from collections.abc import Callable

from PySide6.QtCore import QObject, Qt, Signal
from PySide6.QtWidgets import (
    QAbstractItemView, QDialog, QHBoxLayout, QHeaderView, QLabel, QMessageBox, QPushButton, QTableWidget,
    QTableWidgetItem, QVBoxLayout, QWidget,
)

from . import speech
from .gui_util import format_eta, format_speed
from .i18n import tr
from .widgets import AnimatedProgress, format_size


class _Relay(QObject):
    """Javljanja iz radne niti stižu u glavnu nit preko signala (Qt elementi se diraju samo iz glavne niti)."""

    progress = Signal(object)  # (preuzeto, ukupno, brzina) ili udio 0..1 ili None
    finished = Signal(object)  # None = uspjeh, inače izuzetak


class TaskDialog(QDialog):
    """Mali prozor s trakom napretka za posao koji traje: `work(on_progress, cancel)` radi u svojoj niti."""

    def __init__(self, parent: QWidget | None, title: str, text: str,
                 work: Callable[[Callable[[object], None], threading.Event], None]):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setModal(True)
        self.setMinimumWidth(460)
        self.error: BaseException | None = None
        self.cancelled = False
        self._cancel = threading.Event()
        layout = QVBoxLayout(self)
        label = QLabel(text)
        label.setWordWrap(True)
        layout.addWidget(label)
        self.bar = AnimatedProgress(self, bar=8)
        self.bar.set_fraction(None, "work")
        layout.addWidget(self.bar)
        self.detail = QLabel("")
        self.detail.setObjectName("mutedLabel")
        layout.addWidget(self.detail)
        buttons = QHBoxLayout()
        buttons.addStretch(1)
        self.cancel_button = QPushButton(tr("speech.cancel"))
        self.cancel_button.clicked.connect(self._ask_cancel)
        buttons.addWidget(self.cancel_button)
        layout.addLayout(buttons)
        self._relay = _Relay()
        self._relay.progress.connect(self._show_progress)
        self._relay.finished.connect(self._finish)
        self._work = work
        self._started = False

    def exec(self) -> int:
        if not self._started:
            self._started = True
            threading.Thread(target=self._run, daemon=True).start()
        return super().exec()

    def _run(self) -> None:
        try:
            self._work(self._relay.progress.emit, self._cancel)
        except BaseException as exc:  # granica niti: greška ide prozoru
            self._relay.finished.emit(exc)
            return
        self._relay.finished.emit(None)

    def _show_progress(self, value) -> None:
        if isinstance(value, tuple):
            done, total, speed = value
            self.bar.set_fraction(done / total if total else None, "video")
            parts = [tr("speech.download.amount", done=format_size(done), total=format_size(total))]
            if speed:
                parts.append(format_speed(speed))
                parts.append(tr("progress.eta", time=format_eta(int((total - done) / speed))))
            self.detail.setText(" · ".join(parts))
        else:
            self.bar.set_fraction(value, "work")
            self.detail.setText(f"{value:.0%}" if value is not None else "")

    def _ask_cancel(self) -> None:
        self.cancel_button.setEnabled(False)
        self.detail.setText(tr("speech.cancelling"))
        self._cancel.set()

    def reject(self) -> None:  # Esc ili ✕: isto kao „Otkaži" (posao se prekine, prozor čeka da nit stane)
        if self._started and not self._cancel.is_set():
            self._ask_cancel()

    def _finish(self, error) -> None:
        self.cancelled = isinstance(error, speech.SpeechCancelled) or (error is not None and self._cancel.is_set())
        self.error = None if self.cancelled else error
        self.done(QDialog.DialogCode.Accepted if error is None else QDialog.DialogCode.Rejected)


def ensure_model(parent: QWidget | None) -> bool:
    """Pita za preuzimanje modela (veličina + upozorenje da titl može imati grešaka) i preuzme ga uz traku.
    True = model je spreman."""
    if speech.model_ready():
        return True
    left = speech.remaining_bytes()
    box = QMessageBox(parent)
    box.setIcon(QMessageBox.Icon.Question)
    box.setWindowTitle(tr("speech.download.title"))
    box.setText(tr("speech.download.question", size=format_size(left)))
    download = box.addButton(tr("speech.download.yes"), QMessageBox.ButtonRole.AcceptRole)
    box.addButton(tr("speech.cancel"), QMessageBox.ButtonRole.RejectRole)
    box.setDefaultButton(download)
    box.exec()
    if box.clickedButton() is not download:
        return False

    def work(report, cancel):
        speech.download_model(lambda done, total, speed: report((done, total, speed)), cancel)

    dialog = TaskDialog(parent, tr("speech.download.title"), tr("speech.download.progress"), work)
    dialog.exec()
    if dialog.error is not None:
        key = getattr(dialog.error, "key", None)
        QMessageBox.warning(parent, tr("speech.download.title"),
                            tr("speech.download.failed", error=tr(key) if key else str(dialog.error)))
    return speech.model_ready()


def offer_model_removal(parent: QWidget | None) -> None:
    """Titl iz govora je isključen: model (1,5 GB) može ostati za sljedeći put ili se obrisati."""
    if not speech.model_dir().is_dir():
        return
    stored = speech.MODEL_BYTES - speech.remaining_bytes()
    if stored <= 0:
        speech.delete_model()  # prazan folder: nema šta da se pita
        return
    box = QMessageBox(parent)
    box.setIcon(QMessageBox.Icon.Question)
    box.setWindowTitle(tr("speech.download.title"))
    box.setText(tr("speech.delete.question", size=format_size(stored)))
    keep = box.addButton(tr("speech.delete.keep"), QMessageBox.ButtonRole.RejectRole)
    remove = box.addButton(tr("speech.delete.yes"), QMessageBox.ButtonRole.DestructiveRole)
    box.setDefaultButton(keep)
    box.exec()
    if box.clickedButton() is remove:
        speech.delete_model()


class ReviewDialog(QDialog):
    """Titl iz govora prije upisa u sliku: korisnik vidi redove (vrijeme + tekst) i ispravi pogrešne riječi."""

    def __init__(self, parent: QWidget | None, video: str, subtitle: str):
        super().__init__(parent)
        self.subtitle = subtitle
        self.setWindowTitle(tr("speech.review.title"))
        self.resize(720, 560)
        layout = QVBoxLayout(self)
        name = QLabel(os.path.basename(video))
        name.setObjectName("dialogTitle")
        name.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        layout.addWidget(name)
        warning = QLabel(tr("speech.review.warning"))
        warning.setWordWrap(True)
        layout.addWidget(warning)
        self.lines = speech.read_srt(subtitle)
        self.table = QTableWidget(len(self.lines), 2, self)
        self.table.setHorizontalHeaderLabels([tr("speech.review.time"), tr("speech.review.text")])
        self.table.verticalHeader().setVisible(False)
        self.table.setWordWrap(True)
        # Visina reda prati širinu kolone (dugi redovi se prelome), i kad se prozor poveća
        self.table.verticalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.DoubleClicked
                                   | QAbstractItemView.EditTrigger.EditKeyPressed
                                   | QAbstractItemView.EditTrigger.AnyKeyPressed)
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        for row, line in enumerate(self.lines):
            stamp = QTableWidgetItem(speech.format_time(line.start).split(",")[0])
            stamp.setFlags(stamp.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.table.setItem(row, 0, stamp)
            self.table.setItem(row, 1, QTableWidgetItem(line.text))
        layout.addWidget(self.table, 1)
        buttons = QHBoxLayout()
        buttons.addStretch(1)
        keep = QPushButton(tr("speech.review.keep"))
        keep.clicked.connect(self.reject)
        buttons.addWidget(keep)
        burn = QPushButton(tr("speech.review.burn"))
        burn.setDefault(True)
        burn.clicked.connect(self._save_and_accept)
        buttons.addWidget(burn)
        layout.addLayout(buttons)

    def edited_lines(self) -> list[speech.Line]:
        result = []
        for row, line in enumerate(self.lines):
            item = self.table.item(row, 1)
            result.append(speech.Line(line.start, line.end, (item.text() if item else line.text).strip()))
        return result

    def save(self) -> None:
        speech.write_srt(self.edited_lines(), self.subtitle)

    def _save_and_accept(self) -> None:
        self.save()
        self.accept()

    def reject(self) -> None:
        self.save()  # i „Ostavi pored videa" čuva ispravke u fajlu titla
        super().reject()


def review_and_burn(parent: QWidget | None, video: str, subtitle: str, duration: float | None = None) -> str:
    """Pregled titla iz govora, pa upis u sliku. Vraća „burned", „kept" (titl ostaje pored videa) ili „failed"."""
    from .burn import burn_subtitles, can_burn

    if not (os.path.isfile(subtitle) and can_burn(video)):
        return "kept"
    review = ReviewDialog(parent, video, subtitle)
    if review.exec() != QDialog.DialogCode.Accepted:
        return "kept"

    def work(report, cancel):
        burn_subtitles(video, subtitle, report, cancel, duration)

    dialog = TaskDialog(parent, tr("speech.review.title"), tr("pp.burn"), work)
    dialog.exec()
    if dialog.cancelled:
        return "kept"
    if dialog.error is not None:
        return "failed"
    try:
        os.remove(subtitle)  # titl je sada u slici; fajl pored videa bi bio dupli
    except OSError:
        pass
    return "burned"
