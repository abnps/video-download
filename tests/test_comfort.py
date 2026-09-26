"""v0.9.0: tamna tema, obavještenje i napredak u traci zadataka, pretraga istorije, šablon imena fajla."""

import os
import tempfile
import time
import unittest
from pathlib import Path
from unittest import mock

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QSettings  # noqa: E402
from PySide6.QtGui import QPalette  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402
from yt_dlp import YoutubeDL  # noqa: E402

from videodl import theme  # noqa: E402
from videodl.download import DownloadResult  # noqa: E402
from videodl.gui import MainWindow, apply_theme, filter_history  # noqa: E402
from videodl.i18n import set_language  # noqa: E402
from videodl.jobs import ItemStatus  # noqa: E402
from videodl.presets import NAME_TEMPLATES, build_ydl_options, get_preset  # noqa: E402
from videodl.probe import Entry, ProbeResult  # noqa: E402
from videodl.store import HistoryEntry  # noqa: E402

app = QApplication.instance() or QApplication([])
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


class _Recorder:
    def __init__(self):
        self.calls = []

    def set(self, fraction, state=None):
        self.calls.append(("set", fraction))

    def clear(self):
        self.calls.append(("clear", None))


class WindowTestCase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.settings = QSettings(os.path.join(self.tmp.name, "s.ini"), QSettings.Format.IniFormat)
        self.settings.setValue("language", "bs")
        self.extras = []
        self.notes = []

    def window(self, result_for=None):
        def probe(url, http_headers=None):
            return ProbeResult(url.rsplit("/", 1)[-1], (Entry(url, url.rsplit("/", 1)[-1], None, 4),), False)

        def download(url, preset, output_dir, subfolder, on_progress, cancel_event, **extra):
            self.extras.append(extra)
            if result_for:
                return result_for(url)
            path = os.path.join(output_dir, url.rsplit("/", 1)[-1] + ".mp4")
            with open(path, "wb") as file:
                file.write(b"x")
            return DownloadResult(ItemStatus.DONE, filepath=path)

        window = MainWindow(settings=self.settings, probe_fn=probe, download_fn=download,
                            thumbnail_fetch=lambda u: None, data_dir_path=self.tmp.name)
        self.addCleanup(window.deleteLater)
        self.addCleanup(lambda: window.set_theme("light", save=False))
        window.set_output_dir(self.tmp.name)
        window._notifier = lambda title, body: self.notes.append((title, body))
        window._taskbar = _Recorder()
        return window

    def run_all(self, window, *names):
        before = len(window._queue.items())
        window.add_links_from_text(" ".join(f"https://v/{name}" for name in names))
        self.assertTrue(wait_until(lambda: len(window._queue.items()) == before + len(names)))
        window._start_all()
        self.assertTrue(wait_until(lambda: all(i.status not in (ItemStatus.WAITING, ItemStatus.ACTIVE)
                                               for i in window._queue.items()) and not window._download_jobs))


class ThemeTest(WindowTestCase):
    def test_dark_theme_changes_everything_and_is_remembered(self):
        window = self.window()
        window.set_theme("dark")
        self.assertTrue(theme.is_dark())
        self.assertIn(theme.DARK["bg"], window.styleSheet())
        self.assertEqual(app.palette().color(QPalette.ColorRole.Window).name(), theme.DARK["bg"])
        self.assertEqual(self.settings.value("theme"), "dark")
        checked = [a.data() for a in window.theme_actions.actions() if a.isChecked()]
        self.assertEqual(checked, ["dark"])
        window.add_links_from_text("https://v/a")
        self.assertTrue(wait_until(lambda: len(window._rows) == 1))
        row = next(iter(window._rows.values()))
        self.assertIn(theme.DARK["link"], row.format_link.text())

        window.set_theme("light")
        self.assertIn(theme.LIGHT["link"], row.format_link.text())
        self.assertEqual(app.palette().color(QPalette.ColorRole.Window).name(), theme.LIGHT["bg"])

    def test_same_as_windows_follows_the_system(self):
        window = self.window()
        with mock.patch("videodl.gui.system_prefers_dark", return_value=True):
            window.set_theme("system")
        self.assertTrue(theme.is_dark())
        with mock.patch("videodl.gui.system_prefers_dark", return_value=False):
            window._on_system_scheme()
        self.assertFalse(theme.is_dark())
        window.set_theme("light")
        self.assertFalse(window._follows_system)

    def test_every_theme_has_the_same_colours(self):
        self.assertEqual(set(theme.LIGHT), set(theme.DARK))
        apply_theme(app)


