"""Titl iz govora (Ahmed 14.11.2026): model se preuzima naknadno (provjera, nastavak, prekid), titl se pravi
samo kad video nema nijedan, a izmišljeni redovi se izbacuju. Pravi model se u testovima ne koristi."""

import functools
import hashlib
import http.server
import os
import shutil
import subprocess
import tempfile
import threading
import unittest
from collections import namedtuple
from pathlib import Path
from unittest import mock

from videodl import speech
from videodl.download import download
from videodl.i18n import MESSAGE_NO_SUBS, MESSAGE_SPEECH, MESSAGE_SPEECH_FAILED, set_language, tr
from videodl.jobs import ItemStatus
from videodl.presets import get_preset, subtitle_languages
from videodl.widgets import display_message

FFMPEG = shutil.which("ffmpeg")
Segment = namedtuple("Segment", "start end text no_speech_prob avg_logprob")
Info = namedtuple("Info", "language")


class _Quiet(http.server.SimpleHTTPRequestHandler):
    """Statički server s podrškom za „Range" (nastavak prekinutog preuzimanja)."""

    ranges: list = []

    def log_message(self, *args):
        pass

    def do_GET(self):
        path = Path(self.directory) / self.path.lstrip("/")
        if not path.is_file():
            self.send_error(404)
            return
        data = path.read_bytes()
        wanted = self.headers.get("Range")
        self.ranges.append(wanted)
        if wanted:
            start = int(wanted.split("=")[1].split("-")[0])
            self.send_response(206)
            self.send_header("Content-Range", f"bytes {start}-{len(data) - 1}/{len(data)}")
            data = data[start:]
        else:
            self.send_response(200)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)


class ModelDownloadTest(unittest.TestCase):
    def setUp(self):
        self.served = tempfile.TemporaryDirectory()
        self.data = tempfile.TemporaryDirectory()
        self.addCleanup(self.served.cleanup)
        self.addCleanup(self.data.cleanup)
        root = Path(self.served.name)
        files = []
        for name, content in (("config.json", b"{}"), ("model.bin", os.urandom(3 * 1024 * 1024 + 17))):
            (root / name).write_bytes(content)
            files.append((name, len(content), hashlib.sha256(content).hexdigest()))
        self.files = tuple(files)
        _Quiet.ranges = []
        server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), functools.partial(_Quiet, directory=str(root)))
        threading.Thread(target=server.serve_forever, daemon=True).start()
        self.addCleanup(server.server_close)
        self.addCleanup(server.shutdown)
        env = {"VIDEODL_SPEECH_URL": f"http://127.0.0.1:{server.server_address[1]}",
               "VIDEODL_DATA_DIR": self.data.name}
        for patch in (mock.patch.dict(os.environ, env), mock.patch.object(speech, "MODEL_FILES", self.files),
                      mock.patch.object(speech, "MODEL_BYTES", sum(size for _n, size, _d in self.files))):
            patch.start()
            self.addCleanup(patch.stop)

    def test_downloads_checks_and_reports_progress(self):
        self.assertFalse(speech.model_ready())
        self.assertEqual(speech.remaining_bytes(), speech.MODEL_BYTES)
        seen = []
        speech.download_model(lambda done, total, speed: seen.append((done, total)))
        self.assertTrue(speech.model_ready())
        self.assertEqual(speech.model_dir(), Path(self.data.name) / "modeli" / speech.MODEL_NAME)
        self.assertEqual(seen[-1], (speech.MODEL_BYTES, speech.MODEL_BYTES))
        self.assertEqual([done for done, _t in seen], sorted(done for done, _t in seen))  # traka ide samo naprijed
        self.assertEqual(speech.remaining_bytes(), 0)
        speech.delete_model()
        self.assertFalse(speech.model_ready())

    def test_wrong_checksum_is_rejected_and_not_kept(self):
        name, size, _digest = self.files[1]
        with mock.patch.object(speech, "MODEL_FILES", (self.files[0], (name, size, "0" * 64))):
            with self.assertRaises(speech.SpeechError):
                speech.download_model()
        self.assertFalse(speech.model_ready())
        self.assertFalse((speech.model_dir() / f"{name}.part").exists())  # sljedeći pokušaj kreće ispočetka

    def test_interrupted_download_continues_where_it_stopped(self):
        name, size, _digest = self.files[1]
        folder = speech.model_dir()
        folder.mkdir(parents=True)
        content = (Path(self.served.name) / name).read_bytes()
        (folder / f"{name}.part").write_bytes(content[:1_000_000])
        self.assertEqual(speech.remaining_bytes(), speech.MODEL_BYTES - 1_000_000)
        seen = []
        speech.download_model(lambda done, total, speed: seen.append(done))
        self.assertTrue(speech.model_ready())
        self.assertIn("bytes=1000000-", _Quiet.ranges)
        self.assertGreaterEqual(seen[0], 1_000_000)  # traka kreće od već preuzetog

    def test_cancel_keeps_the_partial_file(self):
        cancel = threading.Event()

        def stop_after_first(done, total, speed):
            if done > len(b"{}"):
                cancel.set()

        with self.assertRaises(speech.SpeechCancelled):
            speech.download_model(stop_after_first, cancel)
        self.assertFalse(speech.model_ready())
        self.assertTrue((speech.model_dir() / "model.bin.part").is_file())

    def test_full_disk_is_reported_before_downloading(self):
        usage = shutil.disk_usage(self.data.name)._replace(free=speech.SPACE_MARGIN)
        with mock.patch.object(shutil, "disk_usage", return_value=usage):
            with self.assertRaises(speech.SpeechError) as caught:
                speech.download_model()
        self.assertEqual(caught.exception.key, "speech.error.space")
        self.assertEqual(_Quiet.ranges, [])  # ništa nije ni traženo sa servera
        for code in ("bs", "en", "de", "es", "fr"):
            set_language(code)
            for key in ("speech.error.space", "speech.error.network", "speech.error.checksum"):
                self.assertNotEqual(tr(key), key)
        set_language("bs")

    def test_only_https_or_local_address(self):
        with mock.patch.dict(os.environ, {"VIDEODL_SPEECH_URL": "http://primjer.test/model"}):
            with self.assertRaises(speech.SpeechError):
                speech.download_model()


