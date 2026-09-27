"""Preuzimanje na telefonu: yt-dlp piše u privremeni folder aplikacije, a Kotlin gotov fajl premješta u
Galeriju (Movies/Video Download) ili Muziku (Music/Video Download). Nikad ne piše direktno u korisnikove foldere.

Bez ffmpeg-a (licenca, odluka B): YouTube i mnogi sajtovi daju sliku i zvuk ODVOJENO, pa se biraju H.264 slika
(MP4) i AAC zvuk (M4A), preuzmu se posebno, a spaja ih Androidov MediaMuxer (Kotlin, `Muxer.kt`) bez ponovnog
kodiranja. Kad sajt nudi jedan fajl sa slikom i zvukom, uzima se on. Zvuk je M4A kakav sajt nudi (MP3 kasnije).
"""

import os

from yt_dlp import YoutubeDL
from yt_dlp.utils import DownloadCancelled, sanitize_filename

try:  # samo na Androidu (Chaquopy ima modul `java`): imitacija preglednika kroz Androidov mrežni sloj
    import java  # noqa: F401

    import vd_net  # noqa: F401  (registruje handler)
except ImportError:
    pass


class _FileLog:
    """Detaljan zapis yt-dlp-a za posljednje preuzimanje (cache/zadnji-log.txt, samo u memoriji aplikacije):
    kad sajt ne radi na telefonu, vidi se šta je tačno vratio (i stranica, kroz dump_intermediate_pages)."""

    LIMIT = 400_000

    def __init__(self, path: str):
        self.path = path
        self.size = 0
        self.file = open(path, "w", encoding="utf-8", errors="replace")

    def _write(self, level: str, message: str) -> None:
        if self.size < self.LIMIT:
            line = f"[{level}] {message}\n"
            self.size += len(line)
            self.file.write(line)
            self.file.flush()

    def debug(self, message):
        self._write("debug", message)

    def info(self, message):
        self._write("info", message)

    def warning(self, message):
        self._write("warning", message)

    def error(self, message):
        self._write("error", message)

    def close(self):
        self.file.close()


class Cancelled(DownloadCancelled):
    """Korisnik je kliknuo Zaustavi. yt-dlp svoj DownloadCancelled uvijek pušta dalje (obična greška bi se
    mogla „progutati" u ponovnim pokušajima), pa preuzimanje stvarno staje."""


def _has_video(fmt: dict) -> bool:
    return fmt.get("vcodec") not in (None, "none")


def _has_audio(fmt: dict) -> bool:
    return fmt.get("acodec") not in (None, "none")


def _size(fmt: dict) -> float:
    return float(fmt.get("filesize") or fmt.get("filesize_approx") or 0)


def _video_candidates(formats: list) -> list:
    """Formati slike koje telefon spaja bez ponovnog kodiranja: H.264 MP4 bez zvuka (za spajanje sa M4A)."""
    return [f for f in formats if _has_video(f) and not _has_audio(f) and f.get("ext") == "mp4"
            and str(f.get("vcodec") or "").startswith("avc1")]


def _best_audio(formats: list):
    audio = sorted((f for f in formats if _has_audio(f) and not _has_video(f) and f.get("ext") == "m4a"),
                   key=lambda f: (f.get("abr") or 0, _size(f)))
    return audio[-1] if audio else None


def plan(info: dict, kind: str, height: int = 0) -> list[str]:
    """Koje formate preuzeti: jedan ID, dva ID-a (slika pa zvuk, za spajanje) ili opšti izbor yt-dlp-a.
    `height` > 0 ograničava visinu slike (izbor 1080p/720p/480p); 0 = najbolja dostupna."""
    formats = info.get("formats") or []
    audio = _best_audio(formats)
    if kind == "audio":
        return [audio["format_id"]] if audio else ["ba/b"]
    fits = (lambda f: (f.get("height") or 0) <= height) if height else (lambda f: True)
    key = lambda f: (f.get("height") or 0, f.get("fps") or 0, _size(f))  # noqa: E731
    video_h264 = sorted((f for f in _video_candidates(formats) if fits(f)), key=key)
    combined = sorted((f for f in formats if _has_video(f) and _has_audio(f) and f.get("ext") == "mp4" and fits(f)),
                      key=lambda f: (f.get("height") or 0, _size(f)))
    best_combined = combined[-1] if combined else None
    if video_h264 and audio and (best_combined is None
                                 or (video_h264[-1].get("height") or 0) > (best_combined.get("height") or 0)):
        return [video_h264[-1]["format_id"], audio["format_id"]]
    if best_combined:
        return [best_combined["format_id"]]
    limit = f"[height<={height}]" if height else ""
    return [f"b[ext=mp4]{limit}/b{limit}/b"]  # sajt bez opisa formata (npr. direktan fajl)


