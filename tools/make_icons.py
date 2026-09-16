"""Crta ikone (ekstenzija + prozor aplikacije): bijela strelica nadolje na ljubičastoj podlozi.

Pokretanje: python tools/make_icons.py
"""

import os
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QPointF, QRectF, Qt  # noqa: E402
from PySide6.QtGui import QColor, QGuiApplication, QImage, QPainter, QPainterPath, QPen  # noqa: E402

OUT = Path(__file__).resolve().parent.parent / "extension" / "icons"
ACCENT = QColor("#6c4ce0")


def draw(size: int) -> QImage:
    image = QImage(size, size, QImage.Format.Format_ARGB32)
    image.fill(Qt.GlobalColor.transparent)
    painter = QPainter(image)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    s = size / 16  # crta se u mreži 16x16, pa skalira

    background = QPainterPath()
    background.addRoundedRect(QRectF(0.5 * s, 0.5 * s, 15 * s, 15 * s), 3.5 * s, 3.5 * s)
    painter.fillPath(background, ACCENT)

    pen = QPen(QColor("white"), 1.8 * s)
    pen.setCapStyle(Qt.PenCapStyle.RoundCap)
    pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
    painter.setPen(pen)
    painter.drawLine(QPointF(8 * s, 3.5 * s), QPointF(8 * s, 9.5 * s))
    painter.drawPolyline([QPointF(5 * s, 7 * s), QPointF(8 * s, 10 * s), QPointF(11 * s, 7 * s)])
    painter.drawLine(QPointF(4.5 * s, 12.5 * s), QPointF(11.5 * s, 12.5 * s))
    painter.end()
    return image


if __name__ == "__main__":
    app = QGuiApplication([])
    OUT.mkdir(parents=True, exist_ok=True)
    for size in (16, 32, 48, 128):
        draw(size).save(str(OUT / f"icon{size}.png"))
    print("Ikone:", OUT)
