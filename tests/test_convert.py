"""MP4 → MP3: pravo pretvaranje ffmpeg-om i dugme „MP3" na kartici preuzetog videa."""

import json
import os
import shutil
import subprocess
import tempfile
import threading
import time
import unittest
from pathlib import Path
from unittest import mock

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QSettings  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

from videodl import convert, store  # noqa: E402
from videodl.download import DownloadResult  # noqa: E402
from videodl.gui import MainWindow  # noqa: E402
from videodl.i18n import set_language  # noqa: E402
from videodl.jobs import ItemStatus  # noqa: E402
from videodl.probe import Entry, ProbeResult  # noqa: E402

app = QApplication.instance() or QApplication([])
HAS_FFMPEG = bool(shutil.which("ffmpeg") and shutil.which("ffprobe"))


def wait_until(condition, timeout=10.0):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        app.processEvents()
        if condition():
            return True
        time.sleep(0.01)
    app.processEvents()
    return condition()


def make_mp4(path: Path, seconds: int = 4) -> None:
    subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-f", "lavfi", "-i",
                    "testsrc=size=160x90:rate=25", "-f", "lavfi", "-i", "sine=frequency=440", "-t", str(seconds),
                    "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac", "-shortest", str(path)],
                   check=True, timeout=120)


@unittest.skipUnless(HAS_FFMPEG, "potreban ffmpeg")
class RealConvertTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.video = Path(self.tmp.name) / "Moja pjesma.mp4"
        make_mp4(self.video)

    def test_mp3_next_to_original_and_original_kept(self):
        steps = []
        out = Path(convert.convert_to_mp3(str(self.video), on_progress=steps.append, duration=4))
        self.assertEqual(out.name, "Moja pjesma.mp3")
        self.assertTrue(self.video.is_file())  # original ostaje
        self.assertEqual(steps[-1], 1.0)
        info = json.loads(subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration:stream=codec_name,bit_rate", "-of", "json",
             str(out)], capture_output=True, text=True, check=True).stdout)
        self.assertEqual(info["streams"][0]["codec_name"], "mp3")
        self.assertEqual(info["streams"][0]["bit_rate"], "192000")
        self.assertAlmostEqual(float(info["format"]["duration"]), 4.0, delta=0.3)

    def test_existing_mp3_is_never_overwritten(self):
        first = convert.convert_to_mp3(str(self.video))
        second = convert.convert_to_mp3(str(self.video))
        self.assertTrue(second.endswith("Moja pjesma (1).mp3"))
        self.assertTrue(Path(first).is_file())

    def test_cancel_and_errors_leave_no_partial_file(self):
        cancel = threading.Event()
        cancel.set()
        with self.assertRaises(convert.ConvertError):
            convert.convert_to_mp3(str(self.video), cancel_event=cancel)
        broken = Path(self.tmp.name) / "pokvaren.mp4"
        broken.write_bytes(b"ovo nije video")
        with self.assertRaises(convert.ConvertError):
            convert.convert_to_mp3(str(broken))
        with self.assertRaises(convert.ConvertError):
            convert.convert_to_mp3(str(Path(self.tmp.name) / "nema.mp4"))
        leftovers = [p.name for p in Path(self.tmp.name).iterdir() if p.suffix in (".part", ".mp3")]
        self.assertEqual(leftovers, [])

    def test_only_existing_mp4_is_convertible(self):
        self.assertTrue(convert.is_convertible(str(self.video)))
        self.assertFalse(convert.is_convertible(str(self.video.with_suffix(".mp3"))))
        self.assertFalse(convert.is_convertible(None))


class ConvertButtonTest(unittest.TestCase):
    def setUp(self):
        set_language("bs")
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.settings = QSettings(os.path.join(self.tmp.name, "s.ini"), QSettings.Format.IniFormat)
        self.settings.setValue("language", "bs")
        self.converted = []

    def window(self, preset="best", convert_fn=None):
        def probe(url, http_headers=None):
            return ProbeResult("Video", (Entry(url, "Video", None, 4),), False)

        def download(url, preset_obj, output_dir, subfolder, on_progress, cancel_event, **extra):
            ext = "mp3" if preset_obj.is_audio else "mp4"
            path = Path(output_dir) / f"{url.rsplit('/', 1)[-1]}.{ext}"
            path.write_bytes(b"x" * 10)
            return DownloadResult(ItemStatus.DONE, filepath=str(path))

        def fake_convert(source, on_progress=None, cancel_event=None, duration=None):
            self.converted.append(source)
            on_progress(0.5)
            target = Path(source).with_suffix(".mp3")
            target.write_bytes(b"mp3")
            return str(target)

        window = MainWindow(settings=self.settings, probe_fn=probe, download_fn=download,
                            thumbnail_fetch=lambda u: None, data_dir_path=self.tmp.name,
                            convert_fn=convert_fn or fake_convert)
        self.addCleanup(window.deleteLater)
        window.set_output_dir(self.tmp.name)
        window.set_parallel(1)
        window.preset_combo.setCurrentIndex(window.preset_combo.findData(preset))
        window.add_links_from_text("https://v/a")
        self.assertTrue(wait_until(lambda: len(window._queue.items()) == 1))
        return window, window._queue.items()[0]

    def test_button_appears_only_after_mp4_is_downloaded(self):
        window, item = self.window()
        row = window._rows[item.id]
        self.assertTrue(row.convert_button.isHidden())  # još čeka
        window._start_all()
        self.assertTrue(wait_until(lambda: item.status == ItemStatus.DONE))
        self.assertFalse(row.convert_button.isHidden())
        self.assertEqual(row.convert_button.text(), "MP3")
        layout = row.layout()
        # Odmah desno od dugmeta za folder.
        self.assertEqual(layout.indexOf(row.convert_button), layout.indexOf(row.action_button) + 1)

    def test_no_button_for_mp3_download(self):
        window, item = self.window(preset="mp3")
        window._start_all()
        self.assertTrue(wait_until(lambda: item.status == ItemStatus.DONE))
        self.assertTrue(window._rows[item.id].convert_button.isHidden())

    def test_click_converts_records_history_and_folder_shows_mp3(self):
        window, item = self.window()
        window._start_all()
        self.assertTrue(wait_until(lambda: item.status == ItemStatus.DONE))
        row = window._rows[item.id]
        row.convert_button.click()
        self.assertTrue(wait_until(lambda: item.convert_state == "done"))
        self.assertEqual(self.converted, [item.filepath])
        self.assertTrue(row.convert_button.isHidden())
        self.assertIn("MP3 spreman", row.status_label.text())
        history = store.load_history(store.history_path(Path(self.tmp.name)))
        self.assertTrue(history[0].filepath.endswith(".mp3"))
        with mock.patch("videodl.gui.reveal") as reveal:
            row.action_button.click()
        reveal.assert_called_once_with(item.convert_path)

    def test_failure_is_shown_and_button_stays_for_retry(self):
        def failing(source, on_progress=None, cancel_event=None, duration=None):
            raise convert.ConvertError("ffmpeg nije uspio.")

        window, item = self.window(convert_fn=failing)
        window._start_all()
        self.assertTrue(wait_until(lambda: item.status == ItemStatus.DONE))
        row = window._rows[item.id]
        row.convert_button.click()
        self.assertTrue(wait_until(lambda: item.convert_state == "failed"))
        self.assertIn("nije uspjelo", row.status_label.text())
        self.assertFalse(row.convert_button.isHidden())


if __name__ == "__main__":
    unittest.main()
