#!/usr/bin/env python3
"""四象限待办悬浮窗 —— 应用入口。

在 Wayland 会话下，Qt 的置顶/透明 windowFlags 会被合成器忽略，
因此强制走 XWayland(xcb)；maleoon 无可用 GPU，禁掉 GL 探测。
"""
import os
import sys


def _setup_env():
    # 默认强制 xcb(XWayland)；可用 TODO_QUADRANT_QPA 覆盖。
    os.environ["QT_QPA_PLATFORM"] = os.environ.get("TODO_QUADRANT_QPA", "xcb")
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
    config.auto_load_api_key(os.path.dirname(os.path.abspath(__file__)))
    _load_style(app)

    win = FloatingWindow()
    win.show()
    return app.exec_()


if __name__ == "__main__":
    sys.exit(main())
