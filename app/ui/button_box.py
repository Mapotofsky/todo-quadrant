"""固定文案的 QDialogButtonBox。

麒麟的 qt5-ukui-filedialog 插件在打开/关闭文件对话框时会加载、卸载
QTranslator，Qt 随之向所有控件发送 LanguageChange。QDialogButtonBox 收到后
会把标准 Ok/Cancel 按当前翻译重新设置，覆盖掉调用方手工写入的中文文案
（应用没装 Qt 中文翻译，于是显示成英文 OK/Cancel）。

保留标准 Ok/Cancel 可以继续享受默认按钮和平台按钮顺序，这里只在其
changeEvent 之后再写回文案。
"""
from PyQt5.QtCore import QEvent
from PyQt5.QtWidgets import QDialogButtonBox


class FixedTextButtonBox(QDialogButtonBox):
    def __init__(self, ok_text, cancel_text, parent=None):
        super().__init__(QDialogButtonBox.Ok | QDialogButtonBox.Cancel, parent)
        self._texts = {
            QDialogButtonBox.Ok: ok_text,
            QDialogButtonBox.Cancel: cancel_text,
        }
        self._apply_texts()

    def _apply_texts(self):
        for standard, text in self._texts.items():
            button = self.button(standard)
            if button is not None:
                button.setText(text)

    def changeEvent(self, event):
        super().changeEvent(event)
        if event.type() == QEvent.LanguageChange:
            self._apply_texts()
