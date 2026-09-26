"""Preuzimanje jedne stavke: ukupan napredak, prekid i čišćenje privremenih fajlova."""

import glob
import os
import subprocess
import threading
import time
from collections.abc import Callable
from dataclasses import dataclass

from yt_dlp import YoutubeDL
from yt_dlp.postprocessor import FFmpegExtractAudioPP, FFmpegMergerPP, PostProcessor
from yt_dlp.utils import DownloadCancelled

from .browser import Cookie, cookie_file
from .jobs import ItemStatus
from .presets import Preset, build_ydl_options, pick_subtitles
from .i18n import MESSAGE_NO_OUTPUT, MESSAGE_NO_SUBS
from .ytdl import YdlLogger, error_message

DOWNLOADING = "downloading"
SUBTITLE_ERROR = "Unable to download video subtitles"
PROCESSING = "processing"

# Duži ffmpeg koraci; prije njihovog početka prekid još ne ostavlja polovičan izlaz.
# Ključ uzimamo iz klase jer yt-dlp skraćuje ime (FFmpegMergerPP -> "Merger").
# Oznake su ključevi prevoda (i18n); prevode se tek pri prikazu u glavnoj niti.
_PP_LABELS = {
    FFmpegMergerPP.pp_key(): "pp.merge",
    FFmpegExtractAudioPP.pp_key(): "pp.extract_audio",
}


@dataclass(frozen=True)
class Progress:
    phase: str
    fraction: float | None  # ukupno za stavku, 0..1; None kad nije poznato
    speed: float | None = None  # bajtova u sekundi
    eta: int | None = None  # sekundi
    label: str = ""


@dataclass(frozen=True)
class DownloadResult:
    status: ItemStatus
    filepath: str | None = None
    message: str = ""
    already_existed: bool = False


