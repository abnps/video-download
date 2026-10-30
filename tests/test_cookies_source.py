"""Faza 3 (Ahmed 29.10.2026): kolačići za prijavu iz browsera ili cookies.txt, i poglavlja kao posebni fajlovi."""

import os
import tempfile
import time
import unittest
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QSettings  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

from videodl.browser import COOKIE_BROWSERS, Cookie, cookie_options  # noqa: E402
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
