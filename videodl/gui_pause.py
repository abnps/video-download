"""Zaštita od blokade, kartica pauze, nastavak reda, poruka 50/50 i mjesečni pregled (Ahmed 2.11.2026).

Dio prozora MainWindow (gui.py). Pravila su bez Qt-a: razmaci i blokade u pacing.py, red o podršci u support.py,
pregled u recap.py; ovdje se samo prikazuje i povezuje s redom preuzimanja.
"""

import dataclasses
import time
from datetime import date

from PySide6.QtCore import QTimer, Slot
from PySide6.QtGui import QFont
from PySide6.QtWidgets import QFrame, QMessageBox, QHBoxLayout, QLabel, QPushButton, QVBoxLayout

from . import pacing, recap
from .i18n import MESSAGE_PAUSE, tr
from .jobs import ItemStatus
from .widgets import format_size

SUCCESS_MIN = 50  # poruka „Gotovo: 50/50" za grupu od bar toliko preuzimanja bez ijedne greške
TIPS = tuple(f"tip.{number}" for number in range(1, 9))


def clock_text(seconds: float) -> str:
    seconds = max(0, int(seconds + 0.999))
    return f"{seconds // 60}:{seconds % 60:02d}"


class PauseMixin:
    """Metode prozora MainWindow; koriste njegovo stanje (self._queue, self._support, self._settings…)."""

    def _init_pause_state(self) -> None:
        self._pacer = pacing.Pacer()
        self._recap = recap.RecapState()
        self._recap_enabled = True
        self._card_mode = ""  # "", "pause", "resume", "success"
        self._card_pause: pacing.Pause | None = None
        self._card_patient = True  # pauza odbrojana do kraja (dostignuće „Strpljivi")
        self._tip_index = 0
        self._pace_announced: dict[str, float] = {}  # porodica -> rok pauze za koju je poruka već prikazana
        self._recap_dialog = None
        self._pace_timer = QTimer(self)
        self._pace_timer.setSingleShot(True)
        self._pace_timer.timeout.connect(self._start_next)
        self._card_timer = QTimer(self)
        self._card_timer.setInterval(1000)
        self._card_timer.timeout.connect(self._tick_pause)

    # ---------- kartica ----------

    def _build_pause_card(self, layout) -> None:
        """Kartica iznad liste: pauza (odbrojavanje), nastavak reda iz prošlog puta ili „Gotovo: 50/50"."""
        self.pause_card = QFrame()
        self.pause_card.setObjectName("supportBanner")
        box = QVBoxLayout(self.pause_card)
        box.setContentsMargins(14, 10, 10, 10)
        box.setSpacing(4)
        self.pause_title = QLabel()
        self.pause_title.setWordWrap(True)
        font = QFont(self.pause_title.font())
        font.setBold(True)
        self.pause_title.setFont(font)
        box.addWidget(self.pause_title)
        self.pause_text = QLabel()
        self.pause_text.setWordWrap(True)
        box.addWidget(self.pause_text)
        self.pause_tip = QLabel()
        self.pause_tip.setWordWrap(True)
        self.pause_tip.setObjectName("supportNote")
        box.addWidget(self.pause_tip)
        self.pause_support = QLabel()
        self.pause_support.setWordWrap(True)
        box.addWidget(self.pause_support)
        buttons = QHBoxLayout()
        buttons.addStretch(1)
        self.pause_support_button = QPushButton()
        self.pause_support_button.setObjectName("supportButton")
        self.pause_support_button.clicked.connect(self._open_support)
        buttons.addWidget(self.pause_support_button)
        self.pause_secondary = QPushButton()
        self.pause_secondary.clicked.connect(self._card_secondary)
        buttons.addWidget(self.pause_secondary)
        self.pause_primary = QPushButton()
        self.pause_primary.setDefault(False)
        self.pause_primary.clicked.connect(self._card_primary)
        buttons.addWidget(self.pause_primary)
        box.addLayout(buttons)
        self.pause_card.hide()
        layout.addWidget(self.pause_card)

    def _site_name(self, family: str | None) -> str:
        return pacing.NAMES.get(family or "", family or "")

    def _support_line(self, mode: str) -> str:
        """Red o podršci po pravilima (support.note_allowed); "" = bez reda. Poziv se računa kad se prikaže."""
        now = time.time()
        if self._support.snoozed(now):
            return tr("pause.thanks")
        if not self._support.note_allowed(now):
            return ""
        self._support.note_shown(now)
        self._save_settings()
        count, size = self._recap.today(date.today())
        if mode == "pause" and count:
            return tr("pause.support_today", count=count, size=format_size(size))
        return tr("pause.support_plain")

    def _show_card(self, mode: str, title: str, text: str = "", tip: str = "", support_line: str = "",
                   primary: str = "", secondary: str = "") -> None:
        self._card_mode = mode
        self.pause_title.setText(title)
        for label, value in ((self.pause_text, text), (self.pause_tip, tip), (self.pause_support, support_line)):
            label.setText(value)
            label.setVisible(bool(value))
        offer = bool(support_line) and not self._support.snoozed(time.time())
        self.pause_support_button.setText(tr("support.button"))
        self.pause_support_button.setVisible(offer)
        self.pause_primary.setText(primary)
        self.pause_primary.setVisible(bool(primary))
        self.pause_secondary.setText(secondary)
        self.pause_secondary.setVisible(bool(secondary))
        self.pause_card.show()

    def _hide_card(self) -> None:
        self._card_mode = ""
        self._card_pause = None
        self._card_timer.stop()
        self.pause_card.hide()

    @Slot()
    def _card_primary(self) -> None:
        mode = self._card_mode
        if mode == "pause":
            self._continue_now()
        elif mode == "resume":
            self._hide_card()
            self._start_all()
        else:
            self._hide_card()

    @Slot()
    def _card_secondary(self) -> None:
        if self._card_mode == "pause":
            self._continue_later()
        else:
            self._hide_card()

    # ---------- raspored ----------

    def _family_running(self, family: str) -> int:
        items = (self._queue.get(item_id) for item_id in self._download_jobs)
        return sum(1 for item in items if item is not None and pacing.family_of(item.url) == family)

    def _pace_held(self, item) -> bool:
        """Stavka sa strogog sajta čeka razmak/pauzu ili je dosta istovremenih s tog sajta (scheduler.pick_next)."""
        family = pacing.family_of(item.url)
        if family is None:
            return False
        if self._pacer.remaining(family) > 0:
            return True
        cap = self._pacer.parallel_cap(family)
        return cap is not None and self._family_running(family) >= cap

    def _waiting_families(self) -> set:
        """Porodice sajtova čije stavke čekaju da krenu (uz „Preuzmi" ili ručno pokrenute)."""
        manual = set(self._manual)
        return {pacing.family_of(item.url) for item in self._queue.items()
                if item.status == ItemStatus.WAITING and (self._running or item.id in manual)} - {None}

    def _pace_waiting(self) -> bool:
        """Ima stavki koje čekaju samo pauzu: red ne smije stati (kreće kad pauza prođe)."""
        return any(self._pacer.remaining(family) > 0 for family in self._waiting_families())

    def _schedule_pace(self) -> None:
        waits = {family: self._pacer.remaining(family) for family in self._waiting_families()}
        waits = {family: wait for family, wait in waits.items() if wait > 0}
        if not waits:
            self._pace_timer.stop()
            return
        self._pace_timer.start(int(min(waits.values()) * 1000) + 50)
        for family in sorted(waits, key=waits.get, reverse=True):  # duža pauza prva: ona ide na karticu
            self._announce_pace(family)

    def _announce_pace(self, family: str) -> None:
        """Poruka o pauzi, jednom po pauzi: razmak u statusnoj traci, predah i blokada na kartici. Zove se kad
        god nešto s tog sajta čeka, pa i kad je pauza zadata dok ništa nije čekalo, a link stigne tek poslije
        (ranije je takva stavka čekala i do minut bez ikakve poruke; pregled 9.11.2026)."""
        if self._pace_announced.get(family) == self._pacer.deadline(family):
            return
        pause = self._pacer.pending(family)
        if pause is None:
            return
        remaining = self._pacer.remaining(family)
        if pause.card:
            self._show_pause(dataclasses.replace(pause, seconds=remaining))  # sam bilježi da je prikazana
            return
        seconds = pause.seconds if pause.seconds - remaining < 1 else remaining
        self._set_status(tr("pace.gap", seconds=f"{seconds:.0f}", site=self._site_name(family)))
        self._pace_announced[family] = self._pacer.deadline(family)

    def _note_paced_start(self, item) -> None:
        self._pacer.started(pacing.family_of(item.url))

    def _note_paced_finish(self, item) -> None:
        """Poslije preuzimanja sa strogog sajta: razmak ili predah prije sljedećeg. Poruku daje _schedule_pace
        (iz _start_next, odmah poslije), i to samo dok nešto s tog sajta čeka."""
        self._pacer.finished(pacing.family_of(item.url))

    def _pause_on_block(self, item, result) -> bool:
        """Sajt je blokirao (429, „nisi bot"): stavka čeka 5/10/15 min i sama nastavlja umjesto da padne."""
        family = pacing.family_of(item.url)
        if family is None or result.status != ItemStatus.FAILED or not pacing.is_block_error(result.message or ""):
            return False
        if item.id in self._remove_when_done:
            return False
        pause = self._pacer.blocked(family, item.block_waits + 1)
        self._settings.setValue("pacing/learned_until", self._pacer.learned_until)
        if pause is None:
            return False  # treći put zaredom: obična greška s razumljivom porukom
        item.block_waits += 1
        item.status = ItemStatus.WAITING
        item.message = MESSAGE_PAUSE
        if not self._running and item.id not in self._manual:
            self._manual.append(item.id)  # pojedinačno pokrenuta stavka nastavlja i bez „Preuzmi sve"
        self._refresh_row(item)
        self._show_pause(pause)
        self._save_queue()
        self._start_next()
        return True

    def _pause_on_probe_block(self, url: str, message: str, output_dir: str, access: dict,
                              preset: str | None = None) -> bool:
        """Sajt je blokirao već ČITANJE linka (npr. YouTube: „potvrdi da nisi robot"): umjesto crvenog reda link
        čeka 5 min i preuzima se sam, kao kad blokada stigne usred preuzimanja (Ahmed 13.11.2026, prijava
        prijatelja). Ako sajt blokira i tada, slijede 10 pa 15 min (_pause_on_block), pa obična greška."""
        family = pacing.family_of(url)
        if family is None or not pacing.is_block_error(message or ""):
            return False
        pause = self._pacer.blocked(family, 1)
        self._settings.setValue("pacing/learned_until", self._pacer.learned_until)
        if pause is None:
            return False
        item = self._queue.add(url, url, preset or self.preset_combo.currentData(), output_dir, **access)
        item.custom_format = bool(preset)
        item.block_waits = 1
        item.status = ItemStatus.WAITING
        item.message = MESSAGE_PAUSE
        if item.id not in self._manual:
            self._manual.append(item.id)  # poslije pauze kreće sam (kartica kaže „nastavljam za …")
        self._append_row(item)
        self._refresh_row(item)
        self._show_pause(pause)
        self._save_queue()
        self._start_next()
        return True

    # ---------- pauza ----------

    def _show_pause(self, pause: pacing.Pause) -> None:
        current = self._card_pause
        if self._card_mode == "pause" and current is not None and current.family != pause.family \
                and self._pacer.remaining(current.family) >= pause.seconds:
            return  # duža pauza drugog sajta već je na kartici
        self._pace_announced[pause.family] = self._pacer.deadline(pause.family)
        self._card_pause = pause
        self._card_patient = True
        tip = tr("pause.tip", tip=tr(TIPS[self._tip_index % len(TIPS)]))
        self._tip_index += 1
        self._settings.setValue("pause/tip", self._tip_index % len(TIPS))
        site = self._site_name(pause.family)
        text = tr("pause.block_text" if pause.kind == "block" else "pause.break_text", site=site)
        self._show_card("pause", "", text, tip, self._support_line("pause"), tr("pause.now"), tr("pause.later"))
        self._update_pause_title()
        self._card_timer.start()

    def _update_pause_title(self) -> None:
        pause = self._card_pause
        if pause is None:
            return
        key = "pause.block_title" if pause.kind == "block" else "pause.break_title"
        self.pause_title.setText(tr(key, site=self._site_name(pause.family),
                                    time=clock_text(self._pacer.remaining(pause.family))))

    @Slot()
    def _tick_pause(self) -> None:
        pause = self._card_pause
        if self._card_mode != "pause" or pause is None:
            self._card_timer.stop()
            return
        if self._pacer.remaining(pause.family) > 0:
            self._update_pause_title()
            return
        # Pauza je odbrojala do kraja: nastavlja se samo.
        patient = self._card_patient
        family = pause.family
        self._hide_card()
        if patient:
            self._achievements.earn("patient")
            self._save_settings()
        if family in self._waiting_families():
            if not (self.isActiveWindow() and not self.isMinimized()):
                self._notifier(tr("pause.resumed_title"), tr("pause.resumed_body", site=self._site_name(family)))
            self._start_next()
        self._maybe_remind_support()

    def _continue_now(self) -> None:
        pause = self._card_pause
        self._card_patient = False
        self._hide_card()
        if pause is not None:
            self._pacer.skip(pause.family)
            self._pace_announced.pop(pause.family, None)
        self._start_next()

    def _continue_later(self) -> None:
        """Ostatak ostaje u redu (i pri sljedećem pokretanju); ono što već radi završava normalno."""
        pause = self._card_pause
        self._card_patient = False
        self._hide_card()
        family = pause.family if pause else None
        if family is not None:
            self._pacer.skip(family)
            self._pace_announced.pop(family, None)
        self._running = False
        self._manual = [item_id for item_id in self._manual
                        if (item := self._queue.get(item_id)) is None or pacing.family_of(item.url) != family]
        waiting = 0
        for item in self._queue.items():
            if item.status == ItemStatus.WAITING:
                waiting += 1
                if item.message == MESSAGE_PAUSE:
                    item.message = ""
                    self._refresh_row(item)
        self._pace_timer.stop()
        self._save_queue()
        self._update_controls()
        self._set_status(tr("pause.later_status", count=waiting))
        self._check_batch_done()

    def _stop_pauses(self) -> None:
        """„Zaustavi": čekanje prestaje (stavke ostaju u redu kao i do sada)."""
        self._pacer.skip()
        self._pace_announced.clear()
        self._pace_timer.stop()
        if self._card_mode == "pause":
            self._card_patient = False
            self._hide_card()
        for item in self._queue.items():
            if item.status == ItemStatus.WAITING and item.message == MESSAGE_PAUSE:
                item.message = ""
                self._refresh_row(item)

    # ---------- nastavak reda, 50/50 ----------

    def _show_resume_card(self, count: int) -> None:
        self._show_card("resume", tr("resume.text", count=count), primary=tr("resume.start"),
                        secondary=tr("support.later"))

    def _show_success(self, done: int, total: int, size: int) -> None:
        if self._card_mode == "pause":
            return
        self._show_card("success", tr("success.title", done=done, total=total, size=format_size(size)),
                        tr("success.text"), support_line=self._support_line("success"),
                        primary=tr("card.close"))

    def _note_batch_success(self, done: list, items: list) -> None:
        if len(done) >= SUCCESS_MIN and len(done) == len(items):
            self._show_success(len(done), len(items), sum(self._sizes.get(item.id, 0) for item in done))

    # ---------- mjesečni pregled ----------

    def _record_recap(self, item) -> None:
        self._recap.record(item.url, self._sizes.get(item.id, 0), item.duration)

    def _maybe_show_recap(self, today: date | None = None) -> None:
        if not self._recap_enabled:
            return
        summary = self._recap.due(today or date.today())
        if summary is None:
            return
        self._recap.shown(summary.period)
        self._save_settings()
        from .recap_dialog import RecapDialog

        dialog = RecapDialog(summary, self._support_line("recap"), not self._support.snoozed(time.time()), self)
        dialog.support_clicked.connect(self._open_support)
        self._recap_dialog = dialog  # testovi ga nađu
        dialog.open()

    def set_pacing(self, enabled: bool) -> None:
        self._pacer.enabled = bool(enabled)
        self._settings.setValue("pacing/enabled", self._pacer.enabled)
        if not self._pacer.enabled:
            # Isključena zaštita: razmaci i predasi prestaju odmah (čekanje poslije stvarne blokade ostaje),
            # a kartica predaha nestaje bez dostignuća „Strpljivi" (pregled 9.11.2026).
            self._pacer.drop_soft()
            pause = self._card_pause
            if self._card_mode == "pause" and pause is not None and self._pacer.remaining(pause.family) <= 0:
                self._card_patient = False
                self._hide_card()
        if self._running or self._manual:
            self._start_next()
        self._update_controls()  # statusna traka odmah pokazuje novo stanje zaštite

    def confirm_pacing_off(self) -> bool:
        """Upozorenje prije isključivanja zaštite (testovi ga zamjenjuju odgovorom bez prozora)."""
        box = QMessageBox(QMessageBox.Icon.Warning, tr("settings.pacing_off_title"), tr("settings.pacing_off_text"),
                          parent=self)
        off = box.addButton(tr("settings.pacing_off_yes"), QMessageBox.ButtonRole.DestructiveRole)
        keep = box.addButton(tr("settings.pacing_off_no"), QMessageBox.ButtonRole.RejectRole)
        box.setDefaultButton(keep)
        box.exec()
        return box.clickedButton() is off

    def set_recap_enabled(self, enabled: bool) -> None:
        self._recap_enabled = bool(enabled)
        self._settings.setValue("recap/enabled", self._recap_enabled)

    def _load_pause_settings(self) -> None:
        self._pacer.enabled = self._settings.value("pacing/enabled", True, type=bool)
        self._pacer.learned_until = self._settings.value("pacing/learned_until", 0.0, type=float)
        self._recap_enabled = self._settings.value("recap/enabled", True, type=bool)
        self._recap = recap.RecapState.from_json(self._settings.value("recap/state", "", type=str))
        self._tip_index = self._settings.value("pause/tip", 0, type=int)

    def _save_pause_settings(self) -> None:
        self._settings.setValue("recap/state", self._recap.to_json())