class NotifyAndTaskbarTest(WindowTestCase):
    def test_notification_and_taskbar_after_whole_batch(self):
        window = self.window()
        self.run_all(window, "a", "b")
        self.assertTrue(wait_until(lambda: self.notes))
        self.assertEqual(self.notes, [("Preuzimanja su završena", "Završeno: 2")])
        sets = [value for kind, value in window._taskbar.calls if kind == "set"]
        self.assertTrue(sets and all(0.0 <= value <= 1.0 for value in sets))
        self.assertEqual(window._taskbar.calls[-1], ("clear", None))
        self.assertEqual(window._batch, {})

    def test_single_download_names_the_video_and_failures_are_counted(self):
        window = self.window()
        self.run_all(window, "jedan")
        self.assertEqual(self.notes, [("Preuzimanje je završeno", "jedan")])

        failing = self.window(lambda url: DownloadResult(ItemStatus.FAILED, message="HTTP Error 404")
                              if url.endswith("lose") else DownloadResult(ItemStatus.DONE, filepath=__file__))
        self.notes.clear()
        self.run_all(failing, "dobar", "lose")
        self.assertEqual(self.notes, [("Preuzimanja su završena", "Završeno: 1 · Neuspjelo: 1")])

    def test_no_notification_when_switched_off_or_stopped_by_hand(self):
        window = self.window()
        window._set_option("_notify_done", False)
        self.assertEqual(self.settings.value("notify_done", type=bool), False)
        self.run_all(window, "a")
        self.assertEqual(self.notes, [])

        window._set_option("_notify_done", True)
        window._batch = {99: 0.3}
        window._stop_all()
        self.assertEqual(self.notes, [])
        self.assertEqual(window._taskbar.calls[-1], ("clear", None))

    def test_no_notification_while_user_looks_at_the_window(self):
        window = self.window()
        with mock.patch.object(window, "isActiveWindow", return_value=True):
            self.run_all(window, "a")
        self.assertEqual(self.notes, [])


class HistorySearchTest(unittest.TestCase):
    def entries(self):
        return [HistoryEntry("https://youtu.be/1", "Dino Merlin – Kad si rekla", "C:/x/Kad si rekla.mp3", 5, 1.0),
                HistoryEntry("https://vimeo.com/2", "Planine Bosne", __file__, 9, 2.0),
                HistoryEntry("https://youtu.be/3", "Stari snimak", "C:/nema/snimak.mp4", 9, 3.0)]

    def test_words_kind_and_missing_files(self):
        entries = self.entries()
        self.assertEqual([e.title for e in filter_history(entries, "merlin REKLA")], ["Dino Merlin – Kad si rekla"])
        self.assertEqual([e.title for e in filter_history(entries, "vimeo")], ["Planine Bosne"])
        self.assertEqual(len(filter_history(entries, "")), 3)
        self.assertEqual([e.title for e in filter_history(entries, kind="audio")], ["Dino Merlin – Kad si rekla"])
        self.assertEqual(len(filter_history(entries, kind="video")), 2)
        self.assertEqual([e.title for e in filter_history(entries, kind="missing")],
                         ["Dino Merlin – Kad si rekla", "Stari snimak"])
        self.assertEqual(filter_history(entries, "nepostojece"), [])

    def test_dialog_filters_as_you_type(self):
        from videodl import store
        from videodl.gui import HistoryDialog
        from videodl.jobs import QueueItem

        with tempfile.TemporaryDirectory() as folder:
            path = store.history_path(__import__("pathlib").Path(folder))
            for index, title in enumerate(("Prvi video", "Druga pjesma", "Treći video")):
                item = QueueItem(index, f"https://v/{index}", title, "best", folder)
                item.filepath = os.path.join(folder, f"{index}.mp4")
                store.append_history(item, path, 1)
            dialog = HistoryDialog(path)
            self.addCleanup(dialog.deleteLater)
            self.assertEqual(dialog.list.count(), 3)
            dialog.search.setText("video")
            self.assertEqual(dialog.list.count(), 2)
            self.assertEqual(dialog.count_label.text(), "Prikazano 2 od 3")
            dialog.search.setText("nema toga")
            self.assertEqual(dialog.list.item(0).text(), "Ništa ne odgovara pretrazi.")
            self.assertFalse(dialog.open_button.isEnabled())


