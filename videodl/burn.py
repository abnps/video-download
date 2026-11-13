"""Upisivanje titla u sliku videa (Ahmed 12.11.2026, bez Qt-a), preko istog ffmpeg-a koji koristi preuzimanje.

Titl postaje dio slike: vidi se u svakom plejeru, na telefonu, TV-u i kad se video pošalje dalje, ali se više ne
može isključiti. Slika se zato kodira ponovo (H.264), zvuk se samo prepiše. Original se zamjenjuje tek kad je novi
fajl gotov; greška ili prekid ga ostavljaju netaknutog.
"""

import os
import shutil
import subprocess
import tempfile
import threading
import uuid
from collections.abc import Callable
from pathlib import Path

from .runtime import find_tool

_NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)
SUBTITLE_SUFFIXES = (".srt", ".vtt", ".ass")
# Brzo kodiranje uz kvalitet koji se okom ne razlikuje od originala (manji crf = veći fajl).
VIDEO_ARGS = ("-c:v:0", "libx264", "-preset", "veryfast", "-crf", "20", "-pix_fmt", "yuv420p")


class BurnError(Exception):
    """Titl nije upisan; poruka je kratka i bez putanja korisnika. Video ostaje kakav je bio."""


class BurnCancelled(BurnError):
    """Korisnik je prekinuo."""


def can_burn(video: str | None) -> bool:
    """Upisuje se samo u MP4 (formati „najbolji", 1080p, 720p, 480p); originalni MKV ostaje bez pretvaranja."""
    return bool(video) and video.lower().endswith(".mp4") and os.path.isfile(video)


def command(ffmpeg: str, video: str, subtitle_name: str, target: str) -> list[str]:
    """`subtitle_name` je samo ime fajla: ffmpeg se pokreće u folderu gdje je titl, pa putanja s dvotačkom,
    apostrofom ili našim slovima ne mora u filter (tamo bi se morala posebno zaštititi)."""
    return [ffmpeg, "-hide_banner", "-nostdin", "-y", "-i", video,
            # Slika s titlom, zvuk kakav jeste; omot (druga „slika" u MP4) se prepisuje ako postoji.
            "-map", "0:v:0", "-map", "0:a?", "-map", "0:v:1?",
            "-filter:v:0", f"subtitles={subtitle_name}", *VIDEO_ARGS,
            "-c:v:1", "copy", "-disposition:v:1", "attached_pic", "-c:a", "copy",
            "-sn",  # ugrađeni titl koji se može isključiti više ne treba (bio bi dupli)
            "-map_metadata", "0", "-map_chapters", "0", "-movflags", "+faststart",
            "-f", "mp4", "-progress", "pipe:1", "-nostats", target]


def burn_subtitles(video: str, subtitle: str, on_progress: Callable[[float | None], None] | None = None,
                   cancel_event: threading.Event | None = None, duration: float | None = None,
                   ffmpeg: str | None = None, popen=subprocess.Popen) -> None:
    """Zamijeni `video` istim videom s titlom `subtitle` upisanim u sliku."""
    source = Path(video)
    if not can_burn(video):
        raise BurnError("Video nije MP4 ili više ne postoji.")
    if not os.path.isfile(subtitle) or not subtitle.lower().endswith(SUBTITLE_SUFFIXES):
        raise BurnError("Titl ne postoji.")
    ffmpeg = ffmpeg or find_tool("ffmpeg")
    if not ffmpeg:
        raise BurnError("ffmpeg nije pronađen.")
    work = Path(tempfile.mkdtemp(prefix="videodl-titl-"))
    # Privremeni fajl je samo ovog pokušaja i u istom folderu (zamjena je tada jedan potez, bez kopiranja).
    partial = source.with_name(f"{source.name}.{uuid.uuid4().hex[:8]}.part")
    process = None
    try:
        name = "titl" + Path(subtitle).suffix.lower()
        shutil.copyfile(subtitle, work / name)
        try:
            process = popen(command(ffmpeg, str(source), name, str(partial)), cwd=str(work),
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, encoding="utf-8",
                            errors="replace", creationflags=_NO_WINDOW)
        except OSError as exc:
            raise BurnError(f"ffmpeg se nije pokrenuo: {exc}") from exc
        stderr_tail: list[str] = []
        reader = threading.Thread(target=_drain, args=(process.stderr, stderr_tail), daemon=True)
        reader.start()
        # Prekid ne zavisi od toga da li ffmpeg nešto ispisuje: čuvar ga provjerava sam.
        threading.Thread(target=_watch_cancel, args=(process, cancel_event), daemon=True).start()
        for line in process.stdout:
            if cancel_event is not None and cancel_event.is_set():
                break
            key, _, value = line.strip().partition("=")
            if key == "out_time_us" and on_progress and duration:
                try:
                    on_progress(max(0.0, min(int(value) / 1_000_000 / duration, 1.0)))
                except ValueError:
                    pass
        process.wait()
        reader.join(timeout=5)
        if cancel_event is not None and cancel_event.is_set():
            raise BurnCancelled("Prekinuto.")
        if process.returncode != 0 or not partial.is_file() or partial.stat().st_size == 0:
            detail = next((line for line in reversed(stderr_tail) if line.strip()), "")
            raise BurnError(f"ffmpeg: {detail[:200]}" if detail else "ffmpeg nije uspio.")
        os.replace(partial, source)
    finally:
        if process is not None:
            if process.poll() is None:  # prvo se ffmpeg ugasi, tek onda se brišu njegovi fajlovi
                process.kill()
                process.wait()
            for stream in (process.stdout, process.stderr):
                if stream is not None:
                    stream.close()
        partial.unlink(missing_ok=True)
        shutil.rmtree(work, ignore_errors=True)


def _drain(stream, tail: list[str], keep: int = 20) -> None:
    for line in stream:
        tail.append(line)
        del tail[:-keep]


def _watch_cancel(process, cancel_event: threading.Event | None) -> None:
    if cancel_event is None:
        return
    while process.poll() is None:
        if cancel_event.wait(0.2):
            process.kill()
            return
