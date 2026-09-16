"""Lokalni test sajt za browser E2E: MP4 u <video>, HLS koji traži Referer, ClearKey DRM stranica.

Mediji se prave ffmpeg-om (sintetički test signal), bez preuzimanja sa interneta.
Pokreće ga run.mjs; ručno: python server.py <radni_folder>
"""

import datetime
import subprocess
import sys
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

PORT = 8765
ORIGIN = f"http://127.0.0.1:{PORT}/"

PAGE = """<!doctype html><html><head><meta charset="utf-8"><title>E2E Lekcija 1</title></head><body>
<h1>E2E test</h1>
<video src="/media/clip.mp4" controls muted autoplay width="320"></video>
<script>fetch('/hls/index.m3u8').then(r => r.text());</script>
</body></html>"""

# Feed nalik X-u: dvije objave, pušta se samo druga; link objave nosi <time>.
FEED = """<!doctype html><html><head><meta charset="utf-8"><title>Početna / Feed</title></head><body>
<article><a href="/korisnik/status/111/photo/1">foto</a><a href="/korisnik/status/111"><time>1h</time></a>
<video id="v1" src="/media/clip.mp4" muted width="480" height="270"></video></article>
<article><a href="/korisnik"><span>@korisnik</span></a><a href="/korisnik/status/222/analytics">stat</a>
<a href="/korisnik/status/222"><time>2h</time></a>
<video id="v2" src="/media/clip.mp4" muted loop width="480" height="270"></video></article>
<script>document.getElementById('v2').play();</script>
</body></html>"""

POST = """<!doctype html><html><head><meta charset="utf-8"><title>Objava 222</title></head><body>
<video src="/media/clip.mp4" controls width="320"></video></body></html>"""

# Feed nalik Instagramu: prvi link u objavi je muzika (/reels/audio/), tek drugi je sam reel.
IG_FEED = """<!doctype html><html><head><meta charset="utf-8"><title>Instagram feed</title></head><body>
<article><a href="/reels/audio/1277456000520564/">Original audio</a>
<a href="/reel/hashtag/?q=%23reelsvideo">#reelsvideo</a><a href="/reel/C1a2B3c4D5e/">reel</a>
<video id="r" src="/media/clip.mp4" muted loop width="360" height="640"></video></article>
<script>document.getElementById('r').play();</script></body></html>"""

IG_REEL = """<!doctype html><html><head><meta charset="utf-8"><title>Reel C1a2</title></head><body>
<video src="/media/clip.mp4" controls width="320"></video></body></html>"""

# Sadržaj iza prijave: stranica postavi kolačić sesije; objava i njen video bez njega vraćaju 403.
SESSION_COOKIE = "sesija=tajna-e2e"
PRIVATE_FEED = """<!doctype html><html><head><meta charset="utf-8"><title>Privatni feed</title></head><body>
<article><a href="/privatno/status/333"><time>3h</time></a>
<video id="p" src="/media/clip.mp4" muted loop width="480" height="270"></video></article>
<script>document.getElementById('p').play();</script></body></html>"""

PRIVATE_POST = """<!doctype html><html><head><meta charset="utf-8"><title>Privatna 333</title></head><body>
<video src="/privatno/clip.mp4" controls width="320"></video></body></html>"""

DRM = """<!doctype html><html><head><meta charset="utf-8"><title>E2E DRM</title></head><body><script>
(async () => {
  const config = [{initDataTypes: ['keyids'], videoCapabilities: [{contentType: 'video/mp4; codecs="avc1.42E01E"'}]}];
  const access = await navigator.requestMediaKeySystemAccess('org.w3.clearkey', config);
  const session = (await access.createMediaKeys()).createSession();
  await session.generateRequest('keyids', new TextEncoder().encode(JSON.stringify({kids: ['AAAAAAAAAAAAAAAAAAAAAA']})));
})();
</script></body></html>"""


