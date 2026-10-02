"""Androidova Python logika bez mreže, telefona i izmjene korisničkih fajlova."""

import base64
import sys
import tempfile
import unittest
from pathlib import Path

ANDROID_PYTHON = Path(__file__).resolve().parents[1] / "android" / "app" / "src" / "main" / "python"
sys.path.insert(0, str(ANDROID_PYTHON))

import vd_core  # noqa: E402
from vd_diagnostics import SafeLog, clean_file, records, render  # noqa: E402


class AndroidAudioTest(unittest.TestCase):
    def test_audio_must_be_a_separate_m4a_stream(self):
        combined = {"format_id": "combined", "ext": "mp4", "vcodec": "avc1.640028", "acodec": "mp4a.40.2"}
        info = {"formats": [combined]}
        self.assertFalse(vd_core.options(info)["audio_available"])
        with self.assertRaisesRegex(ValueError, "AUDIO_UNAVAILABLE"):
            vd_core.plan(info, "audio")
        self.assertEqual(vd_core.plan(info, "video"), ["combined"])

        m4a = {"format_id": "audio", "ext": "m4a", "vcodec": "none", "acodec": "mp4a.40.2"}
        info["formats"].append(m4a)
        self.assertTrue(vd_core.options(info)["audio_available"])
        self.assertEqual(vd_core.plan(info, "audio"), ["audio"])

    def test_standalone_m4a_and_other_audio(self):
        standalone = {"ext": "m4a", "vcodec": "none", "acodec": "mp4a.40.2"}
        self.assertTrue(vd_core.options(standalone)["audio_available"])
        self.assertEqual(vd_core.plan(standalone, "audio"), ["ba[ext=m4a]"])
        standalone["ext"] = "webm"
        self.assertFalse(vd_core.options(standalone)["audio_available"])


class AndroidDiagnosticsTest(unittest.TestCase):
    def test_new_log_keeps_useful_status_without_private_url_or_page(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder, "zadnji-log.txt")
            log = SafeLog(str(path))
            log.info("čitanje linka: https://alice:TOKEN@www.youtube.com/private?token=SECRET")
            log.debug("[debug] Dumping request to https://www.youtube.com: " + base64.b64encode(b"<html>SECRET</html>").decode())
            log.error("HTTP Error 403: Forbidden na https://www.youtube.com/private?key=SECRET")
            log.error("HTTP Error 403 na https://TOKEN.cdn.youtube.com/private?key=SECRET")
            log.error("HTTP Error 403 na https://FAKESECRET.onion/private")
            log.error("Authorization: Bearer SECRET\nCookie: session=SECRET")
            log.close()
            raw = path.read_text(encoding="utf-8")
            shown = "\n".join(render(records(str(path))))
            for secret in ("SECRET", "TOKEN", "/private", "<html>", "Authorization", "Cookie"):
                self.assertNotIn(secret, raw)
                self.assertNotIn(secret, shown)
            self.assertIn("youtube.com", shown)
            self.assertNotIn("FAKESECRET", raw + shown)
            self.assertIn("HTTP Error 403", shown)

    def test_old_log_is_sanitized_before_export_and_on_startup(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder, "zadnji-log.txt")
            secret = "FAKE_REVIEW_TOKEN"
            page = base64.b64encode(f"<html>{secret}</html>".encode()).decode()
            path.write_text(
                f"[info] link: https://alice:{secret}@www.youtube.com/p?token={secret}\n"
                f"[debug] Dumping request to https://www.youtube.com/p\n[debug] {page}\n"
                f"[error] HTTP Error 403: Forbidden\nAuthorization: Bearer {secret}\n",
                encoding="utf-8",
            )
            report = vd_core.report(folder)
            self.assertNotIn(secret, report)
            self.assertNotIn("Authorization", report)
            self.assertIn("HTTP Error 403", report)
            clean_file(str(path))
            self.assertNotIn(secret, path.read_text(encoding="utf-8"))
            self.assertIn("HTTP Error 403", "\n".join(render(records(str(path)))))


