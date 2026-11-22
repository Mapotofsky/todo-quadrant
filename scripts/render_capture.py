"""离屏渲染截图：验证四象限布局、配色、任务状态（完成/逾期/目录）渲染正确。"""
import os
import sys

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _ROOT)

os.environ["QT_QPA_PLATFORM"] = "offscreen"
_DB = os.path.join(_ROOT, "render_todo.db")
if os.path.exists(_DB):
    os.remove(_DB)
os.environ["TODO_QUADRANT_DB"] = _DB

from PyQt5.QtWidgets import QApplication  # noqa: E402
from PyQt5.QtCore import QTimer  # noqa: E402

from app import db  # noqa: E402
from app.ui.floating_window import FloatingWindow  # noqa: E402


def seed():
    db.init()
    db.add_task("写周报", note="周五前提交", important=1, urgent=1, due_at="2099-01-01 10:00")
    db.add_task("准备评审材料", important=1, urgent=0)
    db.add_task("回复客户邮件", important=0, urgent=1, due_at="2000-01-01 09:00")  # 已逾期
    db.add_task("整理桌面文件", important=0, urgent=0, dir_path="/home/ZGYD")
    tid = db.add_task("已完成示例", important=1, urgent=1)
    db.set_done(tid, True)


def main():
    app = QApplication([])
    style = os.path.join(_ROOT, "resources", "style.qss")
    if os.path.exists(style):
        with open(style, encoding="utf-8") as f:
            app.setStyleSheet(f.read())
    seed()
    win = FloatingWindow()
    win.resize(700, 500)
    win.show()

    def capture():
        pix = win.grab()
        out = os.path.join(_ROOT, "render_preview.png")
        pix.save(out, "PNG")
        print(f"SAVED {out} {pix.width()}x{pix.height()}")
        app.quit()

    QTimer.singleShot(600, capture)
    app.exec_()


if __name__ == "__main__":
    main()
