"""对话框样式验证：离屏渲染删除确认框 + 任务编辑框，确认深色主题生效。"""
import os
import sys

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _ROOT)
os.environ["QT_QPA_PLATFORM"] = "offscreen"
os.environ["TODO_QUADRANT_DB"] = os.path.join(_ROOT, "dlg_test.db")
if os.path.exists(os.environ["TODO_QUADRANT_DB"]):
    os.remove(os.environ["TODO_QUADRANT_DB"])

from PyQt5.QtWidgets import QApplication, QMessageBox  # noqa: E402
from PyQt5.QtCore import QTimer  # noqa: E402

from app import db  # noqa: E402
from app.ui.task_dialog import TaskDialog  # noqa: E402


def main():
    app = QApplication([])
    with open(os.path.join(_ROOT, "resources", "style.qss"), encoding="utf-8") as f:
        app.setStyleSheet(f.read())
    db.init()
    tid = db.add_task("测试任务", note="备注内容", important=1, urgent=1,
                      dir_path="/home/ZGYD", due_at="2026-11-25 18:00")

    # 1) 删除确认框（与 delete_task 中一致）
    box = QMessageBox()
    box.setWindowTitle("删除")
    box.setText(f"删除任务「测试任务」？")
    box.setIcon(QMessageBox.Question)
    box.addButton("删除", QMessageBox.YesRole)
    box.addButton("取消", QMessageBox.NoRole)
    box.show()

    # 2) 任务编辑框
    task = db.get_task(tid)
    dlg = TaskDialog(task=task)
    dlg.show()
    dlg.move(340, 60)

    def cap():
        box.adjustSize()
        box.grab().save(os.path.join(_ROOT, "dlg_confirm.png"))
        dlg.grab().save(os.path.join(_ROOT, "dlg_task.png"))
        app.quit()

    QTimer.singleShot(1200, cap)
    app.exec_()
    print("DLG_OK")


if __name__ == "__main__":
    main()
