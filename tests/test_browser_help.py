"""Pomoć → Preuzimanje iz browsera: Edge i Firefox iz prodavnice jednim klikom, Chrome u tri koraka."""

import os
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication, QLabel  # noqa: E402

from videodl import dialogs  # noqa: E402
from videodl.gui import BrowserHelpDialog  # noqa: E402
from videodl.i18n import set_language, tr  # noqa: E402

app = QApplication.instance() or QApplication([])
FOLDER = r"C:\Users\x\AppData\Local\Programs\Video Download\extension"
FOUND = {"msedge.exe": r"C:\Edge\msedge.exe", "chrome.exe": r"C:\Chrome\chrome.exe",
         "firefox.exe": r"C:\Firefox\firefox.exe"}


class BrowserHelpDialogTest(unittest.TestCase):
    def setUp(self):
        set_language("bs")
        self.launched = []
        self.opened = []

    def dialog(self, installed=("msedge.exe", "chrome.exe", "firefox.exe"), launch=None):
        dialog = BrowserHelpDialog(FOLDER, find_browser=lambda exe: FOUND[exe] if exe in installed else None,
                                   launch=launch or self.launched.append, open_url=self.opened.append)
        self.addCleanup(dialog.deleteLater)
        return dialog

    def test_edge_and_firefox_open_the_store_page_in_their_own_browser(self):
        dialog = self.dialog()
        dialog.store_buttons["msedge.exe"].click()
        dialog.store_buttons["firefox.exe"].click()
        self.assertEqual(self.launched, [[FOUND["msedge.exe"], dialogs.EDGE_ADDON_URL],
                                         [FOUND["firefox.exe"], dialogs.FIREFOX_ADDON_URL]])
        self.assertEqual(dialog.note.text(), tr("help.store_opened"))
        self.assertIn("microsoftedge.microsoft.com/addons/detail/", dialogs.EDGE_ADDON_URL)
        self.assertIn("addons.mozilla.org/firefox/addon/video-download-abnps", dialogs.FIREFOX_ADDON_URL)

    def test_store_page_opens_in_default_browser_when_that_browser_is_missing(self):
        dialog = self.dialog(installed=())
        dialog.store_buttons["firefox.exe"].click()
        self.assertEqual(self.launched, [])
        self.assertEqual(self.opened, [dialogs.FIREFOX_ADDON_URL])

    def test_failed_store_launch_falls_back_to_default_browser(self):
        def broken(command):
            raise OSError("nema")

        dialog = self.dialog(launch=broken)
        dialog.store_buttons["msedge.exe"].click()
        self.assertEqual(self.opened, [dialogs.EDGE_ADDON_URL])

    def test_chrome_steps_copy_path_and_open_extensions_page(self):
        dialog = self.dialog()
        dialog.copy_button.click()
        self.assertEqual(QApplication.clipboard().text(), FOLDER)
        self.assertEqual(tr("help.copied"), dialog.note.text())  # Ctrl+V na Windowsu, ⌘⇧G/⌘V na Macu
        dialog.browser_buttons["chrome.exe"].click()
        self.assertEqual(self.launched, [[FOUND["chrome.exe"], "chrome://extensions"]])
        texts = [label.text() for label in dialog.findChildren(QLabel)]
        for key in ("help.chrome_step1", "help.chrome_step2", "help.chrome_step3"):
            self.assertIn(tr(key), texts)
        self.assertIn(FOLDER, texts)  # putanja je vidljiva i može se označiti

    def test_without_chrome_the_address_is_shown(self):
        dialog = self.dialog(installed=("msedge.exe",))
        self.assertEqual(dialog.browser_buttons, {})
        texts = [label.text() for label in dialog.findChildren(QLabel)]
        self.assertIn("<b>chrome://extensions</b>", texts)

    def test_failed_chrome_launch_copies_the_address(self):
        def broken(command):
            raise OSError("nema")

        dialog = self.dialog(launch=broken)
        dialog.browser_buttons["chrome.exe"].click()
        self.assertEqual(QApplication.clipboard().text(), "chrome://extensions")
        self.assertIn("chrome://extensions", dialog.note.text())

    def test_texts_exist_in_every_language(self):
        keys = ("help.stores_title", "help.install_edge", "help.install_firefox", "help.stores_note", "help.store_opened",
                "help.chrome_title", "help.chrome_step1", "help.chrome_step2", "help.chrome_step3", "help.usage")
        try:
            for language in ("bs", "en", "de", "es", "fr"):
                set_language(language)
                for key in keys:
                    with self.subTest(language=language, key=key):
                        self.assertNotEqual(tr(key), key)
        finally:
            set_language("bs")

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


if __name__ == "__main__":
    unittest.main()
