"""Kartica pauze u prozoru (Ahmed 2.11.2026): blokada, predah, „Nastavi odmah/kasnije", nastavak reda,
„Gotovo: 50/50", red o podršci, Postavke i mjesečni pregled."""

import os
import random
import tempfile
import time
import unittest
from datetime import date, datetime, timedelta
from pathlib import Path
from unittest import mock

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QSettings  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

from videodl import pacing  # noqa: E402
from videodl.download import DownloadResult  # noqa: E402
from videodl.gui import MainWindow  # noqa: E402
from videodl.i18n import MESSAGE_PAUSE, set_language  # noqa: E402
from videodl.jobs import ItemStatus  # noqa: E402
from videodl.probe import Entry, ProbeResult  # noqa: E402

app = QApplication.instance() or QApplication([])
DAY = 24 * 60 * 60


def wait_until(condition, timeout=30.0):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        app.processEvents()
        if condition():
            return True
        time.sleep(0.01)
    app.processEvents()
    return condition()


class Clock:
    def __init__(self):
        self.now = 10_000.0

    def __call__(self):
        return self.now


def yt(number):
    return f"https://www.youtube.com/watch?v=video{number:03d}"


class PauseWindowTest(unittest.TestCase):
    def setUp(self):
        set_language("bs")
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.settings = QSettings(os.path.join(self.tmp.name, "s.ini"), QSettings.Format.IniFormat)
        self.settings.setValue("language", "bs")
        self.settings.setValue("parallel", 1)
        patcher = mock.patch("videodl.achievements.AchievementState.take_pending", return_value=[])
        patcher.start()
        self.addCleanup(patcher.stop)
        self.failures = {}  # url -> koliko puta još vratiti blokadu
        self.calls = []

    def window(self):
        counter = iter(range(10_000))

        def probe(url, http_headers=None, **options):
            self.probe_options = options
            return ProbeResult("V", (Entry(url, "V", None, 60),), False)

        def download(url, preset, output_dir, subfolder, on_progress, cancel_event, **extra):
            self.calls.append(url)
            if self.failures.get(url, 0) > 0:
                self.failures[url] -= 1
                return DownloadResult(ItemStatus.FAILED, message="ERROR: HTTP Error 429: Too Many Requests")
            path = Path(output_dir) / f"{next(counter)}.mp4"
            path.write_bytes(b"x" * 100)
            return DownloadResult(ItemStatus.DONE, filepath=str(path))

        window = MainWindow(settings=self.settings, probe_fn=probe, download_fn=download,
                            thumbnail_fetch=lambda u: None, data_dir_path=self.tmp.name)
        self.addCleanup(window.deleteLater)
        window.set_output_dir(self.tmp.name)
        self.clock, self.wall = Clock(), Clock()
        self.wall.now = time.time()
        window._pacer = pacing.Pacer(rng=random.Random(3), clock=self.clock, wall=self.wall)
        window._pace_timer.stop()
        window._notifier = mock.Mock()
        return window

    def add(self, window, urls):
        before = len(window._queue.items())
        window.add_links_from_text(" ".join(urls))
        self.assertTrue(wait_until(lambda: len(window._queue.items()) >= before + len(urls)))

    def idle(self, window):
        return wait_until(lambda: not window._download_jobs)

    def run_out(self, window, family="youtube"):
        """Pušta lažni sat naprijed kad god red čeka pauzu, dok sve ne završi."""
        for _ in range(500):
            self.idle(window)
            if not any(i.status in (ItemStatus.WAITING, ItemStatus.ACTIVE) for i in window._queue.items()):
                return
            self.clock.now += window._pacer.remaining(family) + 0.01
            if window._card_mode == "pause":
                window._tick_pause()
            else:
                window._start_next()
        self.fail("red nije završio")

    # ---------- blokada ----------

    def test_block_waits_five_minutes_and_continues_by_itself(self):
        window = self.window()
        self.failures[yt(1)] = 1
        self.add(window, [yt(1)])
        window._start_all()
        self.assertTrue(wait_until(lambda: window._card_mode == "pause"))
        item = window._queue.items()[0]
        self.assertEqual((item.status, item.message), (ItemStatus.WAITING, MESSAGE_PAUSE))
        self.assertIn("YouTube", window.pause_title.text())
        self.assertIn("5:00", window.pause_title.text())
        self.assertTrue(window._running)  # red ne staje dok stavka čeka pauzu
        self.assertGreater(self.settings.value("pacing/learned_until", type=float), time.time())
        self.clock.now += 120
        window._tick_pause()
        self.assertIn("3:00", window.pause_title.text())
        self.assertEqual(self.calls, [yt(1)])  # ništa ne kreće prije roka
        self.clock.now += 180
        window._tick_pause()
        self.assertTrue(wait_until(lambda: item.status == ItemStatus.DONE))
        self.assertTrue(window.pause_card.isHidden())
        self.assertIn("patient", window._achievements.earned)
        # Prozor nije u fokusu (offscreen): prvo „nastavljam", pa uobičajeno „završeno".
        first = window._notifier.call_args_list[0].args
        self.assertEqual(first[0], "Nastavljam preuzimanje")
        self.assertIn("YouTube", first[1])

    def test_third_block_in_a_row_becomes_a_normal_error(self):
        window = self.window()
        self.failures[yt(1)] = 4
        self.add(window, [yt(1)])
        window._start_all()
        self.run_out(window)
        item = window._queue.items()[0]
        self.assertEqual(item.status, ItemStatus.FAILED)
        self.assertEqual(len(self.calls), 4)  # 1 + čekanja od 5, 10 i 15 min

    def test_continue_now_skips_the_wait_without_the_badge(self):
        window = self.window()
        self.failures[yt(1)] = 1
        self.add(window, [yt(1)])
        window._start_all()
        self.assertTrue(wait_until(lambda: window._card_mode == "pause"))
        self.assertEqual(window.pause_primary.text(), "Nastavi odmah")
        window.pause_primary.click()
        self.assertTrue(wait_until(lambda: window._queue.items()[0].status == ItemStatus.DONE))
        self.assertNotIn("patient", window._achievements.earned)

    def test_continue_later_keeps_the_rest_for_next_start(self):
        window = self.window()
        self.failures[yt(1)] = 1
        self.add(window, [yt(1), yt(2)])
        window._start_all()
        self.assertTrue(wait_until(lambda: window._card_mode == "pause"))
        window.pause_secondary.click()  # „Nastavi kasnije"
        self.assertFalse(window._running)
        self.assertTrue(window.pause_card.isHidden())
        self.assertTrue(all(i.status == ItemStatus.WAITING and i.message == "" for i in window._queue.items()))
        self.assertIn("2", window.status_label.text())
        window._save_queue()
        again = MainWindow(settings=self.settings, probe_fn=lambda *a, **k: None, download_fn=window._download_fn,
                           thumbnail_fetch=lambda u: None, data_dir_path=self.tmp.name)
        self.addCleanup(again.deleteLater)
        again.set_output_dir(self.tmp.name)
        self.assertEqual(again._card_mode, "resume")
        self.assertIn("2", again.pause_title.text())
        again.pause_primary.click()  # „Nastavi preuzimanje"
        self.assertTrue(wait_until(lambda: all(i.status == ItemStatus.DONE for i in again._queue.items())))

    def test_stop_ends_the_pause(self):
        window = self.window()
        self.failures[yt(1)] = 1
        self.add(window, [yt(1)])
        window._start_all()
        self.assertTrue(wait_until(lambda: window._card_mode == "pause"))
        window._stop_all()
        self.assertTrue(window.pause_card.isHidden())
        self.assertEqual(window._pacer.remaining("youtube"), 0)
        self.assertEqual(window._queue.items()[0].message, "")
        self.assertNotIn("patient", window._achievements.earned)

    # ---------- razmaci i predah ----------

    def test_gaps_from_the_tenth_and_a_break_after_twenty_five(self):
        window = self.window()
        statuses = []
        original = window._set_status
        window._set_status = lambda text, *a: (statuses.append(text), original(text, *a))
        cards = []
        original_show = window._show_pause
        window._show_pause = lambda pause: (cards.append(pause), original_show(pause))
        self.add(window, [yt(n) for n in range(30)])
        window._start_all()
        self.assertTrue(wait_until(lambda: len(self.calls) == 9 and not window._download_jobs))
        self.assertTrue(window._running)
        self.assertGreater(window._pacer.remaining("youtube"), 0)  # 10. čeka razmak
        self.assertTrue(any("Pauza" in text and "YouTube" in text for text in statuses))
        self.run_out(window)
        self.assertTrue(all(i.status == ItemStatus.DONE for i in window._queue.items()))
        self.assertEqual([pause.kind for pause in cards], ["break"])

    def test_other_sites_go_at_full_speed(self):
        window = self.window()
        self.add(window, [f"https://vimeo.com/{n}" for n in range(15)])
        window._start_all()
        self.assertTrue(wait_until(lambda: all(i.status == ItemStatus.DONE for i in window._queue.items())))

    def test_protection_off_means_no_gaps(self):
        window = self.window()
        window.set_pacing(False)
        self.assertFalse(self.settings.value("pacing/enabled", type=bool))
        self.add(window, [yt(n) for n in range(15)])
        self.assertEqual(self.probe_options, {"no_pacing": True})
        window._start_all()
        self.assertTrue(wait_until(lambda: all(i.status == ItemStatus.DONE for i in window._queue.items())))

    def test_two_at_a_time_from_one_site_after_the_tenth(self):
        window = self.window()
        for _ in range(10):
            window._pacer.started("youtube")
            window._pacer.finished("youtube")
        window._pacer.skip()
        self.add(window, [yt(n) for n in range(4)])
        item = window._queue.items()[0]
        with mock.patch.object(window, "_family_running", return_value=2):
            self.assertTrue(window._pace_held(item))
        with mock.patch.object(window, "_family_running", return_value=1):
            self.assertFalse(window._pace_held(item))

    # ---------- 50/50 i podrška ----------

    def test_fifty_without_errors_shows_the_success_card(self):
        window = self.window()
        self.add(window, [f"https://v.test/{n}" for n in range(50)])
        window._start_all()
        self.assertTrue(wait_until(lambda: window._card_mode == "success"))
        self.assertIn("50/50", window.pause_title.text())
        window.pause_primary.click()
        self.assertTrue(window.pause_card.isHidden())

    def test_no_success_card_with_an_error_or_a_small_batch(self):
        window = self.window()
        self.add(window, [f"https://v.test/{n}" for n in range(49)])
        window._start_all()
        self.assertTrue(wait_until(lambda: all(i.status == ItemStatus.DONE for i in window._queue.items())))
        self.assertTrue(wait_until(lambda: not window._batch))
        self.assertEqual(window._card_mode, "")

    def test_support_line_once_a_week_and_thanks_after_supporting(self):
        self.settings.setValue("support/downloads", 20)
        window = self.window()
        window._show_pause(pacing.Pause("youtube", "break", 30))
        self.assertFalse(window.pause_support_button.isHidden())
        self.assertIn("besplatan", window.pause_support.text())
        window._hide_card()
        window._show_pause(pacing.Pause("youtube", "break", 30))
        self.assertTrue(window.pause_support_button.isHidden())
        self.assertTrue(window.pause_support.isHidden())
        window._hide_card()
        window._support.already_supported(time.time())
        window._show_pause(pacing.Pause("youtube", "break", 30))
        self.assertEqual(window.pause_support.text(), "Hvala što podržavaš projekat ♥")
        self.assertTrue(window.pause_support_button.isHidden())
        self.assertTrue(window.pause_tip.text().startswith("💡"))

    def test_settings_dialog_switches(self):
        from videodl.settings_dialog import SettingsDialog
        from videodl.gui_util import PARALLEL_CHOICES, RATE_CHOICES
        from videodl.presets import NAME_TEMPLATES

        window = self.window()
        dialog = SettingsDialog(window, RATE_CHOICES, PARALLEL_CHOICES, NAME_TEMPLATES)
        self.addCleanup(dialog.deleteLater)
        self.assertTrue(dialog.pacing.isChecked() and dialog.recap.isChecked())
        tabs = [dialog.tabs.tabText(i) for i in range(dialog.tabs.count())]
        self.assertEqual(tabs, ["Preuzimanje", "Uz video", "Prijava na sajtove", "Ponašanje", "Izgled i jezik"])
        self.assertTrue(dialog.pacing_note.isHidden())
        with mock.patch.object(window, "confirm_pacing_off", return_value=False) as ask:
            dialog.pacing.setChecked(False)  # upozorenje → „Ostavi uključeno"
        ask.assert_called_once()
        self.assertTrue(dialog.pacing.isChecked() and window._pacer.enabled)
        with mock.patch.object(window, "confirm_pacing_off", return_value=True):
            dialog.pacing.setChecked(False)  # upozorenje → „Isključi"
        self.assertFalse(dialog.pacing_note.isHidden())
        self.assertIn("YouTube", dialog.pacing_note.text())
        dialog.recap.setChecked(False)
        self.assertFalse(window._pacer.enabled)
        self.assertFalse(window._recap_enabled)
        self.assertFalse(self.settings.value("recap/enabled", type=bool))
        with mock.patch.object(window, "confirm_pacing_off") as ask:
            dialog.pacing.setChecked(True)  # uključivanje ne pita ništa
        ask.assert_not_called()
        self.assertTrue(window._pacer.enabled and dialog.pacing_note.isHidden())

    # ---------- mjesečni pregled ----------

    def test_monthly_recap_once_with_an_image_to_share(self):
        window = self.window()
        start = datetime(2026, 10, 3, 18)
        for n in range(12):
            window._recap.record(yt(n), 50 * 1024 * 1024, 600, start + timedelta(hours=n))
        window._maybe_show_recap(date(2026, 11, 2))
        dialog = window._recap_dialog
        self.addCleanup(dialog.deleteLater)
        self.assertEqual(dialog.title.text(), "Tvoj oktobar 🎬")
        self.assertIn("12 videa", dialog.stats.text())
        self.assertIn("Najviše sa: YouTube", dialog.details.text())
        self.assertNotIn("video0", dialog.details.text())  # naslovi i linkovi se ne prikazuju
        path = os.path.join(self.tmp.name, dialog.default_name())
        self.assertTrue(dialog.save_to(path))
        self.assertGreater(os.path.getsize(path), 1000)
        dialog.close()
        window._recap_dialog = None
        window._maybe_show_recap(date(2026, 11, 20))
        self.assertIsNone(window._recap_dialog)  # jednom po mjesecu
        self.assertIn('"last_shown": "2026-10"', self.settings.value("recap/state", type=str))

    def test_recap_can_be_turned_off(self):
        window = self.window()
        window.set_recap_enabled(False)
        for n in range(12):
            window._recap.record(yt(n), 1, 1, datetime(2026, 10, 3))
        window._recap_dialog = None
        window._maybe_show_recap(date(2026, 11, 2))
        self.assertIsNone(window._recap_dialog)


if __name__ == "__main__":
    unittest.main()
