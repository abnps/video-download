"""Pouzdanost reda (pregled 27.9.2026): isti izlazni fajl nikad dvaput istovremeno, zatvaranje ne pokreće
nove poslove, red se čuva sam, „Ukloni sve" ne sakriva MP3 pretvaranje, pauza prije novog pokušaja se poštuje."""

import os
import tempfile
import threading
import time
import unittest
from pathlib import Path
from unittest import mock

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QSettings  # noqa: E402
from PySide6.QtWidgets import QApplication, QMessageBox  # noqa: E402

from videodl import presets, store  # noqa: E402
from videodl.download import DOWNLOADING, DownloadResult, Progress  # noqa: E402
from videodl.gui import MainWindow  # noqa: E402
from videodl.i18n import set_language  # noqa: E402
from videodl.jobs import ItemStatus  # noqa: E402
from videodl.probe import Entry, ProbeResult  # noqa: E402

app = QApplication.instance() or QApplication([])
set_language("bs")

# link -> (naslov, ID videa)
VIDEOS = {
    "https://v/a": ("Prvi", "aaa"),
    "https://v/b": ("Drugi", "bbb"),
    "https://kratko/aaa": ("Prvi", "aaa"),  # isti video kao https://v/a, druga adresa
}


def probe(url, http_headers=None):
    title, video_id = VIDEOS.get(url, (url, None))
    return ProbeResult(title, (Entry(url, title, None, 60, video_id=video_id),), False)


def wait_until(condition, timeout=10.0):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        app.processEvents()
        if condition():
            return True
        time.sleep(0.01)
    app.processEvents()
    return condition()


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.settings = QSettings(os.path.join(self.tmp.name, "settings.ini"), QSettings.Format.IniFormat)
        self.settings.setValue("language", "bs")
        self.release = threading.Event()
        self.addCleanup(self.release.set)
        self.started = []  # (url, vrijeme) svakog početka preuzimanja

    def window(self, download_fn, parallel=1, convert_fn=None):
        window = MainWindow(settings=self.settings, probe_fn=probe, download_fn=download_fn,
                            thumbnail_fetch=lambda url: None, data_dir_path=self.tmp.name, convert_fn=convert_fn)
        self.addCleanup(window.deleteLater)
        window.set_output_dir(self.tmp.name)
        window.set_parallel(parallel)
        return window

    def add(self, window, *urls):
        before = len(window._queue.items())
        window.add_links_from_text("\n".join(urls))
        self.assertTrue(wait_until(lambda: len(window._queue.items()) == before + len(urls)))
        return window._queue.items()[before:]

    def blocking(self, url, preset, output_dir, subfolder, on_progress, cancel_event, **extra):
        self.started.append((url, time.monotonic()))
        on_progress(Progress(DOWNLOADING, 0.1, None, None))
        while not cancel_event.is_set() and not self.release.is_set():
            time.sleep(0.01)
        if cancel_event.is_set():
            return DownloadResult(ItemStatus.CANCELLED, message="Otkazano")
        return DownloadResult(ItemStatus.DONE, filepath=os.path.join(output_dir, url[-1] + ".mp4"))

    def quick(self, url, preset, output_dir, subfolder, on_progress, cancel_event, **extra):
        self.started.append((url, time.monotonic()))
        path = os.path.join(output_dir, url[-1] + ".mp4")
        Path(path).write_bytes(b"x")
        return DownloadResult(ItemStatus.DONE, filepath=path)


