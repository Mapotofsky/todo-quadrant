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
    def __init__(self, quadrant, controller):
        super().__init__()
        self.quadrant = quadrant
        self.controller = controller
        self.setObjectName("tasklist")
        self.setAccessibleName(QUADRANTS[quadrant]["name"] + "任务列表")
        self.setVerticalScrollMode(QAbstractItemView.ScrollPerPixel)
        self.setSelectionMode(QAbstractItemView.SingleSelection)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setFrameShape(QFrame.NoFrame)
        self.empty_add = QPushButton("＋ 添加任务", self.viewport())
        self.empty_add.setObjectName("empty_add")
        self.empty_add.clicked.connect(lambda: controller.new_task(quadrant))
        self.currentItemChanged.connect(self._current_changed)

    def resizeEvent(self, e):
        super().resizeEvent(e)
        self.empty_add.resize(self.empty_add.sizeHint())
        self.empty_add.move((self.viewport().width() - self.empty_add.width()) // 2,
                            (self.viewport().height() - self.empty_add.height()) // 2)
        self._fit_rows()

    def _fit_rows(self):
        """任务行固定为列表视口宽度，避免行内容把「更多」按钮挤出可视区。"""
        width = self.viewport().width()
        if width <= 0:
            return
        for i in range(self.count()):
            row = self.itemWidget(self.item(i))
            if row is not None:
                row.setFixedWidth(width)

    def keyPressEvent(self, e):
        item = self.currentItem()
        if item is not None:
            row = self.itemWidget(item)
            if e.key() == Qt.Key_Space:
                self.controller.toggle_done(row.task["id"], not row.task["done"])
                return
            if e.key() in (Qt.Key_Return, Qt.Key_Enter):
                self.controller.edit_task(row.task["id"])
                return
        super().keyPressEvent(e)

    def _show_current(self, item, focused):
        if item is not None:
            row = self.itemWidget(item)
            if row is not None:
                row.setProperty("keyboard_current", focused)
                row.style().unpolish(row)
                row.style().polish(row)
                row.update()

    def _current_changed(self, current, previous):
        self._show_current(previous, False)
        self._show_current(current, self.hasFocus())

    def focusInEvent(self, e):
        super().focusInEvent(e)
        self._show_current(self.currentItem(), True)

    def focusOutEvent(self, e):
        super().focusOutEvent(e)
        self._show_current(self.currentItem(), False)


class QuadrantHeader(QFrame):
    def __init__(self, quadrant, controller):
        super().__init__()
        self.setObjectName(f"qh_q{quadrant}")
        self.setFixedHeight(28)
        lay = QHBoxLayout(self)
        lay.setContentsMargins(8, 1, 4, 1)
        lay.setSpacing(6)
        self.name = QLabel(QUADRANTS[quadrant]["name"])
        self.name.setObjectName("qh_name")
        self.count = QLabel("待办 0")
        self.count.setObjectName("qh_count")
        add = QPushButton("＋")
        add.setObjectName("hdr_btn")
        add.setFixedSize(26, 24)
        add.setToolTip("在本象限新增")
        add.setAccessibleName(QUADRANTS[quadrant]["name"] + "新增任务")
        add.clicked.connect(lambda: controller.new_task(quadrant))
        lay.addWidget(self.name)
        lay.addWidget(self.count)
        lay.addStretch(1)
        lay.addWidget(add)


class QuadrantView(QWidget):
    tasks_changed = pyqtSignal(list)

    def __init__(self, parent=None):
        super().__init__(parent)
        grid = QGridLayout(self)
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setSpacing(5)
        self.headers = {}
        self.lists = {}
        self.cells = {}
        self._drop_target = None
        self._rows = {}
        positions = {0: (0, 0), 1: (0, 1), 2: (1, 0), 3: (1, 1)}
        for q in QUADRANT_ORDER:
            cell = QFrame()
            cell.setObjectName("quadrant_cell")
            layout = QVBoxLayout(cell)
            layout.setSpacing(2)
            layout.setContentsMargins(2, 2, 2, 2)
            hdr = QuadrantHeader(q, self)
            lst = TaskList(q, self)
            layout.addWidget(hdr)
            layout.addWidget(lst, 1)
            self.headers[q] = hdr
            self.lists[q] = lst
            self.cells[q] = cell
            r, c = positions[q]
            grid.addWidget(cell, r, c)
        for index in (0, 1):
            grid.setColumnStretch(index, 1)
            grid.setRowStretch(index, 1)

        self.reload()

    # ---------- 数据加载 ----------
    def reload(self):
        tasks = db.list_tasks()
        by_q = {q: [] for q in QUADRANT_ORDER}
        for t in tasks:
            by_q[quadrant_of(t["important"], t["urgent"])].append(t)
        focused_list = None
        focused_id = None
        focus = self.window().focusWidget() if self.isVisible() else None
        self._rows.clear()
        for q in QUADRANT_ORDER:
            lst = self.lists[q]
            current = lst.currentItem()
            current_id = current.data(Qt.UserRole) if current is not None else None
            current_index = lst.currentRow()
            if focus is not None and (focus is lst or lst.isAncestorOf(focus)):
                focused_list = lst
                focused_id = current_id
                widget = focus
                while widget is not lst:
                    if isinstance(widget, TaskRow):
                        focused_id = widget.task["id"]
                        break
                    widget = widget.parentWidget()
            lst.clear()
            items = sorted(by_q[q], key=lambda t: t["done"])
            for t in items:
                self._add_row(lst, t)
            self.headers[q].count.setText(f"待办 {sum(not t['done'] for t in items)}")
            lst.empty_add.setVisible(not items)
            lst.setFocusPolicy(Qt.StrongFocus if items else Qt.NoFocus)
            if current_id in self._rows and self._rows[current_id][0] is lst:
                lst.setCurrentItem(self._rows[current_id][1])
            elif items and (current_index >= 0 or focused_list is lst):
                lst.setCurrentRow(min(max(current_index, 0), len(items) - 1))
        if focused_list is not None:
            if focused_id in self._rows:
                self.focus_task(focused_id)
            elif focused_list.count():
                focused_list.setFocus()
            else:
                focused_list.empty_add.setFocus()
        self.tasks_changed.emit(tasks)

    def _add_row(self, lst, t):
        item = QListWidgetItem()
        row = TaskRow(t, self)
        item.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable)
        item.setData(Qt.UserRole, t["id"])
        item.setSizeHint(QSize(0, row.height()))
        lst.addItem(item)
        lst.setItemWidget(item, row)
        width = lst.viewport().width()
        if width > 0:
            row.setFixedWidth(width)
        self._rows[t["id"]] = (lst, item)

    def focus_task(self, task_id):
        lst, item = self._rows[task_id]
        lst.setCurrentItem(item)
        lst.setFocus()

    def refresh_deadlines(self, now):
        for lst, item in self._rows.values():
            lst.itemWidget(item).refresh_deadline(now)

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

    def highlight_drop(self, task, global_pos):
        w = QApplication.widgetAt(global_pos)
        source = quadrant_of(task["important"], task["urgent"])
        target = next((q for q, cell in self.cells.items()
                       if q != source and (w is cell or (w is not None and cell.isAncestorOf(w)))), None)
        self._set_drop_target(target)
        return target

    def _set_drop_target(self, target):
        if target == self._drop_target:
            return
        for q in (self._drop_target, target):
            if q is not None:
                cell = self.cells[q]
                cell.setProperty("drop_target", q == target)
                cell.style().unpolish(cell)
                cell.style().polish(cell)
                cell.update()
        self._drop_target = target

    def handle_drop(self, task, global_pos):
        target = self.highlight_drop(task, global_pos)
        self._set_drop_target(None)
        if target is not None:
            self.move_task_to_quadrant(task["id"], target)

    def _schedule_reload(self):
        # 延迟到当前事件处理返回后再重建，避免在行内控件自身事件里销毁它
        QTimer.singleShot(0, self.reload)
