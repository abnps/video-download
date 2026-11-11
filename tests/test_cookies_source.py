"""Faza 3 (Ahmed 29.10.2026): kolačići za prijavu iz browsera ili cookies.txt, i poglavlja kao posebni fajlovi."""

import os
import tempfile
import time
import unittest
from pathlib import Path
from unittest import mock

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QSettings  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

from videodl import download as download_module, probe as probe_module  # noqa: E402
from videodl.browser import COOKIE_BROWSERS, Cookie, cookie_options, is_cookie_read_error  # noqa: E402
from videodl.download import DownloadResult  # noqa: E402
from videodl.jobs import ItemStatus  # noqa: E402
from videodl.gui import MainWindow  # noqa: E402
from videodl.i18n import get_language, set_language  # noqa: E402
from videodl.presets import build_ydl_options, get_preset  # noqa: E402
from videodl.probe import Entry, ProbeResult  # noqa: E402
from videodl.widgets import friendly_error  # noqa: E402

app = QApplication.instance() or QApplication([])


class CookieOptionsTest(unittest.TestCase):
    def test_extension_cookies_win_then_browser_then_file(self):
        cookie = Cookie(".v.test", "SID", "tajna", "/", True, 0, False)
        with tempfile.TemporaryDirectory() as tmp:
            txt = Path(tmp) / "cookies.txt"
            txt.write_text("# Netscape HTTP Cookie File\n", encoding="utf-8")
            with cookie_options((cookie,), "firefox", str(txt)) as opts:
                self.assertEqual(set(opts), {"cookiefile"})
                self.assertNotEqual(opts["cookiefile"], str(txt))
            with cookie_options((), "firefox", str(txt)) as opts:
                self.assertEqual(opts, {"cookiesfrombrowser": ("firefox",)})
            with cookie_options((), "", str(txt)) as opts:
                copy = opts["cookiefile"]
                self.assertNotEqual(copy, str(txt))  # yt-dlp piše u kopiju, nikad u korisnikov fajl
                Path(copy).write_text("prepisano", encoding="utf-8")
            self.assertFalse(os.path.exists(copy))
            self.assertEqual(txt.read_text(encoding="utf-8"), "# Netscape HTTP Cookie File\n")
            with cookie_options((), "nepoznat", str(Path(tmp) / "nema.txt")) as opts:
                self.assertEqual(opts, {})

    def test_supported_browsers(self):
        self.assertEqual(COOKIE_BROWSERS, ("firefox", "edge", "chrome", "brave"))

    def test_unreadable_browser_cookies_get_a_clear_message(self):
        language = get_language()
        self.addCleanup(set_language, language)
        set_language("bs")
        for message in ("ERROR: Failed to decrypt with DPAPI", "Could not copy Chrome cookie database",
                        "failed to load cookies"):
            with self.subTest(message=message):
                self.assertIn("Firefox", friendly_error(message) or "")


class FakeYdl:
    """yt-dlp zamjena: s kolačićima iz browsera pada kao Edge koji radi; bez njih pročita javni video."""

    calls: list = []

    def __init__(self, opts):
        self.opts = opts
        FakeYdl.calls.append(dict(opts))

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def extract_info(self, url, download=False):
        if "cookiesfrombrowser" in self.opts:
            raise RuntimeError("ERROR: Could not copy Chrome cookie database. See "
                               "https://github.com/yt-dlp/yt-dlp/issues/7271 for more info")
        return {"id": "2128", "title": "Javni video", "duration": 12.0, "formats": [{"url": url, "vcodec": "h264"}],
                "webpage_url": url}


class CookieFallbackTest(unittest.TestCase):
    """Ahmed 10.11.2026: u Postavkama izabran Edge, Edge radi, pa javni video sa x.com nije mogao ni da se pročita.
    Prijava je dodatak: kad kolačići ne mogu da se pročitaju, link se čita (i preuzima) bez njih."""

    def setUp(self):
        FakeYdl.calls = []
        patcher = mock.patch.object(probe_module, "_ydl", return_value=FakeYdl)
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_recognizes_cookie_read_errors_only(self):
        for message in ("Could not copy Chrome cookie database", "ERROR: Failed to decrypt with DPAPI",
                        "could not find firefox cookies database in 'C:/Profiles'", "app-bound encryption"):
            self.assertTrue(is_cookie_read_error(message), message)
        for message in ("HTTP Error 403: Forbidden", "Sign in to confirm you're not a bot", ""):
            self.assertFalse(is_cookie_read_error(message), message)

    def test_reading_falls_back_to_no_cookies_and_says_so(self):
        result = probe_module.probe("https://x.com/a/status/2128/video/1", cookie_browser="edge")
        self.assertEqual(result.entries[0].title, "Javni video")
        self.assertTrue(result.cookie_warning)
        self.assertIn("cookiesfrombrowser", FakeYdl.calls[0])
        self.assertNotIn("cookiesfrombrowser", FakeYdl.calls[1])

    def test_no_fallback_without_a_chosen_source_or_with_extension_cookies(self):
        result = probe_module.probe("https://x.com/a/status/2128/video/1")
        self.assertFalse(result.cookie_warning)
        self.assertEqual(len(FakeYdl.calls), 1)
        # Kolačići iz dodatka imaju prednost i ne daju ovu grešku; nema drugog pokušaja.
        cookie = Cookie(".x.com", "auth", "tajna", "/", True, 0, False)
        result = probe_module.probe("https://x.com/a/status/2128/video/1", cookies=(cookie,), cookie_browser="edge")
        self.assertFalse(result.cookie_warning)

    def test_downloading_falls_back_to_no_cookies(self):
        attempts = []
        real = download_module.download

        def fake_ydl(opts):
            attempts.append("cookiesfrombrowser" in opts)
            if "cookiesfrombrowser" in opts:
                raise RuntimeError("ERROR: Failed to decrypt with DPAPI")
            raise RuntimeError("ERROR: stigao do preuzimanja bez kolačića")

        with mock.patch.object(download_module, "_load"),                 mock.patch.object(download_module, "YoutubeDL", side_effect=fake_ydl),                 mock.patch.object(download_module, "DownloadCancelled", type("Cancelled", (Exception,), {})),                 mock.patch.object(download_module, "_parts_recorder", return_value=lambda f: f),                 tempfile.TemporaryDirectory() as tmp:
            result = real("https://x.com/a/status/2128/video/1", get_preset("best"), tmp, None, None, None,
                          cookie_browser="chrome")
        self.assertEqual(attempts, [True, False])  # drugi pokušaj bez kolačića iz browsera
        self.assertEqual(result.status, ItemStatus.FAILED)
        self.assertIn("bez kolačića", result.message)
        self.assertTrue(result.cookie_warning)


