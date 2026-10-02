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
from urllib.parse import quote, urlencode, urlsplit

from . import __version__, runtime, ytdlp_update

_URL = re.compile(r"\b[a-z][a-z0-9+.-]*://[^\s<>\"']+", re.IGNORECASE)
# Zaglavlja čija je cijela vrijednost tajna (npr. „Cookie: a=1; b=2", „Authorization: Basic …"): do kraja reda.
_HEADER = re.compile(r"\b(proxy-authorization|authorization|set-cookie|cookie)\b\s*[=:]\s*[^\r\n]*", re.IGNORECASE)
# Ime=vrijednost / ime: vrijednost / "ime": "vrijednost" za tajne (i u JSON-u i u argumentima).
_SECRET_NAMES = r"(?:access[_-]?token|refresh[_-]?token|id[_-]?token|token|api[_-]?key|apikey|client[_-]?secret|secret|" \
                r"password|passwd|pwd|pass|session(?:id)?|sid|auth|key)"
_JSON_SECRET = re.compile(rf"(\"{_SECRET_NAMES}\")\s*:\s*\"[^\"]*\"", re.IGNORECASE)
_SECRET = re.compile(rf"\b({_SECRET_NAMES})\b\s*[=:]\s*(?:\"[^\"]*\"|'[^']*'|[^\s&;,]+)", re.IGNORECASE)
_SCHEME_TOKEN = re.compile(r"\b(Bearer|Basic|Token)\s+[A-Za-z0-9._~+/=-]{4,}", re.IGNORECASE)
MAX_ERRORS = 20
# Javni kontakt projekta (Ahmedova odluka 26.9.2026; isti kao na sajtu, test provjerava). Lični e-mail nikad.
CONTACT_EMAIL = "abnpsdev@gmail.com"


def feedback_info() -> str:
    """Kratko i bez ličnih podataka (bez putanja, korisničkog imena i linkova): ide u tijelo e-pošte."""
    return (f"Video Download {__version__} · yt-dlp {ytdlp_update.active_version()} · "
            f"{platform.system()} {platform.release()} ({platform.machine()})")


def feedback_url(subject: str, body: str) -> str:
    """mailto: link za „Prijavi problem ili prijedlog" (program za e-poštu, bez naloga na GitHubu)."""
    return f"mailto:{CONTACT_EMAIL}?" + urlencode({"subject": subject, "body": body}, quote_via=quote)


def _site(match: re.Match) -> str:
    """Od linka ostaje samo ime sajta — bez korisnika, lozinke, putanje i parametara."""
    try:
        host = urlsplit(match.group(0)).hostname
    except ValueError:
        host = None
    return f"<{host}>" if host else "<link>"


def redact(text: str) -> str:
    """Od linka ostaje samo ime sajta; ime korisnika i tajne (tokeni, kolačići, lozinke) se zamjenjuju u cjelini."""
    clean = _URL.sub(_site, text or "")
    clean = _HEADER.sub(lambda match: f"{match.group(1)}: <sakriveno>", clean)
    clean = _JSON_SECRET.sub(lambda match: f'{match.group(1)}: "<sakriveno>"', clean)
    clean = _SECRET.sub(lambda match: f"{match.group(1)}=<sakriveno>", clean)
    clean = _SCHEME_TOKEN.sub(lambda match: f"{match.group(1)} <sakriveno>", clean)
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
