"""Firefox paket dodatka: ispravan manifest i svi fajlovi dodatka, ID isti kao u registraciji hosta."""

import json
import re
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))

import build_firefox  # noqa: E402

from videodl.native_messaging import FIREFOX_EXTENSION_ID  # noqa: E402


class FirefoxPackageTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.zip_path = build_firefox.build(Path(self.tmp.name))
        with zipfile.ZipFile(self.zip_path) as archive:
            self.names = set(archive.namelist())
            self.manifest = json.loads(archive.read("manifest.json"))

    def test_manifest_is_firefox_mv3(self):
        chrome = json.loads((ROOT / "extension" / "manifest.json").read_text(encoding="utf-8"))
        m = self.manifest
        self.assertEqual((m["manifest_version"], m["version"]), (3, chrome["version"]))
        self.assertNotIn("key", m)  # Chrome ID ključ Firefox ne razumije
        self.assertNotIn("minimum_chrome_version", m)
        self.assertEqual(m["background"], {"scripts": ["background.js"], "type": "module"})
        gecko = m["browser_specific_settings"]["gecko"]
        self.assertEqual(gecko["id"], FIREFOX_EXTENSION_ID)  # mora se poklapati s allowed_extensions hosta
        self.assertEqual(gecko["data_collection_permissions"], {"required": ["none"]})
        self.assertIn("nativeMessaging", m["permissions"])

    def test_every_file_the_manifest_needs_is_packed(self):
        m = self.manifest
        needed = {"background.js", m["action"]["default_popup"], *m["icons"].values(),
                  *m["action"]["default_icon"].values()}
        for script in m["content_scripts"]:
            needed.update(script["js"])
        self.assertLessEqual(needed, self.names)
        self.assertNotIn("package.json", self.names)
        # ES moduli koje učitava pozadinska skripta
        imports = re.findall(r'from\s+"\./([^"]+)"', (ROOT / "extension" / "background.js").read_text(encoding="utf-8"))
        self.assertTrue(imports)
        self.assertLessEqual(set(imports), self.names)

    def test_no_chromium_only_webrequest_option_without_guard(self):
        background = (ROOT / "extension" / "background.js").read_text(encoding="utf-8")
        for match in re.finditer(r'"extraHeaders"', background):
            line = background[background.rfind("\n", 0, match.start()) + 1:background.find("\n", match.start())]
            if line.strip().startswith("//"):
                continue
            self.assertIn("EXTRA_HEADERS", line)  # Firefox odbija cijeli listener s "extraHeaders"


if __name__ == "__main__":
    unittest.main()
