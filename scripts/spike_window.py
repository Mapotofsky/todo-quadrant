"""最小验证：在真实桌面确认「置顶 + 半透明 + 无边框 + 拖动」。

用法：/usr/bin/python3 scripts/spike_window.py
验证点：
  1) 窗口是否始终压在其它窗口之上；
  2) 背景是否为半透明圆角（能透出下面桌面/窗口）；
  3) 按住窗口任意处能否拖动；
  4) 右键 → 退出。
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

os.environ["QT_QPA_PLATFORM"] = os.environ.get("TODO_QUADRANT_QPA", "xcb")
os.environ.setdefault("QT_ENABLE_HIGHDPI_SCALING", "1")
os.environ.setdefault("QT_AUTO_SCREEN_SCALE_FACTOR", "1")
if "TODO_QUADRANT_SCALE" in os.environ:
    os.environ["QT_SCALE_FACTOR"] = os.environ["TODO_QUADRANT_SCALE"]
os.environ.setdefault("LIBGL_ALWAYS_SOFTWARE", "1")

from PyQt5.QtCore import Qt  # noqa: E402
from PyQt5.QtWidgets import (  # noqa: E402
    QApplication, QWidget, QVBoxLayout, QFrame, QLabel, QMenu,
)


class Spike(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self._drag = None

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        box = QFrame()
        box.setObjectName("spike")
        outer.addWidget(box)
        lay = QVBoxLayout(box)
        lbl = QLabel("置顶 + 半透明 测试\n（按住拖动 · 右键退出）")
        lbl.setAlignment(Qt.AlignCenter)
        lbl.setObjectName("spike_label")
        lay.addWidget(lbl)
        self.setStyleSheet(
            "QFrame#spike { background-color: rgba(224, 78, 78, 190); border-radius: 14px; }"
            "QLabel#spike_label { color: #fff; font-size: 15px; font-weight: 600; }"
        )

    def mousePressEvent(self, e):
        if e.button() == Qt.LeftButton:
            self._drag = e.globalPos() - self.frameGeometry().topLeft()

    def mouseMoveEvent(self, e):
        if e.buttons() & Qt.LeftButton and self._drag is not None:
            self.move(e.globalPos() - self._drag)

    def mouseReleaseEvent(self, e):
        self._drag = None

    def contextMenuEvent(self, e):
        m = QMenu(self)
        m.addAction("退出", QApplication.instance().quit)
        m.exec_(e.globalPos())


def main():
    app = QApplication(sys.argv)
    w = Spike()
    w.resize(280, 130)
    w.move(120, 120)
    w.show()
    return app.exec_()


if __name__ == "__main__":
    sys.exit(main())
