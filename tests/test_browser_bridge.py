import base64
import hashlib
import http.client
import io
import json
import re
import os
import tempfile
import threading
import time
import unittest
from unittest import mock
from pathlib import Path

from videodl import native_host
from videodl.bridge import BridgeServer
from videodl.browser import cookie_file, parse_browser_request
from videodl.native_messaging import (
    EXTENSION_ID, FIREFOX_EXTENSION_ID, FIREFOX_REGISTRY_PATHS, PROJECT_ROOT, REGISTRY_PATHS, install_native_host,
)


class ParseBrowserRequestTest(unittest.TestCase):
    def test_page_request_uses_host_when_title_missing(self):
        request = parse_browser_request({"page_url": "https://sajt.ba/video/1", "page_title": "  "})
        self.assertEqual(request.page_title, "sajt.ba")
        self.assertIsNone(request.media_url)

    def test_media_request_keeps_only_allowed_headers(self):
        request = parse_browser_request({
            "page_url": "https://sajt.ba/v",
            "page_title": "Lekcija 3",
            "media": {"url": "https://cdn.sajt.ba/x/index.m3u8", "kind": "hls"},
            "headers": {"referer": "https://sajt.ba/v", "User-Agent": "UA", "Cookie": "tajna=1",
                        "Origin": "bad\r\nX: y"},
        })
        self.assertEqual(request.media_url, "https://cdn.sajt.ba/x/index.m3u8")
        self.assertEqual(request.media_kind, "hls")
        self.assertEqual(request.headers, {"Referer": "https://sajt.ba/v", "User-Agent": "UA"})

    def test_unknown_media_kind_becomes_file(self):
        request = parse_browser_request({"page_url": "https://a.ba", "media": {"url": "https://a.ba/v", "kind": "x"}})
        self.assertEqual(request.media_kind, "file")

    def test_only_cookies_of_the_downloaded_site_are_accepted(self):
        request = parse_browser_request({
            "page_url": "https://www.instagram.com/stories/nalog/123/",
            "cookies": [
                {"name": "sessionid", "value": "tajna", "domain": ".instagram.com", "path": "/",
                 "secure": True, "hostOnly": False, "expirationDate": 1893456000.5},
                {"name": "csrftoken", "value": "x", "domain": "www.instagram.com", "hostOnly": True},
                {"name": "tudji", "value": "y", "domain": ".google.com", "hostOnly": False},
                {"name": "los", "value": "a\tb", "domain": ".instagram.com", "hostOnly": False},
                "nije-kolacic",
            ],
        })
        self.assertEqual([c.name for c in request.cookies], ["sessionid", "csrftoken"])
        session = request.cookies[0]
        self.assertEqual((session.domain, session.host_only, session.expires, session.secure),
                         (".instagram.com", False, 1893456000, True))
        self.assertNotIn("tajna", repr(request))

    def test_cookie_file_is_read_by_yt_dlp_and_deleted(self):
        from yt_dlp import YoutubeDL

        request = parse_browser_request({
            "page_url": "https://www.instagram.com/stories/nalog/",
            "cookies": [{"name": "sessionid", "value": "tajna", "domain": ".instagram.com", "hostOnly": False},
                        {"name": "ds_user_id", "value": "42", "domain": "www.instagram.com", "hostOnly": True}],
        })
        with cookie_file(request.cookies) as path:
            self.assertTrue(os.path.isfile(path))
            with YoutubeDL({"quiet": True, "cookiefile": path}) as ydl:
                header = ydl.cookiejar.get_cookie_header("https://www.instagram.com/stories/nalog/")
        self.assertIn("sessionid=tajna", header)
        self.assertIn("ds_user_id=42", header)
        self.assertFalse(os.path.exists(path))
        with cookie_file(()) as nothing:
            self.assertIsNone(nothing)

    def test_invalid_requests_are_rejected(self):
        for payload in ([], {"page_url": "file:///C:/tajno.txt"}, {"page_url": "javascript:alert(1)"},
                        {"page_url": "https://a.ba", "media": {"url": "ftp://a.ba/v"}},
                        {"page_url": "https://a.ba", "media": "https://a.ba/v"}):
            with self.subTest(payload=payload), self.assertRaises(ValueError):
                parse_browser_request(payload)


class BridgeServerTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.bridge_file = Path(self.tmp.name) / "bridge.json"
        self.added = []
        self.focused = threading.Event()
        self.server = BridgeServer(self.added.append, self.focused.set, path=self.bridge_file)
        self.server.start()

    def tearDown(self):
        self.server.stop()
        self.tmp.cleanup()

    def raw(self, method, path, body=None, headers=None):
        connection = http.client.HTTPConnection("127.0.0.1", self.server.port, timeout=5)
        try:
            connection.request(method, path, body=body, headers=headers or {})
            response = connection.getresponse()
            return response.status, response.read()
        finally:
            connection.close()

    def test_bridge_file_describes_running_server(self):
        bridge = native_host.read_bridge(self.bridge_file)
        self.assertEqual(bridge["port"], self.server.port)
        self.assertEqual(native_host.find_running_app(self.bridge_file)["token"], self.server.token)

    def test_requests_without_valid_token_or_host_are_forbidden(self):
        payload = json.dumps({"page_url": "https://a.ba"})
        self.assertEqual(self.raw("POST", "/add", payload)[0], 403)
        self.assertEqual(self.raw("POST", "/add", payload, {native_host.TOKEN_HEADER: "pogresno"})[0], 403)
        # DNS rebinding: ispravan token, ali tuđi Host.
        headers = {native_host.TOKEN_HEADER: self.server.token, "Host": f"zli.sajt:{self.server.port}"}
        self.assertEqual(self.raw("POST", "/add", payload, headers)[0], 403)
        self.assertEqual(self.added, [])

    def test_slow_client_is_cut_off_and_extra_connections_are_refused(self):
        import socket

        from videodl import bridge as bridge_module

        # Zaglavljeni klijenti (otvore vezu i ništa ne pošalju) popune sva mjesta…
        stuck = [socket.create_connection(("127.0.0.1", self.server.port)) for _ in range(bridge_module.MAX_CONNECTIONS)]
        self.addCleanup(lambda: [s.close() for s in stuck])
        time.sleep(0.3)
        # …višak se odmah zatvara umjesto da čeka…
        extra = socket.create_connection(("127.0.0.1", self.server.port))
        extra.settimeout(3)
        try:
            self.assertEqual(extra.recv(1), b"")  # server je odmah zatvorio vezu
        except ConnectionResetError:
            pass
        finally:
            extra.close()
        # …a poslije roka za čitanje mjesta se oslobode i program opet normalno odgovara.
        for s in stuck:
            s.close()
        deadline = time.monotonic() + 5
        status = None
        while time.monotonic() < deadline and status != 200:
            try:
                status, _ = self.raw("GET", "/ping", headers={native_host.TOKEN_HEADER: self.server.token,
                                                              "Host": f"127.0.0.1:{self.server.port}"})
            except OSError:
                time.sleep(0.1)
        self.assertEqual(status, 200)

    def test_request_that_never_finishes_times_out(self):
        import socket

        from videodl import bridge as bridge_module

        self.assertLessEqual(bridge_module.READ_TIMEOUT_SECONDS, 30)
        with mock.patch.object(bridge_module, "READ_TIMEOUT_SECONDS", 0.5):
            server = bridge_module.BridgeServer(lambda r: None, lambda: None, path=Path(self.tmp.name) / "b2.json")
            server.start()
            self.addCleanup(server.stop)
            client = socket.create_connection(("127.0.0.1", server.port))
            client.sendall(b"GET /ping HTTP/1.1\r\n")  # pola zaglavlja, pa ništa
            client.settimeout(5)
            started = time.monotonic()
            try:
                client.recv(1024)
            except (ConnectionResetError, socket.timeout):
                pass
            finally:
                client.close()
            self.assertLess(time.monotonic() - started, 4)  # server je prekinuo, nije čekao zauvijek

    def test_add_and_focus_with_token(self):
        bridge = native_host.read_bridge(self.bridge_file)
        status, _ = native_host.call_app(bridge, "POST", "/add", {
            "page_url": "https://a.ba/v", "media": {"url": "https://a.ba/v.mp4", "kind": "file"}})
        self.assertEqual(status, 200)
        self.assertEqual(self.added[0].media_url, "https://a.ba/v.mp4")
        self.assertEqual(native_host.call_app(bridge, "POST", "/focus")[0], 200)
        self.assertTrue(self.focused.is_set())

    def test_invalid_body_is_rejected_with_message(self):
        bridge = native_host.read_bridge(self.bridge_file)
        status, data = native_host.call_app(bridge, "POST", "/add", {"page_url": "file:///x"})
        self.assertEqual(status, 400)
        self.assertIn("Neispravan link", data["error"])

    def test_stop_removes_only_own_bridge_file(self):
        self.server.stop()
        self.assertFalse(self.bridge_file.exists())
        self.assertIsNone(native_host.find_running_app(self.bridge_file))


