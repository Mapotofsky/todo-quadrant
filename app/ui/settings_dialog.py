"""AI 接口设置对话框。"""
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QDialog, QFormLayout, QLineEdit, QLabel,
)

from app import config
from app.ui.button_box import FixedTextButtonBox


class SettingsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("AI 接口设置")
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

        # 同 TaskDialog：标准 Ok/Cancel 会被 LanguageChange 重译成英文。
        buttons = FixedTextButtonBox("保存", "取消")
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        form.addRow(buttons)

    def save(self):
        config.set_ai_config(
            self.base_url.text().strip(),
            self.api_key.text().strip(),
            self.model.text().strip(),
        )