def make_media(site: Path) -> None:
    (site / "media").mkdir(parents=True, exist_ok=True)
    (site / "hls").mkdir(parents=True, exist_ok=True)
    quiet = ["ffmpeg", "-hide_banner", "-loglevel", "error", "-y"]
    if not (site / "media" / "clip.mp4").exists():
        # Šum drži fajl iznad praga ekstenzije za premale video fajlove.
        subprocess.run([*quiet, "-f", "lavfi", "-i", "testsrc=size=640x360:rate=25,noise=alls=30:allf=t",
                        "-f", "lavfi", "-i", "sine=frequency=440", "-t", "8", "-c:v", "libx264", "-b:v", "2M",
                        "-pix_fmt", "yuv420p", "-c:a", "aac", "-movflags", "+faststart",
                        str(site / "media" / "clip.mp4")], check=True)
    if not (site / "hls" / "index.m3u8").exists():
        subprocess.run([*quiet, "-f", "lavfi", "-i", "testsrc2=size=640x360:rate=25", "-f", "lavfi",
                        "-i", "sine=frequency=660", "-t", "8", "-c:v", "libx264", "-g", "50", "-b:v", "1M",
                        "-pix_fmt", "yuv420p", "-c:a", "aac", "-f", "hls", "-hls_time", "2",
                        "-hls_playlist_type", "vod", "-hls_segment_filename", str(site / "hls" / "seg%02d.ts"),
                        str(site / "hls" / "index.m3u8")], check=True)


def serve(work: Path) -> None:
    site = work / "site"
    log_path = work / "server.log"
    make_media(site)
    log_path.unlink(missing_ok=True)

    class Handler(SimpleHTTPRequestHandler):
        extensions_map = {**SimpleHTTPRequestHandler.extensions_map,
                          ".m3u8": "application/vnd.apple.mpegurl", ".ts": "video/mp2t", ".mp4": "video/mp4"}

        def __init__(self, *args, **kwargs):
            super().__init__(*args, directory=str(site), **kwargs)

        def log_message(self, format, *args):
            with log_path.open("a", encoding="utf-8") as log:
                # Bilježi se samo da li je kolačić sesije stigao, ne njegova vrijednost.
                has_session = SESSION_COOKIE in (self.headers.get("Cookie") or "")
                log.write(f"{datetime.datetime.now():%H:%M:%S} {format % args} "
                          f"referer={self.headers.get('Referer', '-')} sesija={has_session}\n")

        def do_GET(self):
            if self.path in ("/", "/index.html"):
                return self._html(PAGE)
            if self.path == "/drm.html":
                return self._html(DRM)
            if self.path == "/feed.html":
                return self._html(FEED)
            if self.path == "/korisnik/status/222":
                return self._html(POST)
            if self.path == "/ig-feed.html":
                return self._html(IG_FEED)
            if self.path == "/reel/C1a2B3c4D5e/":
                return self._html(IG_REEL)
            if self.path == "/privatno.html":
                return self._html(PRIVATE_FEED, set_cookie=f"{SESSION_COOKIE}; Path=/; HttpOnly")
            if self.path.startswith("/privatno/"):
                if SESSION_COOKIE not in (self.headers.get("Cookie") or ""):
                    self.send_error(403, "Login required")
                    return
                if self.path == "/privatno/status/333":
                    return self._html(PRIVATE_POST)
                if self.path == "/privatno/clip.mp4":
                    self.path = "/media/clip.mp4"
            if self.path.startswith("/hls/") and not (self.headers.get("Referer") or "").startswith(ORIGIN):
                self.send_error(403, "Referer required")
                return
            return super().do_GET()

        def _html(self, text, set_cookie=None):
            body = text.encode("utf-8")
            self.send_response(200)
            if set_cookie:
                self.send_header("Set-Cookie", set_cookie)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

    server = ThreadingHTTPServer(("127.0.0.1", PORT), Handler)
    print("ready", flush=True)
    server.serve_forever()


if __name__ == "__main__":
    serve(Path(sys.argv[1]))
