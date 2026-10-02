"""Impressum (§ 5 DDG): nastaje tek s podacima; tada je na svim jezicima, u podnožju i bez ličnog e-maila."""

import re
import sys
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

import build_site  # noqa: E402
import site_impressum  # noqa: E402

SAMPLE = {"name": "Proba Probić", "street": "Probna 1", "city": "12345 Probgrad", "country": "Deutschland",
          "phone": "+49 000 000"}


class ImpressumTest(unittest.TestCase):
    def test_no_page_without_data(self):
        with mock.patch.object(site_impressum, "DATA", None):
            pages = build_site.build()
        self.assertFalse(any(name.endswith(site_impressum.PAGE) for name in pages))
        self.assertNotIn(site_impressum.PAGE, pages["index.html"])

    def test_page_on_every_language_with_public_email_only(self):
        with mock.patch.object(site_impressum, "DATA", SAMPLE):
            pages = build_site.build()
        for lang in build_site.LANGUAGES:
            prefix = build_site.TEXTS[lang]["dir"]
            with self.subTest(lang=lang):
                page = pages[f"{prefix}{site_impressum.PAGE}"]
                self.assertIn("Angaben gemäß § 5 DDG", page)
                self.assertIn("Probna 1", page)
                self.assertIn(build_site.CONTACT_EMAIL, page)
                self.assertEqual(set(re.findall(r"[\w.+-]+@[\w-]+\.[\w.]+", page)), {build_site.CONTACT_EMAIL})
                self.assertIn(f'href="{site_impressum.PAGE}"', pages[f"{prefix}terms.html"])


if __name__ == "__main__":
    unittest.main()
