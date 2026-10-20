"""Android „Šta je novo" koristi iste bilješke kao računar (tools/android_changelog.py)."""

import importlib.util
import json
import unittest
from pathlib import Path

PROJECT = Path(__file__).resolve().parent.parent
spec = importlib.util.spec_from_file_location("android_changelog", PROJECT / "tools" / "android_changelog.py")
android_changelog = importlib.util.module_from_spec(spec)
spec.loader.exec_module(android_changelog)


class AndroidChangelogTest(unittest.TestCase):
    def test_asset_is_up_to_date(self):
        # Poslije izmjene videodl/changelog.py: python tools/android_changelog.py
        self.assertEqual(android_changelog.TARGET.read_text(encoding="utf-8"), android_changelog.build())

    def test_latest_versions_in_all_languages(self):
        data = json.loads(android_changelog.build())
        self.assertGreaterEqual(len(data), 3)
        for entry in data[:3]:
            self.assertEqual(set(entry["notes"]), {"bs", "en", "de", "es", "fr"})


if __name__ == "__main__":
    unittest.main()