class NativeHostTest(unittest.TestCase):
    def test_message_framing_round_trip(self):
        stream = io.BytesIO()
        native_host.write_message(stream, {"action": "add", "naslov": "Čćšđž"})
        stream.seek(0)
        self.assertEqual(native_host.read_message(stream), {"action": "add", "naslov": "Čćšđž"})
        self.assertIsNone(native_host.read_message(io.BytesIO(b"\x01")))

    def test_oversized_message_is_refused(self):
        stream = io.BytesIO((native_host.MAX_MESSAGE_BYTES + 1).to_bytes(4, "little"))
        with self.assertRaises(ValueError):
            native_host.read_message(stream)

    def test_add_goes_to_running_app_without_launch(self):
        from videodl.i18n import set_language

        set_language("bs")  # popup dodatka dobija jezik aplikacije preko statusa
        with tempfile.TemporaryDirectory() as tmp:
            bridge_file = Path(tmp) / "bridge.json"
            added = []
            server = BridgeServer(added.append, lambda: None, path=bridge_file)
            server.start()
            try:
                launches = []
                reply = native_host.handle({"action": "add", "request": {"page_url": "https://a.ba/v"}},
                                           {"launch": ["app"]}, bridge_file=bridge_file, launch=launches.append)
                status = native_host.handle({"action": "status"}, {}, bridge_file=bridge_file)
            finally:
                server.stop()
        self.assertEqual(reply, {"ok": True, "launched": False})
        self.assertEqual(launches, [])
        self.assertEqual(added[0].page_url, "https://a.ba/v")
        self.assertEqual((status["ok"], status["running"], status["language"]), (True, True, "bs"))

    def test_add_launches_app_and_waits_for_bridge(self):
        with tempfile.TemporaryDirectory() as tmp:
            bridge_file = Path(tmp) / "bridge.json"
            added = []
            servers = []

            def fake_launch(command):
                self.assertEqual(command, ["pythonw", "pokreni.pyw"])
                server = BridgeServer(added.append, lambda: None, path=bridge_file)
                threading.Timer(0.3, server.start).start()
                servers.append(server)

            try:
                reply = native_host.handle({"action": "add", "request": {"page_url": "https://a.ba/v"}},
                                           {"launch": ["pythonw", "pokreni.pyw"]},
                                           bridge_file=bridge_file, launch=fake_launch, launch_timeout=5)
            finally:
                for server in servers:
                    server.stop()
        self.assertEqual(reply, {"ok": True, "launched": True})
        self.assertEqual(len(added), 1)

    def test_launch_timeout_and_unknown_action(self):
        with tempfile.TemporaryDirectory() as tmp:
            bridge_file = Path(tmp) / "bridge.json"
            now = [0.0]
            reply = native_host.handle({"action": "add", "request": {}}, {"launch": ["x"]},
                                       bridge_file=bridge_file, launch=lambda c: None,
                                       sleep=lambda s: now.__setitem__(0, now[0] + s),
                                       clock=lambda: now[0], launch_timeout=1)
            unknown = native_host.handle({"action": "obrisi"}, {}, bridge_file=bridge_file)
        self.assertFalse(reply["ok"])
        self.assertEqual(reply["code"], "app-timeout")
        self.assertFalse(unknown["ok"])


