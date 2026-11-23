"""无头冒烟测试：用 offscreen 平台验证数据层、AI 解析、提醒与 UI 构造。"""
import os
import sys
from contextlib import closing
from datetime import datetime
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt5.QtCore import Qt  # noqa: E402
from PyQt5.QtTest import QTest  # noqa: E402
from PyQt5.QtWidgets import QApplication, QLabel  # noqa: E402
from app import archive  # noqa: E402
from app import db  # noqa: E402
from app import config  # noqa: E402
from app import ai  # noqa: E402
from app.remind import deadline_status, is_overdue  # noqa: E402
from app.ui.floating_window import FloatingWindow, collapsed_preview  # noqa: E402
from app.ui.quadrant_view import quadrant_of  # noqa: E402
from app.ui.task_dialog import TaskDialog  # noqa: E402
from app.ui.ai_dialog import AiDialog  # noqa: E402
from app.ui.settings_dialog import SettingsDialog  # noqa: E402


def check_preview():
    tomorrow = "2099-01-04 09:00"
    earlier = "2000-01-01 09:00"
    later = "2000-01-02 09:00"

    def task(title, due_at, important=0, urgent=0, done=0):
        return dict(title=title, due_at=due_at, important=important, urgent=urgent, done=done)

    no_date = task("无日期", None, 1, 1)
    done = task("已完成", earlier, 1, 1, 1)
    urgent = task("紧急", later, urgent=1)
    priority = task("重要且紧急", tomorrow, 1, 1)
    tie = task("同日期第二条", tomorrow, 1, 1)
    other = task("其余组最早", earlier)
    assert collapsed_preview([done, no_date, urgent, priority, tie]) == ("重要且紧急", tomorrow)
    assert collapsed_preview([no_date, done, other, urgent]) == ("紧急", later)
    assert collapsed_preview([urgent, task("紧急组更早", earlier, urgent=1)]) == ("紧急组更早", earlier)
    assert collapsed_preview([task("重要不紧急", later, important=1), other]) == ("其余组最早", earlier)
    assert collapsed_preview([priority, task("同组更早到期", later, 1, 1)]) == ("同组更早到期", later)
    assert collapsed_preview([no_date, done]) == ("1 项待办", None)
    assert collapsed_preview([done]) == ("暂无待办", None)
    hidden = dict(priority, hide_when_collapsed=True)
    assert collapsed_preview([hidden, urgent]) == ("紧急", later)
    assert collapsed_preview([hidden, no_date]) == ("2 项待办", None)
    assert deadline_status(later, now=datetime(2000, 1, 4, 9)) == ("逾期 2 天", True)
    assert deadline_status(later, now=datetime(2000, 1, 2, 8, 59))[1] is False
    assert deadline_status(later, now=datetime(2000, 1, 2, 9))[1] is True


def check_task_migration():
    with TemporaryDirectory() as directory, patch.dict(
        os.environ, TODO_QUADRANT_DB=os.path.join(directory, "old.db")
    ):
        with closing(db.connect()) as conn, conn:
            conn.executescript("""
                CREATE TABLE tasks (
                    id INTEGER PRIMARY KEY, title TEXT NOT NULL, note TEXT DEFAULT '',
                    important INTEGER NOT NULL DEFAULT 0, urgent INTEGER NOT NULL DEFAULT 0,
                    dir_path TEXT, due_at TEXT, done INTEGER NOT NULL DEFAULT 0,
                    reminded INTEGER NOT NULL DEFAULT 0, sort_order INTEGER NOT NULL DEFAULT 0,
                    created_at TEXT NOT NULL, completed_at TEXT
                );
                INSERT INTO tasks (title, created_at, due_at)
                VALUES ('旧任务', '2026-01-01T09:00:00', '2026-01-02 09:00');
            """)
        db.init()
        task = db.get_task(1)
        assert task["created_at"] == "2026-01-01T09:00:00"
        assert task["hide_when_collapsed"] == 0
        assert collapsed_preview([task]) == ("旧任务", "2026-01-02 09:00")
        db.update_task(1, hide_when_collapsed=True)
        db.init()
        assert db.get_task(1)["hide_when_collapsed"] == 1


