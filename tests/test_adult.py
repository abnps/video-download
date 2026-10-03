"""Sadržaj 18+: potvrda pri svakom preuzimanju i zamućena sličica (Ahmed 26.9.2026)."""

import os
import tempfile
import time
import unittest
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QSettings  # noqa: E402
from PySide6.QtGui import QColor, QImage, QPixmap  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

from videodl import store  # noqa: E402
from videodl.download import DownloadResult  # noqa: E402
from videodl.gui import MainWindow, adult_thumbnail  # noqa: E402
from videodl.i18n import get_language, set_language  # noqa: E402
from videodl.jobs import DownloadQueue, ItemStatus  # noqa: E402
from videodl.probe import Entry, ProbeResult, _entry, is_adult  # noqa: E402

app = QApplication.instance() or QApplication([])


def wait_until(condition, timeout=10.0):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        app.processEvents()
        if condition():
            return True
        time.sleep(0.01)
    app.processEvents()
    return condition()


class DetectionTest(unittest.TestCase):
    def test_age_limit_18_marks_adult_content(self):
        self.assertTrue(is_adult({"age_limit": 18}))
        self.assertTrue(is_adult({"age_limit": 21}))
        for info in ({}, {"age_limit": 0}, {"age_limit": 16}, {"age_limit": None}, {"age_limit": "18"}, {"age_limit": True}):
            self.assertFalse(is_adult(info), info)
        self.assertTrue(_entry({"title": "x", "age_limit": 18}, "https://v/x").adult)
        self.assertFalse(_entry({"title": "x"}, "https://v/x").adult)

    def test_youtube_is_never_treated_as_adult_content(self):
        for info, url in (({"age_limit": 18, "extractor_key": "Youtube"}, "https://www.youtube.com/watch?v=x"),
                          ({"age_limit": 18}, "https://youtu.be/x"),
                          ({"age_limit": 18}, "https://music.youtube.com/watch?v=x"),
                          ({"age_limit": 18, "ie_key": "YoutubeTab"}, "https://example.test/x"),
                          ({"age_limit": 18, "webpage_url": "https://m.youtube.com/watch?v=x"}, None)):
            with self.subTest(url=url):
                self.assertFalse(is_adult(info, url))
        self.assertFalse(_entry({"title": "x", "age_limit": 18}, "https://www.youtube.com/watch?v=x").adult)
        # sličan naziv nije YouTube
        self.assertTrue(is_adult({"age_limit": 18}, "https://notyoutube.com.example/x"))

    def test_mark_survives_saved_queue_but_confirmation_does_not(self):
        queue = DownloadQueue()
        item = queue.add("https://v/a", "A", "best", "C:/x", adult=True)
        item.adult_ok = True
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "queue.json"
            store.save_queue(queue.items(), path)
            row = store.load_queue(path)[0]
            self.assertIs(row["adult"], True)
            self.assertNotIn("adult_ok", row)  # potvrda se nikad ne pamti na disku


