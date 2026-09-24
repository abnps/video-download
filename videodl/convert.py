"""Pretvaranje preuzetog MP4 videa u MP3 (bez Qt-a), preko istog ffmpeg-a koji koristi preuzimanje.

Original ostaje netaknut. MP3 dobija isto ime u istom folderu; ako takav fajl već postoji,
dodaje se „ (1)", „ (2)"… da se ništa ne pregazi. Kvalitet je isti kao format „MP3" (192 kbps).
"""

import os
import subprocess
import threading
from collections.abc import Callable
from pathlib import Path

from .runtime import find_tool

MP3_BITRATE = "192k"
_NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)


class ConvertError(Exception):
    """Pretvaranje nije uspjelo; poruka je kratka i bez putanja korisnika."""


def is_convertible(path: str | None) -> bool:
    return bool(path) and path.lower().endswith(".mp4") and os.path.isfile(path)


def target_path(source: Path) -> Path:
    """Slobodno ime za MP3 pored originala."""
    candidate = source.with_suffix(".mp3")
    number = 1
    while candidate.exists():
        candidate = source.with_name(f"{source.stem} ({number}).mp3")
        number += 1
    return candidate


def convert_to_mp3(source: str, on_progress: Callable[[float | None], None] | None = None,
                   cancel_event: threading.Event | None = None, duration: float | None = None,
                   ffmpeg: str | None = None, popen=subprocess.Popen) -> str:
    """Vraća putanju napravljenog MP3 fajla. Prekid ili greška brišu nedovršen MP3."""
    src = Path(source)
    if not src.is_file():
        raise ConvertError("Fajl više ne postoji.")
    ffmpeg = ffmpeg or find_tool("ffmpeg")
    if not ffmpeg:
        raise ConvertError("ffmpeg nije pronađen.")
    target = target_path(src)
    partial = target.with_name(target.name + ".part")
    command = [ffmpeg, "-hide_banner", "-nostdin", "-y", "-i", str(src), "-vn", "-map_metadata", "0",
               "-c:a", "libmp3lame", "-b:a", MP3_BITRATE, "-id3v2_version", "3", "-f", "mp3",
               "-progress", "pipe:1", "-nostats", str(partial)]
    process = popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, encoding="utf-8",
                    errors="replace", creationflags=_NO_WINDOW)
    stderr_tail: list[str] = []
    reader = threading.Thread(target=_drain, args=(process.stderr, stderr_tail), daemon=True)
    reader.start()
    try:
        for line in process.stdout:
            if cancel_event is not None and cancel_event.is_set():
                process.kill()
                break
            key, _, value = line.strip().partition("=")
            if key == "out_time_us" and on_progress and duration:
                try:
                    on_progress(min(int(value) / 1_000_000 / duration, 1.0))
                except ValueError:
                    pass
        process.wait()
        reader.join(timeout=5)
        if cancel_event is not None and cancel_event.is_set():
            raise ConvertError("Prekinuto.")
        if process.returncode != 0 or not partial.is_file() or partial.stat().st_size == 0:
            detail = next((line for line in reversed(stderr_tail) if line.strip()), "")
            raise ConvertError(f"ffmpeg: {detail[:200]}" if detail else "ffmpeg nije uspio.")
        os.replace(partial, target)
    except BaseException:
        partial.unlink(missing_ok=True)
        raise
    finally:
        if process.poll() is None:
            process.kill()
            process.wait()
        for stream in (process.stdout, process.stderr):
            if stream is not None:
                stream.close()
    if on_progress:
        on_progress(1.0)
    return str(target)


def _drain(stream, tail: list[str]) -> None:
    """Čita stderr da se ffmpeg ne zaglavi na punom baferu; pamti samo posljednje redove."""
    for line in stream:
        tail.append(line)
        del tail[:-20]
