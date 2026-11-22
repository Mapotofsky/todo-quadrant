"""悬浮窗容器：无边框、半透明、始终置顶、可收起、可拖动。"""
import subprocess
import sys

from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFrame, QLabel, QPushButton,
    QApplication, QMenu, QSizeGrip, QDialog,
)

from app import db
from app.remind import Reminder
from app.ui.quadrant_view import QuadrantView


class TitleBar(QFrame):
    """可拖动标题栏（按住空白/标题处拖动整个窗口）。"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._drag = None

    def mousePressEvent(self, e):
        if e.button() == Qt.LeftButton:
            self._drag = e.globalPos() - self.window().frameGeometry().topLeft()

    def mouseMoveEvent(self, e):
        if e.buttons() & Qt.LeftButton and self._drag is not None:
            self.window().move(e.globalPos() - self._drag)

    def mouseReleaseEvent(self, e):
        self._drag = None
        if hasattr(self.window(), "_save_state"):
            self.window()._save_state()


EXPAND_MIN_W = 520
EXPAND_MIN_H = 340


class FloatingWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        if sys.platform != "win32":
            # 托盘常驻窗口不应出现在任务栏；Qt.Tool 再显式标记为 Utility。
            self.setAttribute(Qt.WA_X11NetWmWindowTypeUtility, True)
        self.close_to_tray = False
        self.collapsed = False
        self._expanded_size = None
        self._build_ui()
        self._update_count()
        self._restore_state()

        self.reminder = Reminder(self)
        self.reminder.task_due.connect(self._on_task_due)

    def _build_ui(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        self.container = QFrame()
        self.container.setObjectName("container")
        outer.addWidget(self.container)

        lay = QVBoxLayout(self.container)
        lay.setContentsMargins(8, 6, 8, 8)
        lay.setSpacing(5)

        # 顶栏
        self.top_bar = TitleBar()
        self.top_bar.setObjectName("topbar")
        tb = QHBoxLayout(self.top_bar)
        tb.setContentsMargins(2, 1, 2, 1)
        self.title_lbl = QLabel("待办 · 四象限")
        self.title_lbl.setObjectName("title")
        self.ai_btn = QPushButton("AI 粘贴")
        self.ai_btn.setObjectName("ai_btn")
        self.add_btn = QPushButton("＋ 新建")
        self.add_btn.setObjectName("add_btn")
        self.settings_btn = QPushButton("⚙")
        self.settings_btn.setObjectName("icon_btn")
        self.collapse_btn = QPushButton("—")
        self.collapse_btn.setObjectName("collapse_btn")
        tb.addWidget(self.title_lbl)
        tb.addStretch(1)
        tb.addWidget(self.ai_btn)
        tb.addWidget(self.add_btn)
        tb.addWidget(self.settings_btn)
        tb.addWidget(self.collapse_btn)

        # 四象限
        self.quadrant = QuadrantView()

        # 收起条
        self.collapsed_bar = TitleBar()
        self.collapsed_bar.setObjectName("collapsedbar")
        cb = QHBoxLayout(self.collapsed_bar)
        cb.setContentsMargins(10, 6, 10, 6)
        self.collapsed_add_btn = QPushButton("＋")
        self.collapsed_add_btn.setObjectName("add_btn")
        self.count_lbl = QLabel("")
        self.count_lbl.setObjectName("count")
        self.expand_btn = QPushButton("展开")
        self.expand_btn.setObjectName("expand_btn")
        cb.addWidget(self.collapsed_add_btn)
        cb.addWidget(self.count_lbl)
        cb.addStretch(1)
        cb.addWidget(self.expand_btn)

        lay.addWidget(self.top_bar)
        lay.addWidget(self.quadrant, 1)
        lay.addWidget(self.collapsed_bar)

        self.collapsed_bar.hide()

        self.collapse_btn.clicked.connect(self._toggle_collapse)
        self.expand_btn.clicked.connect(self._toggle_collapse)
        self.add_btn.clicked.connect(lambda: self.quadrant.new_task())
        self.collapsed_add_btn.clicked.connect(lambda: self.quadrant.new_task())
        self.ai_btn.clicked.connect(self._ai_new)
        self.settings_btn.clicked.connect(self._settings)
        self.quadrant.count_changed.connect(self._update_count)

        self.grip = QSizeGrip(self)

    # ---------- 新建 / 设置 ----------
    def _ai_new(self):
        from app.ui.ai_dialog import AiDialog
        from app.ui.task_dialog import TaskDialog
        dlg = AiDialog(parent=self)
        if dlg.exec_() == QDialog.Accepted and dlg.result:
            tdlg = TaskDialog(prefill=dlg.result, parent=self)
            if tdlg.exec_() == QDialog.Accepted:
                d = tdlg.result_data()
                db.add_task(d["title"], d["note"], d["important"], d["urgent"], d["dir_path"], d["due_at"])
                self.quadrant.reload()

    def _settings(self):
        from app.ui.settings_dialog import SettingsDialog
        dlg = SettingsDialog(parent=self)
        if dlg.exec_() == QDialog.Accepted:
            dlg.save()

    def _on_task_due(self, title, note):
        self.quadrant.reload()
        self._update_count()
        self.count_lbl.setStyleSheet("color:#ff8a8a;")
        QTimer.singleShot(3000, lambda: self.count_lbl.setStyleSheet(""))

    # ---------- 收起 / 展开 ----------
    def _toggle_collapse(self):
        self._apply_collapsed(not self.collapsed)
        self._save_state()

    def _apply_collapsed(self, collapsed):
        self.collapsed = collapsed
        if collapsed:
            # 先记住展开尺寸，再缩小；收起时解除最小尺寸限制
            if self.width() >= EXPAND_MIN_W and self.height() >= EXPAND_MIN_H:
                self._expanded_size = (self.width(), self.height())
            self.setMinimumSize(0, 0)
            self.top_bar.hide()
            self.quadrant.hide()
            self.collapsed_bar.show()
            self._update_count()
            self.adjustSize()
        else:
            self.collapsed_bar.hide()
            self.top_bar.show()
            self.quadrant.show()
            w, h = self._expanded_size or (None, None)
            if not w or not h:
                w = self._int_setting("window_w", 600)
                h = self._int_setting("window_h", 420)
            w = max(w, EXPAND_MIN_W)
            h = max(h, EXPAND_MIN_H)
            self.setMinimumSize(EXPAND_MIN_W, EXPAND_MIN_H)
            self.resize(w, h)

    def _update_count(self, n=None):
        if n is None:
            n = sum(1 for t in db.list_tasks() if not t["done"])
        self.count_lbl.setText(f"{n} 项进行中")

    # ---------- 状态持久化 ----------
    def _int_setting(self, key, default):
        v = db.get_setting(key, None)
        try:
            return int(v) if v is not None else default
        except (TypeError, ValueError):
            return default

    def _restore_state(self):
        x = self._int_setting("window_x", None)
        y = self._int_setting("window_y", None)
        w = max(self._int_setting("window_w", 600), EXPAND_MIN_W)
        h = max(self._int_setting("window_h", 420), EXPAND_MIN_H)
        if x is not None and y is not None:
            # 防止记忆的坐标把窗口放到屏幕外
            scr = QApplication.primaryScreen().availableGeometry()
            x = min(max(x, scr.left()), max(scr.left(), scr.right() - 120))
            y = min(max(y, scr.top()), max(scr.top(), scr.bottom() - 60))
            self.move(x, y)
        self.resize(w, h)
        self.collapsed = db.get_setting("collapsed", "0") == "1"
        self._apply_collapsed(self.collapsed)

    def _save_state(self):
        g = self.geometry()
        db.set_setting("window_x", g.x())
        db.set_setting("window_y", g.y())
        db.set_setting("collapsed", "1" if self.collapsed else "0")
        if not self.collapsed:
            # 收起态的小尺寸不写回，避免污染展开尺寸记忆
            db.set_setting("window_w", g.width())
            db.set_setting("window_h", g.height())

    # ---------- 事件 ----------
    def showEvent(self, e):
        super().showEvent(e)
        if sys.platform != "win32":
            # Qt.Tool 在部分 UKUI/KWin 版本仍会出现在任务栏，显式补上 EWMH 状态。
            QTimer.singleShot(0, self._skip_taskbar)

    def _skip_taskbar(self):
        try:
            subprocess.Popen(
                ["wmctrl", "-i", "-r", hex(int(self.winId())), "-b",
                 "add,skip_taskbar,skip_pager"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        except Exception:
            pass

    def resizeEvent(self, e):
        super().resizeEvent(e)
        self.grip.move(self.width() - self.grip.width(), self.height() - self.grip.height())

    def closeEvent(self, e):
        self._save_state()
        if self.close_to_tray:
            self.hide()
            e.ignore()
            return
        super().closeEvent(e)

    def quit(self):
        self._save_state()
        QApplication.instance().quit()

    def contextMenuEvent(self, e):
        menu = QMenu(self)
        menu.addAction("新建任务", lambda: self.quadrant.new_task())
        menu.addAction("AI 粘贴总结", self._ai_new)
        menu.addAction("设置", self._settings)
        menu.addAction("收起" if not self.collapsed else "展开", self._toggle_collapse)
        if self.close_to_tray:
            menu.addAction("隐藏到托盘", self.close)
        menu.addSeparator()
        menu.addAction("退出", self.quit)
        menu.exec_(e.globalPos())
