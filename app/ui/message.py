"""统一的深色消息/确认对话框。

不用 QMessageBox：UKUI/KDE 平台主题会用「原生对话框助手」接管 QMessageBox，
导致其忽略 QSS（白底白字）。自定义 QDialog 不经过该通道，样式完全可控。
"""
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton


class MessageDialog(QDialog):
    def __init__(self, title, text, buttons, default_index=0, parent=None):
        """buttons: [(按钮文字, ...), ...]，default_index 为默认聚焦按钮。"""
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setModal(True)
        self.setWindowFlags(self.windowFlags() | Qt.WindowStaysOnTopHint)
        self.result_index = -1

        lay = QVBoxLayout(self)
        lay.setContentsMargins(18, 16, 18, 14)
        lay.setSpacing(16)

        lbl = QLabel(text)
        lbl.setWordWrap(True)
        lbl.setMinimumWidth(260)
        lay.addWidget(lbl)

        row = QHBoxLayout()
        row.setSpacing(8)
        row.addStretch(1)
        self._buttons = []
        for i, (btn_text, _) in enumerate(buttons):
            btn = QPushButton(btn_text)
            btn.setMinimumWidth(76)
            btn.setMinimumHeight(26)
            btn.clicked.connect(lambda checked, idx=i: self._finish(idx))
            row.addWidget(btn)
            self._buttons.append(btn)
        lay.addLayout(row)

        default_index = max(0, min(default_index, len(self._buttons) - 1))
        self._buttons[default_index].setDefault(True)
        self._buttons[default_index].setFocus()

    def _finish(self, idx):
        self.result_index = idx
        self.accept()


def confirm(parent, title, text, yes="删除", no="取消"):
    """确认对话框，默认焦点在「取消」。返回 True 表示用户点了 yes。"""
    dlg = MessageDialog(title, text, [(no, "no"), (yes, "yes")],
                        default_index=0, parent=parent)
    dlg.exec_()
    return dlg.result_index == 1


def warn(parent, title, text, ok="知道了"):
    """提示对话框。"""
    dlg = MessageDialog(title, text, [(ok, "ok")], parent=parent)
    dlg.exec_()
