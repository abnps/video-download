"""Animirana traka napretka (varijanta 4): klizi, boja po fazi, klizanje bez procenta, zeleni kraj."""

import os
import time
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtGui import QColor  # noqa: E402
from PySide6.QtWidgets import QApplication, QVBoxLayout, QWidget  # noqa: E402

from videodl.jobs import ItemStatus, QueueItem  # noqa: E402
from videodl.widgets import PROGRESS_COLORS, AnimatedProgress, QueueRow  # noqa: E402

app = QApplication.instance() or QApplication([])


def wait_until(condition, timeout=5.0):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        app.processEvents()
        if condition():
            return True
        time.sleep(0.01)
    app.processEvents()
    return condition()


def pixel(bar: AnimatedProgress, x: int) -> QColor:
    return bar.grab().toImage().pixelColor(x, bar.height() // 2)


class AnimatedProgressTest(unittest.TestCase):
    def setUp(self):
        self.host = QWidget()
        layout = QVBoxLayout(self.host)
        self.bar = AnimatedProgress()
        layout.addWidget(self.bar)
        self.host.resize(400, 30)
        self.host.show()
        self.addCleanup(self.host.deleteLater)

    def test_slides_to_new_value_instead_of_jumping(self):
        self.bar.set_fraction(0.5)
        app.processEvents()
        self.assertLess(self.bar.value, 0.5)  # odmah poslije novog procenta još nije stigla
        self.assertTrue(wait_until(lambda: abs(self.bar.value - 0.5) < 0.001))
        self.assertTrue(self.bar.is_animating())  # sjaj i dalje prelazi

    def test_colour_follows_phase(self):
        self.bar.set_fraction(0.9, "video")
        self.assertTrue(wait_until(lambda: self.bar.value > 0.89))
        self.assertEqual(self.bar.phase, "video")
        self.assertGreater(pixel(self.bar, 5).blue(), pixel(self.bar, 5).red())  # plavo
        self.bar.set_fraction(0.95, "audio")
        self.assertEqual(self.bar.phase, "audio")
        colour = pixel(self.bar, 5)
        self.assertGreater(colour.red(), 100)  # ljubičasto
        self.assertGreater(colour.blue(), colour.green())

    def test_without_percent_it_slides_back_and_forth(self):
        self.bar.set_fraction(None)
        self.assertTrue(self.bar.indeterminate)
        self.assertTrue(self.bar.is_animating())

    def test_finish_turns_green_pulses_and_hides(self):
        self.bar.set_fraction(0.7)
        self.bar.finish()
        self.assertEqual((self.bar.phase, self.bar.value), ("done", 1.0))
        self.assertEqual(pixel(self.bar, 200).name(), QColor(PROGRESS_COLORS["done"]).name())
        self.assertTrue(wait_until(lambda: not self.bar.is_animating(), 3))  # puls je kratak
        self.assertTrue(wait_until(lambda: self.bar.isHidden(), 3))
        self.assertEqual(self.bar.value, 0.0)  # sljedeće preuzimanje kreće od nule

    def test_hidden_bar_uses_no_timer(self):
        self.bar.set_fraction(0.3)
        self.bar.hide()
        self.assertFalse(self.bar.is_animating())


class RowProgressTest(unittest.TestCase):
    def test_row_shows_bar_while_active_and_green_end_after_done(self):
        item = QueueItem(1, "https://v/1", "Video", "best", "C:/x")
        row = QueueRow(item)
        self.addCleanup(row.deleteLater)
        row.resize(600, 80)
        row.show()
        item.status = ItemStatus.ACTIVE
        row.update_item(item)
        self.assertFalse(row.progress.isHidden())
        self.assertTrue(row.progress.indeterminate)  # priprema, još nema procenta
        row.show_progress("Preuzimanje · 40%", 0.4, "audio")
        self.assertEqual(row.progress.phase, "audio")
        item.status = ItemStatus.DONE
        row.update_item(item)
        self.assertEqual(row.progress.phase, "done")
        self.assertTrue(wait_until(lambda: row.progress.isHidden(), 3))

    def test_failed_row_hides_bar_at_once(self):
        item = QueueItem(2, "https://v/2", "Video", "best", "C:/x", status=ItemStatus.ACTIVE)
        row = QueueRow(item)
        self.addCleanup(row.deleteLater)
        row.show()
        row.update_item(item)
        item.status = ItemStatus.FAILED
        row.update_item(item)
        self.assertTrue(row.progress.isHidden())


if __name__ == "__main__":
    unittest.main()