def check_archive():
    with TemporaryDirectory() as directory, patch.dict(
        os.environ, TODO_QUADRANT_DB=os.path.join(directory, "todo.db")
    ):
        db.init()
        export_dir = Path(directory) / "归档"
        export_dir.mkdir()
        settings = SettingsDialog()
        assert settings.archive_dir.text() == ""
        settings.archive_dir.setText(str(export_dir))
        settings.save()
        reopened = SettingsDialog()
        assert reopened.archive_dir.text() == str(export_dir)
        pending = db.add_task("进行中")
        later = db.add_task("稍晚完成", urgent=1, hide_when_collapsed=True)
        early = db.add_task("先完成", note="第一行\n第二行", important=1, urgent=1,
                            dir_path="/work", due_at="2026-01-01 10:00")
        tied = db.add_task("同一时刻完成", important=1)
        next_day = db.add_task("次日完成")
        for task_id, timestamp in (
            (later, "2026-01-01T10:00:00.000002"), (early, "2026-01-01T10:00:00.000001"),
            (tied, "2026-01-01T10:00:00.000001"), (next_day, "2026-01-02T10:00:00"),
        ):
            with patch("app.db._now", return_value=timestamp):
                db.set_done(task_id, True)

        window = FloatingWindow()
        assert window.archive_btn.isEnabled()
        with patch("app.ui.floating_window.confirm", return_value=False):
            window.archive_btn.click()
        assert not list(export_dir.iterdir())

        with patch("app.ui.floating_window.confirm", return_value=True), \
                patch("app.ui.floating_window.warn") as message:
            with patch("pathlib.Path.replace", side_effect=PermissionError("文件发布失败")):
                window.archive_btn.click()
                assert message.call_args.args[1] == "归档失败"
            assert not list(export_dir.iterdir())
            assert len(db.list_tasks()) == 5
            window.archive_btn.click()
            assert message.call_args.args[1] == "归档完成"
        assert not window.archive_btn.isEnabled()
        assert sum(lst.count() for lst in window.quadrant.lists.values()) == 1
        assert [task["id"] for task in db.list_tasks()] == [pending]
        first, = export_dir.glob("*.md")
        assert first.read_text(encoding="utf-8") == (
            "# 已完成\n\n## 2026-01-01\n\n### 先完成\n\n重要·紧急\n\n"
            "第一行\n第二行\n\n/work\n\n2026-01-01 10:00\n\n"
            "### 同一时刻完成\n\n重要·不紧急\n\n### 稍晚完成\n\n不重要·紧急\n\n"
            "## 2026-01-02\n\n### 次日完成\n\n不重要·不紧急\n"
        )
        assert archive.archive_completed(export_dir) is None

        db.set_done(pending, True)
        with closing(db.connect()) as conn, conn:
            conn.execute("""
                CREATE TRIGGER reject_delete BEFORE DELETE ON tasks
                BEGIN SELECT RAISE(ABORT, 'delete failed'); END;
            """)
        try:
            archive.archive_completed(export_dir)
        except archive.ArchiveCommitError as exc:
            second = exc.path
            assert second.is_file() and second != first
        else:
            raise AssertionError("应报告已生成的归档文件")
        assert db.get_task(pending)["done"] == 1
        with closing(db.connect()) as conn, conn:
            conn.execute("DROP TRIGGER reject_delete")
        third = archive.archive_completed(export_dir)
        assert len({first, second, third}) == 3
        assert all(path.is_file() for path in (first, second, third))
        assert not db.list_tasks()
        window.close()


