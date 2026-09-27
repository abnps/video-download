"""MP3 istog videa ne smije obrisati MP4 (proba instalera 0.9.7): yt-dlp za MP3 prvo preuzme „Naslov [id].mp4",
izvuče zvuk i taj fajl obriše. U folderu korisnika to je bio njegov MP4. Pravo preuzimanje s lokalnog servera."""

import functools
import http.server
import shutil
import subprocess
import tempfile
import threading
import unittest
from pathlib import Path

from videodl.download import download
from videodl.jobs import ItemStatus
from videodl.presets import get_preset

FFMPEG = shutil.which("ffmpeg")
FFPROBE = shutil.which("ffprobe")
PAGE = '<!doctype html><html><head><title>Objava</title></head><body><video src="clip.mp4"></video></body></html>'


class _Quiet(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *args):
        pass


@unittest.skipUnless(FFMPEG and FFPROBE, "ffmpeg nije instaliran")
class AudioKeepsVideoTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.served = tempfile.TemporaryDirectory()
        root = Path(cls.served.name)
        subprocess.run([FFMPEG, "-v", "error", "-f", "lavfi", "-i", "testsrc=size=160x90:rate=10", "-f", "lavfi",
                        "-i", "sine=frequency=440", "-t", "2", "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac",
                        "-shortest", str(root / "clip.mp4")], check=True)
        (root / "objava.html").write_text(PAGE, encoding="utf-8")
        cls.server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), functools.partial(_Quiet, directory=str(root)))
        threading.Thread(target=cls.server.serve_forever, daemon=True).start()
        cls.url = f"http://127.0.0.1:{cls.server.server_address[1]}/objava.html"

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.served.cleanup()

    def setUp(self):
        self.out = tempfile.TemporaryDirectory()
        self.addCleanup(self.out.cleanup)
        self.folder = Path(self.out.name)

    def files(self):
        return sorted(p.name for p in self.folder.iterdir())

    def test_mp3_after_mp4_of_the_same_video_keeps_the_mp4(self):
        video = download(self.url, get_preset("best"), self.out.name)
        self.assertEqual(video.status, ItemStatus.DONE, video.message)
        audio = download(self.url, get_preset("mp3"), self.out.name)
        self.assertEqual(audio.status, ItemStatus.DONE, audio.message)
        self.assertTrue(Path(video.filepath).is_file())  # MP4 je i dalje tu
        self.assertEqual(Path(audio.filepath).parent, self.folder)  # MP3 pored videa, ne u privremenom folderu
        self.assertEqual(Path(audio.filepath).suffix, ".mp3")
        self.assertEqual(self.files(), sorted([Path(video.filepath).name, Path(audio.filepath).name]))

    def test_mp3_and_mp4_at_the_same_time_both_survive(self):
        results = {}

        def run(key):
            results[key] = download(self.url, get_preset(key), self.out.name)

        threads = [threading.Thread(target=run, args=(key,)) for key in ("best", "mp3")]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join(120)
        self.assertEqual({key: result.status for key, result in results.items()},
                         {"best": ItemStatus.DONE, "mp3": ItemStatus.DONE})
        self.assertEqual(sorted(Path(p).suffix for p in self.files()), [".mp3", ".mp4"])  # bez ostataka

    def test_second_mp3_keeps_the_existing_one(self):
        first = download(self.url, get_preset("mp3"), self.out.name)
        second = download(self.url, get_preset("mp3"), self.out.name)
        self.assertEqual(second.status, ItemStatus.DONE)
        self.assertTrue(second.already_existed)
        self.assertEqual(first.filepath, second.filepath)
        self.assertEqual(len(self.files()), 1)


if __name__ == "__main__":
    unittest.main()
