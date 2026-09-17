"""Prenos uživo (LIVE) se ne preuzima: odbija ga čitanje linka i samo preuzimanje."""

import functools
import http.server
import tempfile
import threading
import time
import unittest
from pathlib import Path

from yt_dlp.utils import DownloadError

from videodl.download import download
from videodl.i18n import MESSAGE_LIVE, set_language
from videodl.jobs import ItemStatus
from videodl.presets import get_preset
from videodl.probe import probe
from videodl.widgets import display_message
from videodl.ytdl import LiveStreamError, error_message

# HLS bez #EXT-X-ENDLIST: plejlista koja još raste, tj. prenos uživo.
LIVE_M3U8 = """#EXTM3U
#EXT-X-VERSION:3
#EXT-X-TARGETDURATION:4
#EXT-X-MEDIA-SEQUENCE:100
#EXTINF:4.0,
seg100.ts
#EXTINF:4.0,
seg101.ts
"""


class LiveProbeTest(unittest.TestCase):
    def test_single_live_video_is_refused(self):
        for info in ({"id": "a", "title": "Uživo", "live_status": "is_live"},
                     {"id": "b", "title": "Najava", "live_status": "is_upcoming"},
                     {"id": "c", "title": "Uživo", "is_live": True}):
            with self.subTest(info=info), self.assertRaises(LiveStreamError) as caught:
                probe("https://primjer.test/v", extract=lambda url, info=info: info)
            self.assertEqual(error_message(caught.exception), MESSAGE_LIVE)

    def test_finished_stream_recording_is_allowed(self):
        info = {"id": "a", "title": "Snimak", "live_status": "was_live", "duration": 3600}
        result = probe("https://primjer.test/v", extract=lambda url: info)
        self.assertEqual(result.entries[0].title, "Snimak")

    def test_live_entries_in_playlist_are_skipped(self):
        info = {"_type": "playlist", "title": "Kanal", "entries": [
            {"url": "https://primjer.test/1", "title": "Video"},
            {"url": "https://primjer.test/2", "title": "Uživo", "live_status": "is_live"},
        ]}
        result = probe("https://primjer.test/kanal", extract=lambda url: info)
        self.assertEqual([entry.title for entry in result.entries], ["Video"])

        only_live = {"_type": "playlist", "title": "Live", "entries": [
            {"url": "https://primjer.test/2", "title": "Uživo", "live_status": "is_live"}]}
        with self.assertRaises(LiveStreamError):
            probe("https://primjer.test/kanal/live", extract=lambda url: only_live)

    def test_wrapped_error_and_translation(self):
        try:
            try:
                raise LiveStreamError("Live stream")
            except LiveStreamError as inner:
                raise DownloadError("ERROR: Live stream", exc_info=(type(inner), inner, None))
        except DownloadError as exc:
            self.assertEqual(error_message(exc), MESSAGE_LIVE)
        set_language("bs")
        self.assertIn("uživo", display_message(MESSAGE_LIVE))


class _Quiet(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *args):
        pass


class LiveDownloadTest(unittest.TestCase):
    """Pravi yt-dlp nad lokalnim HLS-om koji nema kraja: mora odmah završiti greškom, ne visiti."""

    def test_live_hls_stream_fails_fast(self):
        with tempfile.TemporaryDirectory() as served, tempfile.TemporaryDirectory() as output:
            Path(served, "live.m3u8").write_text(LIVE_M3U8, encoding="utf-8")
            server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), functools.partial(_Quiet, directory=served))
            threading.Thread(target=server.serve_forever, daemon=True).start()
            self.addCleanup(server.server_close)
            self.addCleanup(server.shutdown)
            url = f"http://127.0.0.1:{server.server_address[1]}/live.m3u8"

            with self.assertRaises(LiveStreamError):
                probe(url)

            started = time.monotonic()
            result = download(url, get_preset("best"), output, filename_title="Uživo")
            self.assertLess(time.monotonic() - started, 30)
            self.assertEqual((result.status, result.message), (ItemStatus.FAILED, MESSAGE_LIVE))
            self.assertEqual(list(Path(output).rglob("*")), [])


if __name__ == "__main__":
    unittest.main()
