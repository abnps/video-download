"""Pomoćne funkcije glavnog prozora bez stanja prozora (izdvojeno iz gui.py, Faza 4, 29.10.2026)."""

import functools
import re
import sys
import urllib.request
from pathlib import Path

from PySide6.QtCore import QRect, Qt
from PySide6.QtGui import QColor, QPainter, QPixmap

from .download import PROCESSING, Progress
from .i18n import decimal, tr
from .runtime import bundled_tool, find_tool
from .ytdl import JS_RUNTIMES


_URL_PATTERN = re.compile(r"https?://[^\s<>\"']+", re.IGNORECASE)


MAX_THUMBNAIL_BYTES = 2 * 1024 * 1024


# Ukupno ograničenje brzine u MB/s (0 = bez ograničenja); dijeli se na preuzimanja u toku.
RATE_CHOICES = (0, 1, 2, 5, 10)


# Koliko preuzimanja može ići istovremeno (Preuzimanja → Istovremeno).
PARALLEL_CHOICES = (1, 2, 3, 4)


DEFAULT_PARALLEL = 2


def adult_thumbnail(pixmap: QPixmap) -> QPixmap:
    """Sličica sadržaja 18+: jako zamućena (smanjena pa uvećana) i s oznakom „18+", da se ne vidi preko ramena."""
    if pixmap.isNull():
        return pixmap
    tiny = pixmap.scaled(8, 5, Qt.AspectRatioMode.IgnoreAspectRatio, Qt.TransformationMode.SmoothTransformation)
    result = tiny.scaled(pixmap.size(), Qt.AspectRatioMode.IgnoreAspectRatio, Qt.TransformationMode.SmoothTransformation)
    painter = QPainter(result)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    # veličina prema sličici: red je prikazuje umanjenu, pa oznaka mora ostati čitljiva
    badge = QRect(0, 0, max(44, result.width() * 2 // 5), max(24, result.height() * 2 // 5))
    badge.moveCenter(result.rect().center())
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(QColor(0, 0, 0, 170))
    painter.drawRoundedRect(badge, badge.height() // 4, badge.height() // 4)
    font = painter.font()
    font.setBold(True)
    font.setPixelSize(max(13, badge.height() * 3 // 5))
    painter.setFont(font)
    painter.setPen(QColor("white"))
    painter.drawText(badge, int(Qt.AlignmentFlag.AlignCenter), "18+")
    painter.end()
    return result


def default_output_dir(platform: str = sys.platform) -> str:
    # Mac nema „Videos"; tamo je folder za video „Movies" (u Finderu „Filmovi").
    return str(Path.home() / ("Movies" if platform == "darwin" else "Videos") / "Video Download")


def format_speed(bytes_per_second: float) -> str:
    value = bytes_per_second / 1024
    for unit in ("KB/s", "MB/s", "GB/s"):
        if value < 1024 or unit == "GB/s":
            return decimal(f"{value:.1f} {unit}")
        value /= 1024
    raise AssertionError("nedostižno")


def format_eta(seconds: int) -> str:
    minutes, secs = divmod(int(seconds), 60)
    hours, minutes = divmod(minutes, 60)
    if hours:
        return f"{hours}:{minutes:02d}:{secs:02d}"
    if minutes:
        return f"{minutes}:{secs:02d}"
    return f"{secs} s"


def format_progress(progress: Progress) -> str:
    if progress.phase == PROCESSING:
        return f"{tr(progress.label)}…"
    parts = [tr("progress.downloading") + (f" ({tr(progress.label)})" if progress.label else "")]
    if progress.fraction is not None:
        parts.append(f"{progress.fraction:.0%}")
    if progress.speed:
        parts.append(format_speed(progress.speed))
    if progress.eta is not None:
        parts.append(tr("progress.eta", time=format_eta(progress.eta)))
    return " · ".join(parts)


def extract_urls(text: str) -> list[str]:
    urls = []
    for match in _URL_PATTERN.findall(text or ""):
        url = match.rstrip(".,;)")
        if url not in urls:
            urls.append(url)
    return urls


@functools.cache
def missing_tools() -> tuple[str, ...]:
    # Jednom po pokretanju: zove se pri svakom prevođenju prozora, a traženje po PATH-u (npr. „deno", koji paket
    # nema) je trajalo i pola sekunde pri otvaranju. Node iz paketa se provjeri prije nego išta po PATH-u.
    missing = []
    if not find_tool("ffmpeg"):
        missing.append("missing.ffmpeg")
    if not (any(bundled_tool(name) for name in JS_RUNTIMES) or any(find_tool(name) for name in JS_RUNTIMES)):
        missing.append("missing.js")
    return tuple(missing)


def fetch_thumbnail(url: str) -> bytes | None:
    if not url.lower().startswith(("http://", "https://")):
        return None
    request = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(request, timeout=10) as response:
        return response.read(MAX_THUMBNAIL_BYTES)
