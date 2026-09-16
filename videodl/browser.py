"""Zahtjev iz browser ekstenzije: šta preuzeti i s kojim HTTP zaglavljima."""

from dataclasses import dataclass, field
from urllib.parse import urlsplit

MEDIA_KINDS = ("hls", "dash", "file")
MAX_URL_LENGTH = 8000
MAX_HEADER_LENGTH = 2000

# Samo zaglavlja koja serveri tokova stvarno provjeravaju; ostala se ne prosljeđuju.
_ALLOWED_HEADERS = {"referer": "Referer", "user-agent": "User-Agent", "origin": "Origin"}


@dataclass(frozen=True)
class BrowserRequest:
    page_url: str
    page_title: str
    media_url: str | None = None  # None: preuzima se video sa stranice preko yt-dlp-a
    media_kind: str | None = None
    headers: dict[str, str] = field(default_factory=dict)


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
