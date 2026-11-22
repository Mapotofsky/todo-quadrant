"""Linux 通知区域入口：常驻托盘、显示/新建/退出，以及关闭到托盘。"""
from PyQt5.QtGui import QCursor
from PyQt5.QtWidgets import QMenu, QStyle, QSystemTrayIcon


def create_tray(app, window):
    if not QSystemTrayIcon.isSystemTrayAvailable():
        return None

    icon = app.windowIcon()
    if icon.isNull():
        # 图标资源缺失时仍保留可点击的托盘入口。
        icon = app.style().standardIcon(QStyle.SP_FileDialogDetailedView)
    tray = QSystemTrayIcon(icon, app)
    tray.setToolTip("四象限待办")
    menu = QMenu(window)

    def show_window():
        window.show()
        window.raise_()
        window.activateWindow()

    def new_task():
        show_window()
        if app.activeModalWidget() is None:
            window.quadrant.new_task()

    def activate(reason):
        if reason == QSystemTrayIcon.Trigger:
            show_window()
        elif reason == QSystemTrayIcon.Context and not menu.isVisible():
            # Qt 的 StatusNotifierItem 后端只发出 Context 信号，不自动弹出菜单；
            # XEmbed 后端可能已经自动弹出，避免重复。
            menu.popup(QCursor.pos())

    menu.addAction("显示待办", show_window)
    menu.addAction("新建任务", new_task)
    menu.addSeparator()
    menu.addAction("退出", window.quit)
    tray.setContextMenu(menu)
    tray.activated.connect(activate)
    window.close_to_tray = True
    app.setQuitOnLastWindowClosed(False)
    app.aboutToQuit.connect(tray.hide)
    tray.show()
    return tray
