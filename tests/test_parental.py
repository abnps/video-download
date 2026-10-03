"""Roditeljska zaštita (Ahmed 3.10.2026): uz nju se 18+ ne preuzima i ne nudi potvrda; PIN se čuva samo kao otisak."""

import os
import sys
import time
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))  # test_adult (zajednički prozor za 18+)

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication  # noqa: E402

from videodl import parental  # noqa: E402
from videodl.dialogs import ParentalDialog  # noqa: E402
from videodl.jobs import ItemStatus  # noqa: E402

from test_adult import ConfirmationTest, app, wait_until  # noqa: E402

assert isinstance(app, QApplication)


class PinTest(unittest.TestCase):
    def test_pin_is_stored_only_as_salted_hash(self):
        stored = parental.hash_pin("2468")
        self.assertNotIn("2468", stored)
        self.assertNotEqual(stored, parental.hash_pin("2468"))  # nova so svaki put
        self.assertTrue(parental.check_pin("2468", stored))
        self.assertFalse(parental.check_pin("2469", stored))

    def test_invalid_pins_and_broken_records_never_pass(self):
        for pin in ("", "123", "123456789", "12a4", " 1234"):
            with self.subTest(pin=pin):
                self.assertFalse(parental.valid_pin(pin))
                with self.assertRaises(ValueError):
                    parental.hash_pin(pin)
        for stored in ("", "x", "pbkdf2-sha256$1$zz$00", "md5$1$00$00"):
            self.assertFalse(parental.check_pin("1234", stored))


class BlockingTest(ConfirmationTest):
    def test_adult_video_is_blocked_without_asking_and_others_download(self):
        self.settings.setValue("parental/enabled", True)
        window = self.window(adult=lambda url: url.endswith("/a"))
        self.add(window, "https://v/a", "https://v/b")
        window._start_all()
        self.assertTrue(wait_until(lambda: self.downloads == ["https://v/b"]))
        time.sleep(0.2)
        app.processEvents()
        self.assertEqual(self.asked, [])  # potvrda „Imam 18" se ne nudi
        blocked = next(i for i in window._queue.items() if i.url.endswith("/a"))
        self.assertEqual(blocked.status, ItemStatus.FAILED)
        self.assertIn("roditeljskom", blocked.message)
        self.assertFalse(blocked.adult_ok)
        # „Pokušaj ponovo" ne zaobilazi zaštitu.
        window._on_row_action(blocked.id)
        time.sleep(0.2)
        app.processEvents()
        self.assertEqual(self.downloads, ["https://v/b"])
        self.assertEqual(self.asked, [])

    def test_without_protection_confirmation_still_works(self):
        window = self.window()
        self.add(window, "https://v/a")
        window._start_all()
        self.assertTrue(wait_until(lambda: self.downloads == ["https://v/a"]))
        self.assertEqual(self.asked, [["https://v/a"]])


class DialogTest(unittest.TestCase):
    def test_pin_validation(self):
        dialog = ParentalDialog(False)
        dialog.enabled_box.setChecked(True)
        dialog.pin.setText("12")
        dialog.repeat.setText("12")
        dialog._accept()
        self.assertFalse(dialog.result())
        dialog.pin.setText("1234")
        dialog.repeat.setText("1235")
        dialog._accept()
        self.assertFalse(dialog.result())
        dialog.repeat.setText("1234")
        dialog._accept()
        self.assertTrue(dialog.result())
        self.assertEqual((dialog.chosen_enabled(), dialog.chosen_pin()), (True, "1234"))

    def test_turning_off_carries_no_pin(self):
        dialog = ParentalDialog(True)
        dialog.pin.setText("1234")
        dialog.enabled_box.setChecked(False)
        self.assertEqual((dialog.chosen_enabled(), dialog.chosen_pin()), (False, ""))


if __name__ == "__main__":
    unittest.main()
