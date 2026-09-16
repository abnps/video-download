"""Prevodi (5 jezika) i automatsko ažuriranje bez interneta."""

import hashlib
import io
import json
import os
import string
import tempfile
import threading
import unittest
from pathlib import Path
from unittest import mock

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QSettings  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

from videodl import __version__, updater  # noqa: E402
from videodl.gui import MainWindow  # noqa: E402
from videodl.i18n import LANGUAGES, TEXTS, get_language, pick_language, set_language, tr  # noqa: E402

app = QApplication.instance() or QApplication([])


class TranslationsTest(unittest.TestCase):
    def tearDown(self):
        set_language("bs")

    def test_every_text_exists_in_all_languages_with_same_placeholders(self):
        formatter = string.Formatter()
        for key, texts in TEXTS.items():
            with self.subTest(key=key):
                self.assertEqual(len(texts), len(LANGUAGES))
                self.assertTrue(all(text.strip() for text in texts))
                fields = [sorted({name for _, name, _, _ in formatter.parse(text) if name}) for text in texts]
                self.assertTrue(all(f == fields[0] for f in fields), fields)

    def test_language_choice_from_locale(self):
        self.assertEqual(pick_language("sr_Latn_RS"), "bs")
        self.assertEqual(pick_language("hr-HR"), "bs")
        self.assertEqual(pick_language("de_AT"), "de")
        self.assertEqual(pick_language("fr"), "fr")
        self.assertEqual(pick_language("ja_JP"), "en")
        self.assertEqual(pick_language(None), "en")

    def test_tr_formats_and_falls_back(self):
        set_language("de")
        self.assertEqual(tr("summary.waiting", count=3), "wartend: 3")
        self.assertEqual(tr("nepostojeci.kljuc"), "nepostojeci.kljuc")
        self.assertEqual(set_language("xx"), "en")

    def test_window_switches_language_live(self):
        with tempfile.TemporaryDirectory() as tmp:
            settings = QSettings(os.path.join(tmp, "s.ini"), QSettings.Format.IniFormat)
            settings.setValue("language", "bs")
            window = MainWindow(settings=settings, probe_fn=lambda url, **kw: None, download_fn=None,
                                thumbnail_fetch=lambda url: None)
            self.addCleanup(window.deleteLater)
            self.assertEqual(window.paste_button.text(), "Zalijepi")
            self.assertEqual(window.help_menu.title(), "P&omoć")
            self.assertEqual(window.preset_combo.itemText(0), "Video – najbolji kvalitet (MP4)")

            for code, paste, download, help_title in (("en", "Paste", "Download", "&Help"),
                                                      ("de", "Einfügen", "Herunterladen", "&Hilfe"),
                                                      ("es", "Pegar", "Descargar", "A&yuda"),
                                                      ("fr", "Coller", "Télécharger", "&Aide")):
                window.change_language(code)
                self.assertEqual((window.paste_button.text(), window.download_button.text(), window.help_menu.title()),
                                 (paste, download, help_title))
                checked = [a.data() for a in window.language_actions.actions() if a.isChecked()]
                self.assertEqual(checked, [code])
            self.assertEqual(settings.value("language"), "fr")
            self.assertEqual(window.drop_zone.title.text(), "Déposez un lien ici")


class FakeResponse(io.BytesIO):
    def __init__(self, data: bytes):
        super().__init__(data)
        self.headers = {"Content-Length": str(len(data))}

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()


