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
                log.write(f"{datetime.datetime.now():%H:%M:%S} {format % args} "
                          f"referer={self.headers.get('Referer', '-')}\n")

        def do_GET(self):
            if self.path in ("/", "/index.html"):
                return self._html(PAGE)
            if self.path == "/drm.html":
                return self._html(DRM)
            if self.path.startswith("/hls/") and not (self.headers.get("Referer") or "").startswith(ORIGIN):
                self.send_error(403, "Referer required")
                return
            return super().do_GET()

        def _html(self, text):
            body = text.encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

    server = ThreadingHTTPServer(("127.0.0.1", PORT), Handler)
    print("ready", flush=True)
    server.serve_forever()


if __name__ == "__main__":
    serve(Path(sys.argv[1]))
