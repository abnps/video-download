"""Widgeti glavnog prozora: prazan ekran za lijepljenje linka i red preuzimanja."""

import os

from PySide6.QtCore import (
    QEasingCurve, QElapsedTimer, QPoint, QRectF, QSize, Qt, QTimer, QVariantAnimation, Signal,
)
from PySide6.QtGui import QColor, QFont, QLinearGradient, QPainter, QPainterPath, QPen, QPixmap
from PySide6.QtWidgets import (
    QFrame, QHBoxLayout, QLabel, QSizePolicy, QToolButton, QVBoxLayout, QWidget,
)

from .i18n import MESSAGE_DRM, MESSAGE_EXISTS, MESSAGE_LIVE, MESSAGE_NOT_MEDIA, MESSAGE_RETRY, tr
from .icons import icon
from .jobs import ItemStatus, QueueItem
from .presets import format_section, get_preset

LINK_COLOR = "#1a73e8"
MUTED_COLOR = "#7a7a7a"

# Boje trake napretka po fazi (Ahmedov izbor, varijanta 4).
PROGRESS_TRACK = "#e3ecf8"
PROGRESS_COLORS = {"video": "#1e88e5", "audio": "#8e24aa", "work": "#8e24aa", "done": "#43a047"}


def format_duration(seconds: float | None) -> str:
    if not seconds:
        return ""
    minutes, secs = divmod(int(round(seconds)), 60)
    hours, minutes = divmod(minutes, 60)
    return f"{hours}:{minutes:02d}:{secs:02d}" if hours else f"{minutes}:{secs:02d}"


def format_size(size: int | None) -> str:
    if not size:
        return ""
    value = float(size)
    for unit in ("B", "KB", "MB", "GB"):
        if value < 1024 or unit == "GB":
            return (f"{value:.0f} {unit}" if unit in ("B", "KB") else f"{value:.1f} {unit}").replace(".", ",")
        value /= 1024
    raise AssertionError("nedostižno")


def display_message(message: str) -> str:
    """Poruka stavke za prikaz: posebne vrijednosti se prevode, greške yt-dlp-a ostaju kakve jesu."""
    if message == MESSAGE_DRM:
        return tr("error.drm")
    if message == MESSAGE_LIVE:
        return tr("error.live")
    if message == MESSAGE_NOT_MEDIA:
        return tr("error.not_media")
    if message == MESSAGE_RETRY:
        return tr("row.retrying")
    if message == MESSAGE_EXISTS:
        return tr("row.exists")
    return message


def set_state(widget: QWidget, state: str) -> None:
    # QSS [state="..."] se ponovo primjenjuje tek poslije unpolish/polish.
    widget.setProperty("state", state)
    widget.style().unpolish(widget)
    widget.style().polish(widget)


