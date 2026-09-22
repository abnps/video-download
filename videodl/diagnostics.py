"""Izvještaj o problemu: jedan tekstualni fajl koji se može poslati (bez Qt-a).

Sadrži verzije i okruženje, jer se time objasni većina prijava „ne radi". Linkovi se skraćuju
na ime sajta, a kolačići, tokeni i putanje korisnika se nikad ne upisuju.
"""

import getpass
import os
import platform
import re
import sys
import time
from pathlib import Path

from . import __version__, runtime, ytdlp_update

_URL = re.compile(r"\bhttps?://([^\s/]+)\S*", re.IGNORECASE)
_TOKEN = re.compile(r"(token|cookie|authorization|password|key)\s*[=:]\s*\S+", re.IGNORECASE)
MAX_ERRORS = 20


def redact(text: str) -> str:
    """Od linka ostaje samo ime sajta; ime korisnika i tajne se zamjenjuju."""
    clean = _URL.sub(lambda match: f"<{match.group(1)}>", text or "")
    clean = _TOKEN.sub(lambda match: f"{match.group(1)}=<sakriveno>", clean)
    user = getpass.getuser()
    if user:
        clean = re.sub(rf"\b{re.escape(user)}\b", "<korisnik>", clean)
    return clean


def build_report(errors=(), settings: dict | None = None, now: float | None = None) -> str:
    """Tekst izvještaja; `errors` su posljednje poruke grešaka onim redom kojim su se desile."""
    stamp = time.strftime("%d.%m.%Y %H:%M:%S", time.localtime(now if now is not None else time.time()))
    extension_version = _extension_version()
    lines = [
        "Video Download — izvještaj o problemu",
        f"Vrijeme: {stamp}",
        "",
        f"Aplikacija: {__version__} ({'instalirana' if runtime.is_frozen() else 'iz koda'})",
        f"yt-dlp: {ytdlp_update.active_version()}"
        + (f" (čeka {ytdlp_update.pending_version()})" if ytdlp_update.pending_version() else ""),
        f"Dodatak za browser: {extension_version or 'nije pronađen'}",
        f"Windows: {platform.platform()}",
        f"Python: {platform.python_version()} ({'64' if sys.maxsize > 2**32 else '32'}-bitni)",
        "",
        "Alati:",
    ]
    for tool in ("ffmpeg", "ffprobe", "node"):
        found = runtime.find_tool(tool)
        lines.append(f"  {tool}: {'u paketu' if found and str(runtime.tools_dir()) in found else found or 'nema ga'}")
    lines += ["", "Podešavanja:"]
    for key, value in (settings or {}).items():
        lines.append(f"  {key}: {redact(str(value))}")
    lines += ["", f"Posljednje greške ({min(len(errors), MAX_ERRORS)}):"]
    recent = list(errors)[-MAX_ERRORS:]
    lines += [f"  - {redact(str(error))}" for error in recent] or ["  (nema ih)"]
    lines += ["", "Napomena: linkovi su skraćeni na ime sajta; kolačići i lozinke se ne upisuju."]
    return "\n".join(lines) + "\n"


def default_report_path(folder: str | None = None) -> Path:
    """Radna površina ako postoji, inače folder za preuzimanja koji je aplikacija dobila."""
    desktop = Path.home() / "Desktop"
    base = desktop if desktop.is_dir() else Path(folder or os.getcwd())
    return base / f"VideoDownload-izvjestaj-{time.strftime('%Y%m%d-%H%M')}.txt"


def _extension_version() -> str | None:
    manifest = runtime.extension_dir() / "manifest.json"
    try:
        text = manifest.read_text(encoding="utf-8")
    except OSError:
        return None
    match = re.search(r'"version"\s*:\s*"([^"]+)"', text)
    return match.group(1) if match else None