def options(info: dict) -> dict:
    """Izbor za ekran „Izaberi kvalitet": visine slike (najviše 4, npr. 1080/720/480/360) s procjenom veličine
    (slika + zvuk) i veličina samog zvuka. Veličina 0 = sajt je ne javlja."""
    formats = info.get("formats") or []
    audio = _best_audio(formats)
    audio_size = _size(audio) if audio else 0.0
    by_height, labels = {}, {}
    for fmt in _video_candidates(formats):
        height = fmt.get("height") or 0
        if height and _size(fmt) + audio_size >= by_height.get(height, 0):
            by_height[height] = _size(fmt) + audio_size
            labels[height] = _label(fmt)
    for fmt in formats:  # sajtovi s jednim fajlom (slika i zvuk zajedno)
        if _has_video(fmt) and _has_audio(fmt) and fmt.get("ext") == "mp4" and fmt.get("height"):
            by_height.setdefault(fmt["height"], _size(fmt))
            labels.setdefault(fmt["height"], _label(fmt))
    heights = sorted(by_height, reverse=True)[:4]
    return {"video": [{"height": height, "label": labels[height], "size": by_height[height]} for height in heights],
            "audio_size": audio_size}


def _label(fmt: dict) -> int:
    """„1080p" po užem rubu: uspravni video 1080×1920 (TikTok, Reels) je 1080p, ne 1920p."""
    width, height = fmt.get("width") or 0, fmt.get("height") or 0
    return min(width, height) if width and height else height


def probe(url: str, cache_dir: str) -> str:
    """Brzo čitanje linka za ekran „Izaberi kvalitet": naslov, sličica, trajanje, izbor kvaliteta (JSON).
    Zapis ide u isti dnevnik kao preuzimanje (za „Kopiraj izvještaj")."""
    import json

    log = _FileLog(os.path.join(cache_dir, "zadnji-log.txt"))
    log.info(f"čitanje linka: {url}")
    try:
        with YoutubeDL({"quiet": True, "no_warnings": True, "noplaylist": True, "logger": log, "verbose": True,
                        "dump_intermediate_pages": True}) as ydl:
            info = ydl.extract_info(url, download=False)
            if info.get("_type") == "playlist":
                entries = [entry for entry in info.get("entries") or [] if entry]
                if not entries:
                    raise ValueError("Plejlista nema videa.")
                info = ydl.extract_info(entries[0].get("webpage_url") or entries[0]["url"], download=False)
    except Exception as error:
        log.error(f"{type(error).__name__}: {error}")
        raise
    finally:
        log.close()
    return json.dumps({"url": info.get("webpage_url") or url, "title": info.get("title") or info.get("id") or "",
                       "thumbnail": info.get("thumbnail") or "", "duration": info.get("duration") or 0,
                       "site": info.get("extractor_key") or "", **options(info)}, ensure_ascii=False)


def download(url: str, kind: str, work_dir: str, listener, height: int = 0):
    """`listener` je Kotlin objekat: onProgress(udio, preuzeto, ukupno) i isCancelled().
    Vraća [naslov, ime fajla bez ekstenzije, putanja prvog dijela, putanja drugog dijela ili ""]."""
    # SVE ide kroz JEDNU sesiju yt-dlp-a: linkovi formata (npr. YouTube) vezani su za kolačiće i podatke sesije
    # u kojoj su pročitani; nova sesija za preuzimanje dobije HTTP 403 (nađeno na S26 Ultra, 27.9.2026).
    part = {"before": 0.0, "weight": 1.0}

    def hook(status):
        if listener.isCancelled():
            raise Cancelled()
        if status.get("status") == "downloading":
            total = status.get("total_bytes") or status.get("total_bytes_estimate") or 0
            done = status.get("downloaded_bytes") or 0
            fraction = part["before"] + (done / total) * part["weight"] if total else -1.0
            listener.onProgress(fraction, int(done), int(total))

    hook.cancelled = listener.isCancelled

    log = _FileLog(os.path.join(os.path.dirname(work_dir), "zadnji-log.txt"))
    log.info(f"link: {url} | vrsta: {kind}")
    options = {"quiet": True, "no_warnings": True, "noprogress": True, "noplaylist": True, "retries": 3,
               "progress_hooks": [hook], "logger": log, "verbose": True, "dump_intermediate_pages": True}
    try:
        return _run(url, kind, work_dir, options, part, log, height)
    except Exception as error:
        log.error(f"{type(error).__name__}: {error}")
        raise
    finally:
        log.close()