class AnimatedProgress(QWidget):
    """Traka napretka kartice: klizi do novog procenta, preko nje prelazi sjaj, boja pokazuje fazu
    (video plavo, zvuk ljubičasto), dok ffmpeg radi klizi lijevo-desno, a na kraju zazeleni i pulsira.
    Tajmer za animaciju radi samo dok je traka vidljiva i nešto se dešava."""

    BAR = 6  # debljina trake; widget je malo viši zbog pulsa na kraju
    SHINE_MS = 1600
    SLIDE_MS = 1200
    PULSE_MS = 700
    DONE_HOLD_MS = 1100  # koliko zelena traka ostaje vidljiva poslije završetka

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.setFixedHeight(self.BAR + 2)
        self.phase = "video"
        self.indeterminate = False
        self.target = 0.0
        self._value = 0.0
        self._done_at: int | None = None
        self._clock = QElapsedTimer()
        self._clock.start()
        self._slide = QVariantAnimation(self)
        self._slide.setDuration(600)
        self._slide.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._slide.valueChanged.connect(self._on_slide)
        self._tick = QTimer(self)
        self._tick.setInterval(33)  # ~30 slika u sekundi
        self._tick.timeout.connect(self._on_tick)
        self._hide_timer = QTimer(self)
        self._hide_timer.setSingleShot(True)
        self._hide_timer.timeout.connect(self.hide)

    @property
    def value(self) -> float:
        return self._value

    def set_fraction(self, fraction: float | None, phase: str = "video") -> None:
        self._hide_timer.stop()
        self._done_at = None
        if fraction is None:
            self._slide.stop()
            self.indeterminate = True
            self.phase = "work"
        else:
            fraction = max(0.0, min(1.0, float(fraction)))
            self._slide.stop()
            if self.indeterminate or fraction < self._value:
                self._value = fraction  # poslije klizanja ili novi pokušaj: bez animacije unazad
            self.indeterminate = False
            self.phase = phase
            self.target = fraction
            self._slide.setStartValue(self._value)
            self._slide.setEndValue(fraction)
            self._slide.start()
        self.show()
        self._ensure_ticking()
        self.update()

    def reset(self) -> None:
        self._slide.stop()
        self._hide_timer.stop()
        self._done_at = None
        self._value = self.target = 0.0
        self.indeterminate = False
        self.phase = "video"
        self.update()

    def finish(self) -> None:
        """Gotovo: traka se puni do kraja, zazeleni, kratko pulsira i nestane."""
        if not self.isVisible():
            return
        self._slide.stop()
        self._value = self.target = 1.0
        self.indeterminate = False
        self.phase = "done"
        self._done_at = self._clock.elapsed()
        self._ensure_ticking()
        self._hide_timer.start(self.DONE_HOLD_MS)
        self.update()

    def is_animating(self) -> bool:
        return self._tick.isActive()

    def _ensure_ticking(self) -> None:
        if self.isVisible() and not self._tick.isActive():
            self._tick.start()

    def _on_slide(self, value) -> None:
        self._value = float(value)
        self.update()

    def _on_tick(self) -> None:
        if not self.isVisible():
            self._tick.stop()
            return
        if (self.phase == "done" and self._done_at is not None
                and self._clock.elapsed() - self._done_at > self.PULSE_MS):
            self._tick.stop()  # puls je gotov; zelena traka stoji do skrivanja
        self.update()

    def showEvent(self, event) -> None:
        super().showEvent(event)
        self._ensure_ticking()

    def hideEvent(self, event) -> None:
        super().hideEvent(event)
        self._tick.stop()
        self._hide_timer.stop()
        if self.phase == "done":
            self.reset()

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(Qt.PenStyle.NoPen)
        width, now = self.width(), self._clock.elapsed()
        thickness = float(self.BAR)
        if self.phase == "done" and self._done_at is not None:
            # Puls: traka se na trenutak podeblja pa vrati.
            t = min(1.0, (now - self._done_at) / self.PULSE_MS)
            thickness += 2.0 * (1.0 - abs(2.0 * t - 1.0))
        top = (self.height() - thickness) / 2
        radius = thickness / 2
        track = QPainterPath()
        track.addRoundedRect(QRectF(0, top, width, thickness), radius, radius)
        painter.fillPath(track, QColor(PROGRESS_TRACK))
        color = QColor(PROGRESS_COLORS.get(self.phase, PROGRESS_COLORS["video"]))

        if self.indeterminate:
            segment = width * 0.3
            t = (now % self.SLIDE_MS) / self.SLIDE_MS
            eased = QEasingCurve(QEasingCurve.Type.InOutQuad).valueForProgress(t)
            left = -segment + eased * (width + segment)
            piece = QPainterPath()
            piece.addRoundedRect(QRectF(left, top, segment, thickness), radius, radius)
            painter.setClipPath(track)
            painter.fillPath(piece, color)
            return

        filled = width * self._value
        if filled <= 0:
            return
        bar = QPainterPath()
        bar.addRoundedRect(QRectF(0, top, max(filled, thickness), thickness), radius, radius)
        painter.fillPath(bar, color)
        if self.phase != "done":
            # Sjaj koji prelazi preko popunjenog dijela: vidi se da preuzimanje radi i kad je sporo.
            shine = 60.0
            x = -shine + ((now % self.SHINE_MS) / self.SHINE_MS) * (filled + shine)
            gradient = QLinearGradient(x, 0, x + shine, 0)
            gradient.setColorAt(0.0, QColor(255, 255, 255, 0))
            gradient.setColorAt(0.5, QColor(255, 255, 255, 150))
            gradient.setColorAt(1.0, QColor(255, 255, 255, 0))
            painter.setClipPath(bar)
            painter.fillRect(QRectF(x, top, shine, thickness), gradient)


