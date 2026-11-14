"""Titl iz govora u prozoru: prekidač u Postavkama (bez modela ostaje isključen), pregled titla poslije
preuzimanja (ispravke se čuvaju) i upis u sliku tek kad korisnik klikne „Upiši titl"."""

import os
import tempfile
import time
import unittest
from unittest import mock

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QSettings  # noqa: E402
from PySide6.QtWidgets import QApplication, QDialog  # noqa: E402

from videodl import speech, speech_dialogs  # noqa: E402
from videodl.download import DownloadResult  # noqa: E402
from videodl.gui import NAME_TEMPLATES, PARALLEL_CHOICES, RATE_CHOICES, MainWindow, apply_theme  # noqa: E402
from videodl.i18n import MESSAGE_BURN_FAILED, MESSAGE_SPEECH, set_language  # noqa: E402
from videodl.jobs import ItemStatus  # noqa: E402

app = QApplication.instance() or QApplication([])
apply_theme(app)
set_language("bs")


def fake_probe(url, http_headers=None):
    from videodl.probe import Entry, ProbeResult

    return ProbeResult("Govor", (Entry(url, "Govor", None, 61),), False)


def wait_until(condition, timeout=5.0):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        app.processEvents()
        if condition():
            return True
        time.sleep(0.01)
    return condition()


class SpeechWindowTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.settings = QSettings(os.path.join(self.tmp.name, "settings.ini"), QSettings.Format.IniFormat)
        self.settings.setValue("language", "bs")

    def make_window(self, download_fn):
        window = MainWindow(settings=self.settings, probe_fn=fake_probe, download_fn=download_fn,
                            thumbnail_fetch=lambda url: None, data_dir_path=self.tmp.name)
        window.set_output_dir(self.tmp.name)
        self.addCleanup(window.deleteLater)
        return window

    def test_switch_needs_the_model(self):
        from videodl.settings_dialog import SettingsDialog

        window = self.make_window(lambda *a, **k: None)
        with mock.patch.object(speech, "engine_available", return_value=True), \
                mock.patch.object(speech, "model_ready", return_value=False):
            dialog = SettingsDialog(window, RATE_CHOICES, PARALLEL_CHOICES, NAME_TEMPLATES)
        self.addCleanup(dialog.deleteLater)
        self.assertFalse(dialog.speech.isEnabled())  # bez titlova nema ni titla iz govora
        dialog.subtitles.setChecked(True)
        self.assertTrue(dialog.speech.isEnabled())
        with mock.patch("videodl.settings_dialog.ensure_model", return_value=False) as ask,                 mock.patch("videodl.settings_dialog.offer_model_removal") as offer:
            dialog.speech.setChecked(True)  # korisnik odustao od preuzimanja modela
        ask.assert_called_once()
        offer.assert_not_called()  # odmah poslije odustajanja ne pita za brisanje (preuzimanje nastavlja kasnije)
        self.assertFalse(dialog.speech.isChecked())
        self.assertFalse(window._subtitles_speech)
        with mock.patch("videodl.settings_dialog.ensure_model", return_value=True):
            dialog.speech.setChecked(True)
        self.assertTrue(window._subtitles_speech)
        self.assertTrue(self.settings.value("subtitles_speech", type=bool))
        item = window._queue.add("https://v/x", "x", "best", self.tmp.name)
        with mock.patch.object(speech, "model_ready", return_value=True):
            self.assertTrue(window._download_options(item)["speech_subtitles"])
        with mock.patch.object(speech, "model_ready", return_value=False):  # model obrisan: običan „bez titlova"
            self.assertNotIn("speech_subtitles", window._download_options(item))
        # Isključivanje nudi brisanje modela (1,5 GB); „Ostavi" je podrazumijevano
        with mock.patch("videodl.settings_dialog.offer_model_removal") as offer:
            dialog.speech.setChecked(False)
        offer.assert_called_once()
        self.assertFalse(window._subtitles_speech)

    def test_switch_hidden_without_the_engine(self):
        from videodl.settings_dialog import SettingsDialog

        window = self.make_window(lambda *a, **k: None)
        with mock.patch.object(speech, "engine_available", return_value=False):
            dialog = SettingsDialog(window, RATE_CHOICES, PARALLEL_CHOICES, NAME_TEMPLATES)
        self.addCleanup(dialog.deleteLater)
        self.assertIsNone(dialog.speech)

    def test_review_after_download_then_burn(self):
        video = os.path.join(self.tmp.name, "Govor [x].mp4")
        subtitle = speech.subtitle_path(video, "bs")

        def fake_download(url, preset, output_dir, subfolder, on_progress, cancel_event, **extra):
            open(video, "wb").close()
            speech.write_srt([speech.Line(0, 1, "Laga vrećo")], subtitle)
            return DownloadResult(ItemStatus.DONE, video, MESSAGE_SPEECH, speech_subtitle=subtitle)

        window = self.make_window(fake_download)
        window._subtitles = window._subtitles_burn = window._subtitles_speech = True
        reviewed = []

        def fake_review(parent, path, srt, duration=None):
            reviewed.append((path, srt))
            return "failed"

        with mock.patch.object(speech_dialogs, "review_and_burn", side_effect=fake_review):
            window.add_links_from_text("https://v/x")
            self.assertTrue(wait_until(lambda: len(window._queue.items()) == 1))
            window._start_all()
            self.assertTrue(wait_until(lambda: reviewed))
        self.assertEqual(reviewed, [(video, subtitle)])
        self.assertTrue(wait_until(lambda: window._queue.items()[0].message == MESSAGE_BURN_FAILED))


class ReviewDialogTest(unittest.TestCase):
    def test_corrections_are_saved_and_burn_only_after_confirming(self):
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        video = os.path.join(folder.name, "Govor [x].mp4")
        open(video, "wb").close()
        subtitle = speech.subtitle_path(video, "bs")
        speech.write_srt([speech.Line(117.0, 119.2, "Laga vrećo, cijene džematlije,")], subtitle)
        dialog = speech_dialogs.ReviewDialog(None, video, subtitle)
        self.addCleanup(dialog.deleteLater)
        self.assertEqual(dialog.table.item(0, 0).text(), "00:01:57")
        dialog.table.item(0, 1).setText("Draga braćo, cijenjene džematlije,")
        dialog.reject()  # „Ostavi pored videa": ispravka ostaje u fajlu
        self.assertEqual(speech.read_srt(subtitle)[0].text, "Draga braćo, cijenjene džematlije,")

        burned = []
        with mock.patch.object(speech_dialogs.ReviewDialog, "exec", return_value=QDialog.DialogCode.Rejected):
            self.assertEqual(speech_dialogs.review_and_burn(None, video, subtitle), "kept")

        def fake_task_exec(task):
            task._work(lambda value: None, task._cancel)
            return QDialog.DialogCode.Accepted

        with mock.patch.object(speech_dialogs.ReviewDialog, "exec", return_value=QDialog.DialogCode.Accepted), \
                mock.patch.object(speech_dialogs.TaskDialog, "exec", fake_task_exec), \
                mock.patch("videodl.burn.burn_subtitles", side_effect=lambda *a, **k: burned.append(a[:2])):
            self.assertEqual(speech_dialogs.review_and_burn(None, video, subtitle), "burned")
        self.assertEqual(burned, [(video, subtitle)])
        self.assertFalse(os.path.exists(subtitle))  # titl je sada u slici


if __name__ == "__main__":
    unittest.main()
