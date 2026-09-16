"""Lokalni HTTP most u aplikaciji: prima zahtjeve koje native host prosljeđuje iz browsera."""

import hmac
import json
import os
import secrets
import threading
from collections.abc import Callable
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from . import __version__
from .browser import BrowserRequest, parse_browser_request
from .i18n import get_language
from .native_host import TOKEN_HEADER, bridge_path

MAX_BODY_BYTES = 1024 * 1024


class BridgeServer:
    def __init__(self, on_add: Callable[[BrowserRequest], None], on_focus: Callable[[], None],
                 path: Path | None = None):
        self._on_add = on_add
        self._on_focus = on_focus
        self._path = Path(path) if path else bridge_path()
        # Novi token pri svakom pokretanju; zna ga samo ko može čitati korisnikov AppData.
        self.token = secrets.token_urlsafe(32)
        self._server: ThreadingHTTPServer | None = None

    @property
    def port(self) -> int:
        return self._server.server_address[1]

    def start(self) -> None:
        self._server = ThreadingHTTPServer(("127.0.0.1", 0), _make_handler(self))
        self._server.daemon_threads = True
        threading.Thread(target=self._server.serve_forever, daemon=True).start()
        self._path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self._path.with_suffix(".tmp")
        temporary.write_text(json.dumps({"port": self.port, "token": self.token, "pid": os.getpid()}),
                             encoding="utf-8")
        os.replace(temporary, self._path)

    def stop(self) -> None:
        if self._server is None:
            return
        self._server.shutdown()
        self._server.server_close()
        self._server = None
        try:
            # Briše se samo naš zapis; druga instanca ga je možda već zamijenila.
            if json.loads(self._path.read_text(encoding="utf-8")).get("token") == self.token:
                self._path.unlink()
        except (OSError, ValueError):
            pass


def _make_handler(bridge: BridgeServer):
    class Handler(BaseHTTPRequestHandler):
        server_version = "VideoDownload"

        def log_message(self, format, *args):
            pass  # pythonw nema konzolu

        def do_GET(self):
            if not self._authorized():
                return
            if self.path == "/ping":
                self._reply(200, {"app": "videodl", "version": __version__, "language": get_language()})
            else:
                self._reply(404, {"error": "Nepoznata putanja."})

        def do_POST(self):
            if not self._authorized():
                return
            if self.path == "/focus":
                bridge._on_focus()
                self._reply(200, {"ok": True})
                return
            if self.path != "/add":
                self._reply(404, {"error": "Nepoznata putanja."})
                return
            try:
                length = int(self.headers.get("Content-Length") or 0)
                if not 0 < length <= MAX_BODY_BYTES:
                    raise ValueError("Neispravna veličina zahtjeva.")
                request = parse_browser_request(json.loads(self.rfile.read(length).decode("utf-8")))
            except (ValueError, UnicodeDecodeError) as exc:
                self._reply(400, {"error": str(exc)})
                return
            bridge._on_add(request)
            self._reply(200, {"ok": True})

        def _authorized(self) -> bool:
            # Host štiti od DNS rebinding napada, token od svega ostalog na računaru i webu.
            expected_hosts = (f"127.0.0.1:{bridge.port}", f"localhost:{bridge.port}")
            token = self.headers.get(TOKEN_HEADER) or ""
            if self.headers.get("Host") in expected_hosts and hmac.compare_digest(
                    token.encode("utf-8"), bridge.token.encode("utf-8")):
                return True
            self._reply(403, {"error": "Zabranjeno."})
            return False

        def _reply(self, status: int, payload: dict) -> None:
            body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

    return Handler
