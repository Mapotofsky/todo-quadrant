"""真实 xcb 验证 QMessageBox 深色样式（Fusion 基础样式下）。"""
import os
import sys

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _ROOT)
os.environ["QT_QPA_PLATFORM"] = "xcb"

from PyQt5.QtWidgets import QApplication, QMessageBox  # noqa: E402
from PyQt5.QtCore import QTimer  # noqa: E402


def main():
    app = QApplication([])
    app.setStyle("fusion")
    with open(os.path.join(_ROOT, "resources", "style.qss"), encoding="utf-8") as f:
        app.setStyleSheet(f.read())

    box = QMessageBox()
    box.setWindowTitle("删除")
    box.setText("删除任务「df」？")
    box.setIcon(QMessageBox.Question)
    box.addButton("删除", QMessageBox.YesRole)
    box.addButton("取消", QMessageBox.NoRole)
    box.show()
    box.raise_()
    box.activateWindow()

    def cap():
        pix = box.grab()  # 直接渲染控件自身，不受遮挡影响
        out = os.path.join(_ROOT, "msgbox_real.png")
        pix.save(out, "PNG")
        print(f"SAVED {out} {pix.width()}x{pix.height()}")
        app.quit()

    QTimer.singleShot(1500, cap)
    app.exec_()


if __name__ == "__main__":
    main()