class NativeMessagingInstallTest(unittest.TestCase):
    def test_extension_id_matches_manifest_key(self):
        manifest = json.loads((PROJECT_ROOT / "extension" / "manifest.json").read_text(encoding="utf-8"))
        digest = hashlib.sha256(base64.b64decode(manifest["key"])).hexdigest()[:32]
        self.assertEqual("".join(chr(ord("a") + int(ch, 16)) for ch in digest), EXTENSION_ID)

    def test_install_writes_host_files_and_registry_for_both_browsers(self):
        written = {}
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp) / "native-host"
            manifest_path = install_native_host(
                folder, python_exe=r"C:\Python314\python.exe",
                launch_command=[r"C:\Python314\pythonw.exe", r"C:\Прилози\pokreni.pyw"],
                set_registry=lambda keys, value: written.update(dict.fromkeys(keys, value)), platform="win32")

            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            firefox = json.loads(Path(written[FIREFOX_REGISTRY_PATHS[0]]).read_text(encoding="utf-8"))
            script = (folder / "host.bat").read_bytes()
            config = json.loads((folder / "host-config.json").read_text(encoding="utf-8"))
            host_copied = (folder / "host.py").read_text(encoding="utf-8") == \
                Path(native_host.__file__).read_text(encoding="utf-8")

        self.assertEqual(manifest["allowed_origins"], [f"chrome-extension://{EXTENSION_ID}/"])
        self.assertEqual(manifest["name"], native_host.HOST_NAME)
        self.assertTrue(manifest["path"].endswith("host.bat"))
        self.assertTrue(script.isascii())
        self.assertIn(b'"C:\\Python314\\python.exe" "%~dp0host.py"', script)
        self.assertEqual(config["launch"][1], r"C:\Прилози\pokreni.pyw")
        self.assertTrue(host_copied)
        self.assertEqual(set(written), set(REGISTRY_PATHS) | set(FIREFOX_REGISTRY_PATHS))
        self.assertTrue(all(written[key] == str(manifest_path) for key in REGISTRY_PATHS))
        # Firefox ima svoj manifest: isti host, ali dozvoljava samo naš Firefox dodatak.
        self.assertTrue(written[FIREFOX_REGISTRY_PATHS[0]].endswith(".firefox.json"))
        self.assertEqual(firefox["allowed_extensions"], [FIREFOX_EXTENSION_ID])
        self.assertEqual(firefox["path"], manifest["path"])
        self.assertNotIn("allowed_origins", firefox)



class PresetFromExtensionTest(unittest.TestCase):
    """Dugme „Preuzmi kao MP3" šalje format uz zahtjev; prihvata se samo poznat format."""

    def parse(self, **extra):
        return parse_browser_request({"page_url": "https://v.test/a", "page_title": "A", **extra})

    def test_known_preset_is_kept(self):
        self.assertEqual(self.parse(preset="mp3").preset, "mp3")
        self.assertEqual(self.parse(preset="720p").preset, "720p")

    def test_unknown_or_missing_preset_is_ignored(self):
        for value in (None, "", "exe", 5, {"key": "mp3"}, "mp3; rm -rf"):
            self.assertIsNone(self.parse(preset=value).preset, value)
        self.assertIsNone(self.parse().preset)

if __name__ == "__main__":
    unittest.main()


class UninstallRegistryTest(unittest.TestCase):
    def test_uninstaller_removes_every_key_the_app_registers(self):
        # Svaki browser za koji program registruje host mora se i ukloniti pri deinstalaciji
        # (inače ostaje zapis koji pokazuje na obrisan fajl).
        iss = (PROJECT_ROOT / "installer" / "VideoDownload.iss").read_text(encoding="utf-8-sig")
        removed = set(re.findall(r'Root: HKCU; Subkey: "([^"]+)"; Flags: uninsdeletekey', iss))
        self.assertEqual(set(REGISTRY_PATHS) | set(FIREFOX_REGISTRY_PATHS), removed)
