"""Dostignuća: osvajaju se jednom, čuvaju se lokalno, čestitka ne prekida rad."""

import os
import tempfile
import time
import unittest
from datetime import datetime, timedelta

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QSettings  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

from videodl import achievements, i18n  # noqa: E402
from videodl.achievements import GB, AchievementState, Download  # noqa: E402

app = QApplication.instance() or QApplication([])
NOON = datetime(2026, 10, 19, 12, 0)


def earned_by(download: Download) -> list:
    state = AchievementState()
    state.record(download, now=1.0)
    return state.take_pending()


class RulesTest(unittest.TestCase):
    def test_each_kind_of_download_earns_its_badge(self):
        cases = {
            "audio": Download(url="https://a.ba/1", audio=True, when=NOON),
            "clip": Download(url="https://a.ba/1", clip=True, when=NOON),
            "uhd": Download(url="https://a.ba/1", height=2160, when=NOON),
            "browser": Download(url="https://a.ba/1", from_browser=True, when=NOON),
            "car": Download(url="https://a.ba/1", car=True, when=NOON),
            "subtitles": Download(url="https://a.ba/1", subtitles=True, when=NOON),
            "marathon": Download(url="https://a.ba/1", duration=2 * 3600, when=NOON),
            "parallel": Download(url="https://a.ba/1", running_together=4, when=NOON),
            "comeback": Download(url="https://a.ba/1", retried=True, when=NOON),
            "night": Download(url="https://a.ba/1", when=NOON.replace(hour=2)),
        }
        for key, download in cases.items():
            with self.subTest(key):
                self.assertEqual(earned_by(download), [key])
        self.assertEqual(earned_by(Download(url="https://a.ba/1", when=NOON)), [])
        # Titlovi uz samo zvuk ne postoje; 1080p nije 4K.
        self.assertEqual(earned_by(Download(url="https://a.ba/1", audio=True, subtitles=True, when=NOON)), ["audio"])
        self.assertEqual(earned_by(Download(url="https://a.ba/1", height=1080, when=NOON)), [])

    def test_badge_is_earned_only_once(self):
        state = AchievementState()
        state.record(Download(url="https://a.ba/1", audio=True, when=NOON), now=1.0)
        state.record(Download(url="https://a.ba/2", audio=True, when=NOON), now=2.0)
        self.assertEqual(state.take_pending(), ["audio"])
        self.assertEqual(state.earned["audio"], 1.0)

    def test_sites_and_gigabytes_add_up(self):
        state = AchievementState()
        for host in ("www.a.ba", "m.a.ba", "b.com", "c.org", "d.net"):
            state.record(Download(url=f"https://{host}/v", size=GB // 4, when=NOON))
        self.assertEqual(state.sites, ["a.ba", "b.com", "c.org", "d.net"])  # www i m. su isti sajt
        self.assertNotIn("sites5", state.earned)
        self.assertIn("gb1", state.earned)  # 5 × 0,25 GB
        state.record(Download(url="https://e.io/v", when=NOON))
        self.assertIn("sites5", state.earned)

    def test_seven_days_in_a_row_and_one_year(self):
        state = AchievementState()
        for day in range(6):
            state.record(Download(url="https://a.ba/1", when=NOON + timedelta(days=day)))
        self.assertNotIn("streak7", state.earned)
        state.record(Download(url="https://a.ba/1", when=NOON + timedelta(days=6)))
        self.assertIn("streak7", state.earned)
        state.record(Download(url="https://a.ba/1", when=NOON + timedelta(days=9)))  # pauza prekida niz
        self.assertEqual(state.streak, 1)
        self.assertEqual(state.best_streak, 7)
        state.record(Download(url="https://a.ba/1", when=NOON + timedelta(days=365)))
        self.assertIn("anniversary", state.earned)

    def test_whole_playlist_of_ten(self):
        state = AchievementState()
        state.record_playlist(9)
        self.assertNotIn("playlist", state.earned)
        state.record_playlist(10)
        self.assertIn("playlist", state.earned)

    def test_saved_and_loaded(self):
        state = AchievementState()
        state.record(Download(url="https://a.ba/1", audio=True, when=NOON), now=1.0)
        loaded = AchievementState.from_json(state.to_json())
        self.assertEqual(loaded.earned, {"audio": 1.0})
        self.assertEqual(AchievementState.from_json("pokvareno").earned, {})
        self.assertEqual(loaded.take_pending(), ["audio"])
        self.assertEqual(loaded.pending, [])

    def test_broken_saved_value_does_not_stop_the_program(self):
        for broken in ("[]", "5", '{"earned": [1], "streak": "x", "first_day": "nije datum", "pending": ["nema"]}'):
            with self.subTest(broken):
                state = AchievementState.from_json(broken)
                self.assertEqual(state.earned, {})
                self.assertEqual(state.pending, [])
                state.record(Download(url="https://a.ba/1", when=NOON))  # i dalje radi

    def test_broken_pending_entries_do_not_crash_or_repeat_congratulations(self):
        state = AchievementState.from_json(
            '{"earned": {"audio": 1.0}, "pending": [null, {}, [], 5, "audio", "audio", "clip"], '
            '"sites": ["a.ba", "a.ba", null]}')
        self.assertEqual(state.take_pending(), ["audio"])
        self.assertEqual(state.sites, ["a.ba"])
        self.assertEqual(AchievementState.from_json(5).earned, {})

    def test_invalid_earned_dates_are_ignored_before_opening_the_list(self):
        state = AchievementState.from_json(
            '{"earned": {"audio": NaN, "clip": 1e100, "night": true, "unknown": 1.0}}')
        self.assertEqual(state.earned, {})

    def test_country_second_level_domains_are_separate_sites(self):
        self.assertEqual(achievements.site_of("https://news.bbc.co.uk/v"), "bbc.co.uk")
        self.assertEqual(achievements.site_of("https://www.itv.co.uk/v"), "itv.co.uk")
        self.assertEqual(achievements.site_of("https://m.klix.ba/v"), "klix.ba")

    def test_playlist_with_a_failed_item_is_not_whole(self):
        state = AchievementState()
        state.record_playlist(10, total=11)
        self.assertNotIn("playlist", state.earned)
        state.record_playlist(10, total=10)
        self.assertIn("playlist", state.earned)

    def test_support_note_at_most_once_a_day(self):
        state = AchievementState()
        start = 1_800_000_000.0
        self.assertTrue(state.support_note_allowed(start))
        self.assertFalse(state.support_note_allowed(start + 3600))
        self.assertTrue(state.support_note_allowed(start + 25 * 3600))

    def test_every_badge_has_name_and_description_in_all_languages(self):
        for language in i18n.LANGUAGES:
            i18n.set_language(language)
            for key, _icon in achievements.BADGES:
                for text_key in (f"badge.{key}", f"badge.{key}.desc"):
                    with self.subTest(language=language, key=text_key):
                        self.assertNotEqual(i18n.tr(text_key), text_key)
        i18n.set_language("bs")


class WindowTest(unittest.TestCase):
    def setUp(self):
        i18n.set_language("bs")
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.settings = QSettings(os.path.join(self.tmp.name, "s.ini"), QSettings.Format.IniFormat)
        self.settings.setValue("language", "bs")  # inače jezik sistema (na GitHubu engleski)

    def window(self):
        from videodl.gui import MainWindow

        window = MainWindow(settings=self.settings, probe_fn=lambda *a, **k: None, download_fn=lambda *a, **k: None,
                            thumbnail_fetch=lambda u: None, data_dir_path=self.tmp.name)
        self.addCleanup(window.deleteLater)
        return window

    def test_badge_dialog_and_list(self):
        window = self.window()
        window._support.last_dialog = time.time() - 2 * 24 * 3600  # sedmični prozor prije 2 dana
        window._achievements.record(Download(url="https://a.ba/1", audio=True, when=NOON))
        window._maybe_remind_support()
        dialog = window._achievement_dialog
        self.assertIsNotNone(dialog)
        self.assertEqual(dialog.headline.text(), "🎵 Melomanija")
        self.assertFalse(dialog.support_note.isHidden())
        dialog.accept()
        self.assertIn("audio", AchievementState.from_json(self.settings.value("achievements/state")).earned)

        window.show_achievements_list()
        lists = [w for w in window.findChildren(type(dialog).__mro__[1]) if hasattr(w, "summary")]
        self.assertTrue(lists)
        listing = lists[-1]
        self.assertIn("Osvojeno 1 od", listing.summary.text())
        self.assertTrue(listing.list.item(0).text().startswith("🎵  Melomanija"))
        listing.accept()

    def test_several_at_once_in_one_dialog_without_second_support_note(self):
        window = self.window()
        window._support.last_dialog = time.time() - 2 * 24 * 3600  # sedmični prozor prije 2 dana
        window._achievements.record(Download(url="https://a.ba/1", audio=True, clip=True, when=NOON))
        window._maybe_remind_support()
        dialog = window._achievement_dialog
        self.assertEqual(dialog.headline.text(), "🏆 Nova dostignuća!")
        self.assertIn("Melomanija", dialog.message.text())
        self.assertIn("Montažer", dialog.message.text())
        dialog.accept()
        window._achievements.record(Download(url="https://a.ba/2", car=True, when=NOON))
        window._maybe_remind_support()
        self.assertTrue(window._achievement_dialog.support_note.isHidden())  # isti dan: bez druge poruke


class OneInvitationADayTest(WindowTest):
    def test_weekly_dialog_waits_after_achievement_with_support_note(self):
        window = self.window()
        window._support.downloads = 7
        window._support.last_dialog = time.time() - 8 * 24 * 3600  # sedmični prozor bi sada smio
        window._achievements.record(Download(url="https://a.ba/1", audio=True, when=NOON))
        window._maybe_remind_support()
        self.assertFalse(window._achievement_dialog.support_note.isHidden())
        window._achievement_dialog.accept()
        window._maybe_remind_support()
        self.assertIsNone(window._support_dialog)  # isti dan: bez drugog poziva na prilog


if __name__ == "__main__":
    unittest.main()