class UpdaterTest(unittest.TestCase):
    def setUp(self):
        self.installer = b"MZ fake installer" * 1000
        self.digest = hashlib.sha256(self.installer).hexdigest()
        self.urls = []

    def opener(self, pages):
        def open_url(request, timeout):
            self.urls.append(request.full_url)
            return FakeResponse(pages[request.full_url])
        return open_url

    def release_json(self, version="9.9.9", **extra):
        name = f"VideoDownload-Setup-{version}.exe"
        return json.dumps({
            "tag_name": f"v{version}", "body": "Novo:\n- nešto", **extra,
            "assets": [
                {"name": name, "browser_download_url": f"https://github.com/r/{name}", "size": len(self.installer)},
                {"name": f"{name}.sha256", "browser_download_url": f"https://github.com/r/{name}.sha256"},
                {"name": "izvorni.zip", "browser_download_url": "https://github.com/r/izvorni.zip"},
            ],
        }).encode("utf-8")

    def test_versions(self):
        self.assertTrue(updater.is_newer("0.10.0", "0.9.9"))
        self.assertTrue(updater.is_newer("v1.0.0", "0.99"))
        self.assertFalse(updater.is_newer("0.4.1", "0.4.1"))
        self.assertFalse(updater.is_newer("0.4.0", "0.4.1"))

    def test_fetch_latest_finds_installer_and_checksum(self):
        pages = {updater.LATEST_RELEASE_API: self.release_json()}
        release = updater.fetch_latest(opener=self.opener(pages))
        self.assertEqual(release.version, "9.9.9")
        self.assertTrue(release.installer_url.endswith("VideoDownload-Setup-9.9.9.exe"))
        self.assertTrue(release.checksum_url.endswith(".sha256"))
        self.assertIn("nešto", release.notes)

    def test_prerelease_is_ignored_and_missing_installer_is_an_error(self):
        pages = {updater.LATEST_RELEASE_API: self.release_json(prerelease=True)}
        self.assertIsNone(updater.fetch_latest(opener=self.opener(pages)))
        pages = {updater.LATEST_RELEASE_API: json.dumps({"tag_name": "v9", "assets": []}).encode()}
        with self.assertRaises(updater.UpdateError) as caught:
            updater.fetch_latest(opener=self.opener(pages))
        self.assertEqual(caught.exception.key, "update.no_asset")

    def test_download_verifies_sha256(self):
        pages = {updater.LATEST_RELEASE_API: self.release_json()}
        release = updater.fetch_latest(opener=self.opener(pages))
        with tempfile.TemporaryDirectory() as tmp:
            good = {release.checksum_url: f"{self.digest}  x.exe\n".encode(), release.installer_url: self.installer}
            progress = []
            path = updater.download_installer(release, Path(tmp), on_progress=lambda d, t: progress.append((d, t)),
                                              opener=self.opener(good))
            self.assertEqual(path.read_bytes(), self.installer)
            self.assertEqual(progress[-1], (len(self.installer), len(self.installer)))

            bad = {release.checksum_url: ("0" * 64).encode(), release.installer_url: self.installer}
            with self.assertRaises(updater.UpdateError) as caught:
                updater.download_installer(release, Path(tmp) / "b", opener=self.opener(bad))
            self.assertEqual(caught.exception.key, "update.checksum")
            self.assertEqual(list((Path(tmp) / "b").iterdir()), [])  # ništa neprovjereno ne ostaje

    def test_insecure_urls_are_refused(self):
        with self.assertRaises(updater.UpdateError):
            updater.fetch_latest(url="http://primjer.com/latest", opener=self.opener({}))
        self.assertEqual(self.urls, [])

    def test_installer_gets_silent_flags_and_language(self):
        with mock.patch("subprocess.Popen") as popen:
            updater.launch_installer(Path(r"C:\t\VideoDownload-Setup-9.9.9.exe"), "de")
        args = popen.call_args.args[0]
        self.assertIn("/SILENT", args)
        self.assertIn("/LANG=german", args)
        self.assertIn("/update=1", args)

    def test_window_reports_latest_version_on_manual_check(self):
        with tempfile.TemporaryDirectory() as tmp:
            settings = QSettings(os.path.join(tmp, "s.ini"), QSettings.Format.IniFormat)
            settings.setValue("language", "en")
            release = updater.Release(__version__, "", "x.exe", "https://x", "https://x.sha256", 1)
            window = MainWindow(settings=settings, probe_fn=None, download_fn=None, thumbnail_fetch=lambda u: None,
                                update_fetch=lambda: release)
            self.addCleanup(window.deleteLater)
            shown = threading.Event()
            with mock.patch("videodl.gui.QMessageBox.information", side_effect=lambda *a: shown.set()) as info:
                window.check_for_updates(manual=True)
                for _ in range(200):
                    app.processEvents()
                    if shown.is_set():
                        break
                    threading.Event().wait(0.01)
            self.assertTrue(shown.is_set())
            self.assertIn(__version__, info.call_args.args[2])
            self.assertIn("latest", info.call_args.args[2])


if __name__ == "__main__":
    unittest.main()
