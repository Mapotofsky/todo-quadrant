"""任务新建 / 编辑对话框（含截止时间与 AI 预填）。"""
import os

from PyQt5.QtCore import Qt, QDateTime
from PyQt5.QtWidgets import (
    QDialog, QFormLayout, QLineEdit, QPlainTextEdit, QCheckBox,
    QHBoxLayout, QPushButton, QFileDialog, QDialogButtonBox, QLabel,
    QDateTimeEdit,
)


_QUAD_NAME = {
    (1, 1): "重要·紧急",
    (1, 0): "重要·不紧急",
    (0, 1): "不重要·紧急",
    (0, 0): "不重要·不紧急",
}


class TaskDialog(QDialog):
    def __init__(self, task=None, default_quadrant=None, prefill=None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("新建任务" if task is None else "编辑任务")
        self.setModal(True)
        self.setMinimumWidth(420)
        self.setWindowFlags(self.windowFlags() | Qt.WindowStaysOnTopHint)
        self._task = task

        form = QFormLayout(self)

        self.title_edit = QLineEdit()
        self.title_edit.setPlaceholderText("任务标题")
        form.addRow("标题", self.title_edit)

        self.note_edit = QPlainTextEdit()
        self.note_edit.setPlaceholderText("备注（可选）")
        self.note_edit.setMaximumHeight(90)
        form.addRow("备注", self.note_edit)

        quad = QHBoxLayout()
        self.imp_check = QCheckBox("重要")
        self.urg_check = QCheckBox("紧急")
        quad.addWidget(self.imp_check)
        quad.addWidget(self.urg_check)
        quad.addStretch(1)
        self.quad_hint = QLabel("")
        self.quad_hint.setStyleSheet("color:#999;")
        quad.addWidget(self.quad_hint)
        form.addRow("象限", quad)

        self.dir_edit = QLineEdit()
        self.dir_edit.setPlaceholderText("可选：关联目录绝对路径")
        dir_row = QHBoxLayout()
        dir_row.addWidget(self.dir_edit)
        browse = QPushButton("浏览…")
        browse.clicked.connect(self._browse)
        dir_row.addWidget(browse)
        form.addRow("目录", dir_row)

        self.due_check = QCheckBox("截止时间")
        self.due_edit = QDateTimeEdit()
        self.due_edit.setDisplayFormat("yyyy-MM-dd HH:mm")
        self.due_edit.setCalendarPopup(True)
        self.due_edit.setDateTime(QDateTime.currentDateTime().addDays(1))
        due_row = QHBoxLayout()
        due_row.addWidget(self.due_check)
        due_row.addWidget(self.due_edit, 1)
        form.addRow("提醒", due_row)

        self.imp_check.stateChanged.connect(self._update_hint)
        self.urg_check.stateChanged.connect(self._update_hint)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.button(QDialogButtonBox.Ok).setText("确定")
        buttons.button(QDialogButtonBox.Cancel).setText("取消")
        buttons.accepted.connect(self._on_accept)
        buttons.rejected.connect(self.reject)
        form.addRow(buttons)

        if task is not None:
            self._fill(task)
        elif prefill is not None:
            self._fill(prefill)
        elif default_quadrant is not None:
            from app.ui.quadrant_view import QUADRANTS
            q = QUADRANTS[default_quadrant]
            self.imp_check.setChecked(bool(q["important"]))
            self.urg_check.setChecked(bool(q["urgent"]))
        self._update_hint()

    def _fill(self, data):
        self.title_edit.setText(data.get("title", ""))
        self.note_edit.setPlainText(data.get("note", ""))
        self.imp_check.setChecked(bool(data.get("important")))
        self.urg_check.setChecked(bool(data.get("urgent")))
        if data.get("dir_path"):
            self.dir_edit.setText(data["dir_path"])
        if data.get("due_at"):
            dt = QDateTime.fromString(data["due_at"], "yyyy-MM-dd HH:mm")
            if dt.isValid():
                self.due_check.setChecked(True)
                self.due_edit.setDateTime(dt)

    def _browse(self):
        start = self.dir_edit.text() or os.path.expanduser("~")
        d = QFileDialog.getExistingDirectory(self, "选择关联目录", start)
        if d:
            self.dir_edit.setText(d)

    def _update_hint(self):
        key = (1 if self.imp_check.isChecked() else 0,
               1 if self.urg_check.isChecked() else 0)
        self.quad_hint.setText("→ " + _QUAD_NAME[key])

    def _on_accept(self):
        if not self.title_edit.text().strip():
            from app.ui.message import warn
            warn(self, "提示", "标题不能为空")
            return
        self.accept()

    def result_data(self):
        return {
            "title": self.title_edit.text().strip(),
            "note": self.note_edit.toPlainText().strip(),
            "important": 1 if self.imp_check.isChecked() else 0,
            "urgent": 1 if self.urg_check.isChecked() else 0,
            "dir_path": self.dir_edit.text().strip() or None,
            "due_at": self.due_edit.dateTime().toString("yyyy-MM-dd HH:mm") if self.due_check.isChecked() else None,
        }
