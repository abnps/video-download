"""GUI test bez ekrana: pravi prozor i red, lažno čitanje linkova, preuzimanje i sličice."""

import os
import tempfile
from pathlib import Path
import threading
import time
import unittest
from unittest import mock

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QBuffer, QByteArray, QIODevice, QSettings  # noqa: E402
from PySide6.QtGui import QColor, QImage  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

from videodl.browser import BrowserRequest, Cookie  # noqa: E402
from videodl.download import DOWNLOADING, PROCESSING, DownloadResult, Progress  # noqa: E402
from videodl.gui import (  # noqa: E402
    MainWindow, apply_theme, extract_urls, format_eta, format_progress, format_speed,
)
from videodl.i18n import get_language, set_language  # noqa: E402
from videodl.jobs import ItemStatus, QueueItem  # noqa: E402
from videodl.probe import Entry, ProbeResult  # noqa: E402
from videodl.widgets import format_duration, format_size  # noqa: E402
from videodl.ytdl import NotMediaError  # noqa: E402

app = QApplication.instance() or QApplication([])
apply_theme(app)
set_language("bs")


def wait_until(condition, timeout=5.0):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        app.processEvents()
        if condition():
            return True
        time.sleep(0.01)
    app.processEvents()
    return condition()


def png_bytes() -> bytes:
    image = QImage(64, 36, QImage.Format.Format_RGB32)
    image.fill(QColor("#e53935"))
    data = QByteArray()
    buffer = QBuffer(data)
    buffer.open(QIODevice.OpenModeFlag.WriteOnly)
    image.save(buffer, "PNG")
    return bytes(data)


def fake_probe(url, http_headers=None):
    if "lista" in url:
        return ProbeResult("Moja lista", (
            Entry("https://v/1", "Major Lazer – Cold Water (Official Lyric Video)", "https://img/1.jpg", 189),
            Entry("https://v/2", "Peace Is The Mission (Extended)", None, 1275)), True)
    if "lose" in url:
        raise RuntimeError("ERROR: Unsupported URL")
    return ProbeResult("Jedan", (Entry(url, "Jedan", None, 61),), False)


class FormattingTest(unittest.TestCase):
    def test_formatting(self):
        self.assertEqual(format_speed(3.2 * 1024 * 1024), "3,2 MB/s")
        self.assertEqual(format_eta(7), "7 s")
        self.assertEqual(format_eta(185), "3:05")
        self.assertEqual(format_eta(3725), "1:02:05")
        text = format_progress(Progress(DOWNLOADING, 0.456, 2048, 12, "video"))
        self.assertEqual(text, "Preuzimanje (video) · 46% · 2,0 KB/s · još 12 s")
        self.assertEqual(format_progress(Progress(PROCESSING, None, label="Konverzija zvuka")),
                         "Konverzija zvuka…")
        self.assertEqual(format_duration(189), "3:09")
        self.assertEqual(format_duration(3725), "1:02:05")
        self.assertEqual(format_duration(None), "")
        self.assertEqual(format_size(int(23.8 * 1024 * 1024)), "23,8 MB")
        set_language("en")
        try:
            self.assertEqual((format_speed(3.2 * 1024 * 1024), format_size(int(23.8 * 1024 * 1024))),
                             ("3.2 MB/s", "23.8 MB"))
        finally:
            set_language("bs")

    def test_extract_urls_from_mixed_text(self):
        text = "Pogledaj https://youtu.be/abc, i (https://vimeo.com/1). Isto: https://youtu.be/abc\nnije-link"
        self.assertEqual(extract_urls(text), ["https://youtu.be/abc", "https://vimeo.com/1"])
        self.assertEqual(extract_urls("bez linka"), [])


class MainWindowTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.settings = QSettings(os.path.join(self.tmp.name, "settings.ini"), QSettings.Format.IniFormat)
        self.settings.setValue("language", "bs")
        self.release = threading.Event()
        self.calls = []
        self.extras = []

    def tearDown(self):
        self.release.set()
        self.tmp.cleanup()

    def make_window(self, download_fn, probe_fn=fake_probe, thumbnail_fetch=lambda url: None, parallel=1):
        window = MainWindow(settings=self.settings, probe_fn=probe_fn, download_fn=download_fn,
                            thumbnail_fetch=thumbnail_fetch, data_dir_path=self.tmp.name)
        window.set_output_dir(self.tmp.name)
        window.set_parallel(parallel)
        self.addCleanup(window.deleteLater)
        return window

    def quick_download(self, url, preset, output_dir, subfolder, on_progress, cancel_event, **extra):
        self.calls.append((url, preset.key, output_dir, subfolder))
        self.extras.append(extra)
        on_progress(Progress(DOWNLOADING, 0.5, 1024, 3))
        return DownloadResult(ItemStatus.DONE, filepath=os.path.join(output_dir, f"{url[-1]}.mp4"))

    def blocking_download(self, url, preset, output_dir, subfolder, on_progress, cancel_event, **extra):
        self.calls.append((url, preset.key, output_dir, subfolder))
        on_progress(Progress(DOWNLOADING, 0.1, None, None))
        while not cancel_event.is_set() and not self.release.is_set():
            time.sleep(0.01)
        if cancel_event.is_set():
            return DownloadResult(ItemStatus.CANCELLED, message="Otkazano")
        return DownloadResult(ItemStatus.DONE, filepath=url)

    def statuses(self, window):
        return [item.status for item in window._queue.items()]

    def test_pasted_links_wait_for_download_button(self):
        window = self.make_window(self.quick_download)
        self.assertEqual(window.stack.currentIndex(), 0)  # prazan ekran
        self.assertFalse(window.download_button.isEnabled())
        window.preset_combo.setCurrentIndex(window.preset_combo.findData("mp3"))
        QApplication.clipboard().setText("https://v/lista")
        window._paste_from_clipboard()

        self.assertTrue(wait_until(lambda: len(window._queue.items()) == 2))
        self.assertEqual(window.stack.currentIndex(), 1)
        time.sleep(0.1)
        app.processEvents()
        self.assertEqual(self.calls, [])  # kao u uzoru: tek „Preuzmi" pokreće
        self.assertEqual(window.download_button.text(), "Preuzmi")
        self.assertTrue(window.download_button.isEnabled())

        window.download_button.click()
        self.assertTrue(wait_until(lambda: self.statuses(window) == [ItemStatus.DONE, ItemStatus.DONE]))
        self.assertEqual(self.calls, [
            ("https://v/1", "mp3", self.tmp.name, "Moja lista"),
            ("https://v/2", "mp3", self.tmp.name, "Moja lista"),
        ])
        row = window._rows[window._queue.items()[0].id]
        self.assertTrue(row.status_label.text().startswith("Završeno"))
        self.assertEqual(row.action_button.property("kind"), "folder")
        self.assertIn("završeno: 2", window.summary_label.text())
        self.assertEqual(window.download_button.text(), "Preuzmi")
        self.assertEqual(self.settings.value("preset_key"), "mp3")

        window._clear_finished()
        self.assertEqual(window._rows, {})
        self.assertEqual(window.stack.currentIndex(), 0)

    def test_play_button_opens_downloaded_file(self):
        target = os.path.join(self.tmp.name, "a.mp4")

        def download_real_file(url, preset, output_dir, subfolder, on_progress, cancel_event, **extra):
            with open(target, "wb") as file:
                file.write(b"x" * 2048)
            return DownloadResult(ItemStatus.DONE, filepath=target)

        window = self.make_window(download_real_file)
        window.add_links_from_text("https://v/a")
        self.assertTrue(wait_until(lambda: len(window._queue.items()) == 1))
        item = window._queue.items()[0]
        row = window._rows[item.id]
        self.assertTrue(row.play_button.isHidden())  # nema šta da se pusti prije preuzimanja

        window._start_all()
        self.assertTrue(wait_until(lambda: item.status == ItemStatus.DONE))
        self.assertFalse(row.play_button.isHidden())
        self.assertEqual(row.play_button.toolTip(), "Pusti video")
        self.assertIn("2 KB", row.status_label.text())
        if os.environ.get("VIDEODL_SCREENSHOT"):
            window.resize(820, 200)
            window.show()
            wait_until(lambda: False, timeout=0.2)
            window.grab().save(os.environ["VIDEODL_SCREENSHOT"].replace(".png", "-pusti.png"))
        with mock.patch("videodl.gui.play_file") as play:
            row.play_button.click()
        play.assert_called_once_with(target)

        os.remove(target)
        with mock.patch("videodl.gui.play_file") as play:
            row.play_button.click()
        play.assert_not_called()
        self.assertIn("ne postoji", window.status_label.text())

    def test_invalid_clipboard_and_probe_error_are_reported(self):
        window = self.make_window(self.quick_download)
        QApplication.clipboard().setText("nije link")
        window._paste_from_clipboard()
        self.assertIn("nema linka", window.status_label.text())

        window.add_links_from_text("https://v/lose")
        self.assertTrue(wait_until(lambda: "Unsupported URL" in window.status_label.text()))
        self.assertNotIn("ERROR", window.status_label.text())
        self.assertTrue(wait_until(lambda: not window._probe_jobs))

        # Neuspio link je vidljiv crveni red, a „Pokušaj ponovo" ga daje yt-dlp-u direktno.
        [failed] = window._queue.items()
        row = window._rows[failed.id]
        self.assertEqual(failed.status, ItemStatus.FAILED)
        self.assertIn("Unsupported URL", row.status_label.text())
        self.assertEqual(row.action_button.property("kind"), "retry")
        row.action_button.click()
        self.assertTrue(wait_until(lambda: failed.status == ItemStatus.DONE))
        self.assertEqual(self.calls[0][0], "https://v/lose")

    def test_stop_then_row_retry_downloads_only_that_item(self):
        window = self.make_window(self.blocking_download)
        window.add_links_from_text("https://v/a https://v/b")
        self.assertTrue(wait_until(lambda: len(window._queue.items()) == 2))
        first, second = window._queue.items()
        window._start_all()
        self.assertTrue(wait_until(lambda: "10%" in window._rows[first.id].status_label.text()))
        self.assertEqual(window.download_button.text(), "Zaustavi")
        self.assertEqual(window._rows[first.id].action_button.property("kind"), "stop")

        window.download_button.click()
        self.assertTrue(wait_until(lambda: first.status == ItemStatus.CANCELLED))
        self.assertEqual(second.status, ItemStatus.WAITING)
        self.assertEqual(window._download_jobs, {})
        self.assertEqual(window.download_button.text(), "Preuzmi")
        self.assertEqual(window._rows[first.id].action_button.property("kind"), "retry")

        self.release.set()
        window._rows[first.id].action_button.click()
        self.assertTrue(wait_until(lambda: first.status == ItemStatus.DONE))
        time.sleep(0.1)
        app.processEvents()
        self.assertEqual(second.status, ItemStatus.WAITING)  # pokrenut je samo taj red

        window._start_all()
        self.assertTrue(wait_until(lambda: second.status == ItemStatus.DONE))
        self.assertEqual([c[0] for c in self.calls], ["https://v/a", "https://v/a", "https://v/b"])

    def reading_download(self, url, preset, output_dir, subfolder, on_progress, cancel_event, **extra):
        """Yt-dlp još čita informacije o videu: napredak se ne javlja i prekid tu ne djeluje."""
        self.calls.append((url, preset.key, output_dir, subfolder))
        while not self.release.is_set():
            time.sleep(0.01)
        if cancel_event.is_set():
            return DownloadResult(ItemStatus.CANCELLED)
        return DownloadResult(ItemStatus.DONE, filepath=url)

    def test_stop_while_reading_link_reacts_at_once(self):
        window = self.make_window(self.reading_download)
        window.add_links_from_text("https://v/a")
        self.assertTrue(wait_until(lambda: len(window._queue.items()) == 1))
        item = window._queue.items()[0]
        window._start_all()
        self.assertTrue(wait_until(lambda: item.status == ItemStatus.ACTIVE))

        window.download_button.click()  # nit još visi na čitanju linka
        self.assertEqual(item.status, ItemStatus.CANCELLED)  # bez čekanja
        self.assertEqual(window._download_jobs, {})
        self.assertEqual(window.download_button.text(), "Preuzmi")

        # Kasni odgovor napuštene niti ne smije pregaziti novi pokušaj.
        self.release.set()
        time.sleep(0.2)
        app.processEvents()
        window._rows[item.id].action_button.click()
        self.assertTrue(wait_until(lambda: item.status == ItemStatus.DONE))

    def test_stop_while_reading_links_drops_pending_results(self):
        started = threading.Event()

        def slow_probe(url, **access):
            started.set()
            self.release.wait(5)
            return ProbeResult("Kasni", (Entry(url, "Kasni"),), is_playlist=False)

        window = self.make_window(self.quick_download, probe_fn=slow_probe)
        window.add_links_from_text("https://v/sporo")
        self.assertTrue(wait_until(started.is_set))
        window.download_button.click()  # „Zaustavi" dok traje čitanje
        self.release.set()
        time.sleep(0.3)
        app.processEvents()
        self.assertEqual(window._queue.items(), [])  # rezultat se više ne koristi

    def test_two_downloads_run_at_once_when_allowed(self):
        window = self.make_window(self.blocking_download, parallel=2)
        window.add_links_from_text("https://v/a https://v/b https://v/c")
        self.assertTrue(wait_until(lambda: len(window._queue.items()) == 3))
        first, second, third = window._queue.items()
        window._start_all()
        self.assertTrue(wait_until(lambda: len(window._download_jobs) == 2))
        self.assertEqual([first.status, second.status, third.status],
                         [ItemStatus.ACTIVE, ItemStatus.ACTIVE, ItemStatus.WAITING])
        self.assertIn("2", window.summary_label.text())

        self.release.set()  # oba završavaju, treći kreće sam
        self.assertTrue(wait_until(lambda: third.status == ItemStatus.DONE))
        self.assertEqual(window._download_jobs, {})

    def test_stop_cancels_every_running_download(self):
        window = self.make_window(self.blocking_download, parallel=2)
        window.add_links_from_text("https://v/a https://v/b")
        self.assertTrue(wait_until(lambda: len(window._queue.items()) == 2))
        window._start_all()
        self.assertTrue(wait_until(lambda: len(window._download_jobs) == 2))
        window.download_button.click()
        self.assertTrue(wait_until(lambda: self.statuses(window) == [ItemStatus.CANCELLED, ItemStatus.CANCELLED]))
        self.assertEqual(window._download_jobs, {})

    def test_broken_connection_retries_by_itself(self):
        attempts = []

        def flaky(url, preset, output_dir, subfolder, on_progress, cancel_event, **extra):
            attempts.append(url)
            if len(attempts) < 3:
                return DownloadResult(ItemStatus.FAILED, message="Unable to download video data: Connection reset")
            return DownloadResult(ItemStatus.DONE, filepath=os.path.join(output_dir, "a.mp4"))

        window = self.make_window(flaky)
        with mock.patch("videodl.gui.AUTO_RETRY_DELAY_MS", 10):
            window.add_links_from_text("https://v/a")
            self.assertTrue(wait_until(lambda: len(window._queue.items()) == 1))
            item = window._queue.items()[0]
            window._start_all()
            self.assertTrue(wait_until(lambda: item.status == ItemStatus.DONE, timeout=10))
        self.assertEqual((len(attempts), item.auto_retries), (3, 2))

    def test_other_errors_are_not_retried(self):
        def refused(url, preset, output_dir, subfolder, on_progress, cancel_event, **extra):
            self.calls.append(url)
            return DownloadResult(ItemStatus.FAILED, message="Unsupported URL: https://v/a")

        window = self.make_window(refused)
        window.add_links_from_text("https://v/a")
        self.assertTrue(wait_until(lambda: len(window._queue.items()) == 1))
        item = window._queue.items()[0]
        window._start_all()
        self.assertTrue(wait_until(lambda: item.status == ItemStatus.FAILED))
        time.sleep(0.2)
        app.processEvents()
        self.assertEqual((len(self.calls), item.auto_retries), (1, 0))

    def test_copied_link_is_caught_from_clipboard(self):
        window = self.make_window(self.quick_download)
        QApplication.clipboard().setText("https://v/kopirano")
        self.assertTrue(wait_until(lambda: len(window._queue.items()) == 1))
        self.assertEqual(self.calls, [])  # samo u redu, preuzimanje čeka „Preuzmi"

        # Isti tekst po drugi put ne dodaje ništa novo.
        window._on_clipboard_change()
        time.sleep(0.1)
        app.processEvents()
        self.assertEqual(len(window._queue.items()), 1)

        # Isključeno hvatanje: kopiran link se ignoriše.
        window.set_watch_clipboard(False)
        QApplication.clipboard().setText("https://v/drugi")
        time.sleep(0.2)
        app.processEvents()
        self.assertEqual(len(window._queue.items()), 1)
        self.assertEqual(self.settings.value("watch_clipboard"), False)

    def test_text_without_link_in_clipboard_is_ignored(self):
        window = self.make_window(self.quick_download)
        QApplication.clipboard().setText("obična bilješka bez linka")
        time.sleep(0.2)
        app.processEvents()
        self.assertEqual(window._queue.items(), [])

    def test_copied_link_that_is_not_media_makes_no_row(self):
        probed = []

        def probe(url, http_headers=None):
            probed.append(url)
            if "preuzmi" in url:
                raise NotMediaError(url)  # npr. link bez ekstenzije koji vodi na .zip
            return fake_probe(url)

        window = self.make_window(self.quick_download, probe_fn=probe)
        exe = "https://github.com/abnps/video-download/releases/download/v0.7.7/VideoDownload-Setup-0.7.7.exe"
        QApplication.clipboard().setText(exe)
        self.assertTrue(wait_until(lambda: "preskočeno" in window.status_label.text()))
        self.assertEqual(probed, [])  # .exe se ne šalje ni na čitanje

        QApplication.clipboard().setText("https://x.test/preuzmi?id=7")
        self.assertTrue(wait_until(lambda: probed == ["https://x.test/preuzmi?id=7"] and not window._probe_jobs))
        self.assertIn("preskočeno", window.status_label.text())
        self.assertEqual(window._queue.items(), [])

        # Pravi video iz clipboarda i dalje dolazi u red.
        QApplication.clipboard().setText("https://v/kopirano")
        self.assertTrue(wait_until(lambda: len(window._queue.items()) == 1))

    def test_pasted_or_browser_link_that_is_not_media_makes_no_row_either(self):
        from videodl.probe import probe  # pravo čitanje: .exe odbija bez interneta

        window = self.make_window(self.quick_download, probe_fn=probe)
        QApplication.clipboard().setText("https://x.test/Setup.exe")
        window._paste_from_clipboard()  # dugme „Zalijepi"
        self.assertTrue(wait_until(lambda: "preskočeno" in window.status_label.text() and not window._probe_jobs))
        window._on_browser_request(BrowserRequest("https://x.test/arhiva.zip", "Arhiva"))
        self.assertTrue(wait_until(lambda: not window._probe_jobs))
        self.assertIn("arhiva.zip", window.status_label.text())
        self.assertEqual(window._queue.items(), [])
        self.assertEqual(window._rows, {})

    def test_old_exe_card_is_not_restored(self):
        from videodl import store

        store.save_queue([
            QueueItem(1, "https://github.com/abnps/video-download/releases/download/v0.7.7/VideoDownload-Setup-0.7.7.exe",
                      "Setup", "best", self.tmp.name),
            QueueItem(2, "https://v/pravi", "Pravi video", "best", self.tmp.name)],
            store.queue_path(Path(self.tmp.name)))
        window = self.make_window(self.quick_download)
        self.assertEqual([item.url for item in window._queue.items()], ["https://v/pravi"])

    def test_queue_survives_restart_and_history_is_written(self):
        window = self.make_window(self.quick_download)
        window.add_links_from_text("https://v/a https://v/b")
        self.assertTrue(wait_until(lambda: len(window._queue.items()) == 2))
        first = window._queue.items()[0]
        window._rows[first.id].action_button.click()  # preuzmi samo prvi
        self.assertTrue(wait_until(lambda: first.status == ItemStatus.DONE))
        window.close()

        # Novi prozor sa istim folderom podataka: nedovršeno se vraća, gotovo ne.
        again = self.make_window(self.quick_download)
        urls = [item.url for item in again._queue.items()]
        self.assertEqual(urls, ["https://v/b"])
        self.assertEqual(again._queue.items()[0].status, ItemStatus.WAITING)

        from videodl import store
        history = store.load_history(store.history_path(Path(self.tmp.name)))
        self.assertEqual([entry.url for entry in history], ["https://v/a"])

    def test_browser_request_can_ask_for_mp3(self):
        window = self.make_window(self.quick_download)
        window.preset_combo.setCurrentIndex(window.preset_combo.findData("best"))
        window.browser_request.emit(BrowserRequest(page_url="https://v/pjesma", page_title="Pjesma",
                                                   media_url="https://v/pjesma.m3u8", preset="mp3"))
        self.assertTrue(wait_until(lambda: self.statuses(window) == [ItemStatus.DONE]))
        item = window._queue.items()[0]
        self.assertEqual((item.preset_key, item.custom_format), ("mp3", True))
        self.assertEqual(self.calls[0][1], "mp3")

        # Promjena glavnog formata ne dira stavku koja je došla sa izabranim formatom.
        window.preset_combo.setCurrentIndex(window.preset_combo.findData("720p"))
        self.assertEqual(item.preset_key, "mp3")

    def test_browser_page_request_with_mp3_marks_every_item(self):
        window = self.make_window(self.quick_download)
        window.browser_request.emit(BrowserRequest(page_url="https://v/lista", page_title="Lista", preset="mp3"))
        self.assertTrue(wait_until(lambda: len(window._queue.items()) == 2))
        self.assertEqual({item.preset_key for item in window._queue.items()}, {"mp3"})

    def test_menu_options_reach_the_download(self):
        window = self.make_window(self.quick_download)
        window._set_option("_subtitles", True)
        window._set_option("_thumbnail_cover", True)
        window._set_option("_rate_limit", 2)
        window.add_links_from_text("https://v/a")
        self.assertTrue(wait_until(lambda: len(window._queue.items()) == 1))
        item = window._queue.items()[0]
        window.set_item_section(item.id, (150.0, 370.0))
        self.assertIn("2:30", window._rows[item.id].format_link.text())

        window._start_all()
        self.assertTrue(wait_until(lambda: item.status == ItemStatus.DONE))
        extra = self.extras[0]
        self.assertEqual(extra["section"], (150.0, 370.0))
        self.assertTrue(extra["subtitles"] and extra["thumbnail"])
        self.assertEqual(extra["subtitle_langs"][0], "bs")
        self.assertEqual(extra["ratelimit"], 2 * 1024 * 1024)  # jedno preuzimanje dobija cijeli limit
        self.assertTrue(window.subtitles_action.isChecked())

        window.set_parallel(2)  # dva istovremena dijele ukupni limit
        self.assertEqual(window._download_options(item)["ratelimit"], 1024 * 1024)

    def test_plain_download_gets_no_extra_options(self):
        window = self.make_window(self.quick_download)
        window.add_links_from_text("https://v/a")
        self.assertTrue(wait_until(lambda: len(window._queue.items()) == 1))
        window._start_all()
        self.assertTrue(wait_until(lambda: self.statuses(window) == [ItemStatus.DONE]))
        for key in ("section", "subtitles", "thumbnail", "ratelimit"):
            self.assertNotIn(key, self.extras[0])

    def test_whole_playlist_option_reaches_link_reading(self):
        seen = []

        def probe_fn(url, http_headers=None, whole_playlist=False):
            seen.append(whole_playlist)
            return fake_probe(url)

        window = self.make_window(self.quick_download, probe_fn=probe_fn)
        window.add_links_from_text("https://v/a")
        self.assertTrue(wait_until(lambda: len(seen) == 1))
        window._set_option("_whole_playlist", True)
        window.add_links_from_text("https://v/b")
        self.assertTrue(wait_until(lambda: len(seen) == 2))
        self.assertEqual(seen, [False, True])

    def test_options_and_clip_survive_restart(self):
        window = self.make_window(self.quick_download)
        window._set_option("_thumbnail_cover", True)
        window._set_option("_rate_limit", 5)
        window.add_links_from_text("https://v/a")
        self.assertTrue(wait_until(lambda: len(window._queue.items()) == 1))
        window.set_item_section(window._queue.items()[0].id, (10.0, 20.0))
        window.close()

        again = self.make_window(self.quick_download)
        self.assertTrue(again._thumbnail_cover)
        self.assertEqual(again._rate_limit, 5)
        self.assertEqual(again._queue.items()[0].section, (10.0, 20.0))

    def test_remove_active_row_cancels_and_removes(self):
        window = self.make_window(self.blocking_download)
        window.add_links_from_text("https://v/a https://v/b")
        self.assertTrue(wait_until(lambda: len(window._queue.items()) == 2))
        first, second = window._queue.items()
        window._rows[second.id].remove_button.click()
        self.assertEqual([i.id for i in window._queue.items()], [first.id])

        window._rows[first.id].action_button.click()  # pojedinačno pokretanje
        self.assertTrue(wait_until(lambda: first.status == ItemStatus.ACTIVE))
        window._rows[first.id].remove_button.click()
        self.assertTrue(wait_until(lambda: not window._queue.items()))
        self.assertEqual(window._rows, {})
        self.assertEqual(window._download_jobs, {})

    def test_format_change_applies_to_waiting_but_not_custom_items(self):
        window = self.make_window(self.quick_download)
        window.add_links_from_text("https://v/a https://v/b")
        self.assertTrue(wait_until(lambda: len(window._queue.items()) == 2))
        first, second = window._queue.items()
        window.set_item_preset(first.id, "m4a")
        self.assertIn("M4A", window._rows[first.id].format_link.text())

        window.preset_combo.setCurrentIndex(window.preset_combo.findData("720p"))
        self.assertEqual((first.preset_key, second.preset_key), ("m4a", "720p"))
        self.assertIn("MP4 720p", window._rows[second.id].format_link.text())

        window._start_all()
        self.assertTrue(wait_until(lambda: self.statuses(window) == [ItemStatus.DONE, ItemStatus.DONE]))
        window.set_item_preset(first.id, "mp3")  # drugi format već preuzetog videa: ponovo u red
        self.assertEqual(first.status, ItemStatus.WAITING)

    def test_browser_media_request_starts_only_that_item_with_headers(self):
        window = self.make_window(self.quick_download)
        window.add_links_from_text("https://v/zalijepljen")
        self.assertTrue(wait_until(lambda: len(window._queue.items()) == 1))
        window.preset_combo.setCurrentIndex(window.preset_combo.findData("720p"))
        headers = {"Referer": "https://sajt.ba/lekcija", "User-Agent": "UA"}
        # Emit iz druge niti, kao što radi lokalni most.
        threading.Thread(target=window.browser_request.emit, args=(BrowserRequest(
            "https://sajt.ba/lekcija", "Lekcija 3", "https://cdn.sajt.ba/a/index.m3u8", "hls", headers),)).start()

        self.assertTrue(wait_until(lambda: len(window._queue.items()) == 2
                                   and window._queue.items()[1].status == ItemStatus.DONE))
        pasted, browser_item = window._queue.items()
        self.assertEqual(pasted.status, ItemStatus.WAITING)
        self.assertEqual(browser_item.title, "Lekcija 3")
        self.assertEqual(self.calls, [("https://cdn.sajt.ba/a/index.m3u8", "720p", self.tmp.name, None)])
        self.assertEqual(self.extras, [{"http_headers": headers, "filename_title": "Lekcija 3"}])
        self.assertIn("Iz browsera", window.status_label.text())

    def test_browser_page_request_is_probed_with_headers_and_started(self):
        seen = []

        def probe_with_headers(url, http_headers=None):
            seen.append((url, http_headers))
            return ProbeResult("Video", (Entry(url, "Video"),), False)

        window = self.make_window(self.quick_download, probe_fn=probe_with_headers)
        window.browser_request.emit(BrowserRequest("https://www.youtube.com/watch?v=x", "YT", headers={"User-Agent": "UA"}))

        self.assertTrue(wait_until(lambda: window._queue.items()
                                   and window._queue.items()[0].status == ItemStatus.DONE))
        self.assertEqual(seen, [("https://www.youtube.com/watch?v=x", {"User-Agent": "UA"})])
        self.assertEqual(self.extras, [{"http_headers": {"User-Agent": "UA"}, "filename_title": None}])

    def test_browser_cookies_reach_probe_and_download(self):
        seen = []

        def probe_with_access(url, http_headers=None, cookies=()):
            seen.append(cookies)
            return ProbeResult("Storija", (Entry(url, "Storija"),), False)

        window = self.make_window(self.quick_download, probe_fn=probe_with_access)
        cookies = (Cookie(".instagram.com", "sessionid", "tajna", host_only=False),)
        window.browser_request.emit(BrowserRequest("https://www.instagram.com/stories/nalog/1/", "Priče",
                                                   headers={"User-Agent": "UA"}, cookies=cookies))
        self.assertTrue(wait_until(lambda: window._queue.items()
                                   and window._queue.items()[0].status == ItemStatus.DONE))
        self.assertEqual(seen, [cookies])
        self.assertEqual(self.extras[0]["cookies"], cookies)
        self.assertNotIn("tajna", repr(window._queue.items()[0]))

    def test_thumbnail_and_duration_are_shown(self):
        fetched = []

        def fetch(url):
            fetched.append(url)
            return png_bytes()

        window = self.make_window(self.quick_download, thumbnail_fetch=fetch)
        window.add_links_from_text("https://v/lista")
        self.assertTrue(wait_until(lambda: len(window._queue.items()) == 2))
        first, second = window._queue.items()
        self.assertTrue(wait_until(lambda: window._rows[first.id].thumbnail.has_pixmap()))
        self.assertFalse(window._rows[second.id].thumbnail.has_pixmap())  # nema sličice: zamjenska
        self.assertEqual(window._rows[second.id].thumbnail._duration, "21:15")
        self.assertEqual(fetched, ["https://img/1.jpg"])

    def test_settings_are_restored(self):
        self.settings.setValue("output_dir", r"D:\Filmovi")
        self.settings.setValue("preset_key", "720p")
        window = MainWindow(settings=self.settings, probe_fn=fake_probe, download_fn=self.quick_download,
                            thumbnail_fetch=lambda url: None)
        self.addCleanup(window.deleteLater)
        self.assertEqual(window.output_dir, r"D:\Filmovi")
        self.assertIn("Filmovi", window.folder_label.text())
        self.assertEqual(window.preset_combo.currentData(), "720p")

    def test_screenshots_render(self):
        target = os.environ.get("VIDEODL_SCREENSHOT")
        window = self.make_window(self.blocking_download, thumbnail_fetch=lambda url: png_bytes())
        window.resize(820, 440)
        window.show()
        wait_until(lambda: False, timeout=0.2)
        empty = window.grab()
        self.assertFalse(empty.isNull())
        if target:
            empty.save(target.replace(".png", "-prazno.png"))

        window.add_links_from_text("https://v/lista https://v/jedan")
        self.assertTrue(wait_until(lambda: len(window._queue.items()) == 3))
        window._start_all()
        self.assertTrue(wait_until(lambda: bool(window._download_jobs)))
        wait_until(lambda: False, timeout=0.3)
        full = window.grab()
        self.assertFalse(full.isNull())
        if target:
            full.save(target)
        window._stop_all()
        self.assertTrue(wait_until(lambda: not window._download_jobs))


if __name__ == "__main__":
    unittest.main()
