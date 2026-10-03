"""Mac verzija (beta): putanje, veza s dodatkom, Finder, browseri i ažuriranje.

Testovi zadaju sistem sami (platform="darwin"), pa prolaze i na Windowsu i na Mac računaru u CI-ju.
"""

import json
import os
import plistlib
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from videodl import desktop, dialogs, native_host, runtime, updater  # noqa: E402
from videodl.gui import default_output_dir  # noqa: E402
from videodl.native_messaging import (  # noqa: E402
    EXTENSION_ID, FIREFOX_EXTENSION_ID, MAC_CHROMIUM_DIRS, install_native_host, mac_manifest_targets,
    uninstall_native_host,
)


class PathsTest(unittest.TestCase):
    def test_data_folder_per_system(self):
        home = Path("/Users/ana")
        self.assertEqual(runtime.user_data_base("darwin", {}, home), home / "Library" / "Application Support")
        self.assertEqual(runtime.user_data_base("win32", {"LOCALAPPDATA": r"C:\L"}, home), Path(r"C:\L"))
        self.assertEqual(runtime.user_data_base("linux", {}, home), home / ".local" / "share")

    def test_download_folder_is_movies_on_mac(self):
        self.assertTrue(default_output_dir("darwin").endswith(os.path.join("Movies", "Video Download")))
        self.assertTrue(default_output_dir("win32").endswith(os.path.join("Videos", "Video Download")))


class MacNativeMessagingTest(unittest.TestCase):
    def install(self, support: Path, folder: Path, **extra) -> Path:
        return install_native_host(folder, platform="darwin", mac_support_dir=support, **extra)

    def test_manifests_go_only_to_installed_browsers(self):
        with tempfile.TemporaryDirectory() as tmp:
            support = Path(tmp) / "Application Support"
            (support / "Google" / "Chrome").mkdir(parents=True)
            (support / "Mozilla").mkdir(parents=True)  # Firefox postoji, Edge ne
            self.install(support, Path(tmp) / "native-host", python_exe="/usr/bin/python3",
                         launch_command=["/usr/bin/python3", "/p/pokreni.pyw"])

            chrome = support / "Google" / "Chrome" / "NativeMessagingHosts" / f"{native_host.HOST_NAME}.json"
            firefox = support / "Mozilla" / "NativeMessagingHosts" / f"{native_host.HOST_NAME}.json"
            self.assertEqual(json.loads(chrome.read_text())["allowed_origins"], [f"chrome-extension://{EXTENSION_ID}/"])
            self.assertEqual(json.loads(firefox.read_text())["allowed_extensions"], [FIREFOX_EXTENSION_ID])
            self.assertFalse((support / "Microsoft Edge").exists())  # ne pravi foldere za browser koji nema

            script = Path(json.loads(chrome.read_text())["path"])
            self.assertEqual(script.name, "host.sh")
            self.assertIn('exec "/usr/bin/python3" "$(dirname "$0")/host.py" "$@"', script.read_text())
            if sys.platform != "win32":
                self.assertTrue(os.access(script, os.X_OK))

            uninstall_native_host(Path(tmp) / "native-host", platform="darwin", mac_support_dir=support)
            self.assertFalse(chrome.exists())
            self.assertFalse(firefox.exists())
            self.assertFalse((Path(tmp) / "native-host").exists())

    def test_installed_app_is_its_own_host(self):
        with tempfile.TemporaryDirectory() as tmp:
            support = Path(tmp)
            (support / "Google" / "Chrome").mkdir(parents=True)
            app = Path("/Applications/Video Download.app/Contents/MacOS/Video Download")
            self.install(support, Path(tmp) / "native-host", host_executable=app)
            chrome = support / "Google" / "Chrome" / "NativeMessagingHosts" / f"{native_host.HOST_NAME}.json"
            self.assertEqual(json.loads(chrome.read_text())["path"], str(app))
            self.assertFalse((Path(tmp) / "native-host" / "host.py").exists())  # nema kopije skripte

    def test_temporary_location_is_not_registered(self):
        # Iz .dmg-a ili preko App Translocation putanja nestaje kad se program zatvori: ne registrovati.
        from videodl.native_messaging import TemporaryLocationError, mac_location_is_temporary

        for path in ("/Volumes/Video Download/Video Download.app/Contents/MacOS/Video Download",
                     "/private/var/folders/x/T/AppTranslocation/ABC/d/Video Download.app/Contents/MacOS/Video Download"):
            with self.subTest(path=path), tempfile.TemporaryDirectory() as tmp:
                self.assertTrue(mac_location_is_temporary(path))
                (Path(tmp) / "Google" / "Chrome").mkdir(parents=True)
                with self.assertRaises(TemporaryLocationError):
                    self.install(Path(tmp), Path(tmp) / "native-host", host_executable=Path(path))
                self.assertFalse((Path(tmp) / "Google" / "Chrome" / "NativeMessagingHosts").exists())
        self.assertFalse(mac_location_is_temporary("/Applications/Video Download.app/Contents/MacOS/Video Download"))

    def test_every_supported_browser_has_a_target(self):
        targets = [target for target, _ in mac_manifest_targets(Path("/S"))]
        self.assertEqual(len(targets), len(MAC_CHROMIUM_DIRS) + 1)
        self.assertTrue(all(t.name == f"{native_host.HOST_NAME}.json" for t in targets))


