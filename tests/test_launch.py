"""Isto pokretanje za sve ulaze: pokreni.pyw i `python -m videodl` (pregled 26.9.2026)."""

import sys
import unittest
from pathlib import Path
from unittest import mock

from videodl import launch

ROOT = Path(__file__).resolve().parent.parent


class LaunchTest(unittest.TestCase):
    def test_both_entry_points_use_the_same_launcher(self):
        for entry in (ROOT / "pokreni.pyw", ROOT / "videodl" / "__main__.py"):
            with self.subTest(entry=entry.name):
                text = entry.read_text(encoding="utf-8")
                self.assertIn("from videodl.launch import run", text)
                self.assertNotIn("from videodl.gui import", text)  # prozor samo preko launch.run

    def test_new_yt_dlp_is_activated_before_the_window_is_imported(self):
        calls = []
        fake_gui = mock.MagicMock()
        fake_gui.main.side_effect = lambda: calls.append("gui") or 0
        with mock.patch("videodl.ytdlp_update.activate", side_effect=lambda: calls.append("activate")), \
                mock.patch.dict(sys.modules, {"videodl.gui": fake_gui}):
            self.assertEqual(launch.run(["app"]), 0)
        self.assertEqual(calls, ["activate", "gui"])

    def test_browser_call_runs_the_host_without_window_or_yt_dlp(self):
        with mock.patch("videodl.native_host.main", return_value=0) as host, \
                mock.patch("videodl.ytdlp_update.activate") as activate:
            self.assertEqual(launch.run(["app", "chrome-extension://abc/"]), 0)
        host.assert_called_once()
        activate.assert_not_called()


if __name__ == "__main__":
    unittest.main()
