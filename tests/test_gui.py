"""GUI test bez ekrana: pravi prozor i red, lažno čitanje linkova i preuzimanje."""

import os
import tempfile
import threading
import time
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QSettings  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

from videodl.browser import BrowserRequest  # noqa: E402
from videodl.download import DOWNLOADING, PROCESSING, DownloadResult, Progress  # noqa: E402
from videodl.gui import (  # noqa: E402
    COL_STATUS, MainWindow, format_eta, format_progress, format_speed,
)
from videodl.jobs import ItemStatus  # noqa: E402
from videodl.probe import Entry, ProbeResult  # noqa: E402

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


def fake_probe(url, http_headers=None):
    if "lista" in url:
        return ProbeResult("Moja lista", (Entry("https://v/1", "Prvi"), Entry("https://v/2", "Drugi")), True)
    if "lose" in url:
        raise RuntimeError("ERROR: Unsupported URL")
    return ProbeResult("Jedan", (Entry(url, "Jedan"),), False)


class FormattingTest(unittest.TestCase):
    def test_formatting(self):
        self.assertEqual(format_speed(3.2 * 1024 * 1024), "3,2 MB/s")
        self.assertEqual(format_eta(7), "7 s")
        self.assertEqual(format_eta(185), "3:05")
        self.assertEqual(format_eta(3725), "1:02:05")
        text = format_progress(Progress(DOWNLOADING, 0.456, 2048, 12, "video"))
        self.assertEqual(text, "Preuzimanje (video) · 46% · 2,0 KB/s · još 12 s")
        self.assertEqual(format_progress(Progress(PROCESSING, None, label="Konverzija zvuka")),
                         "Konverzija zvuka…")


class MainWindowTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.settings = QSettings(os.path.join(self.tmp.name, "settings.ini"), QSettings.Format.IniFormat)
        self.release = threading.Event()
        self.calls = []
        self.extras = []

    def tearDown(self):
        self.release.set()
        self.tmp.cleanup()

    def make_window(self, download_fn):
        window = MainWindow(settings=self.settings, probe_fn=fake_probe, download_fn=download_fn)
        window.folder_edit.setText(self.tmp.name)
        self.addCleanup(window.deleteLater)
        return window

    def quick_download(self, url, preset, output_dir, subfolder, on_progress, cancel_event, **extra):
        self.calls.append((url, preset.key, output_dir, subfolder))
        self.extras.append(extra)
        on_progress(Progress(DOWNLOADING, 0.5, 1024, 3))
        return DownloadResult(ItemStatus.DONE, filepath=os.path.join(output_dir, f"{url[-1]}.mp4"))

    def blocking_download(self, url, preset, output_dir, subfolder, on_progress, cancel_event, **extra):
        self.calls.append((url, preset.key, output_dir, subfolder))
        on_progress(Progress(DOWNLOADING, 0.1, None, None))
        while not cancel_event.is_set() and not self.release.is_set():
            time.sleep(0.01)
        if cancel_event.is_set():
            return DownloadResult(ItemStatus.CANCELLED, message="Otkazano")
        return DownloadResult(ItemStatus.DONE, filepath=url)

    def test_playlist_is_expanded_and_downloaded_in_order(self):
        window = self.make_window(self.quick_download)
        window.preset_combo.setCurrentIndex(window.preset_combo.findData("mp3"))
        window.url_edit.setText("https://v/lista")
        window._add_urls()

        self.assertTrue(wait_until(lambda: len(window._queue.items()) == 2
                                   and all(i.status == ItemStatus.DONE for i in window._queue.items())))
        self.assertEqual(self.calls, [
            ("https://v/1", "mp3", self.tmp.name, "Moja lista"),
            ("https://v/2", "mp3", self.tmp.name, "Moja lista"),
        ])
        self.assertEqual(window.table.rowCount(), 2)
        self.assertEqual(window.table.item(0, COL_STATUS).text(), "Završeno")
        self.assertIn("završeno: 2", window.summary_label.text())
        self.assertEqual(self.settings.value("preset_key"), "mp3")

        window._clear_finished()
        self.assertEqual(window.table.rowCount(), 0)

    def test_invalid_input_and_probe_error_are_reported(self):
        window = self.make_window(self.quick_download)
        window.url_edit.setText("nije-link")
        window._add_urls()
        self.assertIn("Ovo nije link", window.status_label.text())
        self.assertEqual(window.url_edit.text(), "nije-link")

        window.url_edit.setText("https://v/lose")
        window._add_urls()
        self.assertTrue(wait_until(lambda: "Unsupported URL" in window.status_label.text()))
        self.assertNotIn("ERROR", window.status_label.text())
        self.assertTrue(wait_until(lambda: not window._probe_jobs))

    def test_stop_cancels_current_and_keeps_rest_waiting(self):
        window = self.make_window(self.blocking_download)
        window.url_edit.setText("https://v/a https://v/b")
        window._add_urls()
        self.assertTrue(wait_until(lambda: len(window._queue.items()) == 2
                                   and window._download_job is not None))
        first, second = window._queue.items()
        self.assertTrue(wait_until(lambda: "10%" in window.table.item(0, COL_STATUS).text()))
        self.assertEqual(window.start_stop_button.text(), "Zaustavi")

        window._toggle_running()
        self.assertTrue(wait_until(lambda: first.status == ItemStatus.CANCELLED))
        self.assertEqual(second.status, ItemStatus.WAITING)
        self.assertIsNone(window._download_job)
        self.assertEqual(window.start_stop_button.text(), "Nastavi")
        self.assertTrue(window.start_stop_button.isEnabled())

        window.table.selectRow(0)
        self.assertTrue(window.retry_button.isEnabled())
        window._retry_selected()
        self.assertEqual(first.status, ItemStatus.WAITING)  # red je i dalje zaustavljen

        self.release.set()
        window._toggle_running()
        self.assertTrue(wait_until(lambda: first.status == ItemStatus.DONE
                                   and second.status == ItemStatus.DONE))
        self.assertEqual([c[0] for c in self.calls], ["https://v/a", "https://v/a", "https://v/b"])

    def test_browser_media_request_goes_straight_to_queue_with_headers(self):
        window = self.make_window(self.quick_download)
        window.preset_combo.setCurrentIndex(window.preset_combo.findData("720p"))
        headers = {"Referer": "https://sajt.ba/lekcija", "User-Agent": "UA"}
        # Emit iz druge niti, kao što radi lokalni most.
        threading.Thread(target=window.browser_request.emit, args=(BrowserRequest(
            "https://sajt.ba/lekcija", "Lekcija 3", "https://cdn.sajt.ba/a/index.m3u8", "hls", headers),)).start()

        self.assertTrue(wait_until(lambda: window._queue.items()
                                   and window._queue.items()[0].status == ItemStatus.DONE))
        item = window._queue.items()[0]
        self.assertEqual(item.title, "Lekcija 3")
        self.assertEqual(self.calls, [("https://cdn.sajt.ba/a/index.m3u8", "720p", self.tmp.name, None)])
        self.assertEqual(self.extras, [{"http_headers": headers, "filename_title": "Lekcija 3"}])
        self.assertIn("Iz browsera", window.status_label.text())

    def test_browser_page_request_is_probed_with_headers(self):
        seen = []

        def probe_with_headers(url, http_headers=None):
            seen.append((url, http_headers))
            return ProbeResult("Video", (Entry(url, "Video"),), False)

        window = MainWindow(settings=self.settings, probe_fn=probe_with_headers, download_fn=self.quick_download)
        self.addCleanup(window.deleteLater)
        window.folder_edit.setText(self.tmp.name)
        window.browser_request.emit(BrowserRequest("https://www.youtube.com/watch?v=x", "YT", headers={"User-Agent": "UA"}))

        self.assertTrue(wait_until(lambda: window._queue.items()
                                   and window._queue.items()[0].status == ItemStatus.DONE))
        self.assertEqual(seen, [("https://www.youtube.com/watch?v=x", {"User-Agent": "UA"})])
        self.assertEqual(self.extras, [{"http_headers": {"User-Agent": "UA"}, "filename_title": None}])

    def test_settings_are_restored(self):
        self.settings.setValue("output_dir", r"D:\Filmovi")
        self.settings.setValue("preset_key", "720p")
        window = MainWindow(settings=self.settings, probe_fn=fake_probe, download_fn=self.quick_download)
        self.addCleanup(window.deleteLater)
        self.assertEqual(window.folder_edit.text(), r"D:\Filmovi")
        self.assertEqual(window.preset_combo.currentData(), "720p")

    def test_screenshot_renders(self):
        window = self.make_window(self.blocking_download)
        window.url_edit.setText("https://v/lista")
        window._add_urls()
        self.assertTrue(wait_until(lambda: window._download_job is not None))
        window.show()
        wait_until(lambda: False, timeout=0.2)
        pixmap = window.grab()
        self.assertFalse(pixmap.isNull())
        target = os.environ.get("VIDEODL_SCREENSHOT")
        if target:
            pixmap.save(target)
        window._toggle_running()
        self.assertTrue(wait_until(lambda: window._download_job is None))


if __name__ == "__main__":
    unittest.main()