class ElidedLabel(QLabel):
    """Jednoredni tekst koji se skraćuje sa „…" umjesto da širi prozor."""

    def __init__(self, text: str = "", parent: QWidget | None = None):
        super().__init__(text, parent)
        self.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)

    def minimumSizeHint(self) -> QSize:
        return QSize(0, super().minimumSizeHint().height())

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setPen(self.palette().color(self.foregroundRole()))
        rect = self.contentsRect()
        text = self.fontMetrics().elidedText(self.text(), Qt.TextElideMode.ElideRight, rect.width())
        painter.drawText(rect, int(self.alignment() | Qt.AlignmentFlag.AlignVCenter), text)


class Thumbnail(QWidget):
    WIDTH, HEIGHT = 96, 54

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.setFixedSize(self.WIDTH, self.HEIGHT)
        self._pixmap: QPixmap | None = None
        self._duration = ""

    def set_pixmap(self, pixmap: QPixmap) -> None:
        self._pixmap = pixmap
        self.update()

    def has_pixmap(self) -> bool:
        return self._pixmap is not None

    def set_duration(self, text: str) -> None:
        self._duration = text
        self.update()

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        frame = QPainterPath()
        frame.addRoundedRect(QRectF(self.rect()), 3, 3)
        painter.setClipPath(frame)

        if self._pixmap is not None:
            scaled = self._pixmap.scaled(self.size(), Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                                         Qt.TransformationMode.SmoothTransformation)
            painter.drawPixmap((self.width() - scaled.width()) // 2, (self.height() - scaled.height()) // 2, scaled)
        else:
            painter.fillRect(self.rect(), QColor("#2f3136"))
            play = QPainterPath()
            cx, cy = self.width() / 2, self.height() / 2
            play.moveTo(cx - 6, cy - 9)
            play.lineTo(cx + 9, cy)
            play.lineTo(cx - 6, cy + 9)
            play.closeSubpath()
            painter.fillPath(play, QColor(255, 255, 255, 200))

        if self._duration:
            font = QFont(self.font())
            font.setPointSizeF(max(font.pointSizeF() - 1.5, 7))
            font.setBold(True)
            painter.setFont(font)
            width = painter.fontMetrics().horizontalAdvance(self._duration) + 8
            badge = QRectF(self.width() - width - 3, self.height() - 16, width, 13)
            painter.fillRect(badge, QColor(0, 0, 0, 190))
            painter.setPen(QColor("white"))
            painter.drawText(badge, int(Qt.AlignmentFlag.AlignCenter), self._duration)


class DropZone(QWidget):
    """Prazan ekran: isprekidan okvir sa strelicom i poziv da se link prevuče ili zalijepi."""

    paste_requested = Signal()

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.setObjectName("dropZone")
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.setSpacing(6)

        self.box = _DashedBox()
        layout.addWidget(self.box, 0, Qt.AlignmentFlag.AlignHCenter)
        layout.addSpacing(10)
        self.title = title = QLabel()
        title.setObjectName("dropTitle")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)
        self.paste_link = QLabel()
        self.paste_link.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.paste_link.linkActivated.connect(lambda _href: self.paste_requested.emit())
        layout.addWidget(self.paste_link)
        self.folder_hint = QLabel()
        self.folder_hint.setObjectName("dropHint")
        self.folder_hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addSpacing(14)
        layout.addWidget(self.folder_hint)

        self._folder = ""
        self.retranslate()

    def retranslate(self) -> None:
        self.title.setText(tr("drop.title"))
        self.paste_link.setText(f'<a href="paste" style="color:{LINK_COLOR}">{tr("drop.paste")}</a>')
        self.folder_hint.setText(tr("drop.folder", folder=self._folder))

    def set_folder(self, folder: str) -> None:
        self._folder = folder
        self.folder_hint.setText(tr("drop.folder", folder=folder))