class RateBudget:
    """Zajedničko ograničenje brzine: dijeli se na preuzimanja koja STVARNO rade.

    Jedno preuzimanje dobija cijeli limit; kad krene drugo, oba dobijaju pola. yt-dlp za obična
    HTTP preuzimanja čita `ratelimit` iz svojih postavki pri svakom dijelu, pa se udio mijenja
    i usred preuzimanja (HLS dijelovi dobijaju udio koji važi kad počnu)."""

    def __init__(self, bytes_per_second: int):
        self.total = int(bytes_per_second)
        self._active = 0
        self._lock = threading.Lock()

    def join(self) -> None:
        with self._lock:
            self._active += 1

    def leave(self) -> None:
        with self._lock:
            self._active = max(0, self._active - 1)

    def share(self) -> int:
        with self._lock:
            return max(1, self.total // max(1, self._active))


class PartsProgress:
    """Spaja napredak više dijelova (video + zvuk) u jedan ukupan procenat."""

    def __init__(self):
        self._weights: dict[str, float] = {}
        self._fractions: dict[str, float] = {}

    def set_parts(self, formats: list[dict]) -> None:
        ids = [str(f.get("format_id")) for f in formats]
        self._weights = dict(zip(ids, _part_weights(formats)))
        self._fractions = dict.fromkeys(ids, 0.0)

    def update(self, format_id, downloaded: float, total: float | None) -> float | None:
        part = min(downloaded / total, 1.0) if total else None
        key = str(format_id)
        if key not in self._weights:
            return part
        if part is not None:
            self._fractions[key] = part
        total_weight = sum(self._weights.values())
        return sum(w * self._fractions[k] for k, w in self._weights.items()) / total_weight


def _part_weights(formats: list[dict]) -> list[float]:
    # Veličina je najtačnija; bitrate je srazmjeran veličini jer dijelovi traju isto.
    for keys in (("filesize", "filesize_approx"), ("tbr",)):
        values = [next((f[k] for k in keys if f.get(k)), None) for f in formats]
        if all(values):
            return [float(v) for v in values]
    return [1.0] * len(formats)


def _part_label(info: dict) -> str:
    if info.get("vcodec") == "none":
        return "progress.audio"
    if info.get("acodec") == "none":
        return "progress.video"
    return ""


class _PartsRecorderPP(PostProcessor):
    """Prije preuzimanja javlja koji se dijelovi (formati) preuzimaju."""

    def __init__(self, on_info: Callable[[dict], None]):
        super().__init__()
        self._on_info = on_info

    def run(self, information):
        self._on_info(information)
        return [], information


class _Attempt:
    def __init__(self, cancel_event: threading.Event, on_progress: Callable[[Progress], None],
                 clock: Callable[[], float] = time.monotonic, min_interval: float = 0.2):
        self._cancel = cancel_event
        self._on_progress = on_progress
        self._clock = clock
        self._min_interval = min_interval
        self._last_emit: float | None = None
        self.parts = PartsProgress()
        # Samo fajlovi koje je OVAJ pokušaj počeo pisati; ranije preuzeti se ne diraju.
        self.touched: set[str] = set()
        self.real_download = False

    def record_parts(self, info: dict) -> None:
        self.parts.set_parts(info.get("requested_formats") or [info])

    def progress_hook(self, d: dict) -> None:
        self._check_cancel()
        if d.get("status") != "downloading":
            return
        self.real_download = True
        self.touched.update(p for p in (d.get("tmpfilename"), d.get("filename")) if p)
        info = d.get("info_dict") or {}
        total = d.get("total_bytes") or d.get("total_bytes_estimate")
        fraction = self.parts.update(info.get("format_id"), d.get("downloaded_bytes") or 0, total)
        self._emit(Progress(DOWNLOADING, fraction, d.get("speed"), d.get("eta"), _part_label(info)))

    def postprocessor_hook(self, d: dict) -> None:
        key = d.get("postprocessor")
        if d.get("status") != "started" or key == _PartsRecorderPP.pp_key():
            return
        if key in _PP_LABELS:
            self._check_cancel()
        self._emit(Progress(PROCESSING, None, label=_PP_LABELS.get(key, "pp.processing")), force=True)

    def cleanup(self) -> None:
        for path in self.touched:
            fragments = glob.glob(glob.escape(path) + "-Frag*")
            for candidate in (path, path + ".ytdl", *fragments):
                try:
                    os.remove(candidate)
                except OSError:
                    pass

    def _check_cancel(self) -> None:
        if self._cancel.is_set():
            raise DownloadCancelled()

    def _emit(self, progress: Progress, force: bool = False) -> None:
        now = self._clock()
        if not force and self._last_emit is not None and now - self._last_emit < self._min_interval:
            return
        self._last_emit = now
        self._on_progress(progress)


def download(url: str, preset: Preset, output_dir: str, subfolder: str | None = None,
             on_progress: Callable[[Progress], None] | None = None,
             cancel_event: threading.Event | None = None, *,
             http_headers: dict[str, str] | None = None,
             filename_title: str | None = None,
             cookies: tuple[Cookie, ...] = (),
             section: tuple[float, float] | None = None,
             subtitles: bool = False,
             subtitle_langs: list[str] | None = None,
             thumbnail: bool = False,
             ratelimit: "int | RateBudget | None" = None,
             name_template: str | None = None) -> DownloadResult:
    cancel_event = cancel_event or threading.Event()
    if cancel_event.is_set():
        return DownloadResult(ItemStatus.CANCELLED)
    if isinstance(ratelimit, RateBudget):
        budget = ratelimit
        budget.join()
        try:
            return download(url, preset, output_dir, subfolder, on_progress, cancel_event, http_headers=http_headers,
                            filename_title=filename_title, cookies=cookies, section=section, subtitles=subtitles,
                            subtitle_langs=subtitle_langs, thumbnail=thumbnail, ratelimit=_LiveShare(budget),
                            name_template=name_template)
        finally:
            budget.leave()

    attempt = _Attempt(cancel_event, on_progress or (lambda progress: None))
    no_subtitles = False
    try:
        # Kolačići prijave postoje na disku samo dok radi ovo jedno preuzimanje.
        with cookie_file(cookies) as cookiefile:
            live = ratelimit if isinstance(ratelimit, _LiveShare) else None
            opts = build_ydl_options(preset, output_dir, subfolder, YdlLogger(), http_headers=http_headers,
                                     filename_title=filename_title, source_url=url, cookiefile=cookiefile,
                                     section=section, subtitles=subtitles, subtitle_langs=subtitle_langs,
                                     thumbnail=thumbnail, ratelimit=live.budget.share() if live else ratelimit,
                                     name_template=name_template)
            opts["progress_hooks"] = [attempt.progress_hook]
            if live:
                # Udio se osvježava pri svakom javljanju napretka (drugo preuzimanje počelo ili završilo).
                opts["progress_hooks"].append(lambda _d: opts.__setitem__("ratelimit", live.budget.share()))
            opts["postprocessor_hooks"] = [attempt.postprocessor_hook]
            with YoutubeDL(opts) as ydl:
                ydl.add_post_processor(_PartsRecorderPP(attempt.record_parts), when="before_dl")
                if subtitles and not preset.is_audio:
                    # Prvo se pročita koje titlove video ima, pa se uzme najviše jedan po jeziku
                    # (inače bi automatski prevodi dali po titl za svaki traženi jezik).
                    info = ydl.extract_info(url, download=False)
                    chosen = pick_subtitles(info, subtitle_langs or ["en"])
                    ydl.params["subtitleslangs"] = chosen
                    if not chosen:
                        ydl.params["writesubtitles"] = ydl.params["writeautomaticsub"] = False
                        no_subtitles = True
                    info = ydl.process_ie_result(info, download=True)
                else:
                    info = ydl.extract_info(url, download=True)
    except DownloadCancelled:
        attempt.cleanup()
        return DownloadResult(ItemStatus.CANCELLED)
    except Exception as exc:  # granica radne niti: svaka greška postaje status stavke
        attempt.cleanup()
        # yt-dlp ponekad umota prekid u DownloadError; bitno je šta je korisnik tražio.
        if cancel_event.is_set():
            return DownloadResult(ItemStatus.CANCELLED)
        if subtitles and SUBTITLE_ERROR in str(exc):
            # yt-dlp zbog neuspjelog titla (npr. HTTP 429) prekida cijelo preuzimanje; video je važniji.
            result = download(url, preset, output_dir, subfolder, on_progress, cancel_event,
                              http_headers=http_headers, filename_title=filename_title, cookies=cookies,
                              section=section, subtitles=False, thumbnail=thumbnail, ratelimit=ratelimit,
                              name_template=name_template)
            if result.status == ItemStatus.DONE:
                return DownloadResult(ItemStatus.DONE, result.filepath, MESSAGE_NO_SUBS, result.already_existed)
            return result
        return DownloadResult(ItemStatus.FAILED, message=error_message(exc))

    filepath = _final_path(info)
    if not output_is_usable(filepath):
        # yt-dlp je javio uspjeh, ali fajla nema, prazan je ili se ne može pročitati: nije „Završeno".
        return DownloadResult(ItemStatus.FAILED, filepath, MESSAGE_NO_OUTPUT)
    if subtitles and not no_subtitles and filepath:
        _plain_name_for_first_subtitle(filepath, (info or {}).get("requested_subtitles") or {})
    return DownloadResult(ItemStatus.DONE, filepath, MESSAGE_NO_SUBS if no_subtitles else "",
                          already_existed=not attempt.real_download)


MEDIA_SUFFIXES = frozenset((".mp4", ".mkv", ".webm", ".mov", ".m4v", ".avi", ".flv", ".ts", ".3gp",
                            ".mp3", ".m4a", ".aac", ".opus", ".ogg", ".oga", ".wav", ".flac", ".wma"))
_NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)


