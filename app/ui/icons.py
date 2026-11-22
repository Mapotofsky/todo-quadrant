"""用 Qt 绘制两端共用的操作图标。"""
from PyQt5.QtCore import QPointF, QRectF, QSize, Qt
from PyQt5.QtGui import QColor, QIcon, QPainter, QPen, QPixmap, QPolygonF
from PyQt5.QtWidgets import QPushButton


def icon_button(icon, label, name):
    button = QPushButton()
    button.setObjectName(name)
    button.setToolTip(label)
    button.setAccessibleName(label)
    button.setFixedSize(26, 26)
    button.setIconSize(QSize(16, 16))
    pixmap = QPixmap(32, 32)
    pixmap.setDevicePixelRatio(2)
    pixmap.fill(Qt.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.Antialiasing)
    color = QColor("#e6e8f0")
    painter.setPen(QPen(color, 1.35, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
    if icon == "folder":
        painter.drawPolygon(QPolygonF([
            QPointF(1.5, 4), QPointF(6.5, 4), QPointF(8, 6),
            QPointF(14.5, 6), QPointF(14.5, 13), QPointF(1.5, 13),
        ]))
    elif icon == "more":
        painter.setBrush(color)
        for x in (3, 8, 13):
            painter.drawEllipse(QPointF(x, 8), 0.6, 0.6)
    elif icon == "settings":
        for y, x in ((3, 6), (8, 10), (13, 5)):
            painter.drawLine(QPointF(1.5, y), QPointF(x - 2, y))
            painter.drawLine(QPointF(x + 2, y), QPointF(14.5, y))
            painter.drawEllipse(QRectF(x - 2, y - 2, 4, 4))
    elif icon == "collapse":
        painter.drawLine(QPointF(3, 8), QPointF(13, 8))
    elif icon == "add":
        painter.drawLine(QPointF(3, 8), QPointF(13, 8))
        painter.drawLine(QPointF(8, 3), QPointF(8, 13))
    painter.end()
    button.setIcon(QIcon(pixmap))
    return button
