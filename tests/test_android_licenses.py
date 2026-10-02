"""Android (Postavke → Licence): svaka komponenta iz APK-a ima tekst licence u assets/licenses."""

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from videodl import legal  # noqa: E402

LICENSES = ROOT / "android" / "app" / "src" / "main" / "assets" / "licenses"


class AndroidLicensesTest(unittest.TestCase):
    def test_every_component_has_its_license_text(self):
        for component in legal.ANDROID_COMPONENTS:
            for name in component.license_files:
                with self.subTest(component=component.name, file=name):
                    self.assertGreater((LICENSES / name).stat().st_size, 200)

    def test_notices_match_component_list(self):
        # Ako ovo padne: python tools/android_licenses.py
        self.assertEqual((LICENSES / "NOTICES.txt").read_text(encoding="utf-8"), legal.android_notices_text())

    def test_known_texts(self):
        self.assertIn("Apache License", (LICENSES / "Apache-2.0.txt").read_text(encoding="utf-8"))
        self.assertIn("Chaquo Ltd", (LICENSES / "Chaquopy-LICENSE.txt").read_text(encoding="utf-8"))
        self.assertIn("unlicense", (LICENSES / "yt-dlp-LICENSE").read_text(encoding="utf-8").lower())
        python = (LICENSES / "Python-LICENSE.txt").read_text(encoding="utf-8")
        self.assertIn("PYTHON SOFTWARE FOUNDATION LICENSE", python)
        for bundled in ("bzip2", "libffi"):
            self.assertIn(bundled, python)


if __name__ == "__main__":
    unittest.main()