def main():
    app = QApplication([])
    db.init()
    check_preview()
    check_task_migration()
    check_archive()

    # ---- 数据层（含截止时间）----
    tid = db.add_task("写周报", note="周五前", important=1, urgent=1, due_at="2099-01-01 10:00")
    created = db.get_task(tid)["created_at"]
    assert datetime.fromisoformat(created)
    assert db.get_task(tid)["title"] == "写周报"
    assert db.get_task(tid)["due_at"] == "2099-01-01 10:00"
    db.update_task(tid, note="周五下班前")
    assert db.get_task(tid)["note"] == "周五下班前"
    assert db.get_task(tid)["created_at"] == created
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
    win.setWindowFlags((win.windowFlags() & ~Qt.WindowType_Mask) | Qt.Window)
    win.show()
    app.processEvents()
    app.setActiveWindow(win)
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

    # ---- 键盘完成后跟随任务，原组内次序保持 ----
    app.processEvents()
    lst = win.quadrant.lists[2]
    c_id = lst.item(0).data(Qt.UserRole)
    app.setActiveWindow(win)
    win.quadrant.focus_task(tid)
    assert win.focusWidget() is lst, (win.focusWidget(), app.focusWidget())
    with patch("app.db._now", return_value="2026-01-01T10:00:00.000001") as clock:
        QTest.keyClick(lst, Qt.Key_Space)
        clock.assert_called_once_with("microseconds")
    app.processEvents()
    assert db.get_task(tid)["done"] == 1
    assert db.get_task(tid)["completed_at"] == "2026-01-01T10:00:00.000001"
    assert win.focusWidget() is lst and lst.currentItem().data(Qt.UserRole) == tid, (
        app.activeWindow(), app.focusWidget(), lst.currentRow(), lst.currentItem().data(Qt.UserRole))
    assert lst.item(0).data(Qt.UserRole) == c_id
    assert win.quadrant.headers[2].count.text() == "待办 1"
    QTest.keyClick(lst, Qt.Key_Space)
    app.processEvents()
    assert db.get_task(tid)["done"] == 0
    assert db.get_task(tid)["completed_at"] is None
    edited = TaskDialog(task=db.get_task(tid))
    assert "未完成" in {label.text() for label in edited.findChildren(QLabel)}
    row = lst.itemWidget(lst.currentItem())
    with patch("app.db._now", return_value="2026-01-01T10:00:00.000002"):
        row.check.click()
    app.processEvents()
    updated = db.get_task(tid)
    assert updated["completed_at"] == "2026-01-01T10:00:00.000002"
    edited = TaskDialog(task=updated)
    labels = {label.text() for label in edited.findChildren(QLabel)}
    assert {created.replace("T", " "), "2026-01-01 10:00:00"} <= labels
    db.set_done(tid, False)
    win.quadrant.reload()

    # ---- 对话框（含 AI 预填 + 截止）----
    dlg = TaskDialog(default_quadrant=0)
    dlg.title_edit.setText("测试")
    assert dlg.result_data()["title"] == "测试"
    assert dlg.result_data()["important"] == 1
    assert dlg.result_data()["urgent"] == 1
    assert dlg.options.isHidden()
    assert dlg.focusWidget() is dlg.title_edit
    assert dlg.result_data()["hide_when_collapsed"] is False

    dlg.hide_when_collapsed.setChecked(True)
    new_id = db.add_task(**dlg.result_data())
    edited = TaskDialog(task=db.get_task(new_id))
    assert edited.hide_when_collapsed.isChecked() and not edited.options.isHidden()
    edited.hide_when_collapsed.setChecked(False)
    db.update_task(new_id, **edited.result_data())
    assert db.get_task(new_id)["hide_when_collapsed"] == 0
    db.delete_task(new_id)

    edited = TaskDialog(task=db.get_task(tid))
    edited.hide_when_collapsed.setChecked(True)
    db.update_task(tid, **edited.result_data())
    win.quadrant.reload()
    assert win._preview_due_at is None
    assert collapsed_preview(db.list_tasks()) == ("5 项待办", None)
    edited.hide_when_collapsed.setChecked(False)
    db.update_task(tid, **edited.result_data())
    win.quadrant.reload()
    assert win._preview_due_at == "2099-01-02 10:00"

    dlg2 = TaskDialog(prefill={"title": "预填", "note": "n", "important": 1, "urgent": 0, "due_at": "2099-05-05 08:30"})
    assert dlg2.result_data()["title"] == "预填"
    assert dlg2.result_data()["due_at"] == "2099-05-05 08:30"
    assert dlg2.result_data()["important"] == 1
    assert not dlg2.options.isHidden()

    # ---- 目录按钮及更多菜单 ----
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
    edit, delete = row.more_btn.menu().actions()
    edit.trigger()
    assert ctrl.edited == 7
    delete.trigger()
    assert ctrl.deleted == 7
    row_nodir = TaskRow({"id": 8, "title": "t2", "note": "", "important": 0, "urgent": 0,
                         "dir_path": None, "due_at": None, "done": 0, "sort_order": 0}, ctrl)
    assert not hasattr(row_nodir, "folder_btn")

    AiDialog()
    SettingsDialog()

    # ---- 收起/展开状态机 + 展开尺寸不被收起污染 ----
    win.resize(620, 440)
    win.collapse_btn.click()
    assert win.collapsed is True
    collapsed_h = win.height()
    assert 40 <= collapsed_h <= 44 and win.grip.isHidden()
    assert win.preview_due.text() == "01-02 10:00"
    with patch("app.ui.floating_window.datetime") as clock:
        clock.now.return_value = datetime(2099, 1, 2, 10)
        win.reminder.timer.timeout.emit()
    assert win.preview_due.text() == "已逾期"
    win._save_state()  # 收起态保存不得污染展开尺寸
    assert db.get_setting("window_w") == "620"
    assert db.get_setting("window_h") == "440"
    restarted = FloatingWindow()
    assert restarted.collapsed and restarted.height() == collapsed_h
    restarted._apply_collapsed(False)
    assert (restarted.width(), restarted.height()) == (620, 440)
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
    win.close()

    print("SMOKE OK")


if __name__ == "__main__":
    with TemporaryDirectory() as directory:
        os.environ["TODO_QUADRANT_DB"] = os.path.join(directory, "todo.db")
        main()
