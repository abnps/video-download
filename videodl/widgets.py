"""Widgeti glavnog prozora: prazan ekran za lijepljenje linka i red preuzimanja."""

import os

from PySide6.QtCore import QPoint, QRectF, QSize, Qt, Signal
from PySide6.QtGui import QColor, QFont, QPainter, QPainterPath, QPen, QPixmap
from PySide6.QtWidgets import (
    QFrame, QHBoxLayout, QLabel, QProgressBar, QSizePolicy, QToolButton, QVBoxLayout, QWidget,
)

from .i18n import MESSAGE_DRM, MESSAGE_EXISTS, tr
from .icons import icon
from .jobs import ItemStatus, QueueItem
from .presets import get_preset

LINK_COLOR = "#1a73e8"
MUTED_COLOR = "#7a7a7a"
PROGRESS_MAX = 1000


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
    if message == MESSAGE_EXISTS:
        return tr("row.exists")
    return message


def set_state(widget: QWidget, state: str) -> None:
    # QSS [state="..."] se ponovo primjenjuje tek poslije unpolish/polish.
    widget.setProperty("state", state)
    widget.style().unpolish(widget)
    widget.style().polish(widget)


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

        self.progress = QProgressBar()
        self.progress.setObjectName("rowProgress")
        self.progress.setTextVisible(False)
        self.progress.setFixedHeight(4)
        self.progress.setRange(0, PROGRESS_MAX)
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
            self.progress.setRange(0, 0)
        elif item.status == ItemStatus.DONE:
            text = tr("row.exists") if item.message == MESSAGE_EXISTS else tr("row.done")
            if size:
                text += f" · {format_size(size)}"
            self._set_status(text, "done")
            self._set_action("folder", "#5f6368", tr("row.reveal_tip"))
        elif item.status == ItemStatus.FAILED:
            self._set_status(tr("row.failed", message=display_message(item.message)), "failed")
            self._set_action("retry", "#5f6368", tr("row.retry_tip"))
        else:
            self._set_status(tr("row.cancelled"), "muted")
            self._set_action("retry", "#5f6368", tr("row.retry_tip"))

        self.progress.setVisible(active)
        can_play = item.status == ItemStatus.DONE and bool(item.filepath) and os.path.isfile(item.filepath)
        self.play_button.setVisible(can_play)
        self.play_button.setToolTip(tr("row.play_audio") if get_preset(item.preset_key).is_audio else tr("row.play_video"))
        self.remove_button.setToolTip(tr("row.cancel_remove_tip") if active else tr("row.remove_tip"))
        self.status_label.setToolTip(item.filepath or display_message(item.message))

    def show_progress(self, text: str, fraction: float | None) -> None:
        self._set_status(text, "muted")
        if fraction is None:
            self.progress.setRange(0, 0)
        else:
            self.progress.setRange(0, PROGRESS_MAX)
            self.progress.setValue(round(fraction * PROGRESS_MAX))

    def _set_status(self, text: str, state: str) -> None:
        self.status_label.setText(text)
        set_state(self.status_label, state)
        self.status_label.update()

    def _set_action(self, kind: str, color: str, tooltip: str) -> None:
        self.action_button.setIcon(icon(kind, color))
        self.action_button.setToolTip(tooltip)
        self.action_button.setProperty("kind", kind)
