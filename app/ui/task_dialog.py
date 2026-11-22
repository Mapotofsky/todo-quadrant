"""任务新建 / 编辑对话框（含截止时间与 AI 预填）。"""
import os
import shutil
import subprocess
import sys

from PyQt5.QtCore import Qt, QDateTime, QTimer
from PyQt5.QtGui import QPalette
from PyQt5.QtWidgets import (
    QApplication, QDialog, QFormLayout, QLineEdit, QPlainTextEdit, QCheckBox,
    QHBoxLayout, QPushButton, QFileDialog, QLabel, QDateTimeEdit, QWidget,
)

from app.ui.button_box import FixedTextButtonBox

_PICKER_TITLE = "选择关联目录"


def _system_picker_qss():
    """按系统调色板生成目录选择器的局部样式。

    UKUI 的原生文件对话框由 qt5-ukui-filedialog 插件在本进程内创建，会继承
    应用的全局 QSS。结果是文件列表、侧栏跟随系统（浅色），按钮和输入框却
    被染成应用的深色，出现半系统半应用的割裂外观。这里用系统调色板覆盖应用
    QSS 影响对话框的那几条规则，让选择器整体回到系统配色。
    """
    palette = QApplication.palette()
    colors = {
        "window": palette.color(QPalette.Window).name(),
        "window_text": palette.color(QPalette.WindowText).name(),
        "base": palette.color(QPalette.Base).name(),
        "text": palette.color(QPalette.Text).name(),
        "button": palette.color(QPalette.Button).name(),
        "button_text": palette.color(QPalette.ButtonText).name(),
        "light": palette.color(QPalette.Light).name(),
        "mid": palette.color(QPalette.Mid).name(),
        "midlight": palette.color(QPalette.Midlight).name(),
        "highlight": palette.color(QPalette.Highlight).name(),
        "highlighted_text": palette.color(QPalette.HighlightedText).name(),
    }
    return """
QDialog { background-color: %(window)s; color: %(window_text)s; }
QDialog QLabel, QDialog QCheckBox { color: %(window_text)s; background: transparent; }
QDialog QCheckBox { spacing: 4px; }
QDialog QPushButton { background-color: %(button)s; color: %(button_text)s;
    border: 1px solid %(mid)s; border-radius: 4px; padding: 3px 8px; }
QDialog QPushButton:hover { background-color: %(light)s; }
QDialog QPushButton:pressed { background-color: %(midlight)s; }
QDialog QLineEdit, QDialog QComboBox, QDialog QSpinBox {
    background-color: %(base)s; color: %(text)s;
    border: 1px solid %(mid)s; border-radius: 4px; padding: 4px 6px;
    selection-background-color: %(highlight)s; selection-color: %(highlighted_text)s; }
QDialog QComboBox QAbstractItemView { background-color: %(base)s; color: %(text)s;
    selection-background-color: %(highlight)s; selection-color: %(highlighted_text)s; }
QDialog QScrollBar:vertical { background: transparent; width: 10px; margin: 0; }
QDialog QScrollBar::handle:vertical { background: %(mid)s; border-radius: 5px; min-height: 20px; }
QDialog QScrollBar::add-line:vertical, QDialog QScrollBar::sub-line:vertical { height: 0; }
QDialog QMenu { background-color: %(window)s; color: %(window_text)s; border: 1px solid %(mid)s; }
QDialog QMenu::item:selected { background-color: %(highlight)s; color: %(highlighted_text)s; }
""" % colors


def _style_picker_window(window):
    window.setStyleSheet(_system_picker_qss())
    if sys.platform != "win32" and shutil.which("wmctrl"):
        # 用 EWMH 加 above；对原生窗口 setWindowFlags 会重建窗口并报 BadWindow。
        try:
            subprocess.run(
                ["wmctrl", "-i", "-r", hex(int(window.winId())), "-b", "add,above"],
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                check=False, timeout=2)
        except (OSError, subprocess.SubprocessError):
            pass
    else:
        window.setWindowFlag(Qt.WindowStaysOnTopHint, True)
        window.show()
    window.raise_()
    window.activateWindow()


