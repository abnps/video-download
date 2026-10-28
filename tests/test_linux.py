"""Linux verzija (beta): putanje, veza s dodatkom, browseri, tekstovi i ažuriranje AppImage-a.

Testovi zadaju sistem sami (platform="linux"), pa prolaze i na Windowsu i na Linux računaru u CI-ju.
"""

import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path, PurePosixPath
from unittest import mock

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from videodl import desktop, dialogs, legal, native_host, runtime, updater  # noqa: E402
from videodl.native_messaging import (  # noqa: E402
    CHROMIUM_EXTENSION_IDS, FIREFOX_EXTENSION_ID, LINUX_CHROMIUM_DIRS, install_native_host, linux_manifest_targets,
    uninstall_native_host,
)

APPIMAGE = "/home/ana/Programi/VideoDownload-linux-x86_64.AppImage"


class LinuxPathsTest(unittest.TestCase):
    def test_config_folder_follows_xdg(self):
        self.assertEqual(runtime.user_config_base({}, Path("/home/ana")), Path("/home/ana/.config"))
        self.assertEqual(runtime.user_config_base({"XDG_CONFIG_HOME": "/x/cfg"}, Path("/home/ana")), Path("/x/cfg"))

    def test_appimage_only_for_frozen_linux_with_existing_file(self):
        with tempfile.NamedTemporaryFile(delete=False) as file:
            path = file.name
        self.addCleanup(os.unlink, path)
        with mock.patch.object(runtime, "is_frozen", return_value=True), mock.patch.object(runtime, "IS_LINUX", True):
            self.assertEqual(runtime.linux_appimage({"APPIMAGE": path}), Path(path))
            self.assertIsNone(runtime.linux_appimage({"APPIMAGE": path + ".nema"}))
            self.assertIsNone(runtime.linux_appimage({}))
        with mock.patch.object(runtime, "is_frozen", return_value=False), mock.patch.object(runtime, "IS_LINUX", True):
            self.assertIsNone(runtime.linux_appimage({"APPIMAGE": path}))

    def test_programs_we_start_get_system_libraries(self):
        environ = {"LD_LIBRARY_PATH": "/tmp/.mount_x/_internal", "LD_LIBRARY_PATH_ORIG": "/usr/local/lib",
                   "LD_PRELOAD": "/tmp/.mount_x/x.so"}
        runtime.restore_system_env(environ)
        self.assertEqual(environ, {"LD_LIBRARY_PATH": "/usr/local/lib"})

    def test_chrome_gets_extension_copy_on_a_stable_path(self):
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "mount" / "extension"
            source.mkdir(parents=True)
            (source / "manifest.json").write_text('{"version": "2"}', encoding="utf-8")
            target = Path(tmp) / "data" / "extension"
            target.mkdir(parents=True)
            (target / "stari.js").write_text("", encoding="utf-8")  # ostatak stare verzije se briše
            self.assertEqual(runtime.user_extension_dir(source, target), target)
            self.assertEqual(sorted(p.name for p in target.iterdir()), ["manifest.json"])
            with mock.patch.object(runtime, "linux_appimage", return_value=None):
                self.assertEqual(runtime.user_extension_dir(source), source)  # Windows/Mac/razvoj: bez kopije


    def test_menu_entry_points_to_the_appimage_and_follows_a_move(self):
        with tempfile.TemporaryDirectory() as tmp:
            icon = Path(tmp) / "icon.png"
            icon.write_bytes(b"png")
            data = Path(tmp) / "share"
            entry = runtime.install_linux_menu_entry(PurePosixPath("/home/ana/Programi/Video Download.AppImage"), icon,
                                                     data)
            self.assertEqual(entry, data / "applications" / "io.github.abnps.videodownload.desktop")
            text = entry.read_text(encoding="utf-8")
            self.assertIn('Exec="/home/ana/Programi/Video Download.AppImage"\n', text)
            self.assertIn("Icon=io.github.abnps.videodownload\n", text)
            self.assertTrue((data / "icons/hicolor/128x128/apps/io.github.abnps.videodownload.png").is_file())
            runtime.install_linux_menu_entry(PurePosixPath("/opt/x/VideoDownload.AppImage"), icon, data)
            self.assertIn('Exec="/opt/x/VideoDownload.AppImage"\n', entry.read_text(encoding="utf-8"))

    def test_menu_entry_escapes_special_characters(self):
        # Specifikacija: prvo escape za navodnike (\$, \"), pa se svaka kosa crta u vrijednosti udvostruči.
        self.assertEqual(runtime._desktop_exec(PurePosixPath('/home/a/$x"y.AppImage')),
                         r'"/home/a/\\$x\\"y.AppImage"')


