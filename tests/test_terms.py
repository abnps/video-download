"""Uslovi korištenja: isti tekst u instaleru i u aplikaciji, na svih 5 jezika."""

import os
import re
import tempfile
import unittest
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QSettings  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

from videodl.gui import MainWindow, TermsDialog, terms_text  # noqa: E402
from videodl.i18n import LANGUAGES, set_language  # noqa: E402
from videodl.updater import INSTALLER_LANGUAGES  # noqa: E402

app = QApplication.instance() or QApplication([])
PROJECT = Path(__file__).resolve().parent.parent
ASSETS = PROJECT / "videodl" / "assets"

# Ključne tvrdnje koje svaki prevod mora imati: vlastiti videi, DRM, bez veze sa YouTube-om.
KEY_PHRASES = {
    "bs": ("vlastitih videa", "DRM", "nije povezan sa YouTube-om"),
    "en": ("your own videos", "DRM", "not affiliated with"),
    "de": ("deiner eigenen Videos", "DRM", "nicht mit YouTube"),
    "es": ("tus propios vídeos", "DRM", "no está afiliado a YouTube"),
    "fr": ("tes propres vidéos", "DRM", "n'est pas affilié à YouTube"),
}


class TermsFilesTest(unittest.TestCase):
    def test_every_language_has_terms_with_bom_and_key_points(self):
        for language in LANGUAGES:
            with self.subTest(language=language):
                raw = (ASSETS / f"terms_{language}.txt").read_bytes()
                self.assertTrue(raw.startswith(b"\xef\xbb\xbf"), "Inno Setup treba BOM za UTF-8")
                text = raw.decode("utf-8-sig")
                for phrase in KEY_PHRASES[language]:
                    self.assertIn(phrase, text)
                # Isti broj odjeljaka u svakom prevodu (1.–7.)
                self.assertEqual(len(re.findall(r"(?m)^[1-7]\. ", text)), 7)

    def test_installer_shows_terms_in_its_language(self):
        script = (PROJECT / "installer" / "VideoDownload.iss").read_text(encoding="utf-8-sig")
        for language, inno_name in INSTALLER_LANGUAGES.items():
            with self.subTest(language=language):
                self.assertRegex(script, rf'Name: "{inno_name}";.*LicenseFile: "\.\.\\videodl\\assets\\terms_{language}\.txt"')


class TermsDialogTest(unittest.TestCase):
    def tearDown(self):
        set_language("bs")

    def test_help_menu_shows_terms_in_app_language(self):
        with tempfile.TemporaryDirectory() as tmp:
            settings = QSettings(os.path.join(tmp, "s.ini"), QSettings.Format.IniFormat)
            settings.setValue("language", "de")
            window = MainWindow(settings=settings, probe_fn=None, download_fn=None, thumbnail_fetch=lambda u: None,
                                data_dir_path=tmp)
            self.addCleanup(window.deleteLater)
            self.assertEqual(window.terms_action.text(), "Nutzungsbedingungen…")
            self.assertIn(window.terms_action, window.help_menu.actions())
            dialog = TermsDialog(window)
            self.addCleanup(dialog.deleteLater)
            self.assertIn("NUTZUNGSBEDINGUNGEN", dialog.browser.toPlainText())

    def test_unknown_language_falls_back_to_english(self):
        self.assertIn("TERMS OF USE", terms_text("xx"))


if __name__ == "__main__":
    unittest.main()
