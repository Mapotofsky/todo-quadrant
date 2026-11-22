"""SQLite 数据访问层：任务 + 设置（零第三方依赖，Python 标准库）。"""
import os
import sqlite3
import datetime


def _db_path():
    override = os.environ.get("TODO_QUADRANT_DB")
    if override:
        return override
    return os.path.join(os.path.expanduser("~"), ".config", "todo-quadrant", "todo.db")


def connect():
    path = _db_path()
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    return conn


def init():
    conn = connect()
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS tasks (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            title        TEXT    NOT NULL,
            note         TEXT    DEFAULT '',
            important    INTEGER NOT NULL DEFAULT 0,
            urgent       INTEGER NOT NULL DEFAULT 0,
            dir_path     TEXT,
            due_at       TEXT,
            done         INTEGER NOT NULL DEFAULT 0,
            reminded     INTEGER NOT NULL DEFAULT 0,
            sort_order   INTEGER NOT NULL DEFAULT 0,
            created_at   TEXT    NOT NULL,
            completed_at TEXT
        );
        CREATE INDEX IF NOT EXISTS idx_tasks_open ON tasks(done, important, urgent);
        CREATE TABLE IF NOT EXISTS settings (
            key   TEXT PRIMARY KEY,
            value TEXT
        );
        """
    )
    conn.commit()
    conn.close()


def _now():
    return datetime.datetime.now().isoformat(timespec="seconds")


def add_task(title, note="", important=0, urgent=0, dir_path=None, due_at=None):
    conn = connect()
    cur = conn.execute(
        "INSERT INTO tasks (title, note, important, urgent, dir_path, due_at, done, reminded, sort_order, created_at) "
        "VALUES (?, ?, ?, ?, ?, ?, 0, 0, 0, ?)",
        (title, note, int(important), int(urgent), dir_path, due_at, _now()),
    )
    conn.commit()
    task_id = cur.lastrowid
    conn.close()
    return task_id


def get_task(task_id):
    conn = connect()
    row = conn.execute("SELECT * FROM tasks WHERE id = ?", (task_id,)).fetchone()
    conn.close()
    return dict(row) if row else None


def list_tasks():
    conn = connect()
    rows = conn.execute("SELECT * FROM tasks ORDER BY sort_order ASC, id ASC").fetchall()
    conn.close()
    return [dict(r) for r in rows]


def update_task(task_id, **fields):
    allowed = {"title", "note", "important", "urgent", "dir_path", "due_at"}
    updates = {k: v for k, v in fields.items() if k in allowed}
    if "due_at" in updates:
        updates["reminded"] = 0  # 改期后重置提醒
    if not updates:
        return
    sets = ", ".join(f"{k} = ?" for k in updates)
    conn = connect()
    conn.execute(f"UPDATE tasks SET {sets} WHERE id = ?", (*updates.values(), task_id))
    conn.commit()
    conn.close()


def delete_task(task_id):
    conn = connect()
    conn.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
    conn.commit()
    conn.close()


def set_done(task_id, done):
    conn = connect()
    conn.execute(
        "UPDATE tasks SET done = ?, completed_at = ? WHERE id = ?",
        (int(done), _now() if done else None, task_id),
    )
    conn.commit()
    conn.close()


def set_quadrant(task_id, important, urgent):
    conn = connect()
    conn.execute(
        "UPDATE tasks SET important = ?, urgent = ? WHERE id = ?",
        (int(important), int(urgent), task_id),
    )
    conn.commit()
    conn.close()


def set_sort_order(task_id, order):
    conn = connect()
    conn.execute("UPDATE tasks SET sort_order = ? WHERE id = ?", (order, task_id))
    conn.commit()
    conn.close()


def set_reminded(task_id, reminded):
    conn = connect()
    conn.execute("UPDATE tasks SET reminded = ? WHERE id = ?", (int(reminded), task_id))
    conn.commit()
    conn.close()


def get_setting(key, default=None):
    conn = connect()
    row = conn.execute("SELECT value FROM settings WHERE key = ?", (key,)).fetchone()
    conn.close()
    return row["value"] if row else default


def set_setting(key, value):
    conn = connect()
    conn.execute(
        "INSERT INTO settings (key, value) VALUES (?, ?) "
        "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
        (key, str(value)),
    )
    conn.commit()
    conn.close()
