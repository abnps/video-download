"""Faza 4 (Ahmed 29.10.2026): host za browser u host\\ (onedir) i samo http(s) linkovi do yt-dlp-a."""

import json
import sys
import tempfile
import threading
import unittest
from pathlib import Path, PureWindowsPath
from unittest import mock

from videodl import native_host, presets
from videodl.download import download
from videodl.i18n import MESSAGE_NOT_MEDIA
from videodl.jobs import ItemStatus
from videodl.native_messaging import install_native_host
from videodl.probe import probe
from videodl.ytdl import NotMediaError, is_web_url


class WebUrlTest(unittest.TestCase):
    def test_only_http_links_with_a_host(self):
        for url in ("https://v.test/a", "http://v.test:8080/x?y=1", "HTTPS://V.TEST/"):
            self.assertTrue(is_web_url(url), url)
        for url in ("file:///C:/Windows/win.ini", "ytsearch:nesto", "--exec=calc", "-o x", "https:///bez-hosta",
                    "javascript:alert(1)", "", None, "http://[::1"):
            self.assertFalse(is_web_url(url), url)

    def test_download_and_probe_refuse_other_links_without_calling_yt_dlp(self):
        with mock.patch("videodl.download.build_ydl_options") as build:
            result = download("--exec=calc", presets.get_preset("best"), tempfile.gettempdir(),
                              cancel_event=threading.Event())
        build.assert_not_called()
        self.assertEqual((result.status, result.message), (ItemStatus.FAILED, MESSAGE_NOT_MEDIA))
        extract = mock.Mock()
        with self.assertRaises(NotMediaError):
            probe("file:///C:/tajno.mp4", extract=extract)
        extract.assert_not_called()


class WindowsHostFolderTest(unittest.TestCase):
    def test_registration_points_to_host_folder(self):
        with tempfile.TemporaryDirectory() as tmp:
            app = Path(tmp) / "VideoDownload"
            manifest = install_native_host(Path(tmp) / "nh", frozen_app_dir=app, platform="win32",
                                           set_registry=lambda *_: None)
            self.assertEqual(Path(json.loads(manifest.read_text())["path"]), app / "host" / "videodl-host.exe")

    def test_host_in_subfolder_starts_the_app_one_folder_up(self):
        exe = r"C:\Programs\VideoDownload\host\videodl-host.exe"
        with mock.patch.object(sys, "frozen", True, create=True), mock.patch.object(sys, "platform", "win32"), \
                mock.patch.object(sys, "executable", exe), mock.patch.object(Path, "resolve", lambda self: self):
            config = native_host.current_config()
        self.assertEqual(PureWindowsPath(config["launch"][0]), PureWindowsPath(r"C:\Programs\VideoDownload\VideoDownload.exe"))


if __name__ == "__main__":
    unittest.main()
