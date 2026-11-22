"""真实 xcb 截图：以用户 DB 副本启动应用，抓取真实窗口外观。"""
import os
import sys
import shutil

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _ROOT)
os.environ["QT_QPA_PLATFORM"] = "xcb"

# 用用户真实 DB 的副本，避免提醒器等写入真实数据
SRC = os.path.expanduser("~/.config/todo-quadrant/todo.db")
COPY = os.path.join(_ROOT, "real_capture.db")
if os.path.exists(SRC):
    shutil.copyfile(SRC, COPY)
os.environ["TODO_QUADRANT_DB"] = COPY

from PyQt5.QtWidgets import QApplication  # noqa: E402
from PyQt5.QtCore import QTimer  # noqa: E402

from app import db  # noqa: E402
from app.ui.floating_window import FloatingWindow  # noqa: E402


def main():
    app = QApplication([])
    with open(os.path.join(_ROOT, "resources", "style.qss"), encoding="utf-8") as f:
        app.setStyleSheet(f.read())
    db.init()
    win = FloatingWindow()
    win.show()

    def capture():
        screen = app.primaryScreen()
        pix = screen.grabWindow(int(win.winId()))
        out = os.path.join(_ROOT, "real_preview.png")
        pix.save(out, "PNG")
        print(f"SAVED {out} {pix.width()}x{pix.height()} geom={win.geometry().getRect()}")
        app.quit()

    QTimer.singleShot(1500, capture)
    app.exec_()


if __name__ == "__main__":
    main()
