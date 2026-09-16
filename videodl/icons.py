"""Jednostavne linijske ikone nacrtane u kodu (bez fajlova sa strane)."""

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QIcon, QPainter, QPainterPath, QPen, QPixmap

_SIZE = 48  # crta se na mreži 24x24, uvećano 2x radi oštrine na HiDPI ekranima


def icon(kind: str, color: str = "#ffffff") -> QIcon:
    pixmap = QPixmap(_SIZE, _SIZE)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.scale(_SIZE / 24, _SIZE / 24)
    pen = QPen(QColor(color), 2.2)
    pen.setCapStyle(Qt.PenCapStyle.RoundCap)
    pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
    painter.setPen(pen)
    _DRAW[kind](painter, QColor(color))
    painter.end()
    return QIcon(pixmap)


def _plus(p: QPainter, _color: QColor) -> None:
    p.drawLine(QPointF(12, 5), QPointF(12, 19))
    p.drawLine(QPointF(5, 12), QPointF(19, 12))


def _download(p: QPainter, _color: QColor) -> None:
    p.drawLine(QPointF(12, 4), QPointF(12, 18))
    p.drawPolyline([QPointF(6.5, 12.5), QPointF(12, 18), QPointF(17.5, 12.5)])


def _download_solid(p: QPainter, color: QColor) -> None:
    path = QPainterPath()
    path.addPolygon([QPointF(9.5, 4), QPointF(14.5, 4), QPointF(14.5, 11), QPointF(19, 11),
                     QPointF(12, 19), QPointF(5, 11), QPointF(9.5, 11), QPointF(9.5, 4)])
    p.fillPath(path, color)


def _stop(p: QPainter, color: QColor) -> None:
    path = QPainterPath()
    path.addRoundedRect(QRectF(6.5, 6.5, 11, 11), 1.5, 1.5)
    p.fillPath(path, color)


def _folder(p: QPainter, _color: QColor) -> None:
    path = QPainterPath()
    path.moveTo(3.5, 7)
    path.lineTo(9, 7)
    path.lineTo(11, 9)
    path.lineTo(20.5, 9)
    path.lineTo(20.5, 18.5)
    path.lineTo(3.5, 18.5)
    path.closeSubpath()
    p.drawPath(path)


def _retry(p: QPainter, _color: QColor) -> None:
    p.drawArc(QRectF(5, 5, 14, 14), 60 * 16, 290 * 16)
    p.drawPolyline([QPointF(15.5, 3.5), QPointF(16, 7.2), QPointF(12.3, 7.8)])


def _close(p: QPainter, _color: QColor) -> None:
    p.drawLine(QPointF(7, 7), QPointF(17, 17))
    p.drawLine(QPointF(17, 7), QPointF(7, 17))


_DRAW = {
    "plus": _plus,
    "download": _download,
    "download-solid": _download_solid,
    "stop": _stop,
    "folder": _folder,
    "retry": _retry,
    "close": _close,
}