class MacHostTest(unittest.TestCase):
    def test_browser_launch_is_recognized(self):
        self.assertTrue(native_host.is_browser_launch(["app", f"chrome-extension://{EXTENSION_ID}/"]))
        self.assertTrue(native_host.is_browser_launch(["app", "/x/com.videodl.bridge.json", FIREFOX_EXTENSION_ID]))
        self.assertFalse(native_host.is_browser_launch(["app"]))
        self.assertFalse(native_host.is_browser_launch(["app", "--self-test", "r.json"]))

    def test_frozen_mac_host_opens_the_app_bundle(self):
        exe = "/Applications/Video Download.app/Contents/MacOS/Video Download"
        with mock.patch.object(sys, "frozen", True, create=True), mock.patch.object(sys, "platform", "darwin"), \
                mock.patch.object(sys, "executable", exe), mock.patch.object(Path, "resolve", lambda self: self):
            config = native_host.current_config()
        self.assertEqual(config["launch"][0], "open")
        self.assertEqual(Path(config["launch"][1]).name, "Video Download.app")

    def test_saved_language_from_mac_preferences(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertIsNone(native_host._mac_saved_language(Path(tmp)))
            with open(Path(tmp) / native_host.MAC_SETTINGS_FILES[0], "wb") as file:
                plistlib.dump({"language": "de"}, file)
            self.assertEqual(native_host._mac_saved_language(Path(tmp)), "de")


class MacDesktopTest(unittest.TestCase):
    def test_reveal_selects_file_in_finder(self):
        calls = []
        with tempfile.NamedTemporaryFile(delete=False) as file:
            path = file.name
        try:
            desktop.reveal(path, platform="darwin", popen=calls.append)
        finally:
            os.unlink(path)
        self.assertEqual(calls, [["open", "-R", path]])

    def test_browsers_found_in_applications(self):
        with tempfile.TemporaryDirectory() as tmp:
            chrome = Path(tmp) / dialogs.MAC_BROWSERS["chrome.exe"]
            chrome.parent.mkdir(parents=True)
            chrome.write_text("")
            self.assertEqual(dialogs.browser_exe("chrome.exe", "darwin", (Path(tmp),)), str(chrome))
            self.assertIsNone(dialogs.browser_exe("msedge.exe", "darwin", (Path(tmp),)))


class MacTextsTest(unittest.TestCase):
    def test_shortcuts_and_windows_wording_follow_the_system(self):
        from videodl import i18n

        language = i18n.get_language()
        self.addCleanup(i18n.set_language, language)
        i18n.set_language("de")
        with mock.patch.object(i18n, "PLATFORM", "darwin"):
            self.assertIn("⌘V", i18n.tr("toolbar.paste_tip"))
            self.assertNotIn("Strg", i18n.tr("toolbar.paste_tip"))
            self.assertEqual(i18n.tr("theme.system"), "Wie macOS")
            self.assertIn("⌘⇧G", i18n.tr("help.copied"))
        with mock.patch.object(i18n, "PLATFORM", "win32"):
            self.assertIn("Strg+V", i18n.tr("toolbar.paste_tip"))
            self.assertEqual(i18n.tr("theme.system"), "Wie Windows")

    def test_every_mac_variant_exists_in_all_languages(self):
        from videodl import i18n

        for key in i18n.MAC_VARIANTS:
            with self.subTest(key=key):
                self.assertEqual(len(i18n.TEXTS[key + "_mac"]), len(i18n.LANGUAGES))


class MacUpdateTest(unittest.TestCase):
    def release(self, *names):
        return {"tag_name": "v9.9.9", "body": "x", "assets": [
            {"name": name, "browser_download_url": f"https://github.com/r/{name}", "size": 5} for name in names]}

    def test_mac_picks_the_dmg_and_opens_it_instead_of_installing(self):
        with mock.patch.object(updater, "PLATFORM", "darwin"):
            release = updater.parse_release(self.release(
                "VideoDownload-Setup-9.9.9.exe", "VideoDownload-Setup-9.9.9.exe.sha256",
                "VideoDownload-macOS-arm64-9.9.9.dmg", "VideoDownload-macOS-arm64-9.9.9.dmg.sha256"))
            self.assertFalse(updater.can_self_install())
        self.assertEqual(release.installer_name, "VideoDownload-macOS-arm64-9.9.9.dmg")
        self.assertEqual(release.version, "9.9.9")

    def test_release_without_mac_build_means_nothing_new_on_mac(self):
        windows_only = self.release("VideoDownload-Setup-9.9.9.exe", "VideoDownload-Setup-9.9.9.exe.sha256")
        with mock.patch.object(updater, "PLATFORM", "darwin"):
            self.assertIsNone(updater.parse_release(windows_only))
        with mock.patch.object(updater, "PLATFORM", "win32"):
            self.assertEqual(updater.parse_release(windows_only).installer_name, "VideoDownload-Setup-9.9.9.exe")
            self.assertTrue(updater.can_self_install())


def _fake_app(folder: Path, version: str, bundle_id: str = "io.github.abnps.videodownload") -> Path:
    app = folder / "Video Download.app"
    (app / "Contents" / "MacOS").mkdir(parents=True)
    (app / "Contents" / "MacOS" / "VideoDownload").write_text("#!/bin/sh\n", encoding="utf-8")
    (app / "Contents" / "Info.plist").write_bytes(plistlib.dumps({
        "CFBundleIdentifier": bundle_id, "CFBundleShortVersionString": version,
        "CFBundleExecutable": "VideoDownload", "CFBundlePackageType": "APPL"}))
    return app


class MacSelfUpdateTest(unittest.TestCase):
    """Plan 1.0, tačka 7: Mac sam preuzme potpisan .dmg, pripremi novu aplikaciju i zamijeni je poslije gašenja."""

    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        self.bundle = _fake_app(self.root / "Applications", "9.9.8")
        self.staged = self.bundle.with_name(".Video Download.app.novo")
        self.dmg = self.root / "VideoDownload-macOS-arm64-9.9.9.dmg"
        self.dmg.write_bytes(b"dmg")

    def signed_release(self):
        return updater.Release("9.9.9", "", self.dmg.name, "https://g/x.dmg", "https://g/x.dmg.sha256", 3,
                               manifest_url="https://g/release-macos.json",
                               signature_url="https://g/release-macos.json.sig")

    def test_mac_uses_its_own_signed_manifest(self):
        names = ["VideoDownload-Setup-9.9.9.exe", "VideoDownload-Setup-9.9.9.exe.sha256", "release.json",
                 "release.json.sig", "VideoDownload-macOS-arm64-9.9.9.dmg",
                 "VideoDownload-macOS-arm64-9.9.9.dmg.sha256", "release-macos.json", "release-macos.json.sig"]
        data = {"tag_name": "v9.9.9", "assets": [{"name": n, "browser_download_url": f"https://g/{n}"} for n in names]}
        with mock.patch.object(updater, "PLATFORM", "darwin"):
            mac = updater.parse_release(data)
        with mock.patch.object(updater, "PLATFORM", "win32"):
            windows = updater.parse_release(data)
        self.assertEqual((mac.manifest_url, mac.signature_url),
                         ("https://g/release-macos.json", "https://g/release-macos.json.sig"))
        self.assertEqual(windows.manifest_url, "https://g/release.json")

    def test_self_install_only_when_signed_and_replaceable(self):
        release = self.signed_release()
        self.assertTrue(updater.can_self_install(release, "darwin", self.bundle))
        unsigned = updater.Release("9.9.9", "", self.dmg.name, "https://g/x.dmg", "https://g/x.dmg.sha256", 3)
        self.assertFalse(updater.can_self_install(unsigned, "darwin", self.bundle))  # izdanja prije 0.9.8
        translocated = Path("/private/var/folders/x/AppTranslocation/1/d/Video Download.app")
        self.assertFalse(updater.can_self_install(release, "darwin", translocated))
        self.assertFalse(updater.can_self_install(release, "darwin", Path("/Volumes/Video Download/Video Download.app")))
        self.assertFalse(updater.can_self_install(release, "linux", self.bundle))
        self.assertTrue(updater.can_self_install(platform="win32"))
        with mock.patch.object(updater.runtime, "mac_app_bundle", return_value=None):
            self.assertFalse(updater.can_self_install(release, "darwin"))  # nije instalirana aplikacija

    def fake_runner(self, version="9.9.9", bundle_id="io.github.abnps.videodownload", codesign=0):
        mount = self.root / "Volumes" / "Video Download"
        shutil.rmtree(mount, ignore_errors=True)
        calls = []

        def run(args, **kwargs):
            calls.append(args[:2])
            result = mock.Mock(returncode=0, stdout=b"")
            if args[:2] == ["hdiutil", "attach"]:
                _fake_app(mount, version, bundle_id)
                result.stdout = plistlib.dumps({"system-entities": [{"dev-entry": "/dev/disk9"},
                                                                    {"mount-point": str(mount)}]})
            elif args[0] == "ditto":
                shutil.copytree(args[1], args[2])
            elif args[0] == "codesign":
                result.returncode = codesign
            return result
        return run, calls

    def test_prepare_copies_checks_and_always_detaches(self):
        run, calls = self.fake_runner()
        staged = updater.prepare_mac_app(self.dmg, self.bundle, runner=run)
        self.assertEqual(staged, self.staged)
        self.assertEqual(plistlib.loads((staged / "Contents/Info.plist").read_bytes())["CFBundleShortVersionString"],
                         "9.9.9")
        self.assertIn(["hdiutil", "detach"], calls)
        self.assertFalse(self.dmg.exists())

    def test_prepare_refuses_wrong_app_version_or_signature(self):
        for name, options in {"version": {"version": "1.0.0"}, "other_app": {"bundle_id": "com.example.other"},
                              "codesign": {"codesign": 1}}.items():
            with self.subTest(case=name):
                run, calls = self.fake_runner(**options)
                with self.assertRaises(updater.UpdateError) as caught:
                    updater.prepare_mac_app(self.dmg, self.bundle, runner=run)
                self.assertEqual(caught.exception.key, "update.unsigned")
                self.assertFalse(self.staged.exists())  # ništa neprovjereno ne ostaje pored aplikacije
                self.assertIn(["hdiutil", "detach"], calls)

    def test_verified_dmg_is_prepared_in_the_worker(self):
        prepared = self.root / "novo.app"
        with mock.patch.object(updater, "PLATFORM", "darwin"), \
                mock.patch.object(updater, "_download_http"), mock.patch.object(updater, "_fetch_small"), \
                mock.patch.object(updater, "_verify"), \
                mock.patch.object(updater, "_verified_manifest", return_value={}) as verified, \
                mock.patch.object(updater.release_signing, "check_installer"), \
                mock.patch.object(updater.runtime, "mac_app_bundle", return_value=self.bundle), \
                mock.patch.object(updater, "prepare_mac_app", return_value=prepared) as prepare:
            result = updater.download_installer(self.signed_release(), self.root / "dl")
        self.assertEqual(result, prepared)
        prepare.assert_called_once_with(self.root / "dl" / self.dmg.name, self.bundle)
        self.assertEqual(verified.call_args.args[1].name, "release-macos.json")

    @unittest.skipUnless(sys.platform == "darwin" or shutil.which("sh"), "treba sh")
    def test_swap_script_replaces_app_and_launches_it(self):
        shell = shutil.which("sh") if sys.platform == "win32" else "/bin/sh"
        staged = _fake_app(self.root / "staged", "9.9.9")
        launched = self.root / "pokrenuto.txt"
        finished = subprocess.Popen([sys.executable, "-c", "pass"])
        finished.wait()  # program je već ugašen: zamjena kreće odmah
        launcher = self.root / "launch.sh"
        launcher.write_text('#!/bin/sh\necho "$1" > "' + launched.as_posix() + '"\n', encoding="utf-8")
        launcher.chmod(0o755)
        process = updater.launch_mac_swap(staged, self.bundle, pid=finished.pid, launch=launcher.as_posix(),
                                          shell=shell)
        process.wait(timeout=30)
        info = plistlib.loads((self.bundle / "Contents/Info.plist").read_bytes())
        self.assertEqual(info["CFBundleShortVersionString"], "9.9.9")
        self.assertFalse(staged.exists())
        self.assertFalse(self.bundle.with_name("Video Download.app.staro").exists())
        self.assertIn("Video Download.app", launched.read_text(encoding="utf-8"))

    @unittest.skipUnless(sys.platform == "darwin", "hdiutil i codesign postoje samo na Macu")
    def test_real_dmg_on_mac(self):
        source = self.root / "dmg-src"
        app = _fake_app(source, "9.9.9")
        if subprocess.run(["codesign", "--force", "--deep", "--sign", "-", str(app)], capture_output=True).returncode:
            self.skipTest("ad-hoc potpis probne aplikacije nije uspio")
        self.dmg.unlink()
        subprocess.run(["hdiutil", "create", "-volname", "Video Download", "-srcfolder", str(source), "-ov",
                        "-format", "UDZO", str(self.dmg)], check=True, capture_output=True)
        staged = updater.prepare_mac_app(self.dmg, self.bundle)
        self.assertEqual(plistlib.loads((staged / "Contents/Info.plist").read_bytes())["CFBundleShortVersionString"],
                         "9.9.9")


if __name__ == "__main__":
    unittest.main()