class SameOutputTest(Base):
    """Nalaz 1: zaštita od istog fajla računa identitet po istim pravilima kao stvarno ime fajla."""

    def test_direct_streams_with_different_video_parameter_get_different_names(self):
        one = presets.direct_output_name("Predavanje", "https://cdn.test/stream.mp4?id=1")
        two = presets.direct_output_name("Predavanje", "https://cdn.test/stream.mp4?id=2")
        self.assertNotEqual(one, two)
        # privremeni potpis i rok važenja nisu drugi video: isto ime, pa se ne preuzima dvaput
        signed = presets.direct_output_name("Predavanje", "https://cdn.test/stream.mp4?id=1&token=abc&expires=9")
        self.assertEqual(one, signed)
        # link bez parametara zadržava ime iz ranijih verzija (već preuzet fajl se i dalje prepoznaje)
        import hashlib
        old = hashlib.sha1(b"cdn.test/index.m3u8").hexdigest()[:8]
        self.assertEqual(presets.direct_output_name("X", "https://cdn.test/index.m3u8"), f"X [{old}].%(ext)s")

    def test_key_matches_real_name_for_streams_long_titles_and_video_ids(self):
        window = self.window(self.blocking)
        q = window._queue
        stream1 = q.add("https://cdn.test/s.mp4?id=1&token=a", "s", "best", self.tmp.name, filename_title="Isto")
        stream2 = q.add("https://cdn.test/s.mp4?id=1&token=b", "s", "best", self.tmp.name, filename_title="Isto")
        stream3 = q.add("https://cdn.test/s.mp4?id=2", "s", "best", self.tmp.name, filename_title="Isto")
        self.assertEqual(window._output_key(stream1), window._output_key(stream2))  # isti fajl
        self.assertNotEqual(window._output_key(stream1), window._output_key(stream3))

        same_video = q.add("https://v/a", "Prvi", "best", self.tmp.name, video_id="aaa")
        other_link = q.add("https://kratko/aaa", "Prvi", "best", self.tmp.name, video_id="aaa")
        self.assertEqual(window._output_key(same_video), window._output_key(other_link))  # „Prvi [aaa]"

        window._name_template = "title"  # „Samo naslov": yt-dlp uzima prvih 150 bajtova naslova
        base = "Dugačak naslov " * 12
        long1 = q.add("https://v/1", base + "prvi dio", "best", self.tmp.name)
        long2 = q.add("https://v/2", base + "drugi dio", "best", self.tmp.name)
        self.assertEqual(window._output_key(long1), window._output_key(long2))

    def test_two_links_of_the_same_video_never_download_at_once(self):
        window = self.window(self.blocking, parallel=2)
        self.add(window, "https://v/a", "https://kratko/aaa")
        window._start_all()
        self.assertTrue(wait_until(lambda: len(self.started) == 1))
        time.sleep(0.2)
        app.processEvents()
        self.assertEqual(len(self.started), 1)  # drugi link istog videa čeka prvi
        self.release.set()
        self.assertTrue(wait_until(lambda: len(self.started) == 2))

    def test_playlist_names_that_share_a_real_folder_wait_for_each_other(self):
        window = self.window(self.blocking, parallel=2)
        prefix = "P" * 80
        for url, title in (("https://v/a", prefix + " prvi"), ("https://kratko/aaa", prefix + " drugi")):
            result = ProbeResult(title, (Entry(url, "Prvi", video_id="aaa"),), True)
            window._on_probed(result, self.tmp.name, {}, False)
        first, second = window._queue.items()
        paths = [presets.build_ydl_options(presets.get_preset(item.preset_key), item.output_dir,
                                          item.subfolder)["outtmpl"] for item in (first, second)]
        self.assertEqual(paths[0], paths[1])  # različiti izvorni nazivi, ali isti stvarni folder
        window._start_all()
        try:
            self.assertTrue(wait_until(lambda: len(self.started) >= 1))
            self.assertFalse(wait_until(lambda: len(self.started) > 1, 0.2))
            self.assertEqual(second.status, ItemStatus.WAITING)
        finally:
            self.release.set()
            self.assertTrue(wait_until(lambda: not window._download_jobs))
        self.assertEqual(len(self.started), 2)
        self.assertTrue(all(item.status == ItemStatus.DONE for item in (first, second)))