class PinnedModelTest(unittest.TestCase):
    def test_every_file_has_size_and_sha256(self):
        self.assertEqual([name for name, _s, _d in speech.MODEL_FILES][-1], "model.bin")
        for _name, size, digest in speech.MODEL_FILES:
            self.assertGreater(size, 0)
            self.assertRegex(digest, r"^[0-9a-f]{64}$")
        self.assertTrue(speech.MODEL_URL.startswith("https://huggingface.co/"))
        self.assertIn(speech.MODEL_REVISION, speech.MODEL_URL)
        self.assertAlmostEqual(speech.MODEL_BYTES / 1e9, 1.6, delta=0.1)


class SubtitleTextTest(unittest.TestCase):
    def test_language_from_site_or_from_most_parts_of_the_video(self):
        self.assertEqual(speech.choose_language("hr", ["en"]), "bs")
        self.assertEqual(speech.choose_language("sr-Latn", []), "bs")
        self.assertEqual(speech.choose_language("de-DE", []), "de")
        # Uvod na arapskom, ostatak na bosanskom: većina dijelova odlučuje
        self.assertEqual(speech.choose_language(None, ["ar", "bs", "hr", "bs", "sr", "bs"]), "bs")
        self.assertEqual(speech.choose_language(None, ["en", "de", "de"]), "de")
        self.assertIsNone(speech.choose_language(None, []))

    def test_made_up_lines_over_silence_are_dropped(self):
        self.assertTrue(speech.keep_line("Uvijek je čovjek u pripravnosti,", 425.1, 427.5, 0.01, -0.2))
        self.assertFalse(speech.keep_line("Al-Fatiha", 30.0, 59.98, 0.1, -0.3))  # jedna riječ preko učenja
        self.assertFalse(speech.keep_line("ترجمة نانسي قنقر", 89.7, 119.7, 0.2, -0.4))  # poznata izmišljena fraza
        self.assertFalse(speech.keep_line("Hvala.", 3.0, 4.0, 0.9, -1.5))  # vjerovatno nije govor
        self.assertFalse(speech.keep_line("   ", 1.0, 2.0, 0.0, 0.0))
        self.assertTrue(speech.keep_line("Kada vam dođe neki fasik, neki pokvarenjak, koji je poznat u društvu "
                                         "kao pokvarenjak,", 230.4, 238.5, 0.02, -0.3))

    def test_srt_round_trip_keeps_our_letters(self):
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        path = os.path.join(folder.name, "titl.srt")
        lines = [speech.Line(0.5, 2.25, "Čuvajte zajednicu, džematlije."), speech.Line(3661.0, 3662.5, "Đ ž ć")]
        speech.write_srt(lines + [speech.Line(5, 6, "  ")], path)
        self.assertEqual(speech.read_srt(path), lines)  # prazan red se ne upisuje
        text = Path(path).read_text(encoding="utf-8")
        self.assertIn("01:01:01,000 --> 01:01:02,500", text)
        self.assertEqual(speech.parse_time("00:00:02.5"), 2.5)

    def test_file_name_marks_subtitles_from_speech(self):
        path = speech.subtitle_path("C:/Videi/Naslov [abc].mp4", "bs")
        self.assertEqual(path, "C:/Videi/Naslov [abc].bs.iz-govora.srt")
        self.assertTrue(speech.is_speech_subtitle(path))
        self.assertFalse(speech.is_speech_subtitle("C:/Videi/Naslov [abc].srt"))


