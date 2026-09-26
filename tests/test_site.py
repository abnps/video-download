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
        expected.add("sitemap.xml")
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
                # Mac (beta): stalni link na .dmg, jasna oznaka i uputstvo za prvo pokretanje
                self.assertIn(build_site.MAC_DMG_URL, index)
                self.assertIn(f'<span class="badge">{build_site.MAC_TEXT[lang][0]}</span>', index)
                for step in build_site.MAC_TEXT[lang][4]:
                    self.assertIn(step, index)
                # Redizajn: namjena i uslovi ostaju vidljivi, demo nosi nazive iz programa, animacije iz site.js
                self.assertIn('<p class="note">', index)
                self.assertIn('href="terms.html"', index)
                self.assertIn("window.VD_TEXT", index)
                self.assertIn(build_site.site_home.app_labels(lang)["paste"], index)
                self.assertIn("assets/site.js", index)
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

    def test_contact_email_on_every_page_and_no_personal_email(self):
        for name, text in self.pages.items():
            if not name.endswith(".html"):
                continue
            with self.subTest(page=name):
                self.assertIn(f'href="mailto:{build_site.CONTACT_EMAIL}"', text)
                self.assertNotIn("bisevac", text.lower())  # lični e-mail nikad na sajtu
        for lang in build_site.LANGUAGES:
            self.assertIn(build_site.CONTACT_EMAIL, self.pages[build_site.TEXTS[lang]["dir"] + "privacy.html"])

    def test_no_third_party_code_and_motion_can_be_turned_off(self):
        # Privatnost: bez tuđih skripti, fontova i stilova; pristupačnost: animacije se gase na zahtjev sistema.
        css = (build_site.SITE / "assets" / "site.css").read_text(encoding="utf-8")
        js = (build_site.SITE / "assets" / "site.js").read_text(encoding="utf-8")
        self.assertIn("prefers-reduced-motion", css)
        self.assertIn("prefers-reduced-motion", js)
        self.assertNotRegex(css + js, r"https?://|@import|fetch\(|XMLHttpRequest|localStorage|document\.cookie")
        for name, text in self.pages.items():
            with self.subTest(page=name):
                self.assertNotRegex(text, r'<script[^>]+src="https?:|<link[^>]+href="https?:[^"]*"[^>]*stylesheet'
                                          r'|<link[^>]+stylesheet[^>]+href="https?:')

    def test_menu_anchors_point_to_existing_sections(self):
        for name, text in self.pages.items():
            index = self.pages[posixpath.join(posixpath.dirname(name), "index.html").lstrip("/")]
            ids = set(re.findall(r'id="([a-z-]+)"', index))
            for anchor in re.findall(r'href="(?:index\.html)?#([a-z-]+)"', text):
                with self.subTest(page=name, anchor=anchor):
                    self.assertIn(anchor, ids)

    def test_search_engines_get_sitemap_canonical_urls_and_app_description(self):
        import json

        sitemap = self.pages["sitemap.xml"]
        self.assertEqual(sitemap.count("<url>"), len(build_site.LANGUAGES) * len(PAGES))
        self.assertIn('hreflang="x-default"', sitemap)
        for name, text in self.pages.items():
            if not name.endswith(".html"):
                continue
            with self.subTest(page=name):
                canonical = re.search(r'<link rel="canonical" href="([^"]+)">', text).group(1)
                self.assertTrue(canonical.startswith(build_site.PUBLIC_URL))
                self.assertIn(f"<loc>{canonical}</loc>", sitemap)  # svaka stranica je u mapi sajta
                self.assertIn('property="og:image"', text)
                for href in re.findall(r'hreflang="[^"]+" href="([^"]+)"', text):
                    self.assertTrue(href.startswith("https://"))  # Google traži pune adrese
        for lang in build_site.LANGUAGES:
            home = self.pages[build_site.TEXTS[lang]["dir"] + "index.html"]
            data = json.loads(re.search(r'<script type="application/ld\+json">(.*?)</script>', home, re.S).group(1))
            self.assertEqual(data["@type"], "SoftwareApplication")
            self.assertEqual(data["softwareVersion"], __version__)
            self.assertEqual(data["offers"]["price"], "0")

    def test_share_button_uses_plain_links_only(self):
        for lang in build_site.LANGUAGES:
            home = self.pages[build_site.TEXTS[lang]["dir"] + "index.html"]
            with self.subTest(lang=lang):
                self.assertIn('class="share"', home)
                self.assertIn("https://wa.me/?text=", home)
                self.assertIn("data-copy", home)
                self.assertNotIn("<iframe", home)  # nikakvi „widgeti" društvenih mreža

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
