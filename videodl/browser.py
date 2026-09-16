"""Zahtjev iz browser ekstenzije: šta preuzeti, s kojim HTTP zaglavljima i kolačićima prijave."""

import contextlib
import os
import tempfile
from collections.abc import Iterator
from dataclasses import dataclass, field
from urllib.parse import urlsplit

MEDIA_KINDS = ("hls", "dash", "file")
MAX_URL_LENGTH = 8000
MAX_HEADER_LENGTH = 2000
MAX_COOKIES = 300
MAX_COOKIE_VALUE = 8000

# Samo zaglavlja koja serveri tokova stvarno provjeravaju; ostala se ne prosljeđuju.
_ALLOWED_HEADERS = {"referer": "Referer", "user-agent": "User-Agent", "origin": "Origin"}


@dataclass(frozen=True)
class Cookie:
    domain: str  # host-only bez tačke na početku, za poddomene sa tačkom
    name: str
    value: str
    path: str = "/"
    secure: bool = False
    expires: int = 0  # 0 = sesijski kolačić
    host_only: bool = True

    def __repr__(self) -> str:
        # Vrijednost kolačića je tajna prijave i ne smije završiti u logu ili poruci greške.
        return f"Cookie(domain={self.domain!r}, name={self.name!r}, value=***)"


@dataclass(frozen=True)
class BrowserRequest:
    page_url: str
    page_title: str
    media_url: str | None = None  # None: preuzima se video sa stranice preko yt-dlp-a
    media_kind: str | None = None
    headers: dict[str, str] = field(default_factory=dict)
    cookies: tuple[Cookie, ...] = ()


def parse_browser_request(payload) -> BrowserRequest:
    if not isinstance(payload, dict):
        raise ValueError("Zahtjev mora biti JSON objekat.")
    page_url = _http_url(payload.get("page_url"), "stranice")
    title = payload.get("page_title")
    title = title.strip()[:300] if isinstance(title, str) else ""

    media_url = media_kind = None
    media = payload.get("media")
    if media is not None:
        if not isinstance(media, dict):
            raise ValueError("Neispravan opis video toka.")
        media_url = _http_url(media.get("url"), "video toka")
        media_kind = media.get("kind") if media.get("kind") in MEDIA_KINDS else "file"

    return BrowserRequest(
        page_url=page_url,
        page_title=title or urlsplit(page_url).hostname or page_url,
        media_url=media_url,
        media_kind=media_kind,
        headers=_headers(payload.get("headers")),
        cookies=_cookies(payload.get("cookies"), [page_url, media_url]),
    )


def _http_url(value, what: str) -> str:
    if isinstance(value, str) and len(value) <= MAX_URL_LENGTH:
        parts = urlsplit(value)
        if parts.scheme in ("http", "https") and parts.hostname:
            return value
    raise ValueError(f"Neispravan link {what}.")


def _headers(raw) -> dict[str, str]:
    if not isinstance(raw, dict):
        return {}
    headers = {}
    for key, value in raw.items():
        name = _ALLOWED_HEADERS.get(str(key).lower())
        if (name and isinstance(value, str) and value and len(value) <= MAX_HEADER_LENGTH
                and "\r" not in value and "\n" not in value):
            headers[name] = value
    return headers


def _cookies(raw, urls: list[str | None]) -> tuple[Cookie, ...]:
    if not isinstance(raw, list):
        return ()
    hosts = {urlsplit(url).hostname for url in urls if url}
    cookies = []
    for entry in raw[:MAX_COOKIES]:
        cookie = _cookie(entry)
        # Prihvataju se samo kolačići sajta sa kog se preuzima (stranica ili tok).
        if cookie is not None and any(_domain_matches(host, cookie) for host in hosts):
            cookies.append(cookie)
    return tuple(cookies)


def _cookie(entry) -> Cookie | None:
    if not isinstance(entry, dict):
        return None
    name, value, domain = entry.get("name"), entry.get("value"), entry.get("domain")
    path = entry.get("path") if isinstance(entry.get("path"), str) and entry.get("path").startswith("/") else "/"
    if not (isinstance(name, str) and isinstance(value, str) and isinstance(domain, str)) or not name or not domain:
        return None
    if len(value) > MAX_COOKIE_VALUE or any(ch in text for text in (name, value, domain, path) for ch in "\t\r\n"):
        return None
    host_only = bool(entry.get("hostOnly", not domain.startswith(".")))
    bare = domain.lstrip(".").lower()
    expires = entry.get("expirationDate")
    return Cookie(
        domain=bare if host_only else f".{bare}",
        name=name,
        value=value,
        path=path,
        secure=bool(entry.get("secure")),
        expires=int(expires) if isinstance(expires, (int, float)) and expires > 0 else 0,
        host_only=host_only,
    )


def _domain_matches(host: str | None, cookie: Cookie) -> bool:
    if not host:
        return False
    host = host.lower()
    bare = cookie.domain.lstrip(".")
    return host == bare or (not cookie.host_only and host.endswith(f".{bare}"))


@contextlib.contextmanager
def cookie_file(cookies: tuple[Cookie, ...] | list[Cookie] | None) -> Iterator[str | None]:
    """Privremeni Netscape cookies fajl za yt-dlp; briše se čim se blok završi."""
    if not cookies:
        yield None
        return
    handle, path = tempfile.mkstemp(prefix="videodl-cookies-", suffix=".txt")
    try:
        with os.fdopen(handle, "w", encoding="utf-8", newline="\n") as file:
            file.write("# Netscape HTTP Cookie File\n")
            for cookie in cookies:
                file.write("\t".join((
                    cookie.domain,
                    "FALSE" if cookie.host_only else "TRUE",
                    cookie.path,
                    "TRUE" if cookie.secure else "FALSE",
                    str(cookie.expires),
                    cookie.name,
                    cookie.value,
                )) + "\n")
        yield path
    finally:
        with contextlib.suppress(OSError):
            os.remove(path)
