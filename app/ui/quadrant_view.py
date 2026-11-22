"""四象限视图：2×2 网格 + 紧凑任务行 + 拖拽换象限 + 每象限快速新增。"""
from PyQt5.QtCore import Qt, pyqtSignal, QUrl, QTimer, QSize
from PyQt5.QtGui import QDesktopServices
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QGridLayout, QHBoxLayout, QFrame, QLabel, QListWidget,
    QListWidgetItem, QPushButton, QAbstractItemView, QDialog, QApplication,
)

from app import db
from app.ui.task_dialog import TaskDialog
from app.ui.task_row import TaskRow


QUADRANTS = {
    0: {"name": "重要·紧急", "important": 1, "urgent": 1},
    1: {"name": "重要·不紧急", "important": 1, "urgent": 0},
    2: {"name": "不重要·紧急", "important": 0, "urgent": 1},
    3: {"name": "不重要·不紧急", "important": 0, "urgent": 0},
}
QUADRANT_ORDER = [0, 1, 2, 3]
_QMAP = {(1, 1): 0, (1, 0): 1, (0, 1): 2, (0, 0): 3}


def quadrant_of(important, urgent):
    return _QMAP[(1 if important else 0, 1 if urgent else 0)]


class TaskList(QListWidget):
    def __init__(self, quadrant, parent=None):
        super().__init__(parent)
        self.quadrant = quadrant
        self.setObjectName("tasklist")
        self.setVerticalScrollMode(QAbstractItemView.ScrollPerPixel)
        self.setSelectionMode(QAbstractItemView.NoSelection)
        self.setFocusPolicy(Qt.NoFocus)
        self.setFrameShape(QFrame.NoFrame)
        self.setSpacing(1)
        # 空象限占位提示
        self.empty_hint = QLabel("空 · 点＋或拖入", self)
        self.empty_hint.setObjectName("empty_hint")
        self.empty_hint.setAlignment(Qt.AlignCenter)
        self.empty_hint.setAttribute(Qt.WA_TransparentForMouseEvents, True)

    def resizeEvent(self, e):
        super().resizeEvent(e)
        self.empty_hint.setGeometry(self.viewport().rect())


class QuadrantHeader(QFrame):
    def __init__(self, quadrant, controller):
        super().__init__()
        self.setObjectName(f"qh_q{quadrant}")
        self.setFixedHeight(22)
        lay = QHBoxLayout(self)
        lay.setContentsMargins(8, 1, 4, 1)
        lay.setSpacing(6)
        self.name = QLabel(QUADRANTS[quadrant]["name"])
        self.name.setObjectName("qh_name")
        self.count = QLabel("0")
        self.count.setObjectName("qh_count")
        add = QPushButton("＋")
        add.setObjectName("hdr_btn")
        add.setFixedSize(20, 20)
        add.setToolTip("在本象限新增")
        add.clicked.connect(lambda: controller.new_task(quadrant))
        lay.addWidget(self.name)
        lay.addWidget(self.count)
        lay.addStretch(1)
        lay.addWidget(add)


class QuadrantView(QWidget):
    count_changed = pyqtSignal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        grid = QGridLayout(self)
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setSpacing(5)
        self.headers = {}
        self.lists = {}
        positions = {0: (0, 0), 1: (0, 1), 2: (1, 0), 3: (1, 1)}
        for q in QUADRANT_ORDER:
            cell = QVBoxLayout()
            cell.setSpacing(2)
            cell.setContentsMargins(0, 0, 0, 0)
            hdr = QuadrantHeader(q, self)
            lst = TaskList(q, self)
            cell.addWidget(hdr)
            cell.addWidget(lst, 1)
            self.headers[q] = hdr
            self.lists[q] = lst
            r, c = positions[q]
            grid.addLayout(cell, r, c)

        self.reload()

    # ---------- 数据加载 ----------
    def reload(self):
        tasks = db.list_tasks()
        by_q = {q: [] for q in QUADRANT_ORDER}
        for t in tasks:
            by_q[quadrant_of(t["important"], t["urgent"])].append(t)
        open_count = 0
        for q in QUADRANT_ORDER:
            lst = self.lists[q]
            lst.clear()
            items = sorted(by_q[q], key=lambda t: (t["sort_order"], t["id"]))
            for t in items:
                if not t["done"]:
                    open_count += 1
                self._add_row(lst, t)
            self.headers[q].count.setText(str(len(items)))
            lst.empty_hint.setVisible(lst.count() == 0)
        self.count_changed.emit(open_count)

    def _add_row(self, lst, t):
        item = QListWidgetItem()
        item.setFlags(Qt.ItemIsEnabled)
        item.setSizeHint(QSize(0, 26))
        lst.addItem(item)
        row = TaskRow(t, self)
        lst.setItemWidget(item, row)

    # ---------- 操作（供 TaskRow 调用）----------
    def open_dir(self, path):
        if path:
            QDesktopServices.openUrl(QUrl.fromLocalFile(path))

    def toggle_done(self, task_id, done):
        db.set_done(task_id, bool(done))
        self._schedule_reload()

    def edit_task(self, task_id):
        task = db.get_task(task_id)
        if not task:
            return
        dlg = TaskDialog(task=task, parent=self.window())
        if dlg.exec_() == QDialog.Accepted:
            db.update_task(task_id, **dlg.result_data())
            self._schedule_reload()

    def delete_task(self, task_id):
        task = db.get_task(task_id)
        if not task:
            return
        from app.ui.message import confirm
        if confirm(self, "删除", f"删除任务「{task['title']}」？"):
            db.delete_task(task_id)
            self._schedule_reload()

    def new_task(self, quadrant=None):
        dlg = TaskDialog(default_quadrant=quadrant, parent=self.window())
        if dlg.exec_() == QDialog.Accepted:
            d = dlg.result_data()
            db.add_task(d["title"], d["note"], d["important"], d["urgent"],
                        d["dir_path"], d["due_at"])
            self._schedule_reload()

    def move_task_to_quadrant(self, task_id, quadrant):
        task = db.get_task(task_id)
        if not task:
            return
        q = QUADRANTS[quadrant]
        db.set_quadrant(task_id, q["important"], q["urgent"])
        cnt = sum(
            1 for t in db.list_tasks()
            if quadrant_of(t["important"], t["urgent"]) == quadrant and t["id"] != task_id
        )
        db.set_sort_order(task_id, cnt)
        self._schedule_reload()

    def handle_drop(self, task_id, global_pos):
        w = QApplication.widgetAt(global_pos)
        target = None
        while w is not None:
            if isinstance(w, TaskList):
                target = w
                break
            w = w.parent()
        if target is None:
            return
        task = db.get_task(task_id)
        if task is None:
            return
        if quadrant_of(task["important"], task["urgent"]) == target.quadrant:
            return
        self.move_task_to_quadrant(task_id, target.quadrant)

    def _schedule_reload(self):
        # 延迟到当前事件处理返回后再重建，避免在行内控件自身事件里销毁它
        QTimer.singleShot(0, self.reload)
