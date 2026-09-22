"""Izvještaj o problemu: šta sadrži i šta nikad ne smije sadržavati."""

import getpass
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from videodl import __version__, diagnostics


class RedactTest(unittest.TestCase):
    def test_links_become_site_names(self):
        text = "Greška na https://www.instagram.com/stories/korisnik/123456/?igsh=Tajna"
        self.assertEqual(diagnostics.redact(text), "Greška na <www.instagram.com>")

    def test_secrets_and_user_name_are_hidden(self):
        clean = diagnostics.redact("Cookie: sessionid=ABC123; token=XYZ")
        self.assertNotIn("ABC123", clean)
        self.assertNotIn("XYZ", clean)
        user = getpass.getuser()
        self.assertNotIn(user, diagnostics.redact(rf"C:\Users\{user}\Videos\film.mp4"))


class ReportTest(unittest.TestCase):
    def test_report_has_versions_tools_and_errors(self):
        errors = ["HTTP Error 403 na https://x.com/a/status/1", "Unsupported URL: https://neki.sajt/abc"]
        report = diagnostics.build_report(errors, {"jezik": "bs", "istovremeno": 2}, now=0)
        self.assertIn(f"Aplikacija: {__version__}", report)
        self.assertIn("yt-dlp:", report)
        self.assertIn("ffmpeg:", report)
        self.assertIn("jezik: bs", report)
        self.assertIn("<x.com>", report)
        self.assertNotIn("https://", report)

    def test_only_the_last_errors_are_included(self):
        report = diagnostics.build_report([f"greška {index}" for index in range(100)])
        self.assertIn("greška 99", report)
        self.assertNotIn("greška 79", report)
        self.assertIn(f"Posljednje greške ({diagnostics.MAX_ERRORS})", report)

    def test_report_without_errors_says_so(self):
        self.assertIn("(nema ih)", diagnostics.build_report())

    def test_default_path_falls_back_when_there_is_no_desktop(self):
        with tempfile.TemporaryDirectory() as tmp:
            with mock.patch.object(Path, "home", return_value=Path(tmp)):
                path = diagnostics.default_report_path(tmp)
            self.assertEqual(path.parent, Path(tmp))
            self.assertTrue(path.name.startswith("VideoDownload-izvjestaj-"))
            self.assertTrue(path.name.endswith(".txt"))


if __name__ == "__main__":
    unittest.main()
