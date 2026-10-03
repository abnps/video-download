"""Provjere nacrta izdanja ne smiju pokrenuti objavu kada neki fajl nedostaje."""

import subprocess
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
        def fake_run(*args, **kwargs):
            if args[1:3] == ("release", "view") and publish_release.INSTALLERS_REPO in args:
                raise subprocess.CalledProcessError(1, args)  # u repou za winget izdanja još nema
            return "v0.9.7"

        with patch.object(publish_release, "run", side_effect=fake_run) as run:
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

    def test_interrupted_installers_copy_is_completed_not_duplicated(self):
        # 0.9.8: kopija za winget pala usred slanja i ostala nacrt; ponovni pokušaj dopuni i objavi to izdanje.
        with patch.object(publish_release, "run", return_value="") as run:
            publish_release.copy_to_installers_repo("v0.9.8")
        steps = [call.args[1:3] for call in run.call_args_list]
        self.assertNotIn(("release", "create"), steps)
        upload = next(call.args for call in run.call_args_list if call.args[1:3] == ("release", "upload"))
        self.assertIn("--clobber", upload)
        self.assertIn(publish_release.INSTALLERS_REPO, upload)
        edit = next(call.args for call in run.call_args_list if call.args[1:3] == ("release", "edit"))
        self.assertIn("--draft=false", edit)

    def test_mac_signature_is_required_and_made_from_the_draft_dmg(self):
        # Plan 1.0, tačka 7: bez release-macos.json(.sig) Mac ne može sam preći na novo izdanje.
        names = publish_release.required_assets(publish_release.__version__, "0.2.0")
        self.assertIn("release-macos.json", names)
        self.assertIn("release-macos.json.sig", names)

        import hashlib
        import os
        import tempfile

        import sign_macos
        from Cryptodome.PublicKey import ECC
        from videodl import release_signing

        version = publish_release.__version__
        dmg_name = f"VideoDownload-macOS-arm64-{version}.dmg"
        uploaded = {}

        def fake_run(*args, **kwargs):
            if args[1:3] == ("release", "download"):
                folder = Path(args[args.index("--dir") + 1])
                (folder / dmg_name).write_bytes(b"dmg" * 100)
                digest = hashlib.sha256(b"dmg" * 100).hexdigest()
                (folder / (dmg_name + ".sha256")).write_text(f"{digest}  {dmg_name}\n", encoding="ascii")
            elif args[1:3] == ("release", "upload"):
                for arg in args:
                    if arg.endswith((".json", ".sig")):
                        uploaded[Path(arg).name] = Path(arg).read_bytes()
            return ""

        key = ECC.generate(curve="ed25519")
        with tempfile.TemporaryDirectory() as temp:
            key_file = Path(temp) / "test-key.pem"
            key_file.write_text(key.export_key(format="PEM"), encoding="ascii")
            with patch.dict(os.environ, {"VIDEODL_SIGNING_KEY": str(key_file)}), \
                    patch.object(sign_macos, "draft"), patch.object(sign_macos, "run", side_effect=fake_run):
                sign_macos.sign_mac(f"v{version}")
        self.assertEqual(set(uploaded), {"release-macos.json", "release-macos.json.sig"})
        manifest = release_signing.verify_manifest(uploaded["release-macos.json"],
                                                   uploaded["release-macos.json.sig"].decode("ascii"),
                                                   public_keys=(release_signing.public_key_hex(key),))
        self.assertEqual((manifest["installer"], manifest["version"]), (dmg_name, version))


if __name__ == "__main__":
    unittest.main()
