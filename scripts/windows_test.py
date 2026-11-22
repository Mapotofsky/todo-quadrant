"""在有 Explorer 托盘的 Windows 会话中验证原生启动及生命周期。"""
import ctypes
import os
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


def check_gui(no_tray):
    import main
    from PyQt5.QtCore import Qt, QTimer
    from PyQt5.QtTest import QTest
    from PyQt5.QtWidgets import QApplication, QStyle, QStyleOptionButton, QSystemTrayIcon
    from app import db
    from app.ui.floating_window import FloatingWindow

    def exercise():
        app = QApplication.instance()
        win = next(w for w in app.topLevelWidgets() if isinstance(w, FloatingWindow))
        assert app.platformName() == "windows"
        assert not app.windowIcon().pixmap(32, 32).isNull()
        if no_tray:
            assert win.isVisible() and app.quitOnLastWindowClosed()
            QTest.keyClick(win, Qt.Key_Escape)
            assert win.isVisible() and not win.collapsed
            QTimer.singleShot(0, win.close)
            return original_exec()

        tray = app.findChild(QSystemTrayIcon)
        assert tray.isVisible() and not win.isVisible()
        assert tray.icon().cacheKey() == app.windowIcon().cacheKey()
        show, new, _, quit_action = tray.contextMenu().actions()
        assert [show.text(), new.text(), quit_action.text()] == ["显示待办", "新建任务", "退出"]

        tray.activated.emit(QSystemTrayIcon.Trigger)
        assert win.isVisible() and not win.collapsed
        hwnd = int(win.winId())
        get_style = ctypes.windll.user32.GetWindowLongPtrW
        get_style.argtypes = (ctypes.c_void_p, ctypes.c_int)
        get_style.restype = ctypes.c_ssize_t
        style = get_style(hwnd, -20)
        assert style & 0x80 and not style & 0x40000  # TOOLWINDOW / APPWINDOW

        QTest.keyClick(win, Qt.Key_Escape)
        assert win.isVisible() and not win.collapsed
        win.collapse_btn.click()
        QTest.keyClick(win, Qt.Key_Escape)
        assert win.isVisible() and win.collapsed
        win.expand_btn.click()
        assert win.isVisible() and not win.collapsed

        post_message = ctypes.windll.user32.PostMessageW
        post_message.argtypes = (ctypes.c_void_p, ctypes.c_uint, ctypes.c_size_t, ctypes.c_ssize_t)
        assert post_message(hwnd, 0x10, 0, 0)  # WM_CLOSE
        QTest.qWait(100)
        assert not win.isVisible()

        task = db.add_task("Windows 自动验收提醒", due_at="2000-01-01 00:00")
        with patch.object(tray, "showMessage", wraps=tray.showMessage) as notify:
            assert win.reminder.timer.interval() == 60_000
            win.reminder.timer.setInterval(25)
            QTest.qWait(200)
            win.reminder.timer.stop()
            assert not win.isVisible() and db.get_task(task)["reminded"] == 1
            notify.assert_called_once_with("任务到期", "Windows 自动验收提醒", QSystemTrayIcon.Information)

        show.trigger()
        assert win.isVisible()
        win.close()
        assert not win.isVisible()
        dialog_cancelled = []

        dialog_checks = []

        def check_and_cancel_dialog():
            dialog = app.activeModalWidget()
            if dialog is None:
                return
            try:
                hwnd = int(dialog.winId())
                assert not get_style(hwnd, -20) & 0x400  # WS_EX_CONTEXTHELP
                for check in (dialog.imp_check, dialog.urg_check, dialog.due_check):
                    option = QStyleOptionButton()
                    check.initStyleOption(option)
                    indicator = check.style().subElementRect(QStyle.SE_CheckBoxIndicator, option, check)
                    unchecked = check.grab(indicator).toImage()
                    assert unchecked.pixelColor(unchecked.rect().center()).alpha() > 0
                    QTest.mouseClick(check, Qt.LeftButton, pos=indicator.center())
                    assert check.isChecked()
                    assert check.grab(indicator).toImage() != unchecked
                data = dialog.result_data()
                assert data["important"] == data["urgent"] == 1 and data["due_at"]
                dialog_checks.append(True)
            except AssertionError as error:
                dialog_checks.append(error)
            finally:
                QTest.keyClick(dialog, Qt.Key_Escape)
                dialog_cancelled.append(not dialog.isVisible())
                if dialog.isVisible():
                    dialog.reject()

        QTimer.singleShot(50, check_and_cancel_dialog)
        new.trigger()
        assert dialog_checks == [True], dialog_checks
        assert dialog_cancelled == [True]
        assert win.isVisible() and len(db.list_tasks()) == 1
        QTimer.singleShot(0, quit_action.trigger)
        return original_exec()

    original_exec = QApplication.exec_
    available = QSystemTrayIcon.isSystemTrayAvailable
    with patch.object(QApplication, "exec_", side_effect=exercise), patch.object(main.config, "auto_load_api_key"):
        with patch.object(QSystemTrayIcon, "isSystemTrayAvailable",
                          side_effect=lambda: not no_tray and available()):
            assert main.main() == 0
    print("WINDOWS FALLBACK OK" if no_tray else "WINDOWS TRAY OK")


def check_migration(directory):
    from app import db

    profile = directory / "迁移测试 用户"
    legacy = profile / ".config" / "todo-quadrant" / "todo.db"
    local = profile / "AppData" / "Local"
    with patch.dict(os.environ, USERPROFILE=str(profile), LOCALAPPDATA=str(local),
                    TODO_QUADRANT_DB=str(legacy)):
        db.init()
        task = db.add_task("旧库任务")
        db.set_setting("window_w", 640)
        original = legacy.read_bytes()
        del os.environ["TODO_QUADRANT_DB"]
        db.init()
        assert db._db_path() == local / "TodoQuadrant" / "todo.db"
        assert db.get_task(task)["title"] == "旧库任务"
        assert db.get_setting("window_w") == "640"
        db.update_task(task, title="新库已修改")
        db.init()
        assert db.get_task(task)["title"] == "新库已修改"
        assert legacy.read_bytes() == original
    print("WINDOWS MIGRATION OK")


if __name__ == "__main__":
    if sys.platform != "win32":
        sys.exit("Windows required")
    if len(sys.argv) > 1:
        check_gui(sys.argv[1] == "fallback")
    else:
        with TemporaryDirectory(prefix="todo-quadrant-windows-") as name:
            directory = Path(name)
            check_migration(directory)
            env = os.environ.copy()
            env.pop("TODO_QUADRANT_QPA", None)
            for mode in ("tray", "fallback"):
                env["TODO_QUADRANT_DB"] = str(directory / mode / "todo.db")
                subprocess.run([sys.executable, __file__, mode], env=env, check=True, timeout=30)
