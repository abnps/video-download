import os
import tempfile
import threading
import unittest
from pathlib import Path

from yt_dlp.postprocessor import FFmpegExtractAudioPP, FFmpegMergerPP
from yt_dlp.utils import DownloadCancelled

from videodl.download import (
    DOWNLOADING, PROCESSING, PartsProgress, _Attempt, _PartsRecorderPP, download,
)
from videodl.jobs import ItemStatus
from videodl.presets import get_preset


class PartsProgressTest(unittest.TestCase):
    def test_parts_are_weighted_by_size(self):
        parts = PartsProgress()
        parts.set_parts([{"format_id": "137", "filesize": 900}, {"format_id": "140", "filesize_approx": 100}])
        self.assertAlmostEqual(parts.update("137", 450, 900), 0.45)
        self.assertAlmostEqual(parts.update("137", 900, 900), 0.9)
        self.assertAlmostEqual(parts.update("140", 50, 100), 0.95)
        self.assertAlmostEqual(parts.update("140", 100, 100), 1.0)

    def test_bitrate_is_used_when_size_is_missing(self):
        parts = PartsProgress()
        parts.set_parts([{"format_id": "v", "tbr": 3000}, {"format_id": "a", "filesize": 10, "tbr": 1000}])
        self.assertAlmostEqual(parts.update("v", 1, 1), 0.75)

    def test_equal_weights_without_any_hint(self):
        parts = PartsProgress()
        parts.set_parts([{"format_id": "v"}, {"format_id": "a", "tbr": 128}])
        self.assertAlmostEqual(parts.update("v", 1, 1), 0.5)

    def test_unknown_total_keeps_last_value_and_unknown_part_reports_itself(self):
        parts = PartsProgress()
        parts.set_parts([{"format_id": "v", "filesize": 1}, {"format_id": "a", "filesize": 1}])
        parts.update("v", 1, 2)
        self.assertAlmostEqual(parts.update("v", 5, None), 0.25)
        self.assertAlmostEqual(parts.update("drugi", 1, 4), 0.25)
        self.assertIsNone(PartsProgress().update("x", 10, None))


class AttemptTest(unittest.TestCase):
    def setUp(self):
        self.cancel = threading.Event()
        self.events = []
        self.now = 0.0
        self.attempt = _Attempt(self.cancel, self.events.append, clock=lambda: self.now)

    def hook(self, **d):
        d.setdefault("info_dict", {"format_id": "18"})
        self.attempt.progress_hook(d)

    def test_progress_is_throttled_but_processing_is_always_reported(self):
        self.hook(status="downloading", downloaded_bytes=10, total_bytes=100, filename="a.mp4")
        self.now = 0.1
        self.hook(status="downloading", downloaded_bytes=20, total_bytes=100, filename="a.mp4")
        self.now = 0.3
        self.hook(status="downloading", downloaded_bytes=30, total_bytes=100, filename="a.mp4",
                  speed=2048, eta=5)
        self.attempt.postprocessor_hook({"status": "started", "postprocessor": "Merger"})
        self.assertEqual([e.phase for e in self.events], [DOWNLOADING, DOWNLOADING, PROCESSING])
        self.assertAlmostEqual(self.events[1].fraction, 0.3)
        self.assertEqual(self.events[1].speed, 2048)
        self.assertEqual(self.events[2].label, "Spajanje videa i zvuka")

    def test_recorder_and_non_start_events_are_ignored(self):
        self.attempt.postprocessor_hook({"status": "started", "postprocessor": _PartsRecorderPP.pp_key()})
        self.attempt.postprocessor_hook({"status": "finished", "postprocessor": "Merger"})
        self.assertEqual(self.events, [])

    def test_ffmpeg_step_keys_match_yt_dlp(self):
        # yt-dlp javlja skraćeno ime koraka; pogrešan ključ tiho gasi natpis i prekid.
        self.assertEqual(FFmpegMergerPP.pp_key(), "Merger")
        self.assertEqual(FFmpegExtractAudioPP.pp_key(), "ExtractAudio")

    def test_part_label_marks_audio_and_video(self):
        self.attempt.record_parts({"requested_formats": [
            {"format_id": "137", "vcodec": "avc1", "acodec": "none", "filesize": 3},
            {"format_id": "140", "vcodec": "none", "acodec": "mp4a", "filesize": 1},
        ]})
        self.hook(status="downloading", downloaded_bytes=1, total_bytes=1,
                  info_dict={"format_id": "140", "vcodec": "none", "acodec": "mp4a"})
        self.assertEqual(self.events[-1].label, "zvuk")
        self.assertAlmostEqual(self.events[-1].fraction, 0.25)

    def test_cancel_raises_in_hooks(self):
        self.cancel.set()
        with self.assertRaises(DownloadCancelled):
            self.hook(status="downloading", downloaded_bytes=1, total_bytes=2)
        with self.assertRaises(DownloadCancelled):
            self.attempt.postprocessor_hook({"status": "started", "postprocessor": "ExtractAudio"})
        # Kratki završni koraci (npr. premještanje) se ne prekidaju.
        self.attempt.postprocessor_hook({"status": "started", "postprocessor": "MoveFiles"})

    def test_cleanup_removes_only_files_of_this_attempt(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp)
            earlier = folder / "Stari [x].mp4"  # ranije preuzet, yt-dlp ga samo prijavi
            part = folder / "Novi [y].f137.mp4.part"
            finished_part = folder / "Novi [y].f140.m4a"
            for path in (earlier, part, Path(f"{part}.ytdl"), Path(f"{part}-Frag3"), finished_part):
                path.write_bytes(b"x")

            self.hook(status="finished", filename=str(earlier), total_bytes=1)
            self.hook(status="downloading", filename=str(finished_part), tmpfilename=f"{finished_part}.part",
                      downloaded_bytes=1, total_bytes=1)
            self.hook(status="finished", filename=str(finished_part))
            self.hook(status="downloading", filename=str(folder / "Novi [y].f137.mp4"),
                      tmpfilename=str(part), downloaded_bytes=1, total_bytes=2)
            self.attempt.cleanup()

            self.assertEqual(sorted(os.listdir(folder)), ["Stari [x].mp4"])
            self.assertTrue(self.attempt.real_download)


class DownloadErrorsTest(unittest.TestCase):
    def test_cancel_before_start(self):
        cancel = threading.Event()
        cancel.set()
        result = download("https://example.invalid/v", get_preset("best"), tempfile.gettempdir(),
                          cancel_event=cancel)
        self.assertEqual(result.status, ItemStatus.CANCELLED)

    def test_invalid_url_becomes_failed_status_with_clean_message(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = download("ovo-nije-link", get_preset("best"), tmp)
        self.assertEqual(result.status, ItemStatus.FAILED)
        self.assertFalse(result.message.startswith("ERROR"))
        self.assertTrue(result.message)


if __name__ == "__main__":
    unittest.main()
