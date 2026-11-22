"""桌面会话中的 Linux 托盘验收：启动隐藏、托盘显示、关闭到托盘、跳过任务栏。"""
import os
import shutil
import subprocess
import sys
from tempfile import TemporaryDirectory
from unittest.mock import patch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ["QT_QPA_PLATFORM"] = "xcb"


def main():
    from PyQt5.QtCore import QTimer
    from PyQt5.QtTest import QTest
    from PyQt5.QtWidgets import QApplication, QSystemTrayIcon

    import main as app_main
    from app.ui.floating_window import FloatingWindow

    failures = []

    def exercise():
        app = QApplication.instance()
        try:
            win = next(w for w in app.topLevelWidgets() if isinstance(w, FloatingWindow))
            tray = app.findChild(QSystemTrayIcon)
            if tray is None:
                assert win.isVisible()
                print("LINUX NO-TRAY FALLBACK OK")
                win.close()
                return

            assert app.platformName() == "xcb"
            assert not win.isVisible()  # 启动后先驻留托盘，不显示浮窗
            assert tray.isVisible()
            assert not tray.icon().isNull()
            assert tray.icon().cacheKey() == app.windowIcon().cacheKey()
            assert win.close_to_tray is True
            assert app.quitOnLastWindowClosed() is False

            show, new, _, quit_action = tray.contextMenu().actions()
            assert [show.text(), new.text(), quit_action.text()] == ["显示待办", "新建任务", "退出"]

            show.trigger()
            QTest.qWait(500)
            assert win.isVisible()
            if shutil.which("wmctrl") and shutil.which("xprop"):
                state = subprocess.check_output(
                    ["xprop", "-id", hex(int(win.winId())), "_NET_WM_STATE"], text=True)
                assert "_NET_WM_STATE_SKIP_TASKBAR" in state, state
                assert "_NET_WM_STATE_SKIP_PAGER" in state, state

            win.close()
            QTest.qWait(100)
            assert not win.isVisible()  # 关闭窗口只是隐藏，进程继续驻留

            tray.activated.emit(QSystemTrayIcon.Context)
            assert tray.contextMenu().isVisible()  # SNI 后端需手动弹出菜单
            QTest.qWait(100)
            tray.contextMenu().hide()

            tray.activated.emit(QSystemTrayIcon.Trigger)
            QTest.qWait(300)
            assert win.isVisible()
            quit_action.trigger()
            print("LINUX TRAY OK")
        except BaseException as exc:
            failures.append(exc)
        finally:
            # 断言失败时也结束事件循环，避免测试挂住。
            QTimer.singleShot(0, app.quit)

    original_exec = QApplication.exec_

    def fake_exec(self):
        QTimer.singleShot(0, exercise)
        return original_exec()

    with TemporaryDirectory(prefix="todo-quadrant-linux-") as directory:
        os.environ["TODO_QUADRANT_DB"] = os.path.join(directory, "todo.db")
        with patch.object(QApplication, "exec_", fake_exec), \
                patch.object(app_main.config, "auto_load_api_key"):
            assert app_main.main() == 0

    if failures:
        raise failures[0]


if __name__ == "__main__":
    main()