def output_is_usable(path: str | None, ffprobe: str | None = None, run=subprocess.run) -> bool:
    """Gotov fajl postoji, nije prazan i (kad je ffprobe tu) ima bar jedan audio ili video tok."""
    if not path or not os.path.isfile(path) or os.path.getsize(path) == 0:
        return False
    if os.path.splitext(path)[1].lower() not in MEDIA_SUFFIXES:
        return True  # nepoznata vrsta (npr. direktan fajl): dovoljno je da postoji
    from .runtime import find_tool

    ffprobe = ffprobe or find_tool("ffprobe")
    if not ffprobe:
        return True
    try:
        result = run([ffprobe, "-v", "error", "-show_entries", "stream=codec_type", "-of", "csv=p=0", path],
                     capture_output=True, text=True, timeout=60, creationflags=_NO_WINDOW)
    except (OSError, subprocess.SubprocessError):
        return True  # ffprobe ne radi: ne proglašavamo ispravan fajl neispravnim
    kinds = {line.strip() for line in result.stdout.splitlines()}
    return result.returncode == 0 and bool(kinds & {"video", "audio"})


def _plain_name_for_first_subtitle(video: str, requested: dict) -> None:
    """„Naslov [id].hr.srt" → „Naslov [id].srt": Windows playeri učitaju samo titl s istim imenom kao video.
    Drugi titl (engleski) zadržava oznaku jezika."""
    base = os.path.splitext(video)[0]
    plain = base + ".srt"
    if not requested or os.path.exists(plain):
        return
    first = next(iter(requested))
    candidate = f"{base}.{first}.srt"
    if os.path.isfile(candidate):
        os.replace(candidate, plain)


class _LiveShare:
    """Oznaka da je limit iz zajedničkog budžeta (budžet je već prijavio ovo preuzimanje)."""

    def __init__(self, budget: RateBudget):
        self.budget = budget


def _final_path(info: dict | None) -> str | None:
    if not info:
        return None
    downloads = info.get("requested_downloads") or []
    if downloads:
        return downloads[-1].get("filepath")
    return info.get("filepath")