class SectionChangeTest(Base):
    """Novi isječak je novi posao; prethodni video i MP3 ostaju sačuvani."""

    def test_change_and_remove_section_requeue_finished_download_without_deleting_files(self):
        sections = []

        def download(url, preset, output_dir, subfolder, on_progress, cancel_event, **extra):
            sections.append(extra.get("section"))
            path = Path(output_dir) / f"video-{len(sections)}.mp4"
            path.write_bytes(b"video")
            return DownloadResult(ItemStatus.DONE, filepath=str(path))

        window = self.window(download)
        [item] = self.add(window, "https://v/a")
        window._start_all()
        self.assertTrue(wait_until(lambda: item.status == ItemStatus.DONE and not window._download_jobs))
        old_video = Path(item.filepath)
        old_mp3 = Path(self.tmp.name) / "video-1.mp3"
        old_mp3.write_bytes(b"mp3")
        item.convert_state, item.convert_path = "done", str(old_mp3)
        item.convert_message, item.message = "stara poruka", "stara poruka"
        window.set_item_section(item.id, (10.0, 20.0))
        self.assertEqual(item.status, ItemStatus.WAITING)
        self.assertIsNone(item.filepath)
        self.assertEqual((item.convert_state, item.convert_path, item.convert_message), ("", None, ""))
        self.assertEqual(item.message, "")
        self.assertNotIn(item.id, window._sizes)
        saved = store.load_queue(store.queue_path(Path(self.tmp.name)))
        self.assertEqual(saved[0]["section"], [10.0, 20.0])
        self.assertIsNone(saved[0]["filepath"])
        self.assertEqual(old_video.read_bytes(), b"video")
        self.assertEqual(old_mp3.read_bytes(), b"mp3")
        # Dugme sada preuzima traženi isječak umjesto otvaranja prethodnog fajla.
        window._on_row_action(item.id)
        self.assertTrue(wait_until(lambda: item.status == ItemStatus.DONE and not window._download_jobs))
        self.assertEqual(sections, [None, (10.0, 20.0)])
        clipped = Path(item.filepath)
        window.set_item_section(item.id, None)
        self.assertEqual(item.status, ItemStatus.WAITING)
        self.assertIsNone(item.filepath)
        self.assertEqual(clipped.read_bytes(), b"video")
        self.assertEqual(old_video.read_bytes(), b"video")

    def test_unchanged_section_keeps_result_and_confirmation(self):
        window = self.window(self.quick)
        [item] = self.add(window, "https://v/a")
        window.set_item_section(item.id, (10.0, 20.0))
        window._start_all()
        self.assertTrue(wait_until(lambda: item.status == ItemStatus.DONE and not window._download_jobs))
        item.adult_ok = True
        before = vars(item).copy()
        sizes = window._sizes.copy()
        with mock.patch.object(window, "_save_queue") as save:
            window.set_item_section(item.id, (10, 20))
        self.assertEqual(vars(item), before)
        self.assertEqual(window._sizes, sizes)
        save.assert_not_called()

    def test_changed_section_resets_failed_cancelled_and_waiting_attempts(self):
        for status in (ItemStatus.FAILED, ItemStatus.CANCELLED, ItemStatus.WAITING):
            with self.subTest(status=status):
                window = self.window(self.quick)
                item = window._queue.add("https://v/a", "Prvi", "best", self.tmp.name, adult=True)
                window._append_row(item)
                item.status, item.message = status, "stara greška"
                item.adult_ok, item.auto_retries = True, 3
                window._retry_at[item.id] = time.monotonic() + 60
                window.set_item_section(item.id, (10, 20))
                self.assertEqual(item.status, ItemStatus.WAITING)
                self.assertEqual(item.message, "")
                self.assertEqual(item.auto_retries, 0)
                self.assertFalse(item.adult_ok)
                self.assertNotIn(item.id, window._retry_at)
                with mock.patch.object(window, "_ask_adult", return_value=False) as ask:
                    window._on_row_action(item.id)
                ask.assert_called_once()
                self.assertEqual(item.status, ItemStatus.WAITING)
                self.assertFalse(self.started)

    def test_active_download_cannot_change_section(self):
        window = self.window(self.blocking)
        [item] = self.add(window, "https://v/a")
        window._start_all()
        self.assertTrue(wait_until(lambda: bool(self.started)))
        try:
            before = vars(item).copy()
            window.set_item_section(item.id, (10, 20))
            self.assertEqual(vars(item), before)
        finally:
            self.release.set()
            self.assertTrue(wait_until(lambda: not window._download_jobs))

    def test_running_conversion_cannot_change_section(self):
        go = threading.Event()
        mp3 = Path(self.tmp.name) / "a.mp3"

        def convert_fn(source, on_progress=None, cancel_event=None, duration=None):
            go.wait(5)
            mp3.write_bytes(b"mp3")
            return str(mp3)

        window = self.window(self.quick, convert_fn=convert_fn)
        [item] = self.add(window, "https://v/a")
        window._start_all()
        self.assertTrue(wait_until(lambda: item.status == ItemStatus.DONE and not window._download_jobs))
        window._on_row_convert(item.id)
        try:
            self.assertIn(item.id, window._convert_jobs)
            before = vars(item).copy()
            window.set_item_section(item.id, (10, 20))
            self.assertEqual(vars(item), before)
        finally:
            go.set()
            self.assertTrue(wait_until(lambda: not window._convert_jobs))
        self.assertEqual(item.convert_state, "done")
        window.set_item_section(item.id, (10, 20))
        self.assertEqual(item.status, ItemStatus.WAITING)
        self.assertIsNone(item.convert_path)
        self.assertEqual(mp3.read_bytes(), b"mp3")


