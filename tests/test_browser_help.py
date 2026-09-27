"""Pomoć → Preuzimanje iz browsera: kopiranje putanje i otvaranje stranice dodataka bez kucanja."""

import os
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication, QLabel  # noqa: E402

from videodl.gui import BrowserHelpDialog  # noqa: E402
from videodl.i18n import set_language, tr  # noqa: E402

app = QApplication.instance() or QApplication([])
FOLDER = r"C:\Users\x\AppData\Local\Programs\Video Download\extension"


class BrowserHelpDialogTest(unittest.TestCase):
    def setUp(self):
        set_language("bs")
        self.launched = []

    def dialog(self, installed=("msedge.exe", "chrome.exe"), launch=None):
        found = {"msedge.exe": r"C:\Edge\msedge.exe", "chrome.exe": r"C:\Chrome\chrome.exe"}
        dialog = BrowserHelpDialog(FOLDER, find_browser=lambda exe: found[exe] if exe in installed else None,
                                   launch=launch or self.launched.append)
        self.addCleanup(dialog.deleteLater)
        return dialog

    def test_copy_path_puts_folder_in_clipboard(self):
        dialog = self.dialog()
        dialog.copy_button.click()
        self.assertEqual(QApplication.clipboard().text(), FOLDER)
        self.assertEqual(tr("help.copied"), dialog.note.text())  # Ctrl+V na Windowsu, ⌘⇧G/⌘V na Macu

    def test_buttons_open_the_extensions_page_of_each_installed_browser(self):
        dialog = self.dialog()
        dialog.browser_buttons["msedge.exe"].click()
        dialog.browser_buttons["chrome.exe"].click()
        self.assertEqual(self.launched, [[r"C:\Edge\msedge.exe", "edge://extensions"],
                                         [r"C:\Chrome\chrome.exe", "chrome://extensions"]])
        self.assertEqual(set(self.dialog(installed=("msedge.exe",)).browser_buttons), {"msedge.exe"})

    def test_failed_launch_copies_the_address(self):
        def broken(command):
            raise OSError("nema")

        dialog = self.dialog(launch=broken)
        dialog.browser_buttons["msedge.exe"].click()
        self.assertEqual(QApplication.clipboard().text(), "edge://extensions")
        self.assertIn("edge://extensions", dialog.note.text())

    def test_online_guide_follows_app_language(self):
        self.assertTrue(BrowserHelpDialog.guide_url().endswith("/bs/extension.html"))
        set_language("en")
        try:
            self.assertEqual(BrowserHelpDialog.guide_url(), "https://abnps.github.io/video-download/extension.html")
            for language in ("de", "es", "fr"):  # sajt ima svih 5 jezika, ne samo bs i en
                set_language(language)
                self.assertEqual(BrowserHelpDialog.guide_url(),
                                 f"https://abnps.github.io/video-download/{language}/extension.html")
        finally:
            set_language("bs")

    def test_firefox_is_mentioned_with_a_link_to_the_signed_extension(self):
        dialog = self.dialog()
        texts = [label.text() for label in dialog.findChildren(QLabel)]
        self.assertTrue(any(text.startswith("Firefox:") and 'href="guide"' in text for text in texts))


if __name__ == "__main__":
    unittest.main()
