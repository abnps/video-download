"""Izgled „Sada i sljedeće" (Ahmed 8.11.2026, za 1.0.9): kartica „Sada preuzima", pozadina kao na sajtu i
grafikon brzine. Bez logike preuzimanja: prozor (gui.py) samo javlja šta trenutno radi.
"""

from PySide6.QtCore import QPointF, QRectF, QSize, Qt, Signal
from PySide6.QtGui import QColor, QLinearGradient, QPainter, QPainterPath, QPen, QPixmap, QRadialGradient
from PySide6.QtWidgets import QFrame, QGridLayout, QHBoxLayout, QLabel, QToolButton, QVBoxLayout, QWidget

from . import theme
from .download import PROCESSING, Progress
from .gui_util import format_eta, format_speed
from .i18n import tr
from .icons import icon
from .jobs import QueueItem
from .presets import get_preset
from .widgets import AnimatedProgress, ElidedLabel, Thumbnail, format_duration, set_state

SPARK_POINTS = 40  # koliko posljednjih brzina grafikon pamti


class BloomBackground(QWidget):
    """Pozadina prozora kao na sajtu: osnovna boja i tri blaga obojena „oblaka" (bez animacije, ne troši CPU)."""

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        rect = QRectF(self.rect())
        painter.fillRect(rect, QColor(theme.c("bg")))
        alpha = 46 if theme.is_dark() else 70
        for key, (fx, fy), (rx, ry) in (("bloom1", (0.12, 0.0), (0.55, 0.45)),
                                        ("bloom2", (0.92, 0.04), (0.45, 0.40)),
                                        ("bloom3", (0.62, 1.02), (0.55, 0.45))):
            center = QPointF(rect.width() * fx, rect.height() * fy)
            radius = max(rect.width() * rx, rect.height() * ry)
            gradient = QRadialGradient(center, radius)
            color = QColor(theme.c(key))
            color.setAlpha(alpha)
            gradient.setColorAt(0.0, color)
            color.setAlpha(0)
            gradient.setColorAt(1.0, color)
            painter.fillRect(rect, gradient)


class Sparkline(QWidget):
    """Mali grafikon brzine preuzimanja (posljednjih nekoliko desetina očitavanja)."""

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.setMinimumSize(80, 30)
        self.values: list[float] = []

    def add(self, value: float) -> None:
        self.values.append(max(0.0, float(value)))
        del self.values[:-SPARK_POINTS]
        self.update()

    def clear(self) -> None:
        self.values.clear()
        self.update()

    def paintEvent(self, event) -> None:
        if len(self.values) < 2:
            return
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        top = max(self.values) or 1.0
        width, height = self.width() - 2, self.height() - 4
        step = width / (SPARK_POINTS - 1)
        start = width - step * (len(self.values) - 1)
        points = [QPointF(1 + start + i * step, 2 + height - height * v / top) for i, v in enumerate(self.values)]
        line = QPainterPath(points[0])
        for point in points[1:]:
            line.lineTo(point)
        area = QPainterPath(line)
        area.lineTo(points[-1].x(), self.height())
        area.lineTo(points[0].x(), self.height())
        area.closeSubpath()
        fill = QLinearGradient(0, 0, 0, self.height())
        accent = QColor(theme.c("accent2"))
        accent.setAlpha(60)
        fill.setColorAt(0.0, accent)
        accent.setAlpha(0)
        fill.setColorAt(1.0, accent)
        painter.fillPath(area, fill)
        painter.setPen(QPen(QColor(theme.c("accent2")), 1.6))
        painter.drawPath(line)


