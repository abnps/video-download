"""yt-dlp „imitacija preglednika" na Androidu: zahtjeve koji je traže (npr. TikTok stranica) šalje Androidov mrežni
sloj (Kotlin `NativeHttp`), pa sajt vidi običan Android telefon umjesto Python programa. Na računaru isto radi
curl_cffi, kojeg na Androidu nema. Ostali zahtjevi idu kroz yt-dlp-ov urllib kao i ranije.

Uvoz ovog modula registruje handler (vd_core ga uvozi).
"""

import email.message
import io
import urllib.parse
import urllib.request

from yt_dlp.networking.common import Request, Response, register_preference, register_rh
from yt_dlp.networking.exceptions import HTTPError, TransportError, UnsupportedRequest
from yt_dlp.networking.impersonate import ImpersonateRequestHandler, ImpersonateTarget

MAX_REDIRECTS = 10
CHUNK = 256 * 1024


def _native():
    from java import jclass

    return jclass("io.github.abnps.videodownload.NativeHttp")


class _NativeReader(io.RawIOBase):
    def __init__(self, response):
        self._response = response
        self._buffer = b""
        self._done = False

    def readable(self):
        return True

    def read(self, size=-1):
        while not self._done and (size is None or size < 0 or len(self._buffer) < size):
            chunk = self._response.read(CHUNK)
            if chunk is None:
                self._done = True
                break
            self._buffer += bytes(chunk)
        if size is None or size < 0:
            size = len(self._buffer)
        data, self._buffer = self._buffer[:size], self._buffer[size:]
        return data

    def close(self):
        if not self.closed:
            self._response.close()
        super().close()


def _headers(flat) -> list[tuple[str, str]]:
    flat = list(flat)
    return [(str(flat[index]), str(flat[index + 1])) for index in range(0, len(flat) - 1, 2)]


@register_rh
class AndroidNativeRH(ImpersonateRequestHandler):
    RH_NAME = "android"
    _SUPPORTED_URL_SCHEMES = ("http", "https")
    _SUPPORTED_IMPERSONATE_TARGET_MAP = {ImpersonateTarget("chrome", None, "android", None): "android"}

    def _check_extensions(self, extensions):
        super()._check_extensions(extensions)
        extensions.pop("impersonate", None)
        extensions.pop("cookiejar", None)
        extensions.pop("timeout", None)
        extensions.pop("legacy_ssl", None)

    def _validate(self, request):
        # Samo zahtjevi koji traže imitaciju; sve ostalo (npr. preuzimanje videa) ide kroz urllib.
        if not request.extensions.get("impersonate") and not self.impersonate:
            raise UnsupportedRequest("android handler: samo za imitaciju preglednika")
        super()._validate(request)

    def send(self, request: Request) -> Response:
        target = self._get_request_target(request)
        try:
            response = super().send(request)
        except HTTPError as error:
            error.response.extensions["impersonate"] = target
            raise
        response.extensions["impersonate"] = target
        return response

    def _send(self, request: Request):
        cookiejar = self._get_cookiejar(request)
        headers = self._get_impersonate_headers(request)
        # Android sam traži i raspakuje gzip samo ako zaglavlje nije zadato ručno; identitet daje NativeHttp.
        for name in list(headers):
            if name.lower() in ("accept-encoding", "user-agent", "content-length", "host"):
                headers.pop(name)
        timeout_ms = int(self._calculate_timeout(request) * 1000)
        method, url, data = request.method, request.url, request.data
        for _ in range(MAX_REDIRECTS + 1):
            send_headers = dict(headers)
            if "cookie" not in {name.lower() for name in send_headers}:
                cookie = cookiejar.get_cookie_header(url)
                if cookie:
                    send_headers["Cookie"] = cookie
            flat = [part for pair in send_headers.items() for part in pair]
            try:
                native = _native().open(method, url, flat, data, timeout_ms)
            except Exception as error:  # IOException iz Jave: mreža, TLS, DNS
                raise TransportError(cause=error) from error
            pairs = _headers(native.headers)
            message = email.message.Message()
            for name, value in pairs:
                message[name] = value
            cookiejar.extract_cookies(_CookieResponse(message), urllib.request.Request(url))
            status = int(native.status)
            location = message.get("Location")
            if status in (301, 302, 303, 307, 308) and location:
                native.close()
                url = urllib.parse.urljoin(url, location)
                if status in (301, 302, 303) and method != "HEAD":
                    method, data = "GET", None
                continue
            response = Response(fp=_NativeReader(native), url=url, headers=message, status=status,
                                reason=str(native.reason) or None)
            if not 200 <= status < 300:
                raise HTTPError(response)
            return response
        raise HTTPError(response=Response(fp=io.BytesIO(), url=url, headers={}, status=310), redirect_loop=True)


class _CookieResponse:
    """Najmanje što http.cookiejar treba od odgovora: zaglavlja preko info()."""

    def __init__(self, message):
        self._message = message

    def info(self):
        return self._message


@register_preference(AndroidNativeRH)
def _android_preference(handler, request):
    # Kad više handlera može, imitacija ide ovdje, a običan zahtjev urllib-u.
    return 500 if request.extensions.get("impersonate") else -500
