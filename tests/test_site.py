"""Zvanični sajt (site/, engleski glavni, ostali jezici u site/<jezik>/): usklađen s aplikacijom, bez zabranjenih
izraza i pokvarenih linkova."""

import posixpath
import re
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))

import build_site  # noqa: E402

from videodl import __version__, changelog  # noqa: E402

PAGES = ("index.html", "terms.html", "privacy.html", "licenses.html", "extension.html")


class SiteTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.pages = build_site.build()

    def test_every_language_has_every_page(self):
        expected = {build_site.TEXTS[lang]["dir"] + page for lang in build_site.LANGUAGES for page in PAGES}
        self.assertEqual(set(self.pages), expected)
        self.assertEqual(build_site.LANGUAGES[0], "en")  # engleski je glavni jezik (korijen sajta)

    def test_site_is_up_to_date(self):
        # Poslije izmjene changeloga, pravnih tekstova ili verzije: python tools/build_site.py
        for name, text in self.pages.items():
            with self.subTest(page=name):
                self.assertEqual((build_site.SITE / name).read_text(encoding="utf-8"), text,
                                 f"site/{name} nije ažuran — pokreni python tools/build_site.py")

    def test_front_pages_show_current_version_news_and_smartscreen_help(self):
        for lang, label, more_info, run_anyway in (("en", "Version", "More info", "Run anyway"),
                                                   ("bs", "Verzija", "Više informacija", "Ipak pokreni"),
                                                   ("de", "Version", "Weitere Informationen", "Trotzdem ausführen"),
                                                   ("es", "Versión", "Más información", "Ejecutar de todas formas"),
                                                   ("fr", "Version", "Informations complémentaires", "Exécuter quand même")):
            index = self.pages[build_site.TEXTS[lang]["dir"] + "index.html"]
            with self.subTest(lang=lang):
                self.assertIn(f"<html lang=\"{lang}\">", index)
                self.assertIn(f"{label} {__version__} ·", index)
                for version, _date, items in changelog.entries(lang)[:build_site.NEWS_COUNT]:
                    self.assertIn(f"<h3>{version} <span>", index)
                    self.assertIn(items[0].replace('"', "&quot;")[:30].split("&")[0], index)
                self.assertIn(build_site.INSTALLER_URL, index)
                self.assertIn(more_info, index)
                self.assertIn(run_anyway, index)
                self.assertIn(f"screenshot-light-{lang}.png", index)
                # prekidač jezika i hreflang vode na sve jezike
                for other in build_site.LANGUAGES:
                    self.assertIn(f'hreflang="{other}"', index)
                    self.assertIn(f">{other.upper()}</a>", index)

    def test_no_forbidden_words_on_promo_pages(self):
        self.assertEqual(build_site.forbidden_words(self.pages), [])
        self.assertTrue(build_site.forbidden_words({"index.html": "<p>Preuzmi sa YouTube-a</p>"}))
        self.assertTrue(build_site.forbidden_words({"bs/extension.html": "<p>bypass protection</p>"}))
        self.assertTrue(build_site.forbidden_words({"de/index.html": "<p>Schutz umgehen</p>"}))
        self.assertTrue(build_site.forbidden_words({"fr/index.html": "<p>contourner la protection</p>"}))
        self.assertFalse(build_site.forbidden_words({"index.html": "<p>the site reader yt-dlp</p>"}))

    def test_legal_pages_carry_the_same_text_as_the_app(self):
        self.assertIn("vlastitih videa", self.pages["bs/terms.html"])
        self.assertIn("TERMS OF USE".title().split()[0], self.pages["terms.html"])
        self.assertEqual(set(build_site.LANGUAGES), {"en", "bs", "de", "es", "fr"})  # isti jezici kao u programu
        for prefix in (build_site.TEXTS[lang]["dir"] for lang in build_site.LANGUAGES):
            self.assertIn("GitHub Pages", self.pages[prefix + "privacy.html"])
            self.assertIn("GPL-3.0", self.pages[prefix + "licenses.html"])

    def test_local_links_and_images_exist(self):
        for name, text in self.pages.items():
            folder = posixpath.dirname(name)
            for target in re.findall(r'(?:href|src|srcset)="([^"#:]+)(?:#[^"]*)?"', text):
                path = posixpath.normpath(posixpath.join(folder, target))
                with self.subTest(page=name, target=target):
                    self.assertTrue((build_site.SITE / path).is_file(), path)

    def test_text_conversion(self):
        title, body = build_site.text_to_html("﻿NASLOV\n\nUvod.\n\n1. Prvo\n- a\n  nastavak\n- b\n\nVidi https://x.test/a.")
        self.assertEqual(title, "NASLOV")
        self.assertIn("<h2>1. Prvo</h2>", body)
        self.assertIn("<li>a nastavak</li>", body)
        self.assertIn('<a href="https://x.test/a">https://x.test/a</a>.', body)


if __name__ == "__main__":
    unittest.main()
