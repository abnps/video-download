"""GUI test bez ekrana: pravi prozor i red, lažno čitanje linkova, preuzimanje i sličice."""

import os
import tempfile
import threading
import time
import unittest
from unittest import mock

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QBuffer, QByteArray, QIODevice, QSettings  # noqa: E402
from PySide6.QtGui import QColor, QImage  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

from videodl.browser import BrowserRequest, Cookie  # noqa: E402
from videodl.download import DOWNLOADING, PROCESSING, DownloadResult, Progress  # noqa: E402
from videodl.gui import (  # noqa: E402
    MainWindow, apply_theme, extract_urls, format_eta, format_progress, format_speed,
)
from videodl.i18n import get_language, set_language  # noqa: E402
from videodl.jobs import ItemStatus  # noqa: E402
from videodl.probe import Entry, ProbeResult  # noqa: E402
from videodl.widgets import format_duration, format_size  # noqa: E402

app = QApplication.instance() or QApplication([])
apply_theme(app)
set_language("bs")


def wait_until(condition, timeout=5.0):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        app.processEvents()
        if condition():
            return True
        time.sleep(0.01)
    app.processEvents()
    return condition()


def png_bytes() -> bytes:
    image = QImage(64, 36, QImage.Format.Format_RGB32)
    image.fill(QColor("#e53935"))
    data = QByteArray()
    buffer = QBuffer(data)
    buffer.open(QIODevice.OpenModeFlag.WriteOnly)
    image.save(buffer, "PNG")
    return bytes(data)


def fake_probe(url, http_headers=None):
    if "lista" in url:
        return ProbeResult("Moja lista", (
            Entry("https://v/1", "Major Lazer – Cold Water (Official Lyric Video)", "https://img/1.jpg", 189),
            Entry("https://v/2", "Peace Is The Mission (Extended)", None, 1275)), True)
    if "lose" in url:
        raise RuntimeError("ERROR: Unsupported URL")
    return ProbeResult("Jedan", (Entry(url, "Jedan", None, 61),), False)


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
        self.assertEqual(format_duration(189), "3:09")
        self.assertEqual(format_duration(3725), "1:02:05")
        self.assertEqual(format_duration(None), "")
        self.assertEqual(format_size(int(23.8 * 1024 * 1024)), "23,8 MB")

    def test_extract_urls_from_mixed_text(self):
        text = "Pogledaj https://youtu.be/abc, i (https://vimeo.com/1). Isto: https://youtu.be/abc\nnije-link"
        self.assertEqual(extract_urls(text), ["https://youtu.be/abc", "https://vimeo.com/1"])
        self.assertEqual(extract_urls("bez linka"), [])


class MainWindowTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.settings = QSettings(os.path.join(self.tmp.name, "settings.ini"), QSettings.Format.IniFormat)
        self.settings.setValue("language", "bs")
        self.release = threading.Event()
        self.calls = []
        self.extras = []

    def tearDown(self):
        self.release.set()
        self.tmp.cleanup()

    def make_window(self, download_fn, probe_fn=fake_probe, thumbnail_fetch=lambda url: None):
        window = MainWindow(settings=self.settings, probe_fn=probe_fn, download_fn=download_fn,
                            thumbnail_fetch=thumbnail_fetch)
        window.set_output_dir(self.tmp.name)
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

    def statuses(self, window):
        return [item.status for item in window._queue.items()]

    def test_pasted_links_wait_for_download_button(self):
        window = self.make_window(self.quick_download)
        self.assertEqual(window.stack.currentIndex(), 0)  # prazan ekran
        self.assertFalse(window.download_button.isEnabled())
        window.preset_combo.setCurrentIndex(window.preset_combo.findData("mp3"))
        QApplication.clipboard().setText("https://v/lista")
        window._paste_from_clipboard()

        self.assertTrue(wait_until(lambda: len(window._queue.items()) == 2))
        self.assertEqual(window.stack.currentIndex(), 1)
        time.sleep(0.1)
        app.processEvents()
        self.assertEqual(self.calls, [])  # kao u uzoru: tek „Preuzmi" pokreće
        self.assertEqual(window.download_button.text(), "Preuzmi")
        self.assertTrue(window.download_button.isEnabled())

        window.download_button.click()
        self.assertTrue(wait_until(lambda: self.statuses(window) == [ItemStatus.DONE, ItemStatus.DONE]))
        self.assertEqual(self.calls, [
            ("https://v/1", "mp3", self.tmp.name, "Moja lista"),
            ("https://v/2", "mp3", self.tmp.name, "Moja lista"),
        ])
        row = window._rows[window._queue.items()[0].id]
        self.assertTrue(row.status_label.text().startswith("Završeno"))
        self.assertEqual(row.action_button.property("kind"), "folder")
        self.assertIn("završeno: 2", window.summary_label.text())
        self.assertEqual(window.download_button.text(), "Preuzmi")
        self.assertEqual(self.settings.value("preset_key"), "mp3")

        window._clear_finished()
        self.assertEqual(window._rows, {})
        self.assertEqual(window.stack.currentIndex(), 0)

    def test_play_button_opens_downloaded_file(self):
        target = os.path.join(self.tmp.name, "a.mp4")

        def download_real_file(url, preset, output_dir, subfolder, on_progress, cancel_event, **extra):
            with open(target, "wb") as file:
                file.write(b"x" * 2048)
            return DownloadResult(ItemStatus.DONE, filepath=target)

        window = self.make_window(download_real_file)
        window.add_links_from_text("https://v/a")
        self.assertTrue(wait_until(lambda: len(window._queue.items()) == 1))
        item = window._queue.items()[0]
        row = window._rows[item.id]
        self.assertTrue(row.play_button.isHidden())  # nema šta da se pusti prije preuzimanja

        window._start_all()
        self.assertTrue(wait_until(lambda: item.status == ItemStatus.DONE))
        self.assertFalse(row.play_button.isHidden())
        self.assertEqual(row.play_button.toolTip(), "Pusti video")
        self.assertIn("2 KB", row.status_label.text())
        if os.environ.get("VIDEODL_SCREENSHOT"):
            window.resize(820, 200)
            window.show()
            wait_until(lambda: False, timeout=0.2)
            window.grab().save(os.environ["VIDEODL_SCREENSHOT"].replace(".png", "-pusti.png"))
        with mock.patch("videodl.gui.play_file") as play:
            row.play_button.click()
        play.assert_called_once_with(target)

        os.remove(target)
        with mock.patch("videodl.gui.play_file") as play:
            row.play_button.click()
        play.assert_not_called()
        self.assertIn("ne postoji", window.status_label.text())

    def test_invalid_clipboard_and_probe_error_are_reported(self):
        window = self.make_window(self.quick_download)
        QApplication.clipboard().setText("nije link")
        window._paste_from_clipboard()
        self.assertIn("nema linka", window.status_label.text())

        window.add_links_from_text("https://v/lose")
        self.assertTrue(wait_until(lambda: "Unsupported URL" in window.status_label.text()))
        self.assertNotIn("ERROR", window.status_label.text())
        self.assertTrue(wait_until(lambda: not window._probe_jobs))

        # Neuspio link je vidljiv crveni red, a „Pokušaj ponovo" ga daje yt-dlp-u direktno.
        [failed] = window._queue.items()
        row = window._rows[failed.id]
        self.assertEqual(failed.status, ItemStatus.FAILED)
        self.assertIn("Unsupported URL", row.status_label.text())
        self.assertEqual(row.action_button.property("kind"), "retry")
        row.action_button.click()
        self.assertTrue(wait_until(lambda: failed.status == ItemStatus.DONE))
        self.assertEqual(self.calls[0][0], "https://v/lose")

    def test_stop_then_row_retry_downloads_only_that_item(self):
        window = self.make_window(self.blocking_download)
        window.add_links_from_text("https://v/a https://v/b")
        self.assertTrue(wait_until(lambda: len(window._queue.items()) == 2))
        first, second = window._queue.items()
        window._start_all()
        self.assertTrue(wait_until(lambda: "10%" in window._rows[first.id].status_label.text()))
        self.assertEqual(window.download_button.text(), "Zaustavi")
        self.assertEqual(window._rows[first.id].action_button.property("kind"), "stop")

        window.download_button.click()
        self.assertTrue(wait_until(lambda: first.status == ItemStatus.CANCELLED))
        self.assertEqual(second.status, ItemStatus.WAITING)
        self.assertIsNone(window._download_job)
        self.assertEqual(window.download_button.text(), "Preuzmi")
        self.assertEqual(window._rows[first.id].action_button.property("kind"), "retry")

        self.release.set()
        window._rows[first.id].action_button.click()
        self.assertTrue(wait_until(lambda: first.status == ItemStatus.DONE))
        time.sleep(0.1)
        app.processEvents()
        self.assertEqual(second.status, ItemStatus.WAITING)  # pokrenut je samo taj red

        window._start_all()
        self.assertTrue(wait_until(lambda: second.status == ItemStatus.DONE))
        self.assertEqual([c[0] for c in self.calls], ["https://v/a", "https://v/a", "https://v/b"])

    def test_remove_active_row_cancels_and_removes(self):
        window = self.make_window(self.blocking_download)
        window.add_links_from_text("https://v/a https://v/b")
        self.assertTrue(wait_until(lambda: len(window._queue.items()) == 2))
        first, second = window._queue.items()
        window._rows[second.id].remove_button.click()
        self.assertEqual([i.id for i in window._queue.items()], [first.id])

        window._rows[first.id].action_button.click()  # pojedinačno pokretanje
        self.assertTrue(wait_until(lambda: first.status == ItemStatus.ACTIVE))
        window._rows[first.id].remove_button.click()
        self.assertTrue(wait_until(lambda: not window._queue.items()))
        self.assertEqual(window._rows, {})
        self.assertIsNone(window._download_job)

    def test_format_change_applies_to_waiting_but_not_custom_items(self):
        window = self.make_window(self.quick_download)
        window.add_links_from_text("https://v/a https://v/b")
        self.assertTrue(wait_until(lambda: len(window._queue.items()) == 2))
        first, second = window._queue.items()
        window.set_item_preset(first.id, "m4a")
        self.assertIn("M4A", window._rows[first.id].format_link.text())

        window.preset_combo.setCurrentIndex(window.preset_combo.findData("720p"))
        self.assertEqual((first.preset_key, second.preset_key), ("m4a", "720p"))
        self.assertIn("MP4 720p", window._rows[second.id].format_link.text())

        window._start_all()
        self.assertTrue(wait_until(lambda: self.statuses(window) == [ItemStatus.DONE, ItemStatus.DONE]))
        window.set_item_preset(first.id, "mp3")  # drugi format već preuzetog videa: ponovo u red
        self.assertEqual(first.status, ItemStatus.WAITING)

    def test_browser_media_request_starts_only_that_item_with_headers(self):
        window = self.make_window(self.quick_download)
        window.add_links_from_text("https://v/zalijepljen")
        self.assertTrue(wait_until(lambda: len(window._queue.items()) == 1))
        window.preset_combo.setCurrentIndex(window.preset_combo.findData("720p"))
        headers = {"Referer": "https://sajt.ba/lekcija", "User-Agent": "UA"}
        # Emit iz druge niti, kao što radi lokalni most.
        threading.Thread(target=window.browser_request.emit, args=(BrowserRequest(
            "https://sajt.ba/lekcija", "Lekcija 3", "https://cdn.sajt.ba/a/index.m3u8", "hls", headers),)).start()

        self.assertTrue(wait_until(lambda: len(window._queue.items()) == 2
                                   and window._queue.items()[1].status == ItemStatus.DONE))
        pasted, browser_item = window._queue.items()
        self.assertEqual(pasted.status, ItemStatus.WAITING)
        self.assertEqual(browser_item.title, "Lekcija 3")
        self.assertEqual(self.calls, [("https://cdn.sajt.ba/a/index.m3u8", "720p", self.tmp.name, None)])
        self.assertEqual(self.extras, [{"http_headers": headers, "filename_title": "Lekcija 3"}])
        self.assertIn("Iz browsera", window.status_label.text())

    def test_browser_page_request_is_probed_with_headers_and_started(self):
        seen = []

        def probe_with_headers(url, http_headers=None):
            seen.append((url, http_headers))
            return ProbeResult("Video", (Entry(url, "Video"),), False)

        window = self.make_window(self.quick_download, probe_fn=probe_with_headers)
        window.browser_request.emit(BrowserRequest("https://www.youtube.com/watch?v=x", "YT", headers={"User-Agent": "UA"}))

        self.assertTrue(wait_until(lambda: window._queue.items()
                                   and window._queue.items()[0].status == ItemStatus.DONE))
        self.assertEqual(seen, [("https://www.youtube.com/watch?v=x", {"User-Agent": "UA"})])
        self.assertEqual(self.extras, [{"http_headers": {"User-Agent": "UA"}, "filename_title": None}])

    def test_browser_cookies_reach_probe_and_download(self):
        seen = []

        def probe_with_access(url, http_headers=None, cookies=()):
            seen.append(cookies)
            return ProbeResult("Storija", (Entry(url, "Storija"),), False)

        window = self.make_window(self.quick_download, probe_fn=probe_with_access)
        cookies = (Cookie(".instagram.com", "sessionid", "tajna", host_only=False),)
        window.browser_request.emit(BrowserRequest("https://www.instagram.com/stories/nalog/1/", "Priče",
                                                   headers={"User-Agent": "UA"}, cookies=cookies))
        self.assertTrue(wait_until(lambda: window._queue.items()
                                   and window._queue.items()[0].status == ItemStatus.DONE))
        self.assertEqual(seen, [cookies])
        self.assertEqual(self.extras[0]["cookies"], cookies)
        self.assertNotIn("tajna", repr(window._queue.items()[0]))

    def test_thumbnail_and_duration_are_shown(self):
        fetched = []

        def fetch(url):
            fetched.append(url)
            return png_bytes()

        window = self.make_window(self.quick_download, thumbnail_fetch=fetch)
        window.add_links_from_text("https://v/lista")
        self.assertTrue(wait_until(lambda: len(window._queue.items()) == 2))
        first, second = window._queue.items()
        self.assertTrue(wait_until(lambda: window._rows[first.id].thumbnail.has_pixmap()))
        self.assertFalse(window._rows[second.id].thumbnail.has_pixmap())  # nema sličice: zamjenska
        self.assertEqual(window._rows[second.id].thumbnail._duration, "21:15")
        self.assertEqual(fetched, ["https://img/1.jpg"])

    def test_settings_are_restored(self):
        self.settings.setValue("output_dir", r"D:\Filmovi")
        self.settings.setValue("preset_key", "720p")
        window = MainWindow(settings=self.settings, probe_fn=fake_probe, download_fn=self.quick_download,
                            thumbnail_fetch=lambda url: None)
        self.addCleanup(window.deleteLater)
        self.assertEqual(window.output_dir, r"D:\Filmovi")
        self.assertIn("Filmovi", window.folder_label.text())
        self.assertEqual(window.preset_combo.currentData(), "720p")

    def test_screenshots_render(self):
        target = os.environ.get("VIDEODL_SCREENSHOT")
        window = self.make_window(self.blocking_download, thumbnail_fetch=lambda url: png_bytes())
        window.resize(820, 440)
        window.show()
        wait_until(lambda: False, timeout=0.2)
        empty = window.grab()
        self.assertFalse(empty.isNull())
        if target:
            empty.save(target.replace(".png", "-prazno.png"))

        window.add_links_from_text("https://v/lista https://v/jedan")
        self.assertTrue(wait_until(lambda: len(window._queue.items()) == 3))
        window._start_all()
        self.assertTrue(wait_until(lambda: window._download_job is not None))
        wait_until(lambda: False, timeout=0.3)
        full = window.grab()
        self.assertFalse(full.isNull())
        if target:
            full.save(target)
        window._stop_all()
        self.assertTrue(wait_until(lambda: window._download_job is None))


if __name__ == "__main__":
    unittest.main()
