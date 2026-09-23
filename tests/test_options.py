"""Isječak, titlovi, sličica, ograničenje brzine i cijela plejlista."""

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

from videodl import probe as probe_module
from videodl.download import download
from videodl.jobs import ItemStatus
from videodl.presets import build_ydl_options, format_section, get_preset, parse_section, subtitle_languages


class SectionTextTest(unittest.TestCase):
    def test_parsing_accepts_usual_forms(self):
        self.assertEqual(parse_section("2:30-6:10"), (150.0, 370.0))
        self.assertEqual(parse_section(" 1:02:03 – 1:05:00 "), (3723.0, 3900.0))
        self.assertEqual(parse_section("90-120"), (90.0, 120.0))
        self.assertEqual(parse_section("0:05,5-0:07"), (5.5, 7.0))

    def test_parsing_rejects_nonsense(self):
        for text in ("", "2:30", "6:10-2:30", "2:30-2:30", "a-b", "1:2:3:4-5", "-5-10", None):
            self.assertIsNone(parse_section(text), text)

    def test_format(self):
        self.assertEqual(format_section((150, 370)), "2:30\u20136:10")
        self.assertEqual(format_section((3723, 3900)), "1:02:03\u20131:05:00")
        self.assertEqual(format_section(None), "")


class OptionsTest(unittest.TestCase):
    def test_section_gets_own_file_name_and_ranges(self):
        opts = build_ydl_options(get_preset("best"), r"C:\v", section=(150, 370))
        self.assertIn(" (2.30\u20136.10).%(ext)s", opts["outtmpl"])
        self.assertTrue(opts["force_keyframes_at_cuts"])
        ranges = list(opts["download_ranges"]({}, None))
        self.assertEqual((ranges[0]["start_time"], ranges[0]["end_time"]), (150, 370))
        self.assertNotIn("download_ranges", build_ydl_options(get_preset("best"), r"C:\v"))

    def test_subtitles_only_for_video_and_thumbnail_after_audio(self):
        video = build_ydl_options(get_preset("best"), r"C:\v", subtitles=True, subtitle_langs=["bs.*", "en.*"],
                                  thumbnail=True)
        self.assertEqual([pp["key"] for pp in video["postprocessors"]],
                         ["FFmpegThumbnailsConvertor", "FFmpegEmbedSubtitle", "EmbedThumbnail"])
        self.assertEqual(video["subtitleslangs"], ["bs.*", "en.*"])
        self.assertTrue(video["writethumbnail"])

        audio = build_ydl_options(get_preset("mp3"), r"C:\v", subtitles=True, thumbnail=True)
        self.assertNotIn("writesubtitles", audio)  # MP3 nema gdje primiti titl
        self.assertEqual([pp["key"] for pp in audio["postprocessors"]],
                         ["FFmpegThumbnailsConvertor", "FFmpegExtractAudio", "EmbedThumbnail"])

    def test_rate_limit_and_defaults(self):
        self.assertEqual(build_ydl_options(get_preset("best"), r"C:\v", ratelimit=1_048_576)["ratelimit"], 1_048_576)
        plain = build_ydl_options(get_preset("best"), r"C:\v")
        for key in ("ratelimit", "writesubtitles", "writethumbnail", "postprocessors"):
            self.assertNotIn(key, plain)

    def test_subtitle_languages_follow_app_language(self):
        self.assertEqual(subtitle_languages("bs"), ["bs.*", "hr.*", "sr.*", "en.*"])
        self.assertEqual(subtitle_languages("de"), ["de.*", "en.*"])
        self.assertEqual(subtitle_languages("en"), ["en.*"])


class WholePlaylistTest(unittest.TestCase):
    def test_flag_reaches_yt_dlp_options(self):
        seen = []

        class FakeYDL:
            def __init__(self, opts):
                seen.append(opts)

            def __enter__(self):
                return self

            def __exit__(self, *exc):
                return False

            def extract_info(self, url, download=False):
                return {"id": "x", "title": "Video"}

        with mock.patch.object(probe_module, "YoutubeDL", FakeYDL):
            probe_module.probe("https://www.youtube.com/watch?v=a&list=b")
            probe_module.probe("https://www.youtube.com/watch?v=a&list=b", whole_playlist=True)
        self.assertEqual([opts["noplaylist"] for opts in seen], [True, False])


class _RangeHandler(http.server.SimpleHTTPRequestHandler):
    """Kao pravi CDN: podržava „Range", jer ffmpeg za isječak skače na početak."""

    def log_message(self, *args):
        pass

    def send_head(self):
        path = Path(self.translate_path(self.path))
        header = self.headers.get("Range", "")
        if not path.is_file() or not header.startswith("bytes="):
            return super().send_head()
        size = path.stat().st_size
        first, _, last = header[6:].partition("-")
        start = int(first or 0)
        end = min(int(last) if last else size - 1, size - 1)
        handle = path.open("rb")
        handle.seek(start)
        self.send_response(206)
        self.send_header("Content-Type", "video/mp4")
        self.send_header("Accept-Ranges", "bytes")
        self.send_header("Content-Range", f"bytes {start}-{end}/{size}")
        self.send_header("Content-Length", str(end - start + 1))
        self.end_headers()
        self._remaining = end - start + 1
        return handle

    def copyfile(self, source, outputfile):
        remaining = getattr(self, "_remaining", None)
        if remaining is None:
            return super().copyfile(source, outputfile)
        try:
            while remaining > 0:
                chunk = source.read(min(65536, remaining))
                if not chunk:
                    break
                outputfile.write(chunk)
                remaining -= len(chunk)
        except (ConnectionError, OSError):
            pass  # ffmpeg zatvara vezu čim ima dovoljno


@unittest.skipUnless(shutil.which("ffmpeg") and shutil.which("ffprobe"), "potreban ffmpeg")
class RealSectionDownloadTest(unittest.TestCase):
    """Pravi yt-dlp + ffmpeg nad lokalnim videom od 8 s: isječak 2–5 s mora trajati oko 3 s."""

    def test_only_the_section_is_saved(self):
        with tempfile.TemporaryDirectory() as served, tempfile.TemporaryDirectory() as output:
            clip = Path(served, "clip.mp4")
            subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-f", "lavfi", "-i",
                            "testsrc=size=320x180:rate=25", "-f", "lavfi", "-i", "sine=frequency=440",
                            "-t", "8", "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac", "-shortest",
                            str(clip)], check=True, timeout=120)
            server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), functools.partial(_RangeHandler, directory=served))
            threading.Thread(target=server.serve_forever, daemon=True).start()
            self.addCleanup(server.server_close)
            self.addCleanup(server.shutdown)

            url = f"http://127.0.0.1:{server.server_address[1]}/clip.mp4"
            result = download(url, get_preset("best"), output, filename_title="Isjecak", section=(2.0, 5.0))
            self.assertEqual(result.status, ItemStatus.DONE, result.message)
            self.assertIn("(0.02\u20130.05)", Path(result.filepath).name)
            probe = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "json",
                                    result.filepath], capture_output=True, text=True, check=True)
            duration = float(json.loads(probe.stdout)["format"]["duration"])
            self.assertAlmostEqual(duration, 3.0, delta=0.6)


if __name__ == "__main__":
    unittest.main()