class FakeModel:
    supported_languages = ["ar", "bs", "de", "en", "hr", "sr"]

    def __init__(self, detected="hr", cancel=None):
        self.detected = detected
        self.cancel = cancel
        self.calls = []

    def detect_language(self, samples):
        return self.detected, 0.9, []

    def transcribe(self, samples, **options):
        self.calls.append(options)

        def segments():
            yield Segment(0.0, 30.0, "Muzika", 0.1, -0.3)  # izmišljeno preko uvoda: izbacuje se
            yield Segment(30.5, 33.0, "Dobar dan, draga braćo.", 0.01, -0.2)
            if self.cancel is not None:
                self.cancel.set()
            yield Segment(33.0, 36.0, "Hvala na pažnji.", 0.01, -0.2)

        return segments(), Info(options.get("language") or "bs")


class TranscribeTest(unittest.TestCase):
    def setUp(self):
        import numpy

        self.folder = tempfile.TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)
        self.video = os.path.join(self.folder.name, "Govor [x].mp4")
        Path(self.video).write_bytes(b"")
        self.audio = numpy.zeros(speech.SAMPLE_RATE * 40, dtype=numpy.float32)

    def test_subtitle_next_to_the_video_in_latin_script(self):
        model = FakeModel("sr")
        seen = []
        path = speech.transcribe(self.video, on_progress=seen.append, model_factory=lambda: model, audio=self.audio)
        self.assertEqual(path, os.path.join(self.folder.name, "Govor [x].bs.iz-govora.srt"))
        self.assertEqual([line.text for line in speech.read_srt(path)], ["Dobar dan, draga braćo.", "Hvala na pažnji."])
        options = model.calls[0]
        self.assertEqual(options["language"], "bs")  # srpski bi bio ćirilicom
        self.assertFalse(options["condition_on_previous_text"])  # inače arapski uvod „zarazi" ostatak
        self.assertTrue(options["vad_filter"])
        self.assertIn("č, ć, đ, š, ž", options["initial_prompt"])
        self.assertEqual(seen[0], None)
        self.assertEqual(seen[-1], 1.0)

    def test_site_language_wins_over_detection(self):
        model = FakeModel("ar")
        speech.transcribe(self.video, site_language="de", model_factory=lambda: model, audio=self.audio)
        self.assertEqual(model.calls[0]["language"], "de")

    def test_cancel_stops_between_lines_and_leaves_no_file(self):
        cancel = threading.Event()
        with self.assertRaises(speech.SpeechCancelled):
            speech.transcribe(self.video, model_factory=lambda: FakeModel(cancel=cancel), audio=self.audio,
                              cancel=cancel)
        self.assertEqual([p for p in os.listdir(self.folder.name) if p.endswith(".srt")], [])

    def test_one_recognition_at_a_time(self):
        # Dva videa bez titla odjednom: model (~2 GB memorije) se ne učitava dvaput u isto vrijeme
        running, most = [0], [0]
        gate = threading.Lock()

        class Slow(FakeModel):
            def transcribe(self, samples, **options):
                with gate:
                    running[0] += 1
                    most[0] = max(most[0], running[0])
                import time

                time.sleep(0.15)
                with gate:
                    running[0] -= 1
                return super().transcribe(samples, **options)

        def work(name):
            speech.transcribe(os.path.join(self.folder.name, name), model_factory=Slow, audio=self.audio)

        threads = [threading.Thread(target=work, args=(f"v{i}.mp4",)) for i in range(3)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join(10)
        self.assertEqual(most[0], 1)
        self.assertEqual(len([p for p in os.listdir(self.folder.name) if p.endswith(".srt")]), 3)
        # Čekanje na red se može prekinuti
        cancel = threading.Event()
        cancel.set()
        with speech._ONE_AT_A_TIME:
            with self.assertRaises(speech.SpeechCancelled):
                speech.transcribe(self.video, model_factory=FakeModel, audio=self.audio, cancel=cancel)

    def test_no_model_no_subtitle(self):
        with mock.patch.dict(os.environ, {"VIDEODL_DATA_DIR": self.folder.name}):
            with self.assertRaises(speech.SpeechError):
                speech.transcribe(self.video, audio=self.audio)

    @unittest.skipUnless(FFMPEG, "ffmpeg nije instaliran")
    def test_audio_is_read_with_ffmpeg_without_pyav(self):
        clip = os.path.join(self.folder.name, "ton.mp4")
        subprocess.run([FFMPEG, "-v", "error", "-f", "lavfi", "-i", "sine=frequency=440:duration=2", "-c:a", "aac",
                        clip], check=True)
        samples = speech.decode_audio(clip, FFMPEG)
        self.assertAlmostEqual(len(samples) / speech.SAMPLE_RATE, 2.0, delta=0.1)
        self.assertGreater(float(abs(samples).max()), 0.1)
        with self.assertRaises(speech.SpeechError):
            speech.decode_audio(os.path.join(self.folder.name, "nema.mp4"), FFMPEG)


@unittest.skipUnless(FFMPEG and shutil.which("ffprobe"), "ffmpeg nije instaliran")
class DownloadWithSpeechTest(unittest.TestCase):
    """Preuzimanje videa bez titla: titl iz govora pored videa, samo kad je uključen i model je preuzet."""

    @classmethod
    def setUpClass(cls):
        cls.served = tempfile.TemporaryDirectory()
        root = Path(cls.served.name)
        subprocess.run([FFMPEG, "-v", "error", "-f", "lavfi", "-i", "testsrc=size=160x90:rate=10", "-f", "lavfi",
                        "-i", "sine=frequency=440", "-t", "2", "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac",
                        "-shortest", str(root / "clip.mp4")], check=True)
        (root / "bez-titla.html").write_text(
            '<!doctype html><html><head><title>Bez titla</title></head><body><video controls>'
            '<source src="clip.mp4" type="video/mp4"></video></body></html>', encoding="utf-8")
        cls.server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), functools.partial(_Quiet, directory=str(root)))
        threading.Thread(target=cls.server.serve_forever, daemon=True).start()
        cls.url = f"http://127.0.0.1:{cls.server.server_address[1]}/bez-titla.html"

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.served.cleanup()

    def run_download(self, transcribe=None, ready=True, **extra):
        output = tempfile.TemporaryDirectory()
        self.addCleanup(output.cleanup)
        progress = []

        def fake(video, site_language=None, on_progress=None, cancel=None):
            on_progress(None)
            on_progress(0.5)
            path = speech.subtitle_path(video, "bs")
            speech.write_srt([speech.Line(0, 1, "Zdravo.")], path)
            return path

        with mock.patch.object(speech, "engine_available", return_value=True), \
                mock.patch.object(speech, "model_ready", return_value=ready), \
                mock.patch.object(speech, "transcribe", side_effect=transcribe or fake) as called:
            result = download(self.url, get_preset("best"), output.name, subtitles=True,
                              subtitle_langs=subtitle_languages("bs"), on_progress=progress.append, **extra)
        return result, Path(output.name), progress, called

    def test_subtitle_from_speech_next_to_the_video(self):
        result, folder, progress, _called = self.run_download(speech_subtitles=True, burn_subtitles=True)
        self.assertEqual((result.status, result.message), (ItemStatus.DONE, MESSAGE_SPEECH))
        self.assertEqual(result.speech_subtitle, speech.subtitle_path(result.filepath, "bs"))
        self.assertTrue(os.path.isfile(result.speech_subtitle))  # upis u sliku tek poslije pregleda
        self.assertIn("pp.speech", {p.label for p in progress})
        set_language("bs")
        self.assertIn("može imati grešaka", display_message(MESSAGE_SPEECH))

    def test_off_or_without_model_nothing_changes(self):
        result, _f, _p, called = self.run_download()
        self.assertEqual((result.message, result.speech_subtitle), (MESSAGE_NO_SUBS, None))
        result, _f, _p, called = self.run_download(ready=False, speech_subtitles=True)
        self.assertEqual((result.message, result.speech_subtitle), (MESSAGE_SPEECH_FAILED, None))
        called.assert_not_called()

    def test_failure_keeps_the_video_and_cancel_cancels(self):
        result, _f, _p, _c = self.run_download(transcribe=speech.SpeechError("nema govora"), speech_subtitles=True)
        self.assertEqual((result.status, result.message), (ItemStatus.DONE, MESSAGE_SPEECH_FAILED))
        self.assertTrue(os.path.isfile(result.filepath))
        result, _f, _p, _c = self.run_download(transcribe=speech.SpeechCancelled("x"), speech_subtitles=True)
        self.assertEqual(result.status, ItemStatus.CANCELLED)

    def test_texts_warn_about_mistakes_in_every_language(self):
        for code, word in (("bs", "grešaka"), ("en", "mistakes"), ("de", "Fehler"), ("es", "errores"),
                           ("fr", "erreurs")):
            set_language(code)
            for key in ("settings.desc.speech", "speech.download.question", "speech.review.warning", "row.speech"):
                self.assertIn(word, tr(key, size="1,6 GB"), (code, key))
        set_language("bs")

