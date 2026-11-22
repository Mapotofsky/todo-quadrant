"""真实 X11 置顶验证：创建置顶窗口，读取自身 _NET_WM_STATE，自终止。"""
import os
import sys
import subprocess

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _ROOT)
os.environ["QT_QPA_PLATFORM"] = "xcb"

from PyQt5.QtWidgets import QApplication, QWidget  # noqa: E402
from PyQt5.QtCore import Qt, QTimer  # noqa: E402


def main():
    app = QApplication([])
    w = QWidget()
    w.setWindowTitle("todo-quadrant-above-test")
    w.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
    w.resize(200, 100)
    w.show()

    def check():
        wid = int(w.winId())
        try:
            out = subprocess.run(
                ["xprop", "-id", str(wid), "_NET_WM_STATE"],
                capture_output=True, text=True, timeout=5,
            )
            print("winid =", wid)
            print(out.stdout.strip() or "(no _NET_WM_STATE output)")
            if out.stderr.strip():
                print("stderr:", out.stderr.strip())
        except Exception as e:  # noqa: BLE001
            print("xprop failed:", e)
        app.quit()

    QTimer.singleShot(1500, check)
    app.exec_()


if __name__ == "__main__":
    main()