def listener_cancelled(options) -> bool:
    return any(getattr(hook, "cancelled", lambda: False)() for hook in options["progress_hooks"])


def _run(url, kind, work_dir, options, part, log, height=0):
    with YoutubeDL(options) as ydl:
        info = ydl.extract_info(url, download=False)
        if info.get("_type") == "playlist":  # prototip: iz plejliste samo prvi video
            entries = [entry for entry in info.get("entries") or [] if entry]
            if not entries:
                raise ValueError("Plejlista nema videa.")
            url = entries[0].get("webpage_url") or entries[0]["url"]
            info = ydl.extract_info(url, download=False)

        if listener_cancelled(options):
            raise Cancelled()
        specs = plan(info, kind, height)
        sizes = [_size(next((f for f in info.get("formats") or [] if f.get("format_id") == spec), {}))
                 for spec in specs]
        weights = [size / sum(sizes) for size in sizes] if all(sizes) else [1 / len(specs)] * len(specs)
        paths = []
        for index, spec in enumerate(specs):
            part.update(before=sum(weights[:index]), weight=weights[index])
            # yt-dlp izbor formata sastavi jednom, u konstruktoru; za svaki dio se sastavlja ponovo.
            ydl.params["format"] = spec
            ydl.format_selector = ydl.build_format_selector(spec)
            ydl.params["outtmpl"] = {"default": os.path.join(work_dir, f"dio{index}.%(ext)s")}
            # Link se čita ponovo pa odmah preuzima: kopija ranije pročitanih podataka daje YouTubeu HTTP 403.
            result = ydl.extract_info(url, download=True)
            downloads = result.get("requested_downloads") or []
            paths.append(downloads[-1]["filepath"] if downloads else result.get("filepath"))

    title = info.get("title") or info.get("id") or "video"
    name = f"{sanitize_filename(title).strip()[:120].rstrip('. ') or 'video'} [{info.get('id', '')}]"
    return [title, name, paths[0], paths[1] if len(paths) > 1 else ""]


def _page_start(line: str, size: int = 3000) -> str:
    """yt-dlp stranicu upisuje kao base64 (dump_intermediate_pages); za izvještaj treba čitljiv početak."""
    import base64
    import re

    raw = line.split("] ", 1)[-1].strip()
    try:
        text = base64.b64decode(raw, validate=True).decode("utf-8", errors="replace")
    except ValueError:
        text = raw
    return "    " + re.sub(r"\s+", " ", text)[:size]


def report(cache_dir: str, limit: int = 20_000) -> str:
    """Sažetak posljednjeg dnevnika za „Kopiraj izvještaj": verzije, sve osim sitnih debug redova, i početak
    stranica koje je sajt vratio (tu se vidi npr. provjera „jesi li robot"). Ide samo tamo gdje ga korisnik zalijepi."""
    import platform
    import sys

    path = os.path.join(cache_dir, "zadnji-log.txt")
    if not os.path.isfile(path):
        return "Nema dnevnika."
    with open(path, encoding="utf-8", errors="replace") as file:
        lines = file.read().splitlines()
    head = [f"Video Download Android | yt-dlp {version()} | Python {sys.version.split()[0]} | {platform.platform()}"]
    keep = []
    for index, line in enumerate(lines):
        important = not line.startswith("[debug]") or any(key in line for key in (
            "Dumping request", "Request Handlers", "Python ", "Proxy", "Extracting URL", "Downloading webpage",
            "Downloading JSON", "Redirect", "HTTP Error", "Unexpected"))
        if important:
            keep.append(line[:600])
        if "Dumping request" in line and index + 1 < len(lines):
            keep.append(_page_start(lines[index + 1]))  # početak stranice koju je sajt vratio
    text = "\n".join(head + keep)
    return text if len(text) <= limit else text[:limit // 2] + "\n…\n" + text[-limit // 2:]


def version() -> str:
    from yt_dlp.version import __version__

    return __version__
