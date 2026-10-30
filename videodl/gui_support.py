"""Podrška, dostignuća, pomoć i dijalozi glavnog prozora. Dio prozora MainWindow (gui.py), izdvojen u Fazi 4 (29.10.2026) bez promjene ponašanja."""

import datetime
import time
from pathlib import Path

from PySide6.QtCore import QUrl, Slot
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import QApplication, QFileDialog, QMessageBox

from . import __version__, achievements, diagnostics, runtime, store, support, ytdlp_update
from .desktop import reveal
from .dialogs import (
    AchievementDialog, AchievementsListDialog, BrowserHelpDialog, HistoryDialog, LegalDialog, SupportDialog, WhatsNewDialog, milestone_line,
)
from .download import DownloadResult
from .gui_util import PARALLEL_CHOICES, RATE_CHOICES
from .i18n import get_language, tr
from .icons import icon
from .presets import get_preset, NAME_TEMPLATES
from .runtime import extension_dir
from .widgets import display_message


class SupportMixin:
    """Metode prozora MainWindow; koriste njegovo stanje (self._settings, self._queue…)."""

    def _maybe_remind_support(self) -> None:
        now = time.time()
        if self._support.should_show_banner(now):
            self.support_banner.show()
        busy = bool(self._download_jobs) or self._running or bool(self._probe_jobs)
        free = self._achievement_dialog is None and self._support_dialog is None
        milestone = self._support.milestone_due(busy)
        badges = self._achievements.take_pending() if free and not busy else []
        if free and (milestone or badges):
            # Čestitka ima prednost; podsjetnik za prilog čeka sljedeću priliku (ne dva prozora odjednom).
            if milestone:
                self._support.milestone_seen(milestone)
            self.show_achievement(milestone, badges, now)
        elif (free and self._support.should_show_dialog(now, busy)
              and now - self._achievements.last_support_note >= achievements.SUPPORT_NOTE_EVERY):
            # Isti dan kad je čestitka već pozvala na prilog nema i sedmičnog prozora (jedan poziv dnevno).
            self.show_support_dialog(automatic=True)
        self._save_settings()

    def show_achievement(self, milestone: int, badges: list, now: float) -> None:
        names = [(achievements.ICONS[key], tr(f"badge.{key}"), tr(f"badge.{key}.desc")) for key in badges]
        if milestone and not names:
            headline, lines = tr("achievement.headline", count=milestone), [milestone_line(milestone)]
        elif len(names) == 1 and not milestone:
            icon, name, desc = names[0]
            headline, lines = f"{icon} {name}", [desc]
        else:
            headline = tr("achievement.new_many")
            lines = ([f"🏆 {tr('achievements.count_name', count=milestone)}"] if milestone else []) + \
                [f"{icon} {name}: {desc}" for icon, name, desc in names]
        show_support = (not self._support.snoozed(now)
                        and now - self._support.last_dialog >= achievements.SUPPORT_NOTE_EVERY
                        and self._achievements.support_note_allowed(now))
        dialog = AchievementDialog(headline, lines, show_support=show_support, parent=self)
        dialog.support_clicked.connect(self._open_support)
        dialog.finished.connect(lambda _result: setattr(self, "_achievement_dialog", None))
        self._achievement_dialog = dialog
        dialog.open()

    def _record_achievements(self, item, result: DownloadResult) -> None:
        preset = get_preset(item.preset_key)
        self._achievements.record(achievements.Download(
            url=item.url, audio=preset.is_audio, car=item.preset_key in ("car", "mp3car"),
            clip=item.section is not None, height=result.height, size=self._sizes.get(item.id, 0),
            from_browser=item.from_browser, subtitles=self._subtitles, duration=item.duration,
            retried=item.auto_retries > 0, running_together=len(self._download_jobs) + 1))

    @Slot()
    def show_achievements_list(self) -> None:
        AchievementsListDialog(self._achievements, self._support.downloads, self._support.milestone_shown,
                               self).open()

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
    def show_settings(self) -> None:
        from .settings_dialog import SettingsDialog

        dialog = SettingsDialog(self, RATE_CHOICES, PARALLEL_CHOICES, NAME_TEMPLATES)
        self._settings_dialog = dialog  # testovi ga nađu; prozor je modalan
        dialog.exec()

    def _show_whats_new(self) -> None:
        WhatsNewDialog(self).exec()

    @Slot()
    def _show_history(self) -> None:
        dialog = HistoryDialog(store.history_path(self._data_dir), self)
        dialog.exec()

    @Slot()
    def _show_browser_help(self) -> None:
        try:
            folder = runtime.user_extension_dir()
        except OSError:
            folder = extension_dir()
        BrowserHelpDialog(str(folder), self).exec()

    def _note_error(self, message: str) -> None:
        if message:
            self._errors.append(f"{datetime.datetime.now():%H:%M:%S} {display_message(message, friendly=False)}")
            del self._errors[:-diagnostics.MAX_ERRORS]

    @Slot()
    def _send_feedback(self) -> None:
        """Poruka autoru preko programa za e-poštu; bez njega se adresa kopira."""
        url = diagnostics.feedback_url(tr("feedback.subject", version=__version__),
                                       tr("feedback.body", info=diagnostics.feedback_info()))
        if not QDesktopServices.openUrl(QUrl(url)):
            QApplication.clipboard().setText(diagnostics.CONTACT_EMAIL)
            self._set_status(tr("feedback.no_mail", email=diagnostics.CONTACT_EMAIL))

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
