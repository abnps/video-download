"""Link koji nije video ni audio (.exe, .zip, obična stranica) ne postaje stavka za preuzimanje."""

import http.server
import tempfile
import threading
import unittest
from pathlib import Path

from yt_dlp.utils import DownloadError, UnsupportedError

from videodl.download import download
from videodl.i18n import LANGUAGES, MESSAGE_NOT_MEDIA, set_language
from videodl.jobs import ItemStatus
from videodl.presets import get_preset
from videodl.probe import probe
from videodl.widgets import display_message
from videodl.ytdl import NotMediaError, error_message, is_network_error, is_obviously_not_media

GITHUB_EXE = "https://github.com/abnps/video-download/releases/download/v0.7.7/VideoDownload-Setup-0.7.7.exe"

# putanja: (Content-Type, tijelo)
BINARY = b"\x00\x01binarni sadrzaj" * 64
FILES = {
    "/preuzmi": ("application/octet-stream", BINARY),  # bez ekstenzije, server ne kaže šta je
    "/pjesma.mp3": ("audio/mpeg", BINARY),
    "/pjesma": ("audio/mpeg", BINARY),  # bez ekstenzije, ali server kaže da je zvuk
    "/snimak.mp4": ("application/octet-stream", BINARY),  # server ne kaže, ali ekstenzija jeste video
    "/stranica": ("text/html; charset=utf-8", b"<html><body><p>Nema videa</p></body></html>"),
}


class _Files(http.server.BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def do_HEAD(self):
        self._send(body=False)

    def do_GET(self):
        self._send(body=True)

    def _send(self, body):
        if self.path not in FILES:
            self.send_error(404)
            return
        content_type, data = FILES[self.path]
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        if body:
            self.wfile.write(data)


def _never(url):
    raise AssertionError("za očigledan fajl koji nije video ne smije se ništa čitati")


class RulesTest(unittest.TestCase):
    def test_obvious_files_are_recognised_by_extension(self):
        for url in (GITHUB_EXE, "https://x.test/a.ZIP", "https://x.test/uputstvo.pdf?dl=1",
                    "https://x.test/Moj%20Program.msi#top", "https://x.test/slika.png"):
            with self.subTest(url=url):
                self.assertTrue(is_obviously_not_media(url))
        for url in ("https://www.youtube.com/watch?v=abc", "https://x.test/pjesma.mp3", "https://x.test/v.mp4",
                    "https://x.test/preuzmi", "https://x.test/a.exe/stranica", "https://x.test/?f=a.exe"):
            with self.subTest(url=url):
                self.assertFalse(is_obviously_not_media(url))

    def test_exe_link_is_refused_without_asking_the_server(self):
        with self.assertRaises(NotMediaError) as caught:
            probe(GITHUB_EXE, extract=_never)
        self.assertEqual(error_message(caught.exception), MESSAGE_NOT_MEDIA)

    def test_guessed_direct_file_needs_a_media_extension(self):
        guessed = {"direct": True, "url": "https://x.test/preuzmi", "ext": "unknown_video", "title": "preuzmi"}
        with self.assertRaises(NotMediaError):
            probe("https://x.test/preuzmi", extract=lambda url: guessed)
        for info in ({**guessed, "ext": "mp3"}, {**guessed, "ext": "mp4"},
                     # server je rekao da je zvuk: lista formata postoji, ekstenzija nije važna
                     {**guessed, "formats": [{"url": "https://x.test/preuzmi", "ext": "mp3", "vcodec": "none"}]},
                     {"id": "abc", "title": "Obični video sa sajta", "ext": "unknown_video"}):
            with self.subTest(info=info):
                self.assertFalse(probe("https://x.test/v", extract=lambda url, info=info: info).is_playlist)

    def test_unsupported_page_gets_the_same_clear_message_in_all_languages(self):
        wrapped = DownloadError("ERROR: Unsupported URL: https://x.test/stranica",
                                (UnsupportedError, UnsupportedError("https://x.test/stranica"), None))
        self.assertEqual(error_message(wrapped), MESSAGE_NOT_MEDIA)
        self.assertFalse(is_network_error(MESSAGE_NOT_MEDIA))  # ne pokušava se automatski ponovo
        try:
            texts = set()
            for language in LANGUAGES:
                set_language(language)
                texts.add(display_message(MESSAGE_NOT_MEDIA))
            self.assertEqual(len(texts), len(LANGUAGES))
        finally:
            set_language("bs")
        self.assertIn("ni audio", display_message(MESSAGE_NOT_MEDIA))


class RealYtdlpTest(unittest.TestCase):
    """Pravi yt-dlp nad lokalnim serverom: mp3/mp4 prolaze, nepoznat fajl i obična stranica ne."""

    def setUp(self):
        server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), _Files)
        threading.Thread(target=server.serve_forever, daemon=True).start()
        self.addCleanup(server.server_close)
        self.addCleanup(server.shutdown)
        self.base = f"http://127.0.0.1:{server.server_address[1]}"

    def test_probe(self):
        for path in ("/pjesma.mp3", "/pjesma", "/snimak.mp4"):
            with self.subTest(path=path):
                self.assertEqual(len(probe(self.base + path).entries), 1)
        for path in ("/preuzmi", "/stranica"):
            with self.subTest(path=path):
                with self.assertRaises(Exception) as caught:
                    probe(self.base + path)
                self.assertEqual(error_message(caught.exception), MESSAGE_NOT_MEDIA)

    def test_retry_download_of_unknown_file_saves_nothing(self):
        # „Pokušaj ponovo" na crvenom redu ide pravo u preuzimanje: ni tada se fajl ne smije skinuti.
        with tempfile.TemporaryDirectory() as output:
            result = download(self.base + "/preuzmi", get_preset("best"), output, filename_title="Preuzmi")
            self.assertEqual((result.status, result.message), (ItemStatus.FAILED, MESSAGE_NOT_MEDIA))
            self.assertEqual(list(Path(output).rglob("*")), [])


if __name__ == "__main__":
    unittest.main()
