"""截止时间与到期提醒：QTimer 扫描及桌面通知。"""
import datetime
import subprocess
import sys

from PyQt5.QtCore import QObject, QTimer, pyqtSignal

from app import db

DUE_FORMAT = "%Y-%m-%d %H:%M"


def parse_due(due_at):
    if not due_at:
        return None
    try:
        return datetime.datetime.strptime(due_at, DUE_FORMAT)
    except (ValueError, TypeError):
        return None


def is_overdue(due_at, now=None):
    dt = parse_due(due_at)
    if dt is None:
        return False
    return dt <= (now or datetime.datetime.now())


class Reminder(QObject):
    task_due = pyqtSignal(str, str)  # title, note

    def __init__(self, parent=None):
        super().__init__(parent)
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.check)
        self.timer.start(60_000)  # 每 60 秒扫描一次

    def check(self):
        now = datetime.datetime.now()
        for t in db.list_tasks():
            if t["done"] or t["reminded"] or not t["due_at"]:
                continue
            dt = parse_due(t["due_at"])
            if dt is None or dt > now:
                continue
            db.set_reminded(t["id"], 1)
            self.task_due.emit(t["title"], t.get("note") or "")
            if sys.platform != "win32":
                self._notify(t["title"])

    def _notify(self, title):
        try:
            subprocess.Popen(
                ["notify-send", "-a", "todo-quadrant", "任务到期", title],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        except Exception:
            pass