class ConfirmationTest(unittest.TestCase):
    def setUp(self):
        self.language = get_language()
        set_language("bs")
        # Prozor (radna nit, odloženo čuvanje reda) zna upisati fajl baš dok se folder briše: na Windowsu je to
        # povremeno rušilo test (WinError 145, CI 3.10.2026), a ne ponašanje programa.
        self.tmp = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        self.settings = QSettings(os.path.join(self.tmp.name, "s.ini"), QSettings.Format.IniFormat)
        self.settings.setValue("language", "bs")
        self.asked = []
        self.answer = True
        self.downloads = []
        self.result = ItemStatus.DONE

    def tearDown(self):
        set_language(self.language)
        self.tmp.cleanup()

    def window(self, adult=True):
        def probe(url, **access):
            marked = adult(url) if callable(adult) else adult
            return ProbeResult("V", (Entry(url, f"Video {url[-1]}", adult=marked),), is_playlist=False)

        def download(url, preset, output_dir, subfolder, on_progress, cancel_event, **extra):
            self.downloads.append(url)
            path = Path(output_dir) / f"{len(self.downloads)}.mp4"
            path.write_bytes(b"x")
            return DownloadResult(self.result, filepath=str(path) if self.result == ItemStatus.DONE else None,
                                  message="" if self.result == ItemStatus.DONE else "greška")

        window = MainWindow(settings=self.settings, probe_fn=probe, download_fn=download,
                            thumbnail_fetch=lambda u: None, data_dir_path=self.tmp.name)
        window.set_output_dir(self.tmp.name)
        window._ask_adult = lambda items: (self.asked.append([i.url for i in items]), self.answer)[1]
        self.addCleanup(window.deleteLater)
        return window

    def add(self, window, *urls):
        before = len(window._queue.items())
        window.add_links_from_text(" ".join(urls))
        self.assertTrue(wait_until(lambda: len(window._queue.items()) >= before + len(urls)))

    def test_declined_adult_video_waits_and_others_still_download(self):
        window = self.window(adult=lambda url: url.endswith("/a"))
        self.add(window, "https://v/a", "https://v/b")
        self.answer = False
        window._start_all()
        self.assertTrue(wait_until(lambda: self.downloads == ["https://v/b"]))  # obični video ide normalno
        time.sleep(0.2)
        app.processEvents()
        self.assertEqual(self.asked, [["https://v/a"]])
        adult_item = next(i for i in window._queue.items() if i.url.endswith("/a"))
        self.assertEqual(adult_item.status, ItemStatus.WAITING)

    def test_confirmation_is_asked_for_every_download(self):
        window = self.window()
        self.add(window, "https://v/a")
        self.result = ItemStatus.FAILED
        window._start_all()
        self.assertTrue(wait_until(lambda: window._queue.items()[0].status == ItemStatus.FAILED))
        self.assertFalse(window._queue.items()[0].adult_ok)  # potvrda ne ostaje poslije preuzimanja
        self.result = ItemStatus.DONE
        window._on_row_action(window._queue.items()[0].id)  # „Pokušaj ponovo" = novo preuzimanje
        self.assertTrue(wait_until(lambda: window._queue.items()[0].status == ItemStatus.DONE))
        self.assertEqual(len(self.asked), 2)
        self.assertEqual(len(self.downloads), 2)

    def test_several_adult_videos_share_one_dialog(self):
        window = self.window()
        self.add(window, "https://v/a", "https://v/b")
        window._start_all()
        self.assertTrue(wait_until(lambda: len(self.downloads) == 2))
        self.assertEqual(len(self.asked), 1)
        self.assertEqual(len(self.asked[0]), 2)

    def test_ordinary_videos_never_ask(self):
        window = self.window(adult=False)
        self.add(window, "https://v/a")
        window._start_all()
        self.assertTrue(wait_until(lambda: self.downloads == ["https://v/a"]))
        self.assertEqual(self.asked, [])

    def test_from_browser_adult_video_starts_only_after_confirmation(self):
        window = self.window()
        self.answer = False
        window._on_probed(ProbeResult("V", (Entry("https://v/c", "C", adult=True),), False), self.tmp.name, {}, True)
        time.sleep(0.2)
        app.processEvents()
        self.assertEqual(self.downloads, [])
        self.assertEqual(len(self.asked), 1)

    def test_adult_thumbnail_is_blurred_and_marked(self):
        image = QImage(192, 108, QImage.Format.Format_RGB32)
        for x in range(192):
            for y in range(108):
                image.setPixelColor(x, y, QColor("white") if (x // 8 + y // 8) % 2 else QColor("black"))
        original = QPixmap.fromImage(image)
        blurred = adult_thumbnail(original).toImage()
        self.assertEqual(blurred.size(), image.size())
        # Oštar šah je nestao: susjedni pikseli su skoro iste boje (nekad crno/bijelo).
        corner = [blurred.pixelColor(x, 3).lightness() for x in range(0, 40, 8)]
        self.assertLess(max(corner) - min(corner), 120)

        window = self.window()
        self.add(window, "https://v/a")
        item = window._queue.items()[0]
        window._set_row_thumbnail(item.id, original)
        shown = window._rows[item.id].thumbnail._pixmap
        self.assertNotEqual(shown.cacheKey(), original.cacheKey())


if __name__ == "__main__":
    unittest.main()
