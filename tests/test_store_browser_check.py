"""Provjera mora odbiti neispravan manifest i nepotpun odgovor hosta."""

import json
import struct
import unittest
from pathlib import Path

from tools import check_store_browser_link as check
from videodl import native_host, native_messaging


class StoreBrowserCheckTest(unittest.TestCase):
    def test_valid_and_invalid_chromium_manifest(self):
        alias = Path(r"C:\Users\Ahmed\AppData\Local\Microsoft\WindowsApps\abnps-videodl-host.exe")
        valid = {
            "name": native_host.HOST_NAME, "path": str(alias), "type": "stdio",
            "allowed_origins": [f"chrome-extension://{value}/" for value in native_messaging.CHROMIUM_EXTENSION_IDS],
        }
        self.assertEqual(check.manifest_problems(valid, native_host.HOST_NAME, alias, "Edge"), [])
        broken = {**valid, "path": "C:\\wrong.exe", "allowed_origins": [], "allowed_extensions": ["other"]}
        self.assertEqual(len(check.manifest_problems(broken, native_host.HOST_NAME, alias, "Edge")), 3)

    def test_firefox_manifest_must_have_its_own_extension_id(self):
        alias = Path(r"C:\WindowsApps\abnps-videodl-host.exe")
        chromium = {"name": native_host.HOST_NAME, "path": str(alias), "type": "stdio",
                    "allowed_origins": [f"chrome-extension://{native_messaging.EXTENSION_ID}/"]}
        self.assertTrue(check.manifest_problems(chromium, native_host.HOST_NAME, alias, "Firefox"))

    def test_status_reply_requires_complete_successful_frame(self):
        body = json.dumps({"ok": True, "running": False}).encode("utf-8")
        frame = struct.pack("<I", len(body)) + body
        self.assertTrue(check.status_reply(frame)["ok"])
        with self.assertRaises(ValueError):
            check.status_reply(frame[:-1])
        rejected = b'{"ok": false}'
        with self.assertRaises(ValueError):
            check.status_reply(struct.pack("<I", len(rejected)) + rejected)

    def test_store_version_is_strict(self):
        self.assertLess(check.version_parts("1.0.2.0"), check.version_parts("1.0.3.0"))
        with self.assertRaises(ValueError):
            check.version_parts("1.0.3")


if __name__ == "__main__":
    unittest.main()