class NowPanel(QFrame):
    """Kartica iznad liste: video koji se upravo preuzima, velika traka s fazama, brzina, vrijeme i grafikon."""

    stop_clicked = Signal(int)  # isto kao dugme „zaustavi" u redu tog videa

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.setObjectName("nowPanel")
        self.item_id: int | None = None
        self._audio = False
        self._phase = ""

        box = QVBoxLayout(self)
        box.setContentsMargins(16, 12, 16, 12)
        box.setSpacing(10)

        top = QHBoxLayout()
        self.chip = QLabel()
        self.chip.setObjectName("nowChip")
        top.addWidget(self.chip)
        top.addStretch(1)
        self.queue_label = QLabel()
        self.queue_label.setObjectName("nowMuted")
        top.addWidget(self.queue_label)
        box.addLayout(top)

        body = QGridLayout()
        body.setHorizontalSpacing(16)
        body.setVerticalSpacing(4)
        self.thumbnail = Thumbnail()
        self.thumbnail.setFixedSize(144, 81)
        body.addWidget(self.thumbnail, 0, 0, 4, 1, Qt.AlignmentFlag.AlignTop)
        self.title = ElidedLabel()
        self.title.setObjectName("nowTitle")
        body.addWidget(self.title, 0, 1)
        self.meta = ElidedLabel()
        self.meta.setObjectName("nowMuted")
        body.addWidget(self.meta, 1, 1)
        self.progress = AnimatedProgress(bar=10)
        self.progress.setObjectName("nowProgress")
        body.addWidget(self.progress, 2, 1)
        phases = QHBoxLayout()
        phases.setSpacing(14)
        self.phase_labels: dict[str, QLabel] = {}
        for key in ("video", "audio", "merge", "convert"):
            label = QLabel()
            label.setObjectName("nowPhase")
            self.phase_labels[key] = label
            phases.addWidget(label)
        phases.addStretch(1)
        self.percent = QLabel()
        self.percent.setObjectName("nowPercent")
        phases.addWidget(self.percent)
        body.addLayout(phases, 3, 1)
        body.setColumnStretch(1, 1)
        box.addLayout(body)

        line = QFrame()
        line.setObjectName("nowDivider")
        box.addWidget(line)
        stats = QHBoxLayout()
        stats.setSpacing(18)
        self.speed_caption, self.speed = self._stat(stats)
        self.eta_caption, self.eta = self._stat(stats)
        self.spark = Sparkline()
        stats.addWidget(self.spark, 1)
        self.stop_button = QToolButton()
        self.stop_button.setObjectName("rowAction")
        self.stop_button.setIconSize(QSize(20, 20))
        self.stop_button.setFixedSize(34, 34)
        self.stop_button.clicked.connect(lambda: self.item_id is not None and self.stop_clicked.emit(self.item_id))
        stats.addWidget(self.stop_button, 0, Qt.AlignmentFlag.AlignVCenter)
        box.addLayout(stats)

        self.retranslate()
        self.hide()

    @staticmethod
    def _stat(layout: QHBoxLayout) -> tuple[QLabel, QLabel]:
        column = QVBoxLayout()
        column.setSpacing(0)
        caption = QLabel()
        caption.setObjectName("nowCaption")
        value = QLabel("—")
        value.setObjectName("nowValue")
        column.addWidget(caption)
        column.addWidget(value)
        layout.addLayout(column)
        return caption, value

    def retranslate(self) -> None:
        self.chip.setText(tr("now.title"))
        for key, label in self.phase_labels.items():
            label.setText(tr(f"now.phase.{key}"))
        self.speed_caption.setText(tr("now.speed"))
        self.eta_caption.setText(tr("now.eta"))
        self.stop_button.setIcon(icon("stop", theme.c("icon")))
        self.stop_button.setToolTip(tr("row.stop_tip"))

    # ---------- podaci ----------

    def show_item(self, item: QueueItem, pixmap: QPixmap | None, waiting: int) -> None:
        """Prikaži stavku (isti red kao u listi); nova stavka briše traku i grafikon."""
        self.queue_label.setText(tr("now.queue", waiting=waiting) if waiting else "")
        if item.id != self.item_id:
            self.item_id = item.id
            preset = get_preset(item.preset_key)
            self._audio = preset.is_audio
            self.title.setText(item.title or item.url)
            self.title.setToolTip(item.title or item.url)
            parts = [preset.short_label]
            if item.duration:
                parts.append(format_duration(item.duration))
            self.meta.setText(" · ".join(parts))
            self.thumbnail.set_seed(item.title or item.url)
            self.thumbnail.set_duration("")
            self.progress.reset()
            self.progress.set_fraction(None)
            self.percent.setText("")
            self.speed.setText("—")
            self.eta.setText("—")
            self.spark.clear()
            self.phase_labels["video"].setVisible(not self._audio)
            self.phase_labels["merge"].setVisible(not self._audio)
            self.phase_labels["convert"].setVisible(self._audio)
            self._set_phase("audio" if self._audio else "video")
        if pixmap is not None:
            self.thumbnail.set_pixmap(pixmap)
        self.show()

    def set_pixmap(self, item_id: int, pixmap: QPixmap) -> None:
        if item_id == self.item_id:
            self.thumbnail.set_pixmap(pixmap)

    def update_progress(self, item_id: int, progress: Progress) -> None:
        if item_id != self.item_id:
            return
        if progress.phase == PROCESSING:
            self._set_phase("convert" if self._audio else "merge")
            self.progress.set_fraction(None)
            self.percent.setText("")
            self.eta.setText("—")
            return
        audio = self._audio or progress.label == "progress.audio"
        self._set_phase("audio" if audio else "video")
        self.progress.set_fraction(progress.fraction, "audio" if audio else "video")
        self.percent.setText(f"{progress.fraction:.0%}" if progress.fraction is not None else "")
        if progress.speed:
            self.speed.setText(format_speed(progress.speed))
            self.spark.add(progress.speed)
        self.eta.setText(format_eta(progress.eta) if progress.eta is not None else "—")

    def clear(self) -> None:
        self.item_id = None
        self.progress.reset()
        self.spark.clear()
        self.hide()

    def _set_phase(self, key: str) -> None:
        self._phase = key
        for name, label in self.phase_labels.items():
            set_state(label, "on" if name == key else "")
