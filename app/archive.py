"""将已完成任务归档为 Markdown。"""
import os
import sqlite3
from contextlib import closing
from datetime import datetime
from pathlib import Path
from tempfile import NamedTemporaryFile

from app import db
from app.quadrants import QUADRANTS, quadrant_of


class ArchiveCommitError(Exception):
    def __init__(self, path):
        super().__init__(str(path))
        self.path = path


def _markdown(tasks):
    sections = ["# 已完成"]
    previous_date = None
    for task in tasks:
        date = task["completed_at"][:10]
        if date != previous_date:
            sections.append(f"## {date}")
            previous_date = date
        sections.append(f"### {task['title']}")
        quadrant = quadrant_of(task["important"], task["urgent"])
        sections.append(QUADRANTS[quadrant]["name"])
        sections.extend(task[field] for field in ("note", "dir_path", "due_at") if task[field])
    return "\n\n".join(sections) + "\n"


def _publish(directory, content):
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S-%f")
    temp = NamedTemporaryFile(
        mode="w", encoding="utf-8", newline="\n", dir=directory,
        prefix=f"已完成-{timestamp}-", suffix=".tmp", delete=False,
    )
    source = Path(temp.name)
    target = source.with_suffix(".md")
    try:
        with temp:
            temp.write(content)
            temp.flush()
            os.fsync(temp.fileno())
        if target.exists():
            raise FileExistsError(f"归档文件已存在：{target}")
        source.replace(target)
    except OSError:
        source.unlink(missing_ok=True)
        raise
    return target


def archive_completed(directory):
    """归档当前已完成的任务，返回文件路径。没有完成项时返回 None。"""
    directory = Path(os.path.abspath(os.path.expanduser(directory)))
    path = None
    try:
        with closing(db.connect()) as conn, conn:
            conn.execute("BEGIN IMMEDIATE")
            tasks = conn.execute(
                "SELECT * FROM tasks WHERE done = 1 ORDER BY completed_at, id"
            ).fetchall()
            if not tasks:
                return None
            path = _publish(directory, _markdown(tasks))
            conn.executemany("DELETE FROM tasks WHERE id = ?", ((task["id"],) for task in tasks))
    except sqlite3.Error as exc:
        if path is not None:
            raise ArchiveCommitError(path) from exc
        raise
    return path
