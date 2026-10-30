"""Ažuriranje yt-dlp-a i samog programa. Dio prozora MainWindow (gui.py), izdvojen u Fazi 4 (29.10.2026) bez promjene ponašanja."""

import tempfile
import time
from pathlib import Path

from PySide6.QtCore import QUrl, Slot
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import QApplication, QMessageBox, QProgressDialog

from . import __version__, runtime, updater, ytdlp_update
from .i18n import get_language, tr
from .workers import update_error_text, UpdateCheckJob, UpdateDownloadJob, YtdlpUpdateJob


class UpdatesMixin:
    """Metode prozora MainWindow; koriste njegovo stanje (self._settings, self._queue…)."""

    def update_ytdlp(self, manual: bool, nightly: bool = False) -> None:
        """Novi yt-dlp radi od sljedećeg pokretanja; tekući uvoz se ne može zamijeniti u hodu.
        `nightly`: noćna verzija sa najnovijim popravkama (nudi se kad je redovna već najnovija)."""
        if self._ytdlp_job is not None:
            return
        self._ytdlp_nightly = nightly
        if not manual:
            last = self._settings.value("last_ytdlp_check", 0.0, type=float)
            if time.time() - last < ytdlp_update.CHECK_INTERVAL_SECONDS:
                return
        self._settings.setValue("last_ytdlp_check", time.time())
        if manual:
            self._set_status(tr("ytdlp.checking"))
        job = YtdlpUpdateJob(manual, fetch=ytdlp_update.fetch_nightly if nightly else None)
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
            if manual and getattr(self, "_ytdlp_nightly", False):
                QMessageBox.information(self, tr("menu.update_ytdlp"), tr("ytdlp.nightly_none"))
            elif manual:
                # Redovna je najnovija, a sajt možda i dalje ne radi: ponudi noćnu verziju (popravka dan-dva ranije).
                answer = QMessageBox.question(
                    self, tr("menu.update_ytdlp"),
                    tr("ytdlp.latest", version=ytdlp_update.active_version()) + "\n\n" + tr("ytdlp.nightly_offer"))
                if answer == QMessageBox.StandardButton.Yes:
                    self.update_ytdlp(manual=True, nightly=True)
            return
        text = tr("ytdlp.updated", version=version)
        self._set_status(text)
        if manual:
            QMessageBox.information(self, tr("menu.update_ytdlp"), text)

    def check_for_updates(self, manual: bool) -> None:
        if self._update_check_job is not None:
            return
        if runtime.is_store_package():
            # Microsoft Store sam ažurira svoj paket; naš instaler tu ne smije (ni ne može) ništa mijenjati.
            if manual:
                QMessageBox.information(self, tr("menu.check_updates"), tr("update.store", version=__version__))
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
        if not updater.can_self_install(release):
            # Mac bez potpisanog .dmg-a ili bez prava zamjene: .dmg se preuzima u browseru i prevuče u Applications.
            QDesktopServices.openUrl(QUrl(release.installer_url))
            QMessageBox.information(self, tr("update.available_title"), tr("update.open_download", new=release.version))
            return
        if self._busy_for_update():
            QMessageBox.information(self, tr("update.available_title"), tr("update.busy"))
            return
        self._install_update(release)

    def _busy_for_update(self) -> bool:
        """Instaler zatvara program: ne smije krenuti dok radi bilo koji posao (preuzimanje,
        pretvaranje u MP3, čitanje linka) ili dok red još čeka da se obradi."""
        return bool(self._download_jobs or self._convert_jobs or self._probe_jobs or self._running)

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
