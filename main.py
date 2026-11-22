#!/usr/bin/env python3
"""四象限待办悬浮窗 —— 应用入口。

Windows 使用原生 Qt 后端。麒麟通过 XWayland(xcb) 保持置顶和透明。
"""
import os
import sys


def _setup_env():
    platform = "windows" if sys.platform == "win32" else "xcb"
    os.environ["QT_QPA_PLATFORM"] = os.environ.get("TODO_QUADRANT_QPA", platform)
    os.environ.setdefault("QT_ENABLE_HIGHDPI_SCALING", "1")
    os.environ.setdefault("QT_AUTO_SCREEN_SCALE_FACTOR", "1")
    # 若窗口偏小/发虚，用 TODO_QUADRANT_SCALE=1.5 或 2 覆盖缩放因子。
    if "TODO_QUADRANT_SCALE" in os.environ:
        os.environ["QT_SCALE_FACTOR"] = os.environ["TODO_QUADRANT_SCALE"]
    os.environ.setdefault("LIBGL_ALWAYS_SOFTWARE", "1")


_setup_env()

from PyQt5.QtCore import Qt  # noqa: E402
from PyQt5.QtWidgets import QApplication  # noqa: E402

from app import db, config  # noqa: E402
from app.ui.floating_window import FloatingWindow  # noqa: E402


def _load_style(app):
    here = os.path.dirname(os.path.abspath(__file__))
    path = os.path.join(here, "resources", "style.qss")
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            app.setStyleSheet(f.read())


def main():
    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)
    app = QApplication(sys.argv)
    app.setApplicationName("todo-quadrant")
    app.setOrganizationName("local")
    # 平台 GTK/UKUI 样式会忽略 QMessageBox 的 QSS 背景，Fusion 完全服从 QSS
    app.setStyle("fusion")

    db.init()
    if not getattr(sys, "frozen", False):
        config.auto_load_api_key(os.path.dirname(os.path.abspath(__file__)))
    _load_style(app)

    win = FloatingWindow()
    tray = None
    if sys.platform == "win32":
        from app.ui.windows_tray import create_tray
        tray = create_tray(app, win)
        if tray is None:
            win.setWindowFlags((win.windowFlags() & ~Qt.WindowType_Mask) | Qt.Window)
            win.setAttribute(Qt.WA_QuitOnClose, True)
    if tray is None:
        win.show()
    return app.exec_()


if __name__ == "__main__":
    sys.exit(main())