class AndroidLoginCookiesTest(unittest.TestCase):
    """Instagram prijava (SiteLogin.kt): fajl s kolačićima ide yt-dlp-u samo kad postoji, nikad u dnevnik."""

    def test_cookie_file_only_when_logged_in(self):
        self.assertNotIn("cookiefile", vd_core._with_cookies({}, ""))
        self.assertEqual(vd_core._with_cookies({}, "/x/kolacici.txt")["cookiefile"], "/x/kolacici.txt")

    def test_probe_passes_cookies_and_log_hides_them(self):
        seen = {}

        class FakeYDL:
            def __init__(self, params):
                seen.update(params)

            def __enter__(self):
                return self

            def __exit__(self, *args):
                return False

            def extract_info(self, url, download=False):
                return {"id": "abc", "title": "Reel", "formats": []}

        original = vd_core.YoutubeDL
        vd_core.YoutubeDL = FakeYDL
        try:
            with tempfile.TemporaryDirectory() as folder:
                cookies = Path(folder, "kolacici-1.txt")
                cookies.write_text("# Netscape HTTP Cookie File\n.instagram.com\tTRUE\t/\tTRUE\t0\tsessionid\tSECRET\n")
                vd_core.probe("https://www.instagram.com/reel/abc/", folder, str(cookies))
                self.assertEqual(seen["cookiefile"], str(cookies))
                raw = Path(folder, "zadnji-log.txt").read_text(encoding="utf-8")
                self.assertNotIn("SECRET", raw)
                self.assertNotIn("kolacici", raw)
                # Izvještaj kaže samo da li je prijava korištena.
                report = vd_core.render(vd_core.records(str(Path(folder, "zadnji-log.txt"))))
                self.assertIn("Čitanje linka | <instagram.com> | prijava: da", report)
                vd_core.probe("https://www.instagram.com/reel/abc/", folder, "")
                report = vd_core.render(vd_core.records(str(Path(folder, "zadnji-log.txt"))))
                self.assertIn("Čitanje linka | <instagram.com> | prijava: ne", report)
        finally:
            vd_core.YoutubeDL = original



class AndroidProgressTest(unittest.TestCase):
    """Napredak kao na računaru: ukupno za video + zvuk, brzina i preostalo vrijeme."""

    def test_second_part_counts_whole_download(self):
        # Video (80 MB) je gotov, zvuk (20 MB) je na pola, 2 MB/s.
        part = {"before": 0.8, "weight": 0.2, "done_before": 80_000_000, "rest": 0}
        status = {"total_bytes": 20_000_000, "downloaded_bytes": 10_000_000, "speed": 2_000_000}
        fraction, done, total, speed, eta = vd_core.progress(part, status)
        self.assertAlmostEqual(fraction, 0.9)
        self.assertEqual((done, total), (90_000_000, 100_000_000))
        self.assertEqual((speed, eta), (2_000_000.0, 5))

    def test_first_part_includes_remaining_parts_and_unknown_speed(self):
        part = {"before": 0.0, "weight": 0.8, "done_before": 0, "rest": 20_000_000}
        status = {"total_bytes_estimate": 80_000_000, "downloaded_bytes": 0, "speed": None}
        fraction, done, total, speed, eta = vd_core.progress(part, status)
        self.assertEqual((fraction, done, total, speed, eta), (0.0, 0, 100_000_000, 0.0, -1))

    def test_unknown_size(self):
        part = {"before": 0.0, "weight": 1.0, "done_before": 0, "rest": 0}
        fraction, done, total, _speed, eta = vd_core.progress(part, {"downloaded_bytes": 5, "speed": 10})
        self.assertEqual((fraction, done, total, eta), (-1.0, 5, 0, -1))



class AndroidAdultAndPlaylistTest(unittest.TestCase):
    """18+ po istim pravilima kao računar (YouTube izuzet); plejlista kao spisak bez čitanja svakog videa."""

    def test_adult_rules_match_desktop(self):
        sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
        from videodl import probe as desktop
        cases = [({"age_limit": 18, "extractor_key": "Generic"}, "https://example.com/v"),
                 ({"age_limit": 18, "extractor_key": "Youtube"}, "https://www.youtube.com/watch?v=x"),
                 ({"age_limit": 18}, "https://m.youtube.com/watch?v=x"),
                 ({"age_limit": 18}, "https://youtu.be/x"),
                 ({"age_limit": 0}, "https://example.com/v"),
                 ({"age_limit": True}, "https://example.com/v"),
                 ({}, "https://example.com/v")]
        for info, url in cases:
            with self.subTest(info=info, url=url):
                self.assertEqual(vd_core.is_adult(info, url), desktop.is_adult(info, url))

    def test_playlist_keeps_only_downloadable_entries(self):
        info = {"_type": "playlist", "title": "Lista", "extractor_key": "YoutubeTab", "entries": [
            {"url": "https://www.youtube.com/watch?v=a", "title": "A", "duration": 61.5,
             "thumbnails": [{"url": "https://i/a-small"}, {"url": "https://i/a-big"}]},
            None,
            {"url": "b", "title": "samo ID"},
            {"url": "https://example.com/c", "title": "C", "age_limit": 18, "thumbnail": "https://i/c"},
        ]}
        data = vd_core.playlist_json(info, "https://www.youtube.com/playlist?list=x")
        self.assertTrue(data["playlist"])
        self.assertEqual([e["title"] for e in data["entries"]], ["A", "C"])
        self.assertEqual(data["entries"][0]["thumbnail"], "https://i/a-big")
        self.assertEqual(data["entries"][0]["duration"], 61)
        self.assertEqual([e["adult"] for e in data["entries"]], [False, True])
        with self.assertRaises(ValueError):
            vd_core.playlist_json({"entries": [{"url": "x"}]}, "u")


if __name__ == "__main__":
    unittest.main()
