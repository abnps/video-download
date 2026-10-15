"""Brže pokretanje: prozor ne čeka yt-dlp; on se aktivira i uvozi u pozadini, a korisnici ga čekaju."""

import subprocess
import sys
import threading
import time
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from videodl import ytdlp_update  # noqa: E402


class StartupTest(unittest.TestCase):
    def setUp(self):
        self._state = (ytdlp_update._started, ytdlp_update._ready)
        ytdlp_update._started = False
        ytdlp_update._ready = threading.Event()

    def tearDown(self):
        ytdlp_update._started, ytdlp_update._ready = self._state

    def test_gui_import_does_not_load_ytdlp(self):
        code = "import sys, videodl.gui; print('yt_dlp' in sys.modules)"
        out = subprocess.run([sys.executable, "-c", code], cwd=ROOT, capture_output=True, text=True,
                             env={**__import__("os").environ, "QT_QPA_PLATFORM": "offscreen"}, timeout=120)
        self.assertEqual(out.stdout.strip(), "False", out.stderr)

    def test_ensure_ready_waits_for_background_activation_once(self):
        calls = []

        def slow_activate():
            calls.append(threading.current_thread().name)
            time.sleep(0.3)

        with mock.patch.object(ytdlp_update, "activate", slow_activate):
            ytdlp_update.start_background()
            ytdlp_update.start_background()  # drugi poziv ne pokreće novu nit
            started = time.monotonic()
            ytdlp_update.ensure_ready()
            self.assertGreaterEqual(time.monotonic() - started, 0.2)
        self.assertEqual(calls, ["yt-dlp-start"])
        self.assertTrue(ytdlp_update._ready.is_set())

    def test_without_background_start_nothing_waits_or_activates(self):
        # Testovi i poziv iz browsera ne pokreću aktivaciju (ona može brisati preuzete verzije).
        with mock.patch.object(ytdlp_update, "activate") as activate:
            ytdlp_update.ensure_ready()
        activate.assert_not_called()

    def test_background_error_does_not_block(self):
        with mock.patch.object(ytdlp_update, "activate", side_effect=RuntimeError("pokvareno")):
            ytdlp_update.start_background()
            self.assertTrue(ytdlp_update._ready.wait(5))


if __name__ == "__main__":
    unittest.main()
