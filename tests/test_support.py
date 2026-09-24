"""„Podrži projekat": podsjetnik je primjetan, ali ništa ne blokira i gasi se i bez uplate."""

import os
import tempfile
import time
import unittest
from pathlib import Path
from unittest import mock

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QSettings, QUrl  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

from videodl import support  # noqa: E402
from videodl.download import DownloadResult  # noqa: E402
from videodl.gui import MainWindow  # noqa: E402
from videodl.i18n import set_language  # noqa: E402
from videodl.jobs import ItemStatus  # noqa: E402
from videodl.probe import Entry, ProbeResult  # noqa: E402

app = QApplication.instance() or QApplication([])
DAY = 24 * 60 * 60


def wait_until(condition, timeout=10.0):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        app.processEvents()
        if condition():
            return True
        time.sleep(0.01)
    app.processEvents()
    return condition()


class SupportStateTest(unittest.TestCase):
    def test_banner_every_ten_new_downloads_and_later_postpones(self):
        state = support.SupportState()
        for _ in range(9):
            state.count_download()
        self.assertFalse(state.should_show_banner(0))
        state.count_download()
        self.assertTrue(state.should_show_banner(0))
        state.banner_later()
        self.assertFalse(state.should_show_banner(0))
        for _ in range(10):
            state.count_download()
        self.assertTrue(state.should_show_banner(0))

    def test_dialog_rarely_and_never_while_busy(self):
        state = support.SupportState(downloads=3)
        self.assertFalse(state.should_show_dialog(1000, busy=False))  # ne odmah poslije prvih videa
        state.downloads = 5
        self.assertFalse(state.should_show_dialog(1000, busy=True))
        self.assertTrue(state.should_show_dialog(1000, busy=False))
        state.dialog_shown(1000)
        self.assertFalse(state.should_show_dialog(1000 + 6 * DAY, busy=False))
        self.assertTrue(state.should_show_dialog(1000 + 7 * DAY, busy=False))

    def test_already_supported_silences_everything_for_90_days_without_payment_check(self):
        state = support.SupportState(downloads=50, banner_next=10)
        state.already_supported(1000)
        self.assertFalse(state.should_show_banner(1000 + 89 * DAY))
        self.assertFalse(state.should_show_dialog(1000 + 89 * DAY, busy=False))
        self.assertTrue(state.should_show_dialog(1000 + 91 * DAY, busy=False))

    def test_qr_code_points_to_the_same_link(self):
        try:
            import cv2
            import numpy
        except ImportError:
            self.skipTest("OpenCV nije instaliran")
        path = Path(support.__file__).parent / "assets" / "support-qr.png"
        image = cv2.imdecode(numpy.fromfile(str(path), dtype=numpy.uint8), cv2.IMREAD_COLOR)
        data, _points, _ = cv2.QRCodeDetector().detectAndDecode(image)
        self.assertEqual(data, support.SUPPORT_URL)

    def test_link_is_the_paypal_page(self):
        self.assertEqual(support.SUPPORT_URL, "https://www.paypal.com/ncp/payment/PY6SBUFD6V7JQ")


class SupportWindowTest(unittest.TestCase):
    def setUp(self):
        set_language("bs")
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.settings = QSettings(os.path.join(self.tmp.name, "s.ini"), QSettings.Format.IniFormat)
        self.settings.setValue("language", "bs")

    def window(self):
        counter = iter(range(1000))

        def probe(url, http_headers=None):
            return ProbeResult("V", (Entry(url, "V", None, 4),), False)

        def download(url, preset, output_dir, subfolder, on_progress, cancel_event, **extra):
            path = Path(output_dir) / f"{next(counter)}.mp4"
            path.write_bytes(b"x")
            return DownloadResult(ItemStatus.DONE, filepath=str(path))

        window = MainWindow(settings=self.settings, probe_fn=probe, download_fn=download,
                            thumbnail_fetch=lambda u: None, data_dir_path=self.tmp.name)
        self.addCleanup(window.deleteLater)
        window.set_output_dir(self.tmp.name)
        return window

    def download(self, window, count):
        window.add_links_from_text(" ".join(f"https://v/{i}" for i in range(count)))
        self.assertTrue(wait_until(lambda: len(window._queue.items()) >= count))
        window._start_all()
        self.assertTrue(wait_until(lambda: all(i.status == ItemStatus.DONE for i in window._queue.items())))

    def test_status_bar_link_and_help_menu_open_paypal(self):
        window = self.window()
        self.assertIn("Podrži projekat", window.support_link.text())
        self.assertIn(window.support_action, window.help_menu.actions())
        with mock.patch("videodl.gui.QDesktopServices.openUrl") as open_url:
            window._open_support()
        open_url.assert_called_once_with(QUrl("https://www.paypal.com/ncp/payment/PY6SBUFD6V7JQ"))

    def test_banner_after_ten_downloads_blocks_nothing_and_later_hides_it(self):
        window = self.window()
        self.download(window, 9)
        self.assertTrue(window.support_banner.isHidden())
        self.download(window, 1)
        self.assertFalse(window.support_banner.isHidden())
        self.assertEqual(self.settings.value("support/downloads", type=int), 10)
        # Program i dalje radi normalno dok je traka vidljiva.
        self.download(window, 1)
        window.support_banner_later.click()
        self.assertTrue(window.support_banner.isHidden())

    def test_weekly_dialog_and_already_supported_for_everyone(self):
        window = self.window()
        self.download(window, 5)
        self.assertTrue(wait_until(lambda: window._support_dialog is not None))
        dialog = window._support_dialog
        self.assertIn("Preuzeo si već 5 videa", dialog.findChildren(type(window.status_label))[0].text())
        self.assertFalse(dialog.qr_label.pixmap().isNull())  # i link (dugme) i QR kod
        self.assertEqual(dialog.qr_caption.text(), "Skeniraj kamerom telefona")
        dialog.already_button.click()  # bez ikakve provjere uplate
        self.assertTrue(wait_until(lambda: window._support_dialog is None))
        self.assertGreater(self.settings.value("support/snooze_until", type=float), time.time() + 89 * DAY)

    def test_existing_files_do_not_count(self):
        window = self.window()
        window._download_fn = lambda *a, **k: DownloadResult(ItemStatus.DONE, filepath=__file__, already_existed=True)
        self.download(window, 3)
        self.assertEqual(window._support.downloads, 0)


if __name__ == "__main__":
    unittest.main()