class FileNameTest(WindowTestCase):
    INFO = {"title": "Pjesma", "id": "abc", "ext": "mp3", "artist": "Dino Merlin", "channel": "Kanal X",
            "upload_date": "20240315"}

    def name(self, key, info):
        options = build_ydl_options(get_preset("mp3"), "C:/izlaz", name_template=key)
        with YoutubeDL({"quiet": True}) as ydl:
            return os.path.basename(ydl.evaluate_outtmpl(options["outtmpl"], info))

    def test_templates(self):
        expected = {"title_id": "Pjesma [abc].mp3", "title": "Pjesma.mp3", "artist_title": "Dino Merlin - Pjesma.mp3",
                    "channel_title": "Kanal X - Pjesma.mp3", "date_title": "2024-03-15 Pjesma.mp3"}
        self.assertEqual(set(expected), set(NAME_TEMPLATES))
        for key, name in expected.items():
            with self.subTest(key=key):
                self.assertEqual(self.name(key, self.INFO), name)
                # Bez izvođača, kanala ili datuma ostaje samo naslov (bez „NA - ").
                bare = self.name(key, {"title": "Pjesma", "id": "abc", "ext": "mp3"})
                self.assertIn(bare, ("Pjesma.mp3", "Pjesma [abc].mp3"))

    def test_choice_is_remembered_and_passed_to_download(self):
        window = self.window()
        action = next(a for a in window.name_actions.actions() if a.data() == "artist_title")
        action.trigger()
        self.assertEqual(self.settings.value("name_template"), "artist_title")
        self.run_all(window, "a")
        self.assertEqual(self.extras[-1].get("name_template"), "artist_title")

        window._set_option("_name_template", "title_id")
        self.run_all(window, "b")
        self.assertNotIn("name_template", self.extras[-1])  # zadano ime se ne šalje posebno


if __name__ == "__main__":
    unittest.main()


class CleanupAndNoticeTest(WindowTestCase):
    def test_only_our_old_cookie_files_are_removed(self):
        import time as clock

        from videodl.browser import remove_stale_cookie_files

        folder = Path(self.tmp.name)
        old = folder / "videodl-cookies-stari.txt"
        fresh = folder / "videodl-cookies-aktivni.txt"
        foreign = folder / "tudji-cookies.txt"
        for path in (old, fresh, foreign):
            path.write_text("x", encoding="utf-8")
        hour_ago = clock.time() - 2 * 60 * 60
        os.utime(old, (hour_ago, hour_ago))
        os.utime(foreign, (hour_ago, hour_ago))
        self.assertEqual(remove_stale_cookie_files(str(folder)), 1)
        self.assertEqual(sorted(p.name for p in folder.iterdir() if p.suffix == ".txt"),
                         ["tudji-cookies.txt", "videodl-cookies-aktivni.txt"])

    def test_thumbnail_cache_is_limited(self):
        from PySide6.QtGui import QColor, QImage

        from videodl import gui

        window = self.window()
        image = QImage(16, 9, QImage.Format.Format_RGB32)
        image.fill(QColor("red"))
        with mock.patch.object(gui, "THUMBNAIL_CACHE_MAX", 3):
            for index in range(6):
                window._on_thumbnail(f"https://img/{index}.jpg", image)
        self.assertEqual(list(window._thumbnail_cache), [f"https://img/{i}.jpg" for i in (3, 4, 5)])

    def test_clipboard_notice_is_shown_once_and_can_turn_watching_off(self):
        window = self.window()
        self.assertTrue(window._watch_clipboard)
        self.assertFalse(window.clipboard_notice.isHidden())  # prvo pokretanje: objašnjenje je vidljivo
        self.assertIn("kopirane linkove", window.clipboard_notice_label.text())
        window.clipboard_notice_off.click()
        self.assertTrue(window.clipboard_notice.isHidden())
        self.assertFalse(window._watch_clipboard)
        self.assertEqual(self.settings.value("watch_clipboard", type=bool), False)

        again = self.window()  # sljedeće pokretanje: bez obavijesti
        self.assertTrue(again.clipboard_notice.isHidden())
