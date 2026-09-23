"""Bilješke o izmjenama: potpune na svih 5 jezika i uvijek imaju trenutnu verziju."""

import os
import tempfile
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QSettings  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

from videodl import __version__, changelog  # noqa: E402
from videodl.gui import MainWindow, WhatsNewDialog  # noqa: E402
from videodl.i18n import LANGUAGES, set_language  # noqa: E402
from videodl.updater import parse_version  # noqa: E402

app = QApplication.instance() or QApplication([])


class ChangelogTest(unittest.TestCase):
    def tearDown(self):
        set_language("bs")

    def test_current_version_has_notes_on_top(self):
        # Nova verzija bez bilješke ruši test: bilješka se ne može zaboraviti.
        self.assertEqual(changelog.CHANGES[0][0], __version__)

    def test_versions_go_from_newest_to_oldest_without_repeats(self):
        versions = [parse_version(version) for version, _date, _notes in changelog.CHANGES]
        self.assertEqual(versions, sorted(versions, reverse=True))
        self.assertEqual(len(versions), len(set(versions)))

    def test_every_version_has_every_language_with_same_number_of_items(self):
        for version, date, notes in changelog.CHANGES:
            with self.subTest(version=version):
                self.assertTrue(date)
                self.assertEqual(set(notes), set(LANGUAGES))
                counts = {language: len(items) for language, items in notes.items()}
                self.assertEqual(len(set(counts.values())), 1, counts)
                for items in notes.values():
                    self.assertTrue(all(item.strip() for item in items))

    def test_html_and_release_notes(self):
        html = changelog.to_html("de", __version__)
        self.assertIn(__version__, html)
        self.assertIn("←", html)  # trenutna verzija je označena
        self.assertIn("<li>", html)
        self.assertTrue(changelog.release_notes("0.7.0").startswith("- Isječak videa"))
        with self.assertRaises(KeyError):
            changelog.release_notes("9.9.9")

    def test_help_menu_opens_notes_in_app_language(self):
        with tempfile.TemporaryDirectory() as tmp:
            settings = QSettings(os.path.join(tmp, "s.ini"), QSettings.Format.IniFormat)
            settings.setValue("language", "fr")
            window = MainWindow(settings=settings, probe_fn=None, download_fn=None, thumbnail_fetch=lambda u: None,
                                data_dir_path=tmp)
            self.addCleanup(window.deleteLater)
            self.assertEqual(window.whats_new_action.text(), "Nouveautés (notes de version)…")
            self.assertIn(window.whats_new_action, window.help_menu.actions())
            dialog = WhatsNewDialog(window)
            self.addCleanup(dialog.deleteLater)
            self.assertIn(__version__, dialog.current_label.text())
            self.assertIn("Aide", dialog.browser.toPlainText())  # francuski tekst bilješki


if __name__ == "__main__":
    unittest.main()
