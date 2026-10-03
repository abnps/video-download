"""Razumljive poruke za najčešće greške yt-dlp-a; original ostaje za oblačić i izvještaj o problemu."""

import unittest

from videodl.i18n import LANGUAGES, get_language, set_language, tr
from videodl.widgets import display_message, friendly_error

# Poruke kakve yt-dlp stvarno vraća (bez „ERROR:", to skida ytdl.clean_error).
SAMPLES = {
    "bot": "[youtube] abc123: Sign in to confirm you’re not a bot. Use --cookies-from-browser or --cookies for the authentication.",
    "age": "[youtube] abc123: Sign in to confirm your age. This video may be inappropriate for some users.",
    "private": "[youtube] abc123: Private video. Sign in if you've been granted access to this video",
    "geo": "[generic] abc: The uploader has not made this video available in your country",
    "login": "[instagram] abc: This content is only available for registered users who follow this account",
    "unavailable": "[youtube] abc123: Video unavailable. This video has been removed by the uploader",
    "forbidden": "unable to download video data: HTTP Error 403: Forbidden",
    "rate": "[vimeo] 123: Unable to download JSON metadata: HTTP Error 429: Too Many Requests",
    "format": "[youtube] abc123: Requested format is not available. Use --list-formats for a list of available formats",
    "disk": "unable to write data: [Errno 28] No space left on device",
    "permission": "unable to open for writing: [Errno 13] Permission denied: 'C:\\\\x\\\\a.mp4'",
    "unsupported": "Unsupported URL: https://example.com/page",
    "network": "[generic] Unable to download webpage: <urlopen error [Errno 11001] getaddrinfo failed> (caused by URLError)",
}


class FriendlyErrorTest(unittest.TestCase):
    def setUp(self):
        self.language = get_language()
        set_language("bs")

    def tearDown(self):
        set_language(self.language)

    def test_known_errors_get_a_clear_message(self):
        for key, message in SAMPLES.items():
            with self.subTest(key=key):
                self.assertEqual(friendly_error(message), tr(f"error.friendly.{key}", help="Pomoć",
                                                             update=tr("menu.update_ytdlp")))
                self.assertEqual(display_message(message), friendly_error(message))
                self.assertEqual(display_message(message, friendly=False), message)  # original za oblačić

    def test_tiktok_sensitive_post_is_a_login_message(self):
        # TikTok „osjetljiv sadržaj": video vide samo prijavljeni (3.10.2026, isti video na računaru i telefonu).
        message = ("ERROR: [TikTok] 7691847713507314962: This post may not be comfortable for some audiences. "
                   "Log in for access. Use --cookies-from-browser or --cookies for the authentication.")
        self.assertEqual(friendly_error(message), tr("error.friendly.login"))

    def test_menu_names_are_filled_in_and_unknown_errors_stay_as_they_are(self):
        self.assertIn("Pomoć → Ažuriraj čitač sajtova (yt-dlp)", friendly_error(SAMPLES["forbidden"]))
        self.assertIsNone(friendly_error("Postprocessing: ffprobe and ffmpeg not found"))
        self.assertEqual(display_message("nešto sasvim novo"), "nešto sasvim novo")

    def test_every_language_has_the_messages(self):
        for language in LANGUAGES:
            set_language(language)
            for key in SAMPLES:
                with self.subTest(language=language, key=key):
                    text = friendly_error(SAMPLES[key])
                    self.assertNotIn("{", text)
                    self.assertNotIn("error.friendly", text)


if __name__ == "__main__":
    unittest.main()
