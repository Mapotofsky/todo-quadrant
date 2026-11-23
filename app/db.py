"""SQLite 数据访问层：任务 + 设置（零第三方依赖，Python 标准库）。"""
import os
import sqlite3
import datetime
import sys
from contextlib import closing
from pathlib import Path
from tempfile import TemporaryDirectory


def _legacy_db_path():
    return Path.home() / ".config" / "todo-quadrant" / "todo.db"


def _db_path():
    override = os.environ.get("TODO_QUADRANT_DB")
    if override:
        return Path(override)
    if sys.platform == "win32":
        local = os.environ.get("LOCALAPPDATA") or Path.home() / "AppData" / "Local"
        return Path(local) / "TodoQuadrant" / "todo.db"
    return _legacy_db_path()


def _migrate_windows_db():
    target = _db_path()
    source = _legacy_db_path()
    if target.exists() or not source.is_file():
        return
    target.parent.mkdir(parents=True, exist_ok=True)
    with TemporaryDirectory(dir=target.parent) as directory:
        backup = Path(directory) / target.name
        with closing(sqlite3.connect(source.as_uri() + "?mode=ro", uri=True)) as src:
            with closing(sqlite3.connect(backup)) as dst:
                src.backup(dst)
        try:
            backup.rename(target)
        except FileExistsError:
            # Windows 的 rename 不覆盖并发启动已经创建的目标库。
            pass


def connect():
    path = _db_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    return conn


def init():
    if sys.platform == "win32" and not os.environ.get("TODO_QUADRANT_DB"):
        _migrate_windows_db()
    with closing(connect()) as conn, conn:
        _init_schema(conn)
        conn.execute("BEGIN IMMEDIATE")
        columns = {row["name"] for row in conn.execute("PRAGMA table_info(tasks)")}
        if "hide_when_collapsed" not in columns:
            conn.execute(
                "ALTER TABLE tasks ADD COLUMN hide_when_collapsed INTEGER NOT NULL DEFAULT 0"
            )


def _init_schema(conn):
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
            completed_at TEXT,
            hide_when_collapsed INTEGER NOT NULL DEFAULT 0
        );
        CREATE INDEX IF NOT EXISTS idx_tasks_open ON tasks(done, important, urgent);
        CREATE TABLE IF NOT EXISTS settings (
            key   TEXT PRIMARY KEY,
            value TEXT
        );
        """
    )


def _now(timespec="seconds"):
    return datetime.datetime.now().isoformat(timespec=timespec)


def add_task(title, note="", important=0, urgent=0, dir_path=None, due_at=None,
             hide_when_collapsed=False):
    conn = connect()
    cur = conn.execute(
        "INSERT INTO tasks (title, note, important, urgent, dir_path, due_at, created_at, hide_when_collapsed) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        (title, note, int(important), int(urgent), dir_path, due_at, _now(), int(hide_when_collapsed)),
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
    allowed = {"title", "note", "important", "urgent", "dir_path", "due_at", "hide_when_collapsed"}
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
        (int(done), _now("microseconds") if done else None, task_id),
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
