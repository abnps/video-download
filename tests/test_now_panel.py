"""Izgled „Sada i sljedeće" (1.0.9): kartica „Sada preuzima", grafikon brzine i statusna traka."""

import os
import tempfile
import unittest
from unittest import mock

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QSettings  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

from videodl.download import PROCESSING, Progress  # noqa: E402
from videodl.gui import MainWindow  # noqa: E402
from videodl.i18n import set_language  # noqa: E402
from videodl.jobs import ItemStatus  # noqa: E402
from videodl.now_panel import SPARK_POINTS, Sparkline  # noqa: E402
from videodl.probe import ProbeResult  # noqa: E402

app = QApplication.instance() or QApplication([])


class SparklineTest(unittest.TestCase):
    def test_keeps_only_the_latest_values(self):
        spark = Sparkline()
        for value in range(SPARK_POINTS + 15):
            spark.add(value)
        self.assertEqual(len(spark.values), SPARK_POINTS)
        self.assertEqual(spark.values[-1], SPARK_POINTS + 14)
        spark.add(-5)
        self.assertEqual(spark.values[-1], 0.0)  # brzina nikad negativna
        spark.clear()
        self.assertEqual(spark.values, [])


class NowPanelWindowTest(unittest.TestCase):
    def setUp(self):
        set_language("bs")
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        settings = QSettings(os.path.join(self.tmp.name, "s.ini"), QSettings.Format.IniFormat)
        settings.setValue("language", "bs")
        patcher = mock.patch("videodl.achievements.AchievementState.take_pending", return_value=[])
        patcher.start()
        self.addCleanup(patcher.stop)
        self.window = MainWindow(settings=settings, probe_fn=lambda *a, **k: ProbeResult("", (), False),
                                 download_fn=lambda *a, **k: None, thumbnail_fetch=lambda u: None,
                                 data_dir_path=self.tmp.name)
        self.addCleanup(self.window.deleteLater)

    def add(self, title: str, status: ItemStatus):
        item = self.window._queue.add(f"https://example.test/{title}", title, "best", self.tmp.name, None, duration=90)
        item.status = status
        self.window._append_row(item)
        self.window._refresh_row(item)
        return item

    def test_active_video_is_on_the_card_and_not_repeated_in_the_list(self):
        active = self.add("Prvi", ItemStatus.ACTIVE)
        waiting = self.add("Drugi", ItemStatus.WAITING)
        self.window._update_controls()
        panel = self.window.now_panel
        self.assertFalse(panel.isHidden())
        self.assertEqual(panel.item_id, active.id)
        self.assertEqual(panel.title.text(), "Prvi")
        self.assertEqual(panel.queue_label.text(), "1 u redu")
        self.assertTrue(self.window._rows[active.id].isHidden())
        self.assertFalse(self.window._rows[waiting.id].isHidden())

        self.window._on_download_progress(active.id, Progress("download", 0.4, 2_000_000, 30, "progress.video"))
        self.assertEqual(panel.percent.text(), "40%")
        self.assertEqual(panel.spark.values, [2_000_000.0])
        self.assertNotEqual(panel.speed.text(), "—")
        self.assertEqual(panel.phase_labels["video"].property("state"), "on")
        self.assertTrue(panel.phase_labels["convert"].isHidden())  # „Obrada" se za video vidi tek kad krene
        self.window._on_download_progress(active.id, Progress(PROCESSING, None, label="pp.merge"))
        self.assertEqual(panel.phase_labels["merge"].property("state"), "on")
        # Sve što nije spajanje (npr. pretvaranje u AVI za auto) je „Obrada", ne „Spajanje".
        self.window._on_download_progress(active.id, Progress(PROCESSING, None, label="pp.processing"))
        self.assertEqual(panel.phase_labels["convert"].property("state"), "on")
        self.assertEqual(panel.phase_labels["merge"].property("state"), "")
        self.assertFalse(panel.phase_labels["convert"].isHidden())

        with mock.patch.object(self.window, "_cancel_active") as cancel:
            panel.stop_button.click()  # isto kao „zaustavi" u redu
        cancel.assert_called_once_with(active.id)

        active.status = ItemStatus.DONE
        self.window._refresh_row(active)
        self.window._update_controls()
        self.assertTrue(panel.isHidden())
        self.assertFalse(self.window._rows[active.id].isHidden())

    def test_only_video_is_on_the_card_and_the_list_invites_more_links(self):
        active = self.add("Jedini", ItemStatus.ACTIVE)
        self.window._update_controls()
        self.assertIs(self.window.stack.currentWidget(), self.window.queue_hint)  # ne prazna lista
        self.assertIn("Ctrl+V", self.window.queue_hint.text())
        waiting = self.add("Drugi", ItemStatus.WAITING)
        self.window._update_controls()
        self.assertIs(self.window.stack.currentWidget(), self.window.scroll)
        self.assertFalse(self.window._rows[waiting.id].isHidden())
        self.assertTrue(self.window._rows[active.id].isHidden())

    def test_card_is_never_squeezed_and_turns_compact_on_a_low_window(self):
        # Standardni prozor: puna kartica dobije visinu koju traži (ranije ju je gnječio sakriveni prazan ekran).
        window, panel = self.window, self.window.now_panel
        self.add("Prvi", ItemStatus.ACTIVE)
        for number in range(4):
            self.add(f"Čeka {number}", ItemStatus.WAITING)
        window._update_controls()
        window.show()
        app.processEvents()
        self.assertEqual((window.width(), window.height()), (900, 640))
        self.assertFalse(panel.compact)
        self.assertFalse(panel.details.isHidden())
        self.assertGreaterEqual(panel.height(), panel.minimumSizeHint().height())
        self.assertGreaterEqual(window.scroll.height(), 96)
        self.assertLess(window.stack.minimumSizeHint().height(), window.drop_zone.minimumSizeHint().height())
        full = panel.height()

        # Nizak prozor: sažeta kartica (bez donjeg reda), brzina i vrijeme uz procenat.
        window.resize(900, 520)
        app.processEvents()
        self.assertTrue(panel.compact)
        self.assertTrue(panel.details.isHidden())
        self.assertLess(panel.height(), full)
        self.assertGreaterEqual(panel.height(), panel.minimumSizeHint().height())
        window._on_download_progress(panel.item_id, Progress("download", 0.5, 3_000_000, 12, "progress.video"))
        self.assertIn("još", panel.inline.text())
        self.assertFalse(panel.inline.isHidden())

        # Prozor se ne može smanjiti ispod onoga što raspored traži, pa se kartice ne preklapaju.
        # I uz traku čiji se tekst na uskom prozoru prelama u više redova (Qt to sam ne uračuna u najmanju visinu).
        window.support_banner.show()
        for _ in range(3):
            window.resize(640, 200)
            app.processEvents()
        self.assertGreater(window.height(), 380)
        self.assertEqual(window.height(), window.minimumHeight())
        layout = window.centralWidget().layout()
        for index in range(layout.count()):
            widget = layout.itemAt(index).widget()
            if widget is not None and not widget.isHidden():
                with self.subTest(widget=widget.objectName()):
                    self.assertGreaterEqual(widget.height(), widget.minimumSizeHint().height())
        self.assertEqual(panel.stop_button.accessibleName(), "Zaustavi ovaj video")

    def test_paste_icon_follows_the_theme(self):
        before = self.window.paste_button.icon().pixmap(14, 14).toImage()
        self.window.set_theme("dark", save=False)
        self.addCleanup(self.window.set_theme, "light", False)
        after = self.window.paste_button.icon().pixmap(14, 14).toImage()
        self.assertNotEqual(before, after)

    def test_status_bar_shows_block_protection_and_today(self):
        self.window._update_controls()
        self.assertIn("uključena", self.window.shield_label.text())
        self.assertEqual(self.window.today_label.text(), "")
        self.window.set_pacing(False)  # statusna traka se osvježi sama
        self.assertIn("isključena", self.window.shield_label.text())
        self.assertEqual(self.window.shield_label.property("state"), "off")
        self.window._recap.record("https://example.test/v", 5 * 1024 * 1024, 60)
        self.window._update_controls()
        self.assertTrue(self.window.today_label.text().startswith("Danas: 1"))


if __name__ == "__main__":
    unittest.main()