class ClosingTest(Base):
    """Nalaz 2: poslije potvrde zatvaranja ništa novo ne kreće."""

    def test_close_does_not_start_a_manually_queued_download(self):
        window = self.window(self.blocking, parallel=1)
        first, second = self.add(window, "https://v/a", "https://v/b")
        window._on_row_action(first.id)  # pokrenuto dugmetom u redu
        self.assertTrue(wait_until(lambda: first.status == ItemStatus.ACTIVE))
        window._on_row_action(second.id)  # zakazano „pokreni odmah", čeka slobodno mjesto
        self.assertIn(second.id, window._manual)
        with mock.patch("videodl.gui.QMessageBox.question", return_value=QMessageBox.StandardButton.Yes):
            window.close()
        app.processEvents()
        self.assertEqual([url for url, _ in self.started], ["https://v/a"])
        self.assertFalse(window._download_jobs)
        self.assertNotEqual(second.status, ItemStatus.ACTIVE)
        # I ono što stigne tek tokom zatvaranja (browser, zakazani ponovni pokušaj) ne kreće.
        window._manual.append(second.id)
        window._retry_after_drop(second.id)
        window._start_next()
        app.processEvents()
        self.assertEqual([url for url, _ in self.started], ["https://v/a"])


class AutosaveTest(Base):
    """Nalaz 3: red se sam čuva poslije dodavanja, promjene formata i brisanja (bez urednog zatvaranja)."""

    def saved(self):
        return store.load_queue(store.queue_path(Path(self.tmp.name)))

    def test_queue_survives_a_crash_without_close(self):
        window = self.window(self.blocking)
        [item] = self.add(window, "https://v/a")
        self.assertTrue(wait_until(lambda: [row["url"] for row in self.saved()] == ["https://v/a"], 3))
        window.set_item_preset(item.id, "mp3")
        self.assertTrue(wait_until(lambda: self.saved() and self.saved()[0].get("preset_key") == "mp3", 3))
        window._on_row_remove(item.id)
        self.assertTrue(wait_until(lambda: self.saved() == [], 3))  # obrisano se ne vraća poslije pada


class RemoveAllTest(Base):
    """Nalaz 4: „Ukloni sve" ne sakriva MP3 koji se još pravi; rezultat stiže u istoriju."""

    def test_remove_all_keeps_a_converting_row_and_its_mp3_reaches_history(self):
        go = threading.Event()
        mp3 = os.path.join(self.tmp.name, "a.mp3")

        def convert_fn(source, on_progress=None, cancel_event=None, duration=None):
            go.wait(5)
            Path(mp3).write_bytes(b"mp3")
            return mp3

        window = self.window(self.quick, convert_fn=convert_fn)
        [item] = self.add(window, "https://v/a")
        window._start_all()
        self.assertTrue(wait_until(lambda: item.status == ItemStatus.DONE))
        window._on_row_convert(item.id)
        self.assertIn(item.id, window._convert_jobs)
        window._remove_all()
        self.assertIsNotNone(window._queue.get(item.id))  # red ostaje dok MP3 ne bude gotov
        go.set()
        self.assertTrue(wait_until(lambda: item.convert_state == "done"))
        history = store.load_history(store.history_path(Path(self.tmp.name)))
        self.assertIn(mp3, [entry.filepath for entry in history])
        window._remove_all()
        self.assertIsNone(window._queue.get(item.id))  # poslije završetka se uklanja normalno


class RetryDelayTest(Base):
    """Nalaz 5: novi pokušaj poslije pucanja veze čeka svoj rok i kad se mjesto oslobodi ranije."""

    def test_retry_waits_even_when_another_download_frees_a_slot(self):
        attempts = {"https://v/a": 0}

        def download(url, preset, output_dir, subfolder, on_progress, cancel_event, **extra):
            self.started.append((url, time.monotonic()))
            if url == "https://v/a":
                attempts[url] += 1
                if attempts[url] == 1:
                    return DownloadResult(ItemStatus.FAILED, message="Unable to download: Read timed out")
            else:
                time.sleep(0.2)  # završava POSLIJE pucanja veze prvog, pa oslobodi mjesto
            return DownloadResult(ItemStatus.DONE, filepath=os.path.join(output_dir, url[-1] + ".mp4"))

        with mock.patch("videodl.gui.AUTO_RETRY_DELAY_MS", 800):
            window = self.window(download, parallel=2)
            self.add(window, "https://v/a", "https://v/b")
            window._start_all()
            self.assertTrue(wait_until(lambda: attempts["https://v/a"] == 2, 5))
        starts = [moment for url, moment in self.started if url == "https://v/a"]
        self.assertGreaterEqual(starts[1] - starts[0], 0.7)  # ne odmah kad se oslobodi mjesto


if __name__ == "__main__":
    unittest.main()
