"""Windows 通知区域入口及到期通知。"""
from PyQt5.QtWidgets import QMenu, QStyle, QSystemTrayIcon


def create_tray(app, window):
    if not QSystemTrayIcon.isSystemTrayAvailable():
        return None

    tray = QSystemTrayIcon(app.style().standardIcon(QStyle.SP_FileDialogDetailedView), app)
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

    def notify(title, _note):
        tray.showMessage("任务到期", title, QSystemTrayIcon.Information)

    menu.addAction("显示待办", show_window)
    menu.addAction("新建任务", new_task)
    menu.addSeparator()
    menu.addAction("退出", window.quit)
    tray.setContextMenu(menu)
    tray.activated.connect(activate)
    tray.messageClicked.connect(show_window)
    window.reminder.task_due.connect(notify)
    window.close_to_tray = True
    app.setQuitOnLastWindowClosed(False)
    app.aboutToQuit.connect(tray.hide)
    tray.show()
    return tray
