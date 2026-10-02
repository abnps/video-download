"""Ograničena dijagnostika: čuva samo poznatu vrstu događaja, domen i HTTP status.

Poruke sajtova nisu pouzdan tekst. Tijela stranica, zaglavlja, putanje i proizvoljne
vrijednosti nikad se ne prepisuju u dnevnik, čak ni kada nisu prepoznate kao tajna.
Isti postupak važi za stare dnevnike pri ažuriranju i svakom kopiranju izvještaja.
"""

import html
import json
import os
import re
from http import HTTPStatus
from urllib.parse import unquote, urlsplit

LIMIT = 400_000
HEADER = "Video Download safe diagnostics v2\n"
_URL = re.compile(r"\bhttps?://[^\s<>\"']+", re.IGNORECASE)
_LABEL = re.compile(r"[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?", re.IGNORECASE)
_KNOWN_HOSTS = frozenset({"youtube.com", "youtu.be", "instagram.com", "tiktok.com", "facebook.com",
                          "fb.watch", "x.com", "twitter.com", "vimeo.com", "dailymotion.com"})
_ENTRY = re.compile(r"^\[(info|debug|warning|error)\]\s*(.*)$", re.DOTALL)
_EVENTS = {
    "probe": "Čitanje linka",
    "download": "Preuzimanje",
    "http": "HTTP greška",
    "unsupported": "Nepodržan link",
    "format": "Traženi format nije dostupan",
    "login": "Sajt traži prijavu ili potvrdu",
    "network": "Veza nije uspjela",
    "cancelled": "Prekinuto na zahtjev korisnika",
    "error": "Greška; privatni detalji su izostavljeni",
    "warning": "Upozorenje; privatni detalji su izostavljeni",
}


def _host(value):
    if not isinstance(value, str):
        return None
    labels = value.lower().rstrip(".").split(".")
    if len(labels) < 2 or not all(_LABEL.fullmatch(label) for label in labels):
        return None
    # Poddomena može sadržati korisničko ime ili jednokratni token.
    if not re.fullmatch(r"[a-z]{2,24}", labels[-1]):
        return None
    host = ".".join(labels[-2:])
    return host if host in _KNOWN_HOSTS else None


def _validate(record):
    """Ni postojeći JSON dnevnik ne smije prošvercovati slobodan tekst u izvještaj."""
    if not isinstance(record, dict) or not isinstance(record.get("event"), str) or record["event"] not in _EVENTS:
        return None
    clean = {"v": 2, "event": record["event"]}
    host = _host(record.get("host"))
    if host:
        clean["host"] = host
    status = record.get("status")
    if type(status) is int and 400 <= status <= 599:
        clean["status"] = status
    if clean["event"] in ("probe", "download") and type(record.get("login")) is bool:
        clean["login"] = record["login"]
    return clean


def record(message, level="info"):
    """Iz nepouzdane poruke izdvaja samo zatvoren skup bezbjednih podataka."""
    text = html.unescape(str(message)[:LIMIT]).replace("\\/", "/")
    for _ in range(2):
        text = unquote(text)
    lower = text.lower()
    if "dumping request" in lower or re.search(r"<(?:!doctype|html|head|body|script)\b", lower):
        return None
    status = re.search(r"\bHTTP(?: Error)?[ :]+([45]\d\d)\b", text, re.IGNORECASE)
    if status:
        event = "http"
    elif "cancelled" in lower or "canceled" in lower:
        event = "cancelled"
    elif "audio_unavailable" in lower or "requested format" in lower:
        event = "format"
    elif "unsupported url" in lower:
        event = "unsupported"
    elif any(word in lower for word in ("sign in", "login required", "log in", "confirm you're", "cookies")):
        event = "login"
    elif any(word in lower for word in ("timed out", "timeout", "connection", "network", "name resolution")):
        event = "network"
    elif lower.startswith("čitanje linka:") or "extracting url:" in lower:
        event = "probe"
    elif lower.startswith("link:") or lower.startswith("[download]"):
        event = "download"
    elif level in ("error", "warning"):
        event = level
    else:
        return None
    result = {"v": 2, "event": event}
    if status:
        result["status"] = int(status[1])
    # Samo da/ne: da li je posao dobio kolačiće prijave (nikad sami kolačići ni nalog).
    if event in ("probe", "download"):
        login = re.search(r"\| prijava: (da|ne)\b", text)
        if login:
            result["login"] = login[1] == "da"
    match = _URL.search(text)
    if match:
        try:
            host = _host(urlsplit(match[0]).hostname)
        except ValueError:
            host = None
        if host:
            result["host"] = host
    return result


def records(path):
    """Ograničeno čitanje i kada stari zapis stranice prelazi prvobitni limit."""
    try:
        with open(path, encoding="utf-8", errors="replace") as source:
            text = source.read(LIMIT)
    except FileNotFoundError:
        return []
    result = []
    if text.startswith(HEADER):
        for line in text[len(HEADER):].splitlines():
            try:
                safe = _validate(json.loads(line))
            except (ValueError, TypeError):
                safe = None
            if safe:
                result.append(safe)
        return result
    pending = None

    def flush():
        if pending is not None:
            safe = record(pending[1], pending[0])
            if safe:
                result.append(safe)

    for line in text.splitlines():
        match = _ENTRY.match(line)
        if match:
            flush()
            pending = [match[1], match[2]]
        elif pending is not None:
            pending[1] += "\n" + line
    flush()
    return result


def clean_file(path):
    """Stari zapis zamjenjuje samo provjerenim stavkama; podaci nikad ne idu na mrežu."""
    if not os.path.isfile(path):
        return
    data = HEADER + "".join(json.dumps(item, ensure_ascii=False) + "\n" for item in records(path))
    temporary = path + ".safe-tmp"
    with open(temporary, "w", encoding="utf-8") as target:
        target.write(data)
    os.replace(temporary, path)


def render(items):
    lines = []
    for item in items:
        safe = _validate(item)
        if safe is None:
            continue
        text = _EVENTS[safe["event"]]
        if "status" in safe:
            code = safe["status"]
            try:
                reason = HTTPStatus(code).phrase
            except ValueError:
                reason = ""
            text = f"HTTP Error {code}" + (f": {reason}" if reason else "")
        if "host" in safe:
            text += f" | <{safe['host']}>"
        if "login" in safe:
            text += " | prijava: " + ("da" if safe["login"] else "ne")
        lines.append(text)
    return lines


class SafeLog:
    def __init__(self, path):
        self.file = open(path, "w", encoding="utf-8")
        self.file.write(HEADER)
        self.size = len(HEADER.encode("utf-8"))

    def _write(self, level, message):
        safe = record(message, level)
        if safe is None:
            return
        line = json.dumps(safe, ensure_ascii=False) + "\n"
        size = len(line.encode("utf-8"))
        if self.size + size <= LIMIT:
            self.file.write(line)
            self.file.flush()
            self.size += size

    def info(self, message):
        self._write("info", message)

    def debug(self, message):
        self._write("debug", message)

    def warning(self, message):
        self._write("warning", message)

    def error(self, message):
        self._write("error", message)

    def close(self):
        self.file.close()
