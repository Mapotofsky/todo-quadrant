"""真实 xcb 验证生产路径的删除确认框（自定义 MessageDialog，含按钮区）。"""
import os
import sys

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _ROOT)
os.environ["QT_QPA_PLATFORM"] = "xcb"
os.environ["TODO_QUADRANT_DB"] = os.path.join(_ROOT, "del_test.db")
if os.path.exists(os.environ["TODO_QUADRANT_DB"]):
    os.remove(os.environ["TODO_QUADRANT_DB"])

from PyQt5.QtWidgets import QApplication, QPushButton  # noqa: E402
from PyQt5.QtCore import QTimer  # noqa: E402

from app import db  # noqa: E402
from app.ui.floating_window import FloatingWindow  # noqa: E402


def main():
    app = QApplication([])
    app.setStyle("fusion")
    with open(os.path.join(_ROOT, "resources", "style.qss"), encoding="utf-8") as f:
        app.setStyleSheet(f.read())
    db.init()
    tid = db.add_task("df", important=1, urgent=1)

    win = FloatingWindow()
    win.show()

    def trigger():
        # 与点 ✕ 相同的生产路径；delete_task 内部会 exec_() 阻塞
        QTimer.singleShot(900, grab_and_close)
        win.quadrant.delete_task(tid)

    def grab_and_close():
        box = QApplication.activeModalWidget()
        if box is None:
            print("NO_MODAL")
            app.quit()
            return
        pix = box.grab()
        out = os.path.join(_ROOT, "delete_real.png")
        pix.save(out, "PNG")
        print(f"SAVED {out} {pix.width()}x{pix.height()}")
        # 点「取消」关闭，不真删
        for b in box.findChildren(QPushButton):
            if b.text() == "取消":
                b.click()
                break
        QTimer.singleShot(300, app.quit)

    QTimer.singleShot(1200, trigger)
    app.exec_()


if __name__ == "__main__":
    main()
