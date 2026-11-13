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
from unittest import mock

from videodl import burn, download as download_module
from videodl.download import download
from videodl.i18n import MESSAGE_BURN_FAILED, MESSAGE_NO_SUBS, set_language
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

    def run_download(self, page, **extra):
        output = tempfile.TemporaryDirectory()
        self.addCleanup(output.cleanup)
        result = download(self.base + page, get_preset("best"), output.name, subtitles=True,
                          subtitle_langs=subtitle_languages("bs"), **extra)
        return result, Path(output.name)

    def frame(self, path, second=0.5):
        """Donja trećina slike u trenutku `second` (tu stoji titl), kao sivi pikseli."""
        raw = subprocess.run([FFMPEG, "-v", "error", "-ss", str(second), "-i", str(path), "-frames:v", "1",
                              "-vf", "crop=iw:ih/3:0:ih*2/3", "-f", "rawvideo", "-pix_fmt", "gray", "-"],
                             capture_output=True, check=True).stdout
        self.assertTrue(raw)
        return raw

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

    def test_subtitle_burned_into_the_picture(self):
        # Ahmed 12.11.2026: „titl upisan u sliku" — vidi se u svakom plejeru; fajla s titlom pored videa nema.
        progress = []
        result, folder = self.run_download("sa-titlom.html", burn_subtitles=True, on_progress=progress.append)
        self.assertEqual((result.status, result.message), (ItemStatus.DONE, ""))
        video = Path(result.filepath)
        self.assertNotIn("subtitle", self.streams(video))  # nije poseban (isključiv) titl
        self.assertEqual([p for p in folder.iterdir() if p.suffix in (".srt", ".vtt")], [])
        self.assertTrue(any(p.label == "pp.burn" for p in progress))
        plain, _ = self.run_download("sa-titlom.html")
        changed = sum(a != b for a, b in zip(self.frame(video), self.frame(plain.filepath)))
        self.assertGreater(changed, 50)  # u donjem dijelu slike sada stoji tekst

    def test_failed_burn_keeps_the_video_and_the_subtitle_file(self):
        with mock.patch.object(download_module, "burn_into_picture", side_effect=burn.BurnError("ffmpeg: greška")):
            result, folder = self.run_download("sa-titlom.html", burn_subtitles=True)
        self.assertEqual((result.status, result.message), (ItemStatus.DONE, MESSAGE_BURN_FAILED))
        video = Path(result.filepath)
        self.assertTrue(video.is_file())
        self.assertTrue((folder / (video.stem + ".srt")).is_file())  # titl ostaje pored videa
        set_language("bs")
        self.assertIn("nije upisan", display_message(MESSAGE_BURN_FAILED))

    def test_cancelled_burn_cancels_the_download(self):
        with mock.patch.object(download_module, "burn_into_picture", side_effect=burn.BurnCancelled("Prekinuto.")):
            result, _folder = self.run_download("sa-titlom.html", burn_subtitles=True)
        self.assertEqual(result.status, ItemStatus.CANCELLED)

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


class BurnCommandTest(unittest.TestCase):
    def test_subtitle_is_passed_by_name_only_and_streams_are_kept(self):
        cmd = burn.command("ffmpeg", "C:/Moji videi/Naslov 'a' [x].mp4", "titl.srt", "izlaz.part")
        self.assertEqual(cmd[cmd.index("-filter:v:0") + 1], "subtitles=titl.srt")  # bez putanje u filteru
        self.assertIn("0:a?", cmd)
        self.assertIn("-sn", cmd)
        self.assertEqual(cmd[cmd.index("-c:a") + 1], "copy")

    def test_only_existing_mp4_can_get_subtitles_burned(self):
        with tempfile.TemporaryDirectory() as tmp:
            mp4, mkv = Path(tmp) / "a.mp4", Path(tmp) / "b.mkv"
            mp4.write_bytes(b"x")
            mkv.write_bytes(b"x")
            self.assertTrue(burn.can_burn(str(mp4)))
            self.assertFalse(burn.can_burn(str(mkv)))
            self.assertFalse(burn.can_burn(str(Path(tmp) / "nema.mp4")))
            with self.assertRaises(burn.BurnError):
                burn.burn_subtitles(str(mp4), str(Path(tmp) / "nema.srt"), ffmpeg="ffmpeg")


if __name__ == "__main__":
    unittest.main()
