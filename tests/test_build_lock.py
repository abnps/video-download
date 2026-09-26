"""Zaključane verzije za izdanje: lock fajlovi se slažu, a pravne napomene navode tačan ffmpeg."""

import json
import re
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))

import build_release  # noqa: E402

from videodl import legal  # noqa: E402


class BuildLockTest(unittest.TestCase):
    def setUp(self):
        self.lock = build_release.load_lock()

    def test_requirements_lock_matches_build_lock(self):
        pinned = dict(re.findall(r"^([A-Za-z0-9_.-]+)==(\S+)$", (ROOT / "requirements-lock.txt").read_text(
            encoding="utf-8"), re.MULTILINE))
        self.assertEqual(pinned, self.lock["packages"])

    def test_every_bundled_tool_has_version_hash_and_source(self):
        self.assertEqual(set(self.lock["tools"]), {"ffmpeg", "ffprobe", "node"})
        for name, spec in self.lock["tools"].items():
            with self.subTest(tool=name):
                self.assertRegex(spec["sha256"], r"^[0-9a-f]{64}$")
                self.assertTrue(spec["version"] and spec["source"].startswith("https://"))

    def test_legal_notice_names_the_exact_ffmpeg_build_and_source(self):
        ffmpeg = legal.FFMPEG_WINDOWS
        spec = self.lock["tools"]["ffmpeg"]
        self.assertIn(spec["version"], ffmpeg.note)
        self.assertIn(spec["source"], ffmpeg.note)
        self.assertIn(spec["version"].split("-")[0], ffmpeg.name)
        self.assertIn(legal.FFMPEG, legal.COMPONENTS)  # tačno jedan FFmpeg, onaj za ovaj sistem

    def test_mac_tools_are_pinned_by_url_and_hash(self):
        mac = self.lock["macos_tools"]
        self.assertEqual({k for k in mac if k != "comment"}, {"ffmpeg", "ffprobe", "node"})
        for name in ("ffmpeg", "ffprobe", "node"):
            with self.subTest(tool=name):
                self.assertRegex(mac[name]["sha256"], r"^[0-9a-f]{64}$")
                self.assertTrue(mac[name]["url"].startswith("https://"))
        self.assertIn(mac["ffmpeg"]["source"], legal.FFMPEG_MAC.note)
        self.assertIn(mac["ffmpeg"]["version"].split()[0], legal.FFMPEG_MAC.name)
        self.assertEqual(mac["node"]["version"], self.lock["tools"]["node"]["version"])  # isti Node na oba sistema

    def test_packaged_python_components_are_listed(self):
        listed = {name.lower() for name in legal.PYTHON_DISTRIBUTIONS}
        for package in self.lock["packages"]:
            if package.lower() in ("pyside6", "shiboken6", "pyinstaller"):
                continue  # Qt je posebna komponenta; PyInstaller se ne distribuira (samo alat za build)
            with self.subTest(package=package):
                self.assertIn(package.lower(), listed)

    def test_wrong_tool_hash_is_refused(self):
        broken = json.loads(json.dumps(self.lock))
        broken["tools"]["node"]["sha256"] = "0" * 64
        broken["packages"]["yt-dlp"] = "1999.1.1"
        problems = build_release.verify_environment(broken)
        self.assertTrue(any(p.startswith("node: SHA-256") for p in problems))
        self.assertTrue(any(p.startswith("yt-dlp ") for p in problems))


if __name__ == "__main__":
    unittest.main()
