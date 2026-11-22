"""任务行与首尾省略的标题控件。"""
from html import escape

from PyQt5.QtCore import QEvent, Qt
from PyQt5.QtWidgets import (
    QApplication, QWidget, QHBoxLayout, QVBoxLayout, QCheckBox, QLabel, QMenu,
    QSizePolicy,
)

from app.remind import deadline_status
from app.ui.icons import icon_button


class DeadlineLabel(QLabel):
    def __init__(self):
        super().__init__()
        self.setObjectName("due")

    def update_deadline(self, due_at, done=False, now=None):
        text, overdue = deadline_status(due_at, done, now)
        self.setText(text)
        self.setToolTip(f"截止时间：{due_at}" if text else "")
        self.setVisible(bool(text))
        if self.property("overdue") != overdue:
            self.setProperty("overdue", overdue)
            self.style().unpolish(self)
            self.style().polish(self)


class ElidedLabel(QLabel):
    """按可用宽度自动省略号显示的标签（不撑宽布局）。"""

    def __init__(self, text=""):
        super().__init__()
        self.setTextFormat(Qt.PlainText)
        self.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred)
        self.setFullText(text)

    def setFullText(self, text):
        self._full = text
        self.setAccessibleName(text)
        self._update()

    def resizeEvent(self, e):
        super().resizeEvent(e)
        self._update()

    def _update(self):
        text = self.fontMetrics().elidedText(self._full, Qt.ElideMiddle, self.contentsRect().width())
        self.setText(text)
        self.setToolTip(f"<p>{escape(self._full)}</p>" if text != self._full else "")

    def changeEvent(self, e):
        super().changeEvent(e)
        if e.type() == QEvent.FontChange:
            self._update()


class TaskRow(QWidget):
    def __init__(self, task, controller):
        super().__init__()
        self.task = task
        self.controller = controller
        self._press = None
        self._dragging = False
        self.setObjectName("taskrow")
        self.setAttribute(Qt.WA_Hover, True)
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setFixedHeight(42 if task.get("due_at") else 30)

        lay = QHBoxLayout(self)
        lay.setContentsMargins(3, 0, 2, 0)
        lay.setSpacing(4)

        self.check = QCheckBox()
        self.check.setObjectName("task_check")
        self.check.setAccessibleName("完成：" + task["title"])
        self.check.setFixedSize(22, 24)
        self.check.setChecked(bool(task["done"]))
        self.check.stateChanged.connect(self._on_check)
        lay.addWidget(self.check)

        text_column = QVBoxLayout()
        text_column.setSpacing(0)
        self.title = ElidedLabel(task["title"])
        self.title.setObjectName("task_title")
        self.title.setProperty("done", bool(task["done"]))
        font = self.title.font()
        font.setStrikeOut(bool(task["done"]))
        self.title.setFont(font)
        text_column.addWidget(self.title)
        self.due = DeadlineLabel()
        text_column.addWidget(self.due)
        lay.addLayout(text_column, 1)
        self.refresh_deadline()

        dir_path = task.get("dir_path")
        if dir_path:
            self.folder_btn = icon_button("folder", "打开目录：" + dir_path, "row_btn")
            self.folder_btn.clicked.connect(lambda: controller.open_dir(dir_path))
            lay.addWidget(self.folder_btn)

        self.more_btn = icon_button("more", "更多任务操作", "row_btn")
        menu = QMenu(self.more_btn)
        menu.addAction("编辑", lambda: controller.edit_task(task["id"]))
        menu.addAction("删除…", lambda: controller.delete_task(task["id"]))
        self.more_btn.setMenu(menu)
        lay.addWidget(self.more_btn)

    def refresh_deadline(self, now=None):
        self.due.update_deadline(self.task.get("due_at"), self.task["done"], now)

    def _on_check(self, state):
        self.controller.toggle_done(self.task["id"], state == Qt.Checked)

    # ---------- 拖拽跨象限 ----------
    def mousePressEvent(self, e):
        if e.button() == Qt.LeftButton:
            self.controller.focus_task(self.task["id"])
            self._press = e.globalPos()
            self._dragging = False

    def mouseMoveEvent(self, e):
        if self._press is not None and (e.buttons() & Qt.LeftButton):
            if (not self._dragging and
                    (e.globalPos() - self._press).manhattanLength() >= QApplication.startDragDistance()):
                self._dragging = True
                self.setCursor(Qt.ClosedHandCursor)
            if self._dragging:
                self.controller.highlight_drop(self.task, e.globalPos())

    def mouseReleaseEvent(self, e):
        if self._dragging:
            self._dragging = False
            self.unsetCursor()
            self.controller.handle_drop(self.task, e.globalPos())
        self._press = None

    def mouseDoubleClickEvent(self, e):
        if e.button() == Qt.LeftButton:
            self.controller.edit_task(self.task["id"])