class SplitChaptersTest(unittest.TestCase):
    def test_chapters_go_to_a_folder_named_after_the_video(self):
        opts = build_ydl_options(get_preset("mp3"), os.path.join("C:", "P"), "Lista", split_chapters=True)
        self.assertEqual(opts["postprocessors"][-1], {"key": "FFmpegSplitChapters", "force_keyframes": False})
        self.assertTrue(opts["outtmpl"]["default"].endswith(".%(ext)s"))
        self.assertIn(os.sep.join(("Lista", "%(title).100B", "%(section_number)02d - ")), opts["outtmpl"]["chapter"])
        # Audio radi u privremenom folderu: dijelovi idu u pravi.
        audio = build_ydl_options(get_preset("mp3"), "tmp-posao", split_chapters=True, split_dir="pravi")
        self.assertTrue(audio["outtmpl"]["chapter"].startswith("pravi" + os.sep))

    def test_no_split_for_clips_and_car_formats(self):
        for preset, section in ((get_preset("best"), (1.0, 5.0)), (get_preset("car"), None)):
            opts = build_ydl_options(preset, "P", split_chapters=True, section=section)
            self.assertIsInstance(opts["outtmpl"], str)
            self.assertNotIn("FFmpegSplitChapters", [pp["key"] for pp in opts.get("postprocessors", [])])


class WindowCookieSourceTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.settings = QSettings(os.path.join(self.tmp.name, "s.ini"), QSettings.Format.IniFormat)
        self.settings.setValue("language", "bs")
        self.probed, self.extras = [], []

    def tearDown(self):
        app.processEvents()
        self.tmp.cleanup()

    def window(self):
        def probe(url, **options):
            self.probed.append(options)
            return ProbeResult("V", (Entry(url, "V"),), False)

        window = MainWindow(settings=self.settings, probe_fn=probe, download_fn=lambda *a, **k: None,
                            data_dir_path=Path(self.tmp.name))
        self.addCleanup(window.close)
        return window

    def test_window_tells_once_that_it_downloads_without_signing_in(self):
        window = self.window()
        window.set_cookie_source("edge")
        window._on_probed(ProbeResult("V", (Entry("https://x.test/1", "V"),), False, cookie_warning=True), self.tmp.name,
                          {}, False)
        app.processEvents()
        self.assertIn("Microsoft Edge", window.status_label.text())
        self.assertIn("bez prijave", window.status_label.text())
        window._set_status("")
        window._on_probed(ProbeResult("W", (Entry("https://x.test/2", "W"),), False, cookie_warning=True), self.tmp.name,
                          {}, False)
        app.processEvents()
        self.assertNotIn("bez prijave", window.status_label.text())  # jednom po pokretanju
        window.set_cookie_source("chrome")  # drugi izvor: ako ni on ne radi, poruka opet
        window._on_download_finished(window._queue.items()[0].id, DownloadResult(ItemStatus.DONE, cookie_warning=True))
        app.processEvents()
        self.assertIn("Google Chrome", window.status_label.text())

    def test_chosen_source_reaches_reading_and_downloading_and_is_remembered(self):
        window = self.window()
        window.set_cookie_source("firefox")
        window.add_links_from_text("https://v.test/a")
        deadline = time.monotonic() + 10
        while not window._queue.items() and time.monotonic() < deadline:
            app.processEvents()
        self.assertEqual(self.probed[-1].get("cookie_browser"), "firefox")
        item = window._queue.items()[0]
        self.assertEqual(window._download_options(item)["cookie_browser"], "firefox")
        window.set_cookie_source("", os.path.join(self.tmp.name, "cookies.txt"))
        options = window._download_options(item)
        self.assertNotIn("cookie_browser", options)
        self.assertTrue(options["cookie_txt"].endswith("cookies.txt"))
        self.assertEqual(self.settings.value("cookie_browser"), "")
        window.set_cookie_source("")
        self.assertNotIn("cookie_txt", window._download_options(item))


if __name__ == "__main__":
    unittest.main()
