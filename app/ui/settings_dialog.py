"""应用设置对话框。"""
import os

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QDialog, QFileDialog, QFormLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton,
)

from app import config
from app.ui.button_box import FixedTextButtonBox


class SettingsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("设置")
        self.setModal(True)
        self.setMinimumWidth(440)
        self.setWindowFlags(self.windowFlags() | Qt.WindowStaysOnTopHint)

        c = config.get_ai_config()
        form = QFormLayout(self)

        self.base_url = QLineEdit(c["base_url"])
        self.api_key = QLineEdit(c["api_key"])
        self.api_key.setEchoMode(QLineEdit.Password)
        self.model = QLineEdit(c["model"])
        form.addRow("Base URL", self.base_url)
        form.addRow("API Key", self.api_key)
        form.addRow("Model", self.model)

        hint = QLabel("OpenAI 兼容接口。key 以明文存于本机 SQLite，仅个人使用。")
        hint.setStyleSheet("color:#999;")
        form.addRow(hint)

        self.archive_dir = QLineEdit(config.get_archive_dir())
        browse = QPushButton("浏览…")
        browse.setAutoDefault(False)
        browse.clicked.connect(self._browse_archive_dir)
        archive_row = QHBoxLayout()
        archive_row.addWidget(self.archive_dir, 1)
        archive_row.addWidget(browse)
        form.addRow("归档目录", archive_row)

        # 同 TaskDialog：标准 Ok/Cancel 会被 LanguageChange 重译成英文。
        buttons = FixedTextButtonBox("保存", "取消")
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        form.addRow(buttons)

    def _browse_archive_dir(self):
        start = self.archive_dir.text().strip() or os.path.expanduser("~")
        picker = QFileDialog(self)
        picker.setOption(QFileDialog.DontUseNativeDialog)
        picker.setWindowTitle("选择归档目录")
        picker.setDirectory(os.path.expanduser(start))
        picker.setFileMode(QFileDialog.Directory)
        picker.setOption(QFileDialog.ShowDirsOnly)
        picker.setWindowFlag(Qt.WindowStaysOnTopHint)
        if picker.exec_() == QDialog.Accepted:
            self.archive_dir.setText(picker.selectedFiles()[0])

    def save(self):
        config.set_ai_config(
            self.base_url.text().strip(),
            self.api_key.text().strip(),
            self.model.text().strip(),
        )
        config.set_archive_dir(self.archive_dir.text())
