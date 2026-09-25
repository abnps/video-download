"""Titlovi uz video: .srt pored MP4 i u njemu; video bez titla ili s neuspjelim titlom ipak se preuzme."""

import functools
import http.server
import json
import shutil
import subprocess
import tempfile
import threading
import unittest
from pathlib import Path

from videodl.download import download
from videodl.i18n import MESSAGE_NO_SUBS, set_language
from videodl.jobs import ItemStatus
from videodl.presets import get_preset, subtitle_languages
from videodl.widgets import display_message

FFMPEG = shutil.which("ffmpeg")
FFPROBE = shutil.which("ffprobe")

VTT = """WEBVTT

00:00:00.000 --> 00:00:01.500
Zdravo, ovo je titl.
"""

PAGE = """<!doctype html><html><head><title>{title}</title></head><body>
<video controls><source src="clip.mp4" type="video/mp4">{track}</video></body></html>"""


class _Quiet(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *args):
        pass


@unittest.skipUnless(FFMPEG and FFPROBE, "ffmpeg nije instaliran")
class SubtitleDownloadTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.served = tempfile.TemporaryDirectory()
        root = Path(cls.served.name)
        subprocess.run([FFMPEG, "-v", "error", "-f", "lavfi", "-i", "testsrc=size=160x90:rate=10", "-f", "lavfi",
                        "-i", "sine=frequency=440", "-t", "2", "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac",
                        "-shortest", str(root / "clip.mp4")], check=True)
        (root / "subs.vtt").write_text(VTT, encoding="utf-8")
        (root / "sa-titlom.html").write_text(PAGE.format(
            title="Sa titlom", track='<track kind="subtitles" srclang="en" src="subs.vtt">'), encoding="utf-8")
        (root / "bez-titla.html").write_text(PAGE.format(title="Bez titla", track=""), encoding="utf-8")
        (root / "los-titl.html").write_text(PAGE.format(
            title="Los titl", track='<track kind="subtitles" srclang="en" src="nema.vtt">'), encoding="utf-8")
        cls.server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), functools.partial(_Quiet, directory=str(root)))
        threading.Thread(target=cls.server.serve_forever, daemon=True).start()
        cls.base = f"http://127.0.0.1:{cls.server.server_address[1]}/"

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.served.cleanup()

    def run_download(self, page):
        output = tempfile.TemporaryDirectory()
        self.addCleanup(output.cleanup)
        result = download(self.base + page, get_preset("best"), output.name, subtitles=True,
                          subtitle_langs=subtitle_languages("bs"))
        return result, Path(output.name)

    def streams(self, path):
        probe = subprocess.run([FFPROBE, "-v", "error", "-show_streams", "-of", "json", str(path)],
                               capture_output=True, text=True, check=True)
        return [s["codec_type"] for s in json.loads(probe.stdout)["streams"]]

    def test_subtitle_is_embedded_and_kept_as_srt(self):
        result, folder = self.run_download("sa-titlom.html")
        self.assertEqual(result.status, ItemStatus.DONE, result.message)
        self.assertEqual(result.message, "")
        video = Path(result.filepath)
        self.assertEqual(video.suffix, ".mp4")
        self.assertIn("subtitle", self.streams(video))
        srt = [p for p in folder.iterdir() if p.suffix == ".srt"]
        self.assertEqual(len(srt), 1, list(folder.iterdir()))
        self.assertEqual(srt[0].name, video.stem + ".srt")  # isto ime kao video: playeri ga sami učitaju
        self.assertIn("Zdravo, ovo je titl.", srt[0].read_text(encoding="utf-8"))

    def test_video_without_subtitles_says_so(self):
        result, _folder = self.run_download("bez-titla.html")
        self.assertEqual((result.status, result.message), (ItemStatus.DONE, MESSAGE_NO_SUBS))
        self.assertTrue(Path(result.filepath).is_file())
        set_language("bs")
        self.assertIn("bez titlova", display_message(MESSAGE_NO_SUBS))

    def test_failed_subtitle_does_not_cost_the_video(self):
        result, _folder = self.run_download("los-titl.html")
        self.assertEqual((result.status, result.message), (ItemStatus.DONE, MESSAGE_NO_SUBS))
        self.assertTrue(Path(result.filepath).is_file())
        self.assertNotIn("subtitle", self.streams(result.filepath))


if __name__ == "__main__":
    unittest.main()
