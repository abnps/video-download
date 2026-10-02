"""Provjere nacrta izdanja ne smiju pokrenuti objavu kada neki fajl nedostaje."""

import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
import publish_release  # noqa: E402


class ReleaseReadinessTest(unittest.TestCase):
    def test_android_change_requires_new_version_code(self):
        previous = {"versionCode": 4, "sha256": "a" * 64}
        with self.assertRaises(publish_release.ReleaseError):
            publish_release.check_android_upgrade({"versionCode": 4, "sha256": "b" * 64}, previous)
        publish_release.check_android_upgrade({"versionCode": 5, "sha256": "b" * 64}, previous)

    def test_missing_mac_or_android_prevents_publication(self):
        tag = f"v{publish_release.__version__}"
        draft = {"id": 1, "tag_name": tag, "draft": True, "assets": [
            {"name": name, "state": "uploaded"} for name in
            publish_release.required_assets(publish_release.__version__, "0.2.0")[:5]
        ]}
        with patch.object(publish_release, "check_checkout"), patch.object(publish_release, "draft", return_value=draft), \
             patch.object(publish_release, "run") as run:
            with self.assertRaisesRegex(publish_release.ReleaseError, "Nacrt nema sve"):
                publish_release.validate_draft(tag, publish=True)
            run.assert_not_called()

    def test_publish_moves_previous_release_to_draft(self):
        # Javno je samo posljednje izdanje: novo postaje latest, prethodno ide u nacrt (ne briše se).
        with patch.object(publish_release, "run", return_value="v0.9.7") as run:
            publish_release.publish_latest("v0.9.8")
        edits = [call.args for call in run.call_args_list if call.args[2] == "edit"]
        self.assertEqual(edits[0][3:], ("v0.9.8", "--repo", publish_release.REPO, "--draft=false", "--latest"))
        self.assertEqual(edits[1][3:], ("v0.9.7", "--repo", publish_release.REPO, "--draft=true"))
        self.assertFalse(any("delete" in call.args for call in run.call_args_list))
        # Isti instaler ide i u repo za winget (stalni link).
        create = [call.args for call in run.call_args_list if call.args[1:3] == ("release", "create")]
        self.assertEqual(len(create), 1)
        self.assertIn(publish_release.INSTALLERS_REPO, create[0])
        self.assertTrue(any(str(arg).endswith("VideoDownload-Setup-0.9.8.exe") for arg in create[0]))


if __name__ == "__main__":
    unittest.main()
