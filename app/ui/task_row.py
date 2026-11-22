"""单个任务行（紧凑）：勾选 + 标题 + 截止 + 打开目录/编辑/删除 + 拖拽换象限。"""
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QWidget, QHBoxLayout, QCheckBox, QLabel, QPushButton, QSizePolicy,
)

from app.remind import is_overdue


class ElidedLabel(QLabel):
    """按可用宽度自动省略号显示的标签（不撑宽布局）。"""

    def __init__(self, text=""):
        super().__init__()
        self._full = text
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        self.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        self._update()

    def setFullText(self, text):
        self._full = text
        self._update()

    def resizeEvent(self, e):
        super().resizeEvent(e)
        self._update()

    def _update(self):
        fm = self.fontMetrics()
        self.setText(fm.elidedText(self._full, Qt.ElideRight, max(10, self.width())))


class TaskRow(QWidget):
    def __init__(self, task, controller):
        super().__init__()
        self.task = task
        self.controller = controller
        self._press = None
        self._dragging = False
        self.setObjectName("taskrow")
        self.setAttribute(Qt.WA_Hover, True)
        self.setFixedHeight(26)

        lay = QHBoxLayout(self)
        lay.setContentsMargins(2, 0, 0, 0)
        lay.setSpacing(5)

        self.check = QCheckBox()
        self.check.setChecked(bool(task["done"]))
        self.check.stateChanged.connect(self._on_check)
        lay.addWidget(self.check)

        self.title = ElidedLabel(task["title"])
        lay.addWidget(self.title, 1)

        self.due = QLabel(self._due_text(task))
        self.due.setObjectName("due")
        self.due.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        if not task.get("due_at"):
            self.due.hide()
        lay.addWidget(self.due)

        dir_path = task.get("dir_path")
        if dir_path:
            self.folder_btn = QPushButton("📁")
            self.folder_btn.setObjectName("row_btn")
            self.folder_btn.setToolTip("打开目录：" + dir_path)
            self.folder_btn.setFixedSize(22, 22)
            self.folder_btn.clicked.connect(lambda: controller.open_dir(dir_path))
            lay.addWidget(self.folder_btn)

        self.edit_btn = QPushButton("✎")
        self.edit_btn.setObjectName("row_btn")
        self.edit_btn.setToolTip("编辑")
        self.edit_btn.setFixedSize(22, 22)
        self.edit_btn.clicked.connect(lambda: controller.edit_task(task["id"]))
        lay.addWidget(self.edit_btn)

        self.del_btn = QPushButton("✕")
        self.del_btn.setObjectName("row_btn")
        self.del_btn.setToolTip("删除")
        self.del_btn.setFixedSize(22, 22)
        self.del_btn.clicked.connect(lambda: controller.delete_task(task["id"]))
        lay.addWidget(self.del_btn)

        self._apply_state()

    @staticmethod
    def _due_text(task):
        due = task.get("due_at")
        if not due:
            return ""
        # 'YYYY-MM-DD HH:MM' -> 'MM-DD HH:MM'
        return due[5:16] if len(due) >= 16 else due

    def _apply_state(self):
        done = bool(self.task["done"])
        overdue = (not done) and is_overdue(self.task.get("due_at"))
        f = self.title.font()
        f.setStrikeOut(done)
        self.title.setFont(f)
        if done:
            self.title.setStyleSheet("color:#8b8b96;")
        elif overdue:
            self.title.setStyleSheet("color:#ff8a8a;")
        else:
            self.title.setStyleSheet("color:#e6e8f0;")
        self.due.setStyleSheet("color:#ff8a8a;" if overdue else "color:#8b8b96;")

    def _on_check(self, state):
        self.controller.toggle_done(self.task["id"], state == Qt.Checked)

    # ---------- 拖拽跨象限 ----------
    def mousePressEvent(self, e):
        if e.button() == Qt.LeftButton:
            self._press = e.globalPos()
            self._dragging = False

    def mouseMoveEvent(self, e):
        if self._press is not None and (e.buttons() & Qt.LeftButton):
            if not self._dragging and (e.globalPos() - self._press).manhattanLength() > 6:
                self._dragging = True
                self.setCursor(Qt.ClosedHandCursor)

    def mouseReleaseEvent(self, e):
        if self._dragging:
            self._dragging = False
            self.setCursor(Qt.ArrowCursor)
            self.controller.handle_drop(self.task["id"], e.globalPos())
        self._press = None

    def mouseDoubleClickEvent(self, e):
        self.controller.edit_task(self.task["id"])