class LinuxNativeMessagingTest(unittest.TestCase):
    def test_manifests_go_only_to_installed_browsers(self):
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            (home / ".config" / "google-chrome").mkdir(parents=True)
            (home / ".mozilla").mkdir()  # Firefox postoji, Edge ne
            install_native_host(home / "native-host", platform="linux", linux_home=home,
                                host_executable=Path(APPIMAGE))

            chrome = home / ".config" / "google-chrome" / "NativeMessagingHosts" / f"{native_host.HOST_NAME}.json"
            firefox = home / ".mozilla" / "native-messaging-hosts" / f"{native_host.HOST_NAME}.json"
            self.assertEqual(json.loads(chrome.read_text())["allowed_origins"],
                             [f"chrome-extension://{i}/" for i in CHROMIUM_EXTENSION_IDS])
            self.assertEqual(json.loads(firefox.read_text())["allowed_extensions"], [FIREFOX_EXTENSION_ID])
            self.assertEqual(json.loads(chrome.read_text())["path"], str(Path(APPIMAGE)))
            self.assertFalse((home / ".config" / "microsoft-edge").exists())  # ne pravi foldere za browser koji nema

            uninstall_native_host(home / "native-host", platform="linux", linux_home=home)
            for host_name in native_host.HOST_NAMES:
                self.assertFalse((chrome.parent / f"{host_name}.json").exists())
                self.assertFalse((firefox.parent / f"{host_name}.json").exists())
            self.assertFalse((home / "native-host").exists())

    def test_development_host_script_is_registered_too(self):
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            (home / ".config" / "chromium").mkdir(parents=True)
            install_native_host(home / "native-host", platform="linux", linux_home=home,
                                python_exe="/usr/bin/python3", launch_command=["/usr/bin/python3", "/p/pokreni.pyw"])
            chromium = home / ".config" / "chromium" / "NativeMessagingHosts" / f"{native_host.HOST_NAME}.json"
            self.assertEqual(Path(json.loads(chromium.read_text())["path"]).name, "host.sh")

    def test_every_supported_browser_has_a_target(self):
        targets = [target for target, _ in linux_manifest_targets(Path("/home/ana"))]
        self.assertEqual(len(targets), len(native_host.HOST_NAMES) * (len(LINUX_CHROMIUM_DIRS) + 1))
        self.assertIn(Path("/home/ana/.mozilla/native-messaging-hosts") / f"{native_host.HOST_NAME}.json", targets)

    def test_frozen_linux_host_starts_the_appimage(self):
        with mock.patch.object(sys, "frozen", True, create=True), mock.patch.object(sys, "platform", "linux"), \
                mock.patch.dict(os.environ, {"APPIMAGE": APPIMAGE}):
            self.assertEqual(native_host.current_config(), {"launch": [APPIMAGE]})

    def test_saved_language_from_qt_settings(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertIsNone(native_host._linux_saved_language(Path(tmp)))
            (Path(tmp) / "VideoDownload").mkdir()
            (Path(tmp) / "VideoDownload" / "VideoDownload.conf").write_text("[General]\ntheme=dark\nlanguage=fr\n",
                                                                           encoding="utf-8")
            self.assertEqual(native_host._linux_saved_language(Path(tmp)), "fr")


class LinuxDesktopTest(unittest.TestCase):
    def test_reveal_opens_the_folder_of_a_file(self):
        opened = []
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "video.mp4"
            path.write_bytes(b"")
            with mock.patch.object(desktop.QDesktopServices, "openUrl", side_effect=opened.append):
                desktop.reveal(str(path), platform="linux", popen=self.fail)
            self.assertEqual(Path(opened[0].toLocalFile()), Path(tmp))

    def test_browsers_found_on_path(self):
        found = {"chromium": "/usr/bin/chromium", "firefox": "/usr/bin/firefox"}
        self.assertEqual(dialogs.browser_exe("chrome.exe", "linux", which=found.get), "/usr/bin/chromium")
        self.assertEqual(dialogs.browser_exe("firefox.exe", "linux", which=found.get), "/usr/bin/firefox")
        self.assertIsNone(dialogs.browser_exe("msedge.exe", "linux", which=found.get))


class LinuxTextsTest(unittest.TestCase):
    def test_linux_wording_keeps_ctrl_and_names_no_other_system(self):
        from videodl import i18n

        language = i18n.get_language()
        self.addCleanup(i18n.set_language, language)
        i18n.set_language("en")
        with mock.patch.object(i18n, "PLATFORM", "linux"):
            self.assertEqual(i18n.tr("theme.system"), "Same as system")
            self.assertIn("Ctrl+L", i18n.tr("help.copied"))
            self.assertIn("Ctrl+V", i18n.tr("toolbar.paste_tip"))
        for key in i18n.LINUX_VARIANTS:
            with self.subTest(key=key):
                self.assertEqual(len(i18n.TEXTS[key + "_linux"]), len(i18n.LANGUAGES))
                for text in i18n.TEXTS[key + "_linux"]:
                    self.assertNotIn("Windows", text)
                    self.assertNotIn("⌘", text)

    def test_linux_ffmpeg_is_listed_with_its_source(self):
        self.assertIn(legal.FFMPEG_LINUX, legal.FFMPEG_BUILDS)
        self.assertIn("ffmpeg-9.0.2.tar.xz", legal.FFMPEG_LINUX.note)


class LinuxUpdateTest(unittest.TestCase):
    NAMES = ["VideoDownload-Setup-9.9.9.exe", "VideoDownload-Setup-9.9.9.exe.sha256", "release.json",
             "release.json.sig", "VideoDownload-macOS-arm64-9.9.9.dmg", "VideoDownload-macOS-arm64-9.9.9.dmg.sha256",
             "release-macos.json", "release-macos.json.sig", "VideoDownload-linux-x86_64-9.9.9.AppImage",
             "VideoDownload-linux-x86_64-9.9.9.AppImage.sha256", "release-linux.json", "release-linux.json.sig"]

    def data(self, names):
        return {"tag_name": "v9.9.9", "assets": [{"name": n, "browser_download_url": f"https://g/{n}", "size": 5}
                                                  for n in names]}

    def test_linux_picks_the_appimage_and_its_own_signed_manifest(self):
        with mock.patch.object(updater, "PLATFORM", "linux"):
            release = updater.parse_release(self.data(self.NAMES))
        self.assertEqual(release.installer_name, "VideoDownload-linux-x86_64-9.9.9.AppImage")
        self.assertEqual((release.manifest_url, release.signature_url),
                         ("https://g/release-linux.json", "https://g/release-linux.json.sig"))

    def test_release_without_linux_build_means_nothing_new(self):
        with mock.patch.object(updater, "PLATFORM", "linux"):
            self.assertIsNone(updater.parse_release(self.data(self.NAMES[:8])))

    def test_self_install_only_signed_and_writable_appimage(self):
        with tempfile.TemporaryDirectory() as tmp:
            appimage = Path(tmp) / "VideoDownload.AppImage"
            appimage.write_bytes(b"")
            signed = updater.Release("9.9.9", "", "x.AppImage", "https://g/x", "https://g/x.sha256", 5,
                                     manifest_url="https://g/release-linux.json", signature_url="https://g/s")
            unsigned = updater.Release("9.9.9", "", "x.AppImage", "https://g/x", "https://g/x.sha256", 5)
            self.assertTrue(updater.can_self_install(signed, "linux", appimage=appimage))
            self.assertFalse(updater.can_self_install(unsigned, "linux", appimage=appimage))
            with mock.patch.object(updater.runtime, "linux_appimage", return_value=None):
                self.assertFalse(updater.can_self_install(signed, "linux"))  # nije pokrenut iz AppImage-a

    def test_prepare_puts_new_appimage_next_to_the_old_one(self):
        with tempfile.TemporaryDirectory() as tmp:
            current = Path(tmp) / "Programi" / "VideoDownload.AppImage"
            current.parent.mkdir()
            current.write_bytes(b"staro")
            download = Path(tmp) / "dl" / "VideoDownload-linux-x86_64-9.9.9.AppImage"
            download.parent.mkdir()
            download.write_bytes(b"novo")
            staged = updater.prepare_linux_appimage(download, current)
            self.assertEqual(staged, current.with_name(".VideoDownload.AppImage.novo"))
            self.assertEqual(staged.read_bytes(), b"novo")
            self.assertFalse(download.exists())
            if sys.platform != "win32":
                self.assertTrue(os.access(staged, os.X_OK))
            wrong = Path(tmp) / "dl" / "nesto.AppImage"
            wrong.write_bytes(b"")
            with self.assertRaises(updater.UpdateError):
                updater.prepare_linux_appimage(wrong, current)

    @unittest.skipUnless(sys.platform != "win32" or shutil.which("sh"), "treba sh")
    def test_swap_script_replaces_appimage_and_starts_it(self):
        shell = shutil.which("sh") if sys.platform == "win32" else "/bin/sh"
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            started = root / "pokrenuto.txt"
            current = root / "VideoDownload.AppImage"
            current.write_text("#!/bin/sh\necho staro > '" + started.as_posix() + "'\n", encoding="utf-8")
            staged = root / ".VideoDownload.AppImage.novo"
            staged.write_text("#!/bin/sh\necho novo > '" + started.as_posix() + "'\n", encoding="utf-8")
            staged.chmod(0o755)
            finished = subprocess.Popen([sys.executable, "-c", "pass"])
            finished.wait()  # program je već ugašen: zamjena kreće odmah
            process = updater.launch_linux_swap(Path(staged.as_posix()), Path(current.as_posix()), pid=finished.pid,
                                                shell=shell)
            process.wait(timeout=30)
            self.assertFalse(staged.exists())
            self.assertIn("novo", current.read_text(encoding="utf-8"))
            for _ in range(50):
                if started.exists():
                    break
                subprocess.run([sys.executable, "-c", "import time; time.sleep(0.1)"])
            self.assertEqual(started.read_text(encoding="utf-8").strip(), "novo")


if __name__ == "__main__":
    unittest.main()
