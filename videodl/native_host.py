"""Native messaging host: veza između browser ekstenzije i aplikacije.

Chrome/Edge pokreću ovaj skript za svaku poruku ekstenzije (i dozvoljavaju to samo
našoj ekstenziji). Skript poruku prosljeđuje aplikaciji preko 127.0.0.1 uz tajni
token iz bridge.json. Ako aplikacija nije pokrenuta, pokreće je i čeka da se javi.

Samo standardna biblioteka: kopira se van projekta i radi bez paketa projekta.
"""

import http.client
import json
import os
import struct
import subprocess
import sys
import time
from pathlib import Path

HOST_NAME = "com.videodl.bridge"
TOKEN_HEADER = "X-VideoDL-Token"
MAX_MESSAGE_BYTES = 16 * 1024 * 1024
LAUNCH_TIMEOUT = 30.0


def data_dir() -> Path:
    override = os.environ.get("VIDEODL_DATA_DIR")
    if override:
        return Path(override)
    base = os.environ.get("LOCALAPPDATA") or str(Path.home() / "AppData" / "Local")
    return Path(base) / "VideoDownload"


def bridge_path() -> Path:
    return data_dir() / "bridge.json"


# ---------- protokol browsera: 4 bajta dužine + JSON ----------

def read_message(stream) -> dict | None:
    header = stream.read(4)
    if len(header) < 4:
        return None
    (length,) = struct.unpack("<I", header)
    if length > MAX_MESSAGE_BYTES:
        raise ValueError("Poruka iz browsera je prevelika.")
    body = stream.read(length)
    if len(body) < length:
        return None
    return json.loads(body.decode("utf-8"))


def write_message(stream, message: dict) -> None:
    body = json.dumps(message, ensure_ascii=False).encode("utf-8")
    stream.write(struct.pack("<I", len(body)))
    stream.write(body)
    stream.flush()


# ---------- veza sa aplikacijom ----------

def read_bridge(path: Path | None = None) -> dict | None:
    try:
        data = json.loads(Path(path or bridge_path()).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    if isinstance(data, dict) and isinstance(data.get("port"), int) and isinstance(data.get("token"), str):
        return data
    return None


def call_app(bridge: dict, method: str, path: str, payload: dict | None = None,
             timeout: float = 5.0) -> tuple[int, dict]:
    connection = http.client.HTTPConnection("127.0.0.1", bridge["port"], timeout=timeout)
    try:
        headers = {TOKEN_HEADER: bridge["token"]}
        body = None
        if payload is not None:
            body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
            headers["Content-Type"] = "application/json"
        connection.request(method, path, body=body, headers=headers)
        response = connection.getresponse()
        raw = response.read()
        try:
            data = json.loads(raw.decode("utf-8")) if raw else {}
        except ValueError:
            data = {}
        return response.status, data if isinstance(data, dict) else {}
    finally:
        connection.close()


def find_running_app(path: Path | None = None) -> dict | None:
    bridge = read_bridge(path)
    if bridge is None:
        return None
    try:
        status, data = call_app(bridge, "GET", "/ping", timeout=2.0)
    except OSError:
        return None
    return bridge if status == 200 and data.get("app") == "videodl" else None


def saved_language() -> str | None:
    """Jezik iz podešavanja aplikacije kad ona nije pokrenuta (za popup dodatka)."""
    if os.environ.get("VIDEODL_DATA_DIR"):
        try:
            for line in (data_dir() / "settings.ini").read_text(encoding="utf-8").splitlines():
                if line.startswith("language="):
                    return line.split("=", 1)[1].strip() or None
        except OSError:
            return None
        return None
    if sys.platform != "win32":
        return None
    import winreg

    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\VideoDownload\VideoDownload") as key:
            value, _ = winreg.QueryValueEx(key, "language")
            return str(value) or None
    except OSError:
        return None


def launch_app(command: list[str]) -> None:
    options = {"stdin": subprocess.DEVNULL, "stdout": subprocess.DEVNULL,
               "stderr": subprocess.DEVNULL, "close_fds": True}
    if sys.platform != "win32":
        subprocess.Popen(command, start_new_session=True, **options)
        return
    flags = subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP
    try:
        # Browser drži host u job objektu; bez izlaska iz njega aplikacija bi se
        # mogla ugasiti zajedno sa hostom.
        subprocess.Popen(command, creationflags=flags | subprocess.CREATE_BREAKAWAY_FROM_JOB, **options)
    except OSError:
        subprocess.Popen(command, creationflags=flags, **options)


def handle(message: dict, config: dict, *, bridge_file: Path | None = None, launch=launch_app,
           sleep=time.sleep, clock=time.monotonic, launch_timeout: float = LAUNCH_TIMEOUT) -> dict:
    action = message.get("action") if isinstance(message, dict) else None
    bridge = find_running_app(bridge_file)
    if action == "status":
        language = None
        if bridge is not None:
            try:
                language = call_app(bridge, "GET", "/ping", timeout=2.0)[1].get("language")
            except OSError:
                pass
        return {"ok": True, "running": bridge is not None, "language": language or saved_language()}
    if action != "add":
        return {"ok": False, "code": "connection", "detail": f"unknown action: {action}"}

    launched = False
    if bridge is None:
        launch(config["launch"])
        launched = True
        deadline = clock() + launch_timeout
        while bridge is None and clock() < deadline:
            sleep(0.25)
            bridge = find_running_app(bridge_file)
        if bridge is None:
            return {"ok": False, "launched": True, "code": "app-timeout"}

    try:
        status, data = call_app(bridge, "POST", "/add", message.get("request"))
    except OSError as exc:
        return {"ok": False, "launched": launched, "code": "connection", "detail": str(exc)}
    if status != 200:
        return {"ok": False, "launched": launched, "code": "connection", "detail": data.get("error") or f"HTTP {status}"}
    return {"ok": True, "launched": launched}


def load_config(folder: Path) -> dict:
    return json.loads((folder / "host-config.json").read_text(encoding="utf-8"))


def main() -> int:
    try:
        message = read_message(sys.stdin.buffer)
        if message is None:
            return 0
        reply = handle(message, load_config(Path(__file__).resolve().parent))
    except Exception as exc:  # ekstenzija mora dobiti odgovor i kad nešto pukne
        reply = {"ok": False, "code": "connection", "detail": f"host: {exc}"}
    write_message(sys.stdout.buffer, reply)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
