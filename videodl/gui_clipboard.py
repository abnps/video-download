"""Hvatanje kopiranih linkova (bez krađe fokusa). Dio prozora MainWindow (gui.py), izdvojen u Fazi 4 (29.10.2026) bez promjene ponašanja."""

import contextlib

from PySide6.QtCore import Slot
from PySide6.QtWidgets import QApplication

from .gui_util import extract_urls
from .i18n import tr
from .ytdl import is_obviously_not_media


class ClipboardMixin:
    """Metode prozora MainWindow; koriste njegovo stanje (self._settings, self._queue…)."""

    def set_watch_clipboard(self, enabled: bool, save: bool = True) -> None:
        """Kopiran link (Ctrl+C u browseru) sam ulazi u red; preuzimanje i dalje kreće na „Preuzmi"."""
        self._watch_clipboard = bool(enabled)
        self.watch_clipboard_action.setChecked(self._watch_clipboard)
        if hasattr(self, "watch_clipboard_box"):
            self.watch_clipboard_box.setChecked(self._watch_clipboard)
        clipboard = QApplication.clipboard()
        if self._watch_clipboard:
            self._last_clipboard = clipboard.text()
            if not getattr(self, "_clipboard_hooked", False):
                # Jedna veza (oznaka umjesto UniqueConnection: metoda mixina nije registrovan Qt slot).
                clipboard.dataChanged.connect(self._on_clipboard_change)
            self._clipboard_hooked = True
        else:
            self._unhook_clipboard()
        if save:
            self._save_settings()

    def _unhook_clipboard(self) -> None:
        """Odvezuje samo ako je vezano: PySide inače ispiše upozorenje (isključeno hvatanje pri pokretanju)."""
        if getattr(self, "_clipboard_hooked", False):
            with contextlib.suppress(RuntimeError):
                QApplication.clipboard().dataChanged.disconnect(self._on_clipboard_change)
            self._clipboard_hooked = False

    def _close_clipboard_notice(self, keep: bool) -> None:
        self._settings.setValue("clipboard_notice_seen", True)
        self.clipboard_notice.hide()
        if not keep:
            self.set_watch_clipboard(False)

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
