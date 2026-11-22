"""无头冒烟测试：用 offscreen 平台验证数据层、AI 解析、提醒与 UI 构造。"""
import os
import sys
from tempfile import TemporaryDirectory

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt5.QtWidgets import QApplication  # noqa: E402
from app import db  # noqa: E402
from app import config  # noqa: E402
from app import ai  # noqa: E402
from app.remind import is_overdue  # noqa: E402
from app.ui.floating_window import FloatingWindow  # noqa: E402
from app.ui.quadrant_view import quadrant_of  # noqa: E402
from app.ui.task_dialog import TaskDialog  # noqa: E402
from app.ui.ai_dialog import AiDialog  # noqa: E402
from app.ui.settings_dialog import SettingsDialog  # noqa: E402


def main():
    app = QApplication([])
    db.init()

    # ---- 数据层（含截止时间）----
    tid = db.add_task("写周报", note="周五前", important=1, urgent=1, due_at="2099-01-01 10:00")
    assert db.get_task(tid)["title"] == "写周报"
    assert db.get_task(tid)["due_at"] == "2099-01-01 10:00"
    db.update_task(tid, note="周五下班前")
    assert db.get_task(tid)["note"] == "周五下班前"
    db.update_task(tid, dir_path="/tmp")
    assert db.get_task(tid)["dir_path"] == "/tmp"

    db.set_reminded(tid, 1)
    assert db.get_task(tid)["reminded"] == 1
    db.update_task(tid, due_at="2099-01-02 10:00")  # 改期应重置提醒
    assert db.get_task(tid)["reminded"] == 0

    # ---- 象限映射 ----
    assert quadrant_of(1, 1) == 0
    assert quadrant_of(1, 0) == 1
    assert quadrant_of(0, 1) == 2
    assert quadrant_of(0, 0) == 3

    # ---- 截止判断 ----
    assert is_overdue("2000-01-01 00:00") is True
    assert is_overdue("2999-01-01 00:00") is False
    assert is_overdue(None) is False

    # ---- AI 解析（无网络）----
    r = ai.parse_content('{"title":"买菜","note":"去超市","important":true,"urgent":false,"due_at":null}')
    assert r["title"] == "买菜" and r["important"] is True and r["urgent"] is False and r["due_at"] is None
    r2 = ai.parse_content('前面废话 {"title":"写报告","important":false,"urgent":true} 后面')
    assert r2["title"] == "写报告" and r2["urgent"] is True
    r3 = ai.parse_content("just a plain title no json")
    assert r3["title"] == "just a plain title no json"

    # ---- 配置 ----
    assert config.get_ai_config()["base_url"] == config.DEFAULT_BASE_URL
    config.set_ai_config("http://x/v1", "k", "m")
    assert config.get_ai_config()["api_key"] == "k"

    # ---- 悬浮窗构造 + 分区加载 ----
    win = FloatingWindow()
    win.show()
    db.add_task("A", important=1, urgent=1)
    db.add_task("B", important=1, urgent=0)
    db.add_task("C", important=0, urgent=1)
    db.add_task("D", important=0, urgent=0)
    win.quadrant.reload()
    assert win.quadrant.lists[0].count() == 2  # 写周报 + A
    assert win.quadrant.lists[1].count() == 1  # B
    assert win.quadrant.lists[2].count() == 1  # C
    assert win.quadrant.lists[3].count() == 1  # D

    # ---- 跨象限移动 ----
    win.quadrant.move_task_to_quadrant(tid, 2)
    assert db.get_task(tid)["important"] == 0
    assert db.get_task(tid)["urgent"] == 1

    # ---- 完成切换 ----
    db.set_done(tid, True)
    assert db.get_task(tid)["done"] == 1
    db.set_done(tid, False)
    assert db.get_task(tid)["done"] == 0

    # ---- 对话框（含 AI 预填 + 截止）----
    dlg = TaskDialog(default_quadrant=0)
    dlg.title_edit.setText("测试")
    assert dlg.result_data()["title"] == "测试"
    assert dlg.result_data()["important"] == 1
    assert dlg.result_data()["urgent"] == 1

    dlg2 = TaskDialog(prefill={"title": "预填", "note": "n", "important": 1, "urgent": 0, "due_at": "2099-05-05 08:30"})
    assert dlg2.result_data()["title"] == "预填"
    assert dlg2.result_data()["due_at"] == "2099-05-05 08:30"
    assert dlg2.result_data()["important"] == 1

    # ---- 任务行内按钮确实触发动作（📁 / ✎ / ✕）----
    from app.ui.task_row import TaskRow

    class _Dummy:
        def __init__(self):
            self.opened = None
            self.edited = None
            self.deleted = None

        def open_dir(self, p):
            self.opened = p

        def edit_task(self, i):
            self.edited = i

        def delete_task(self, i):
            self.deleted = i

        def toggle_done(self, i, d):
            pass

        def handle_drop(self, i, p):
            pass

    ctrl = _Dummy()
    row = TaskRow({"id": 7, "title": "t", "note": "", "important": 1, "urgent": 1,
                   "dir_path": "/tmp", "due_at": None, "done": 0, "sort_order": 0}, ctrl)
    assert hasattr(row, "folder_btn")
    row.folder_btn.click()
    assert ctrl.opened == "/tmp"
    row.edit_btn.click()
    assert ctrl.edited == 7
    row.del_btn.click()
    assert ctrl.deleted == 7
    row_nodir = TaskRow({"id": 8, "title": "t2", "note": "", "important": 0, "urgent": 0,
                         "dir_path": None, "due_at": None, "done": 0, "sort_order": 0}, ctrl)
    assert not hasattr(row_nodir, "folder_btn")

    AiDialog()
    SettingsDialog()

    # ---- 收起/展开状态机 + 展开尺寸不被收起污染 ----
    win.resize(620, 440)
    win._save_state()
    win._apply_collapsed(True)
    assert win.collapsed is True
    collapsed_h = win.height()
    assert collapsed_h < 200  # 收起后确实变小
    win._save_state()  # 收起态保存不得污染展开尺寸
    assert int(db.get_setting("window_w")) >= 520
    assert int(db.get_setting("window_h")) >= 340
    win._apply_collapsed(False)
    assert win.collapsed is False
    assert win.width() >= 520 and win.height() >= 340
    assert win.width() == 620 and win.height() == 440  # 内存中恢复了原展开尺寸

    # 毒化的小尺寸在下次启动时会被钳位自愈（显式以展开态恢复）
    db.set_setting("window_w", 300)
    db.set_setting("window_h", 193)
    db.set_setting("collapsed", "0")
    win2 = FloatingWindow()
    assert win2.collapsed is False
    assert win2.width() >= 520 and win2.height() >= 340
    win2.close()

    print("SMOKE OK")


if __name__ == "__main__":
    with TemporaryDirectory() as directory:
        os.environ["TODO_QUADRANT_DB"] = os.path.join(directory, "todo.db")
        main()
