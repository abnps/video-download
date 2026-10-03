"""Provjera sajtova: blokada servera je upozorenje, a promjena sajta (yt-dlp ga ne razumije) je prava greška."""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
import site_check  # noqa: E402


class ClassifyTest(unittest.TestCase):
    def test_blocked_server_is_only_a_warning(self):
        for message in (
            "ERROR: [youtube] jNQ: Sign in to confirm you’re not a bot. Use --cookies-from-browser",
            "ERROR: [TikTok] 7139: Your IP address is blocked from accessing this post",
            "ERROR: [vimeo] 1: Got HTTP Error 403 when using impersonate target",
            "ERROR: [Instagram] B: Instagram sent an empty media response.",
            "ERROR: [dailymotion] x: This video is available in France (geo restriction)",
            "HTTP Error 429: Too Many Requests",
        ):
            with self.subTest(message=message):
                self.assertEqual(site_check.classify(message), "blokirano")

    def test_site_change_is_broken(self):
        for message in (
            "ERROR: [TikTok] 6742: Unable to extract universal data for rehydration",
            "ERROR: [twitter] 157: KeyError('legacy')",
            "nema nijednog formata",
        ):
            with self.subTest(message=message):
                self.assertEqual(site_check.classify(message), "pokvareno")

    def test_every_site_has_a_public_https_link(self):
        self.assertGreaterEqual(len(site_check.SITES), 5)
        for site, url in site_check.SITES:
            self.assertTrue(url.startswith("https://"), site)


if __name__ == "__main__":
    unittest.main()