def _tune_native_picker(dialog, attempt=0):
    """把原生目录选择器置顶，并让它按系统配色显示。

    UKUI 的文件对话框是本进程内的 QDialog，默认没有置顶标记，会被设置了
    WindowStaysOnTopHint 的悬浮窗和任务对话框盖住；它和 QFileDialog 包装层
    是两个不同的顶层窗口，包装层不可见，不能对它下手。这里在弹出后（open()
    不阻塞）按标题找回真正的对话框再补置顶和系统配色；找不到时静默放弃，
    对话框本身仍可用。
    """
    if not dialog.isVisible():
        return
    helper = None
    for widget in QApplication.topLevelWidgets():
        if (widget is not dialog and isinstance(widget, QDialog)
                and widget.isVisible()
                and widget.windowTitle() == dialog.windowTitle()):
            helper = widget
            break
    if helper is not None:
        _style_picker_window(helper)
        return
    if attempt < 60:
        QTimer.singleShot(50, lambda: _tune_native_picker(dialog, attempt + 1))
        return
    # 没有独立顶层窗口，说明当前平台用的是 Qt 内置文件对话框。
    if dialog.isVisible():
        _style_picker_window(dialog)


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
        self.setWindowFlags((self.windowFlags() | Qt.WindowStaysOnTopHint)
                            & ~Qt.WindowContextHelpButtonHint)
        self._task = task
        self._dir_picker = None

        form = QFormLayout(self)

        self.title_edit = QLineEdit()
        self.title_edit.setPlaceholderText("任务标题")
        form.addRow("标题", self.title_edit)

        quad = QHBoxLayout()
        self.imp_check = QCheckBox("重要")
        self.urg_check = QCheckBox("紧急")
        quad.addWidget(self.imp_check)
        quad.addWidget(self.urg_check)
        quad.addStretch(1)
        self.quad_hint = QLabel("")
        self.quad_hint.setObjectName("quad_hint")
        quad.addWidget(self.quad_hint)
        form.addRow("象限", quad)

        self.options_btn = QPushButton("更多选项")
        self.options_btn.setCheckable(True)
        self.options_btn.setAutoDefault(False)
        form.addRow("", self.options_btn)
        self.options = QWidget()
        details = QFormLayout(self.options)
        details.setContentsMargins(0, 0, 0, 0)
        form.addRow(self.options)

        self.note_edit = QPlainTextEdit()
        self.note_edit.setPlaceholderText("备注（可选）")
        self.note_edit.setFixedHeight(68)
        details.addRow("备注", self.note_edit)

        self.dir_edit = QLineEdit()
        self.dir_edit.setPlaceholderText("可选：关联目录绝对路径")
        dir_row = QHBoxLayout()
        dir_row.addWidget(self.dir_edit)
        browse = QPushButton("浏览…")
        browse.setAutoDefault(False)
        browse.clicked.connect(self._browse)
        dir_row.addWidget(browse)
        details.addRow("目录", dir_row)

        self.due_check = QCheckBox("截止时间")
        self.due_edit = QDateTimeEdit()
        self.due_edit.setDisplayFormat("yyyy-MM-dd HH:mm")
        self.due_edit.setCalendarPopup(True)
        self.due_edit.setDateTime(QDateTime.currentDateTime().addDays(1))
        self.due_edit.setEnabled(False)
        self.due_check.toggled.connect(self.due_edit.setEnabled)
        due_row = QHBoxLayout()
        due_row.addWidget(self.due_check)
        due_row.addWidget(self.due_edit, 1)
        details.addRow("提醒", due_row)

        self.imp_check.stateChanged.connect(self._update_hint)
        self.urg_check.stateChanged.connect(self._update_hint)

        # 不用裸 QDialogButtonBox：UKUI 文件对话框插件会触发 LanguageChange，
        # 标准按钮会被重译成英文 OK/Cancel，覆盖手工文案。
        buttons = FixedTextButtonBox("保存", "取消")
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
        has_details = bool(self.note_edit.toPlainText() or self.dir_edit.text()
                           or self.due_check.isChecked())
        self.options_btn.setChecked(has_details)
        self._show_options(has_details)
        self.options_btn.toggled.connect(self._show_options)
        self.title_edit.setFocus()

    def _show_options(self, visible):
        self.options.setVisible(visible)
        self.options_btn.setText("收起更多选项" if visible else "更多选项")
        self.layout().activate()
        if self.isVisible():
            self.resize(self.width(), self.sizeHint().height())

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
        if sys.platform == "win32":
            # Windows 继续使用系统原生目录对话框，不参与 Linux 的置顶/配色修补。
            chosen = QFileDialog.getExistingDirectory(self, _PICKER_TITLE, start)
            if chosen:
                self.dir_edit.setText(chosen)
            return
        if self._dir_picker is not None:
            self._dir_picker.raise_()
            self._dir_picker.activateWindow()
            return

        picker = QFileDialog(self, _PICKER_TITLE, start)
        picker.setFileMode(QFileDialog.Directory)
        picker.setOption(QFileDialog.ShowDirsOnly, True)
        picker.setWindowModality(Qt.ApplicationModal)
        self._dir_picker = picker
        picker.finished.connect(self._on_dir_picker_finished)
        picker.open()
        _tune_native_picker(picker)

    def _on_dir_picker_finished(self, result):
        picker = self.sender()
        if not isinstance(picker, QFileDialog):
            picker = self._dir_picker
        if picker is None:
            return
        if picker is self._dir_picker:
            self._dir_picker = None
        if result == QDialog.Accepted and picker.selectedFiles():
            self.dir_edit.setText(picker.selectedFiles()[0])
        picker.deleteLater()

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
