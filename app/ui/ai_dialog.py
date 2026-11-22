"""AI 粘贴总结对话框：粘贴原文 → 后台线程调用 AI → 得到结构化结果。"""
from PyQt5.QtCore import Qt, QThread, pyqtSignal
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QPlainTextEdit, QPushButton, QLabel,
)

from app import config
from app import ai


class SummarizeThread(QThread):
    result_ready = pyqtSignal(object)
    error_occurred = pyqtSignal(str)

    def __init__(self, text, cfg):
        super().__init__()
        self.text = text
        self.cfg = cfg

    def run(self):
        try:
            r = ai.summarize(
                self.text,
                self.cfg["base_url"],
                self.cfg["api_key"],
                self.cfg["model"],
                system_prompt=self.cfg.get("system_prompt", ""),
            )
            self.result_ready.emit(r)
        except Exception as e:  # noqa: BLE001
            self.error_occurred.emit(str(e))


class AiDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("AI 总结任务")
        self.setModal(True)
        self.setMinimumSize(480, 340)
        self.setWindowFlags(self.windowFlags() | Qt.WindowStaysOnTopHint)
        self.result = None
        self._thread = None

        lay = QVBoxLayout(self)
        self.hint = QLabel("粘贴聊天/文本，AI 将总结为一条待办任务（需先设置接口）")
        self.text_edit = QPlainTextEdit()
        self.text_edit.setPlaceholderText("在此粘贴原始文本…")
        self.status = QLabel("")
        self.status.setStyleSheet("color:#999;")

        btn_row = QHBoxLayout()
        btn_row.addStretch(1)
        self.cancel_btn = QPushButton("取消")
        self.summarize_btn = QPushButton("总结为任务")
        btn_row.addWidget(self.cancel_btn)
        btn_row.addWidget(self.summarize_btn)

        lay.addWidget(self.hint)
        lay.addWidget(self.text_edit, 1)
        lay.addWidget(self.status)
        lay.addLayout(btn_row)

        self.cancel_btn.clicked.connect(self.reject)
        self.summarize_btn.clicked.connect(self._summarize)

    def _summarize(self):
        from app.ui.message import warn
        text = self.text_edit.toPlainText().strip()
        if not text:
            warn(self, "提示", "请先粘贴文本")
            return
        c = config.get_ai_config()
        if not c["api_key"]:
            warn(self, "提示", "尚未配置 API Key，请先在「设置」中填写")
            return
        if self._thread is not None and self._thread.isRunning():
            return

        self.summarize_btn.setEnabled(False)
        self.cancel_btn.setEnabled(False)
        self.status.setText("正在总结…")

        self._thread = SummarizeThread(text, c)
        self._thread.result_ready.connect(self._on_result)
        self._thread.error_occurred.connect(self._on_error)
        self._thread.start()

    def _on_result(self, r):
        if self._thread is not None:
            self._thread.wait()
        self.result = r
        self.accept()

    def _on_error(self, msg):
        from app.ui.message import warn
        if self._thread is not None:
            self._thread.wait()
        self.status.setText("")
        self.summarize_btn.setEnabled(True)
        self.cancel_btn.setEnabled(True)
        warn(self, "总结失败", f"调用 AI 失败：{msg}\n\n原文已保留，可改用手动录入。")
