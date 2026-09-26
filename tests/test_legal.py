"""Pravni dokumenti: licencni ugovor, uslovi korištenja i privatnost na 5 jezika, isti u instaleru
i u aplikaciji, plus spisak komponenti sa punim tekstovima licenci."""

import os
import re
import tempfile
import unittest
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QSettings  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

from videodl import legal  # noqa: E402
from videodl.gui import LegalDialog, MainWindow  # noqa: E402
from videodl.i18n import LANGUAGES, set_language  # noqa: E402
from videodl.updater import INSTALLER_LANGUAGES  # noqa: E402

app = QApplication.instance() or QApplication([])
PROJECT = Path(__file__).resolve().parent.parent
SCRIPT = (PROJECT / "installer" / "VideoDownload.iss").read_text(encoding="utf-8-sig")

# Ključne tvrdnje koje svaki prevod mora sadržati.
KEY_PHRASES = {
    "terms": {"bs": ("vlastitih videa", "DRM", "nije povezan sa YouTube-om"),
              "en": ("your own videos", "DRM", "not affiliated with"),
              "de": ("deiner eigenen Videos", "DRM", "nicht mit YouTube"),
              "es": ("tus propios vídeos", "DRM", "no está afiliado a YouTube"),
              "fr": ("tes propres vidéos", "DRM", "n'est pas affilié à YouTube")},
    "eula": {"bs": ("besplatnu", "kakav jeste", "licenses"),
             "en": ("free", "as is", "licenses"),
             "de": ("kostenlose", "wie besehen", "licenses"),
             "es": ("gratuita", "tal cual", "licenses"),
             "fr": ("gratuite", "en l'état", "licenses")},
    "privacy": {"bs": ("ne prikuplja", "api.github.com", "pypi.org", "%LOCALAPPDATA%\\VideoDownload"),
                "en": ("does not collect", "api.github.com", "pypi.org", "%LOCALAPPDATA%\\VideoDownload"),
                "de": ("erhebt keine", "api.github.com", "pypi.org", "%LOCALAPPDATA%\\VideoDownload"),
                "es": ("no recopila", "api.github.com", "pypi.org", "%LOCALAPPDATA%\\VideoDownload"),
                "fr": ("ne collecte aucune", "api.github.com", "pypi.org", "%LOCALAPPDATA%\\VideoDownload")},
}


class DocumentsTest(unittest.TestCase):
    def test_every_document_exists_in_every_language_with_bom_and_key_points(self):
        for kind, _key in legal.DOCUMENTS:
            counts = set()
            for language in LANGUAGES:
                with self.subTest(kind=kind, language=language):
                    raw = legal.document_path(kind, language).read_bytes()
                    self.assertTrue(legal.document_path(kind, language).name.endswith(f"_{language}.txt"))
                    self.assertTrue(raw.startswith(b"\xef\xbb\xbf"), "Inno Setup treba BOM za UTF-8")
                    text = raw.decode("utf-8-sig")
                    for phrase in KEY_PHRASES[kind][language]:
                        self.assertIn(phrase, text)
                    counts.add(len(re.findall(r"(?m)^\d\. ", text)))
            self.assertEqual(len(counts), 1, f"{kind}: prevodi nemaju isti broj tačaka {counts}")

    def test_agreement_page_is_eula_followed_by_terms(self):
        text = legal.agreement_text("de")
        self.assertLess(text.index("LIZENZVERTRAG"), text.index("NUTZUNGSBEDINGUNGEN"))
        self.assertIn("TERMS OF USE", legal.document_text("terms", "xx"))  # nepoznat jezik → engleski


class InstallerTest(unittest.TestCase):
    def test_installer_shows_agreement_and_privacy_in_its_language(self):
        for language, inno_name in INSTALLER_LANGUAGES.items():
            with self.subTest(language=language):
                self.assertRegex(SCRIPT, rf'Name: "{inno_name}";.*LicenseFile: "\{{#SourceDir\}}\\legal\\agreement_{language}\.txt"')
                self.assertRegex(SCRIPT, rf'Name: "{inno_name}";.*InfoBeforeFile: "\{{#SourceDir\}}\\legal\\privacy_{language}\.txt"')

    def test_uninstall_removes_downloaded_yt_dlp_but_not_user_data(self):
        section = SCRIPT[SCRIPT.index("[UninstallDelete]"):SCRIPT.index("[Run]")]
        self.assertIn(r"{localappdata}\VideoDownload\yt-dlp", section)
        self.assertNotIn("history.json", section)
        self.assertNotIn("queue.json", section)


class ComponentsTest(unittest.TestCase):
    def test_static_license_texts_are_in_the_repo(self):
        folder = PROJECT / "installer" / "licenses"
        self.assertIn("GNU GENERAL PUBLIC LICENSE", (folder / "GPL-3.0.txt").read_text(encoding="utf-8"))
        self.assertIn("GNU LESSER GENERAL PUBLIC LICENSE", (folder / "LGPL-3.0.txt").read_text(encoding="utf-8"))
        self.assertIn("Node.js", (folder / "Node.js-LICENSE.txt").read_text(encoding="utf-8"))

    def test_notices_name_every_component_and_real_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp)
            for name in ("GPL-3.0.txt", "LGPL-3.0.txt", "yt-dlp-LICENSE", "requests-LICENSE", "requests-NOTICE"):
                (folder / name).write_text("x", encoding="utf-8")
            text = legal.notices_text(folder)
        for component in legal.COMPONENTS:
            self.assertIn(component.name, text)
        self.assertIn("licenses/requests-LICENSE, licenses/requests-NOTICE", text)
        # GPL: gdje je izvorni kod ffmpeg-a (build zavisi od sistema: gyan.dev ili Martin Riedl)
        self.assertIn("https://ffmpeg.org/releases/ffmpeg-9.0.2.tar.xz", text)
        self.assertIn(legal.FFMPEG.name, text)

    def test_python_license_is_available_for_the_build(self):
        self.assertTrue(legal.python_license_path().is_file())


class LegalDialogTest(unittest.TestCase):
    def tearDown(self):
        set_language("bs")

    def test_help_menu_shows_all_documents_in_app_language(self):
        with tempfile.TemporaryDirectory() as tmp:
            settings = QSettings(os.path.join(tmp, "s.ini"), QSettings.Format.IniFormat)
            settings.setValue("language", "de")
            window = MainWindow(settings=settings, probe_fn=None, download_fn=None, thumbnail_fetch=lambda u: None,
                                data_dir_path=tmp)
            self.addCleanup(window.deleteLater)
            self.assertEqual(window.legal_action.text(), "Verträge und Lizenzen…")
            self.assertIn(window.legal_action, window.help_menu.actions())
            dialog = LegalDialog(window)
            self.addCleanup(dialog.deleteLater)
            titles = [dialog.tabs.tabText(index) for index in range(dialog.tabs.count())]
            self.assertEqual(titles, ["Lizenzvertrag", "Nutzungsbedingungen", "Datenschutz", "Komponenten und Lizenzen"])
            self.assertIn("ENDBENUTZER-LIZENZVERTRAG", dialog.tabs.widget(0).toPlainText())
            self.assertIn("DATENSCHUTZERKLÄRUNG", dialog.tabs.widget(2).toPlainText())
            self.assertIn("FFmpeg", dialog.tabs.widget(3).toPlainText())


if __name__ == "__main__":
    unittest.main()