class _DashedBox(QWidget):
    def __init__(self):
        super().__init__()
        self.setFixedSize(84, 84)

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        pen = QPen(QColor("#9aa0a6"), 3, Qt.PenStyle.CustomDashLine)
        pen.setDashPattern([3, 2.2])
        pen.setCapStyle(Qt.PenCapStyle.FlatCap)
        painter.setPen(pen)
        painter.drawRoundedRect(QRectF(3, 3, 78, 78), 12, 12)
        arrow = QPen(QColor("#7d8288"), 5)
        arrow.setCapStyle(Qt.PenCapStyle.RoundCap)
        arrow.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
        painter.setPen(arrow)
        painter.drawLine(42, 22, 42, 58)
        painter.drawPolyline([QPoint(29, 46), QPoint(42, 59), QPoint(55, 46)])


class QueueRow(QFrame):
    action_clicked = Signal(int)
    play_clicked = Signal(int)
    convert_clicked = Signal(int)
    remove_clicked = Signal(int)
    format_clicked = Signal(int, QPoint)

    def __init__(self, item: QueueItem, parent: QWidget | None = None):
        super().__init__(parent)
        self.item_id = item.id
        self.setObjectName("queueRow")

        layout = QHBoxLayout(self)
        layout.setContentsMargins(14, 9, 10, 9)
        layout.setSpacing(12)

        self.thumbnail = Thumbnail()
        layout.addWidget(self.thumbnail)

        text = QVBoxLayout()
        text.setSpacing(3)
        self.title_label = ElidedLabel(item.title)
        self.title_label.setObjectName("rowTitle")
        self.title_label.setToolTip(f"{item.title}\n{item.url}")
        text.addWidget(self.title_label)

        detail = QHBoxLayout()
        detail.setSpacing(8)
        self.format_link = QLabel()
        self.format_link.setObjectName("rowLink")
        self.format_link.linkActivated.connect(self._on_format_link)
        detail.addWidget(self.format_link)
        self.status_label = ElidedLabel()
        self.status_label.setObjectName("rowStatus")
        detail.addWidget(self.status_label, 1)
        text.addLayout(detail)

        self.progress = AnimatedProgress()
        self.progress.setObjectName("rowProgress")
        self.progress.hide()
        text.addWidget(self.progress)
        layout.addLayout(text, 1)

        self.play_button = QToolButton()
        self.play_button.setObjectName("rowAction")
        self.play_button.setIcon(icon("play", "#5f6368"))
        self.play_button.setIconSize(QSize(20, 20))
        self.play_button.setFixedSize(34, 34)
        self.play_button.clicked.connect(lambda: self.play_clicked.emit(self.item_id))
        self.play_button.hide()
        layout.addWidget(self.play_button, 0, Qt.AlignmentFlag.AlignVCenter)

        self.action_button = QToolButton()
        self.action_button.setObjectName("rowAction")
        self.action_button.setIconSize(QSize(20, 20))
        self.action_button.setFixedSize(34, 34)
        self.action_button.clicked.connect(lambda: self.action_clicked.emit(self.item_id))
        layout.addWidget(self.action_button, 0, Qt.AlignmentFlag.AlignVCenter)

        # Samo na gotovom MP4: pretvori u MP3 (pored dugmeta za folder).
        self.convert_button = QToolButton()
        self.convert_button.setObjectName("rowConvert")
        self.convert_button.setFixedSize(44, 34)
        self.convert_button.clicked.connect(lambda: self.convert_clicked.emit(self.item_id))
        # Mjesto ostaje i kad je dugme sakriveno, da „Pusti" i folder stoje u istoj koloni u svim redovima.
        policy = self.convert_button.sizePolicy()
        policy.setRetainSizeWhenHidden(True)
        self.convert_button.setSizePolicy(policy)
        self.convert_button.hide()
        layout.addWidget(self.convert_button, 0, Qt.AlignmentFlag.AlignVCenter)

        self.remove_button = QToolButton()
        self.remove_button.setObjectName("rowRemove")
        self.remove_button.setIcon(icon("close", "#9aa0a6"))
        self.remove_button.setIconSize(QSize(12, 12))
        self.remove_button.setFixedSize(20, 20)
        self.remove_button.clicked.connect(lambda: self.remove_clicked.emit(self.item_id))
        layout.addWidget(self.remove_button, 0, Qt.AlignmentFlag.AlignTop)

        self.thumbnail.set_duration(format_duration(item.duration))
        self.update_item(item)

    def _on_format_link(self, _href: str) -> None:
        self.format_clicked.emit(self.item_id, self.format_link.mapToGlobal(self.format_link.rect().bottomLeft()))

    def update_item(self, item: QueueItem, size: int | None = None) -> None:
        preset = get_preset(item.preset_key).short_label
        if item.section:
            preset = f"{preset} · {format_section(item.section)}"
        active = item.status == ItemStatus.ACTIVE
        if active:
            self.format_link.setText(f'<span style="color:{MUTED_COLOR}">{preset}</span>')
        else:
            self.format_link.setText(f'<a href="format" style="color:{LINK_COLOR}">{preset}</a>')

        self.format_link.setToolTip(tr("row.format_tip"))
        if item.status == ItemStatus.WAITING:
            self._set_status(tr("row.waiting"), "muted")
            self._set_action("download-solid", "#5f6368", tr("row.download_tip"))
        elif active:
            self._set_status(tr("row.starting"), "muted")
            self._set_action("stop", "#5f6368", tr("row.stop_tip"))
            if self.progress.isHidden() or self.progress.phase == "done":
                self.progress.reset()
                self.progress.set_fraction(None)  # priprema: traka klizi dok ne stigne prvi procenat
        elif item.status == ItemStatus.DONE:
            text = tr("row.exists") if item.message == MESSAGE_EXISTS else tr("row.done")
            if size:
                text += f" · {format_size(size)}"
            state = "done"
            if item.convert_state == "running":
                text, state = tr("row.converting"), "muted"
            elif item.convert_state == "done":
                text += f" · {tr('row.converted')}"
            elif item.convert_state == "failed":
                text, state = tr("row.convert_failed", error=item.convert_message), "failed"
            self._set_status(text, state)
            self._set_action("folder", "#5f6368", tr("row.reveal_tip"))
        elif item.status == ItemStatus.FAILED:
            self._set_status(tr("row.failed", message=display_message(item.message)), "failed")
            self._set_action("retry", "#5f6368", tr("row.retry_tip"))
        else:
            self._set_status(tr("row.cancelled"), "muted")
            self._set_action("retry", "#5f6368", tr("row.retry_tip"))

        converting = item.status == ItemStatus.DONE and item.convert_state == "running"
        if active:
            self.progress.show()
        elif item.status == ItemStatus.DONE and not converting and not self.progress.isHidden():
            self.progress.finish()  # zazeleni, pulsira i sama nestane
        elif not converting:
            self.progress.hide()
        can_play = item.status == ItemStatus.DONE and bool(item.filepath) and os.path.isfile(item.filepath)
        self.play_button.setVisible(can_play)
        self.convert_button.setText(tr("row.convert"))
        self.convert_button.setToolTip(tr("row.convert_tip"))
        self.convert_button.setVisible(can_play and item.filepath.lower().endswith(".mp4")
                                       and item.convert_state not in ("running", "done"))
        self.play_button.setToolTip(tr("row.play_audio") if get_preset(item.preset_key).is_audio else tr("row.play_video"))
        self.remove_button.setToolTip(tr("row.cancel_remove_tip") if active else tr("row.remove_tip"))
        self.status_label.setToolTip("\n".join(p for p in (item.filepath, item.convert_path) if p)
                                     or display_message(item.message))

    def show_progress(self, text: str, fraction: float | None, phase: str = "video") -> None:
        """`phase`: "video" ili "audio" (boja trake); bez procenta traka klizi (npr. ffmpeg radi)."""
        self._set_status(text, "muted")
        self.progress.set_fraction(fraction, phase)

    def _set_status(self, text: str, state: str) -> None:
        self.status_label.setText(text)
        set_state(self.status_label, state)
        self.status_label.update()

    def _set_action(self, kind: str, color: str, tooltip: str) -> None:
        self.action_button.setIcon(icon(kind, color))
        self.action_button.setToolTip(tooltip)
        self.action_button.setProperty("kind", kind)
