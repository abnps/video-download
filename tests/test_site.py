"""Zvanični sajt (site/): usklađen s aplikacijom, bez zabranjenih izraza, bez pokvarenih linkova."""

import re
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))

import build_site  # noqa: E402

from videodl import __version__, changelog  # noqa: E402


class SiteTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.pages = build_site.build()

    def test_site_is_up_to_date(self):
        # Poslije izmjene changeloga, pravnih tekstova ili verzije: python tools/build_site.py
        for name, text in self.pages.items():
            with self.subTest(page=name):
                self.assertEqual((build_site.SITE / name).read_text(encoding="utf-8"), text,
                                 f"site/{name} nije ažuran — pokreni python tools/build_site.py")

    def test_front_page_shows_current_version_and_news(self):
        index = self.pages["index.html"]
        self.assertIn(f"Verzija {__version__} ·", index)
        for version, _date, _items in changelog.entries("bs")[:build_site.NEWS_COUNT]:
            self.assertIn(f"<h3>{version} <span>", index)
        self.assertIn(build_site.INSTALLER_URL, index)

    def test_no_forbidden_words_on_promo_pages(self):
        self.assertEqual(build_site.forbidden_words(self.pages), [])
        self.assertTrue(build_site.forbidden_words({"index.html": "<p>Preuzmi sa YouTube-a</p>"}))
        self.assertFalse(build_site.forbidden_words({"index.html": "<p>čitač sajtova yt-dlp</p>"}))

    def test_legal_pages_carry_the_same_text_as_the_app(self):
        terms = build_site._asset_text("terms")
        self.assertIn("vlastitih videa", self.pages["uslovi.html"])
        self.assertIn("GitHub Pages", self.pages["privatnost.html"])
        self.assertIn("GPL-3.0", self.pages["licence.html"])
        self.assertTrue(terms)

    def test_local_links_and_images_exist(self):
        for name, text in self.pages.items():
            for target in re.findall(r'(?:href|src|srcset)="([^"#:]+)(?:#[^"]*)?"', text):
                with self.subTest(page=name, target=target):
                    self.assertTrue((build_site.SITE / target).is_file(), target)

    def test_text_conversion(self):
        title, body = build_site.text_to_html("﻿NASLOV\n\nUvod.\n\n1. Prvo\n- a\n  nastavak\n- b\n\nVidi https://x.test/a.")
        self.assertEqual(title, "NASLOV")
        self.assertIn("<h2>1. Prvo</h2>", body)
        self.assertIn("<li>a nastavak</li>", body)
        self.assertIn('<a href="https://x.test/a">https://x.test/a</a>.', body)


if __name__ == "__main__":
    unittest.main()
