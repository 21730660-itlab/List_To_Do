"""SQLite storage for tasks, notes and the links between them.

SQLite was chosen because it ships with Python, keeps everything in a single
file that is easy to back up, needs no server, and lets tasks and notes be
related to each other (many-to-many) with real foreign keys.
"""

from __future__ import annotations

import os
import sqlite3
import sys
from datetime import date, datetime
from pathlib import Path

STATUSES = ("Open", "In Progress", "Done")
PRIORITIES = ("Critical", "High", "Medium", "Low")

SCHEMA = """
CREATE TABLE IF NOT EXISTS tasks (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    title        TEXT NOT NULL,
    description  TEXT NOT NULL DEFAULT '',
    category     TEXT NOT NULL DEFAULT 'General',
    priority     TEXT NOT NULL DEFAULT 'Medium',
    status       TEXT NOT NULL DEFAULT 'Open',
    due_date     TEXT,
    created_at   TEXT NOT NULL,
    updated_at   TEXT NOT NULL,
    completed_at TEXT
);

CREATE TABLE IF NOT EXISTS notes (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    title       TEXT NOT NULL,
    body        TEXT NOT NULL DEFAULT '',
    category    TEXT NOT NULL DEFAULT 'General',
    tags        TEXT NOT NULL DEFAULT '',
    pinned      INTEGER NOT NULL DEFAULT 0,
    created_at  TEXT NOT NULL,
    updated_at  TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS task_notes (
    task_id INTEGER NOT NULL REFERENCES tasks(id) ON DELETE CASCADE,
    note_id INTEGER NOT NULL REFERENCES notes(id) ON DELETE CASCADE,
    PRIMARY KEY (task_id, note_id)
);

CREATE INDEX IF NOT EXISTS idx_tasks_status ON tasks(status);
CREATE INDEX IF NOT EXISTS idx_task_notes_note ON task_notes(note_id);
"""

_PRIORITY_RANK = "CASE priority WHEN 'Critical' THEN 0 WHEN 'High' THEN 1 WHEN 'Medium' THEN 2 ELSE 3 END"
_STATUS_RANK = "CASE status WHEN 'In Progress' THEN 0 WHEN 'Open' THEN 1 ELSE 2 END"

_TASK_FIELDS = {"title", "description", "category", "priority", "status", "due_date"}
_NOTE_FIELDS = {"title", "body", "category", "tags", "pinned"}


def default_db_path() -> Path:
    """Where the database lives: %APPDATA%\\NetOpsDesk on Windows."""
    override = os.environ.get("NETOPS_DESK_DB")
    if override:
        return Path(override)
    if sys.platform == "win32":
        base = Path(os.environ.get("APPDATA", Path.home() / "AppData" / "Roaming"))
        return base / "NetOpsDesk" / "netops.db"
    return Path.home() / ".netops_desk" / "netops.db"


def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")


class Database:
    def __init__(self, path: str | Path | None = None):
        self.path = Path(path) if path else default_db_path()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.is_new = not self.path.exists()
        self.conn = sqlite3.connect(self.path)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA foreign_keys = ON")
        self.conn.execute("PRAGMA journal_mode = WAL")
        self.conn.executescript(SCHEMA)
        self.conn.commit()

    def close(self) -> None:
        self.conn.close()

    # ------------------------------------------------------------------ tasks
    def add_task(self, title: str, description: str = "", category: str = "General",
                 priority: str = "Medium", due_date: str | None = None,
                 status: str = "Open") -> int:
        title = title.strip()
        if not title:
            raise ValueError("Task title cannot be empty")
        now = _now()
        cur = self.conn.execute(
            "INSERT INTO tasks (title, description, category, priority, status, due_date,"
            " created_at, updated_at, completed_at) VALUES (?,?,?,?,?,?,?,?,?)",
            (title, description, category, priority, status, due_date or None, now, now,
             now if status == "Done" else None),
        )
        self.conn.commit()
        return cur.lastrowid

    def update_task(self, task_id: int, **fields) -> None:
        unknown = set(fields) - _TASK_FIELDS
        if unknown:
            raise ValueError(f"Unknown task fields: {unknown}")
        if "title" in fields and not fields["title"].strip():
            raise ValueError("Task title cannot be empty")
        if "due_date" in fields and not fields["due_date"]:
            fields["due_date"] = None
        if "status" in fields:
            current = self.get_task(task_id)
            if fields["status"] == "Done" and current and current["status"] != "Done":
                fields["completed_at"] = _now()
            elif fields["status"] != "Done":
                fields["completed_at"] = None
        if not fields:
            return
        fields["updated_at"] = _now()
        cols = ", ".join(f"{k} = ?" for k in fields)
        self.conn.execute(f"UPDATE tasks SET {cols} WHERE id = ?", (*fields.values(), task_id))
        self.conn.commit()

    def set_task_status(self, task_id: int, status: str) -> None:
        self.update_task(task_id, status=status)

    def delete_task(self, task_id: int) -> None:
        self.conn.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
        self.conn.commit()

    def get_task(self, task_id: int) -> dict | None:
        row = self.conn.execute(self._task_select() + " WHERE t.id = ?", (task_id,)).fetchone()
        return dict(row) if row else None

    def list_tasks(self, status: str | None = None, category: str | None = None,
                   search: str | None = None, limit: int | None = None) -> list[dict]:
        sql = self._task_select() + " WHERE 1=1"
        params: list = []
        if status == "Active":
            sql += " AND t.status != 'Done'"
        elif status:
            sql += " AND t.status = ?"
            params.append(status)
        if category:
            sql += " AND t.category = ?"
            params.append(category)
        if search:
            sql += " AND (t.title LIKE ? OR t.description LIKE ?)"
            params += [f"%{search}%", f"%{search}%"]
        sql += (f" ORDER BY {_STATUS_RANK}, {_PRIORITY_RANK},"
                " t.due_date IS NULL, t.due_date, t.created_at DESC")
        if limit:
            sql += " LIMIT ?"
            params.append(limit)
        return [dict(r) for r in self.conn.execute(sql, params)]

    @staticmethod
    def _task_select() -> str:
        return ("SELECT t.*, (SELECT COUNT(*) FROM task_notes tn WHERE tn.task_id = t.id)"
                " AS note_count FROM tasks t")

    # ------------------------------------------------------------------ notes
    def add_note(self, title: str = "Untitled note", body: str = "", category: str = "General",
                 tags: str = "", pinned: bool = False) -> int:
        now = _now()
        cur = self.conn.execute(
            "INSERT INTO notes (title, body, category, tags, pinned, created_at, updated_at)"
            " VALUES (?,?,?,?,?,?,?)",
            (title.strip() or "Untitled note", body, category, tags, int(pinned), now, now),
        )
        self.conn.commit()
        return cur.lastrowid

    def update_note(self, note_id: int, **fields) -> None:
        unknown = set(fields) - _NOTE_FIELDS
        if unknown:
            raise ValueError(f"Unknown note fields: {unknown}")
        if not fields:
            return
        if "pinned" in fields:
            fields["pinned"] = int(bool(fields["pinned"]))
        if set(fields) != {"pinned"}:  # pinning is not an edit of the note itself
            fields["updated_at"] = _now()
        cols = ", ".join(f"{k} = ?" for k in fields)
        self.conn.execute(f"UPDATE notes SET {cols} WHERE id = ?", (*fields.values(), note_id))
        self.conn.commit()

    def delete_note(self, note_id: int) -> None:
        self.conn.execute("DELETE FROM notes WHERE id = ?", (note_id,))
        self.conn.commit()

    def get_note(self, note_id: int) -> dict | None:
        row = self.conn.execute(self._note_select() + " WHERE n.id = ?", (note_id,)).fetchone()
        return dict(row) if row else None

    def list_notes(self, search: str | None = None, category: str | None = None,
                   pinned_only: bool = False, limit: int | None = None) -> list[dict]:
        sql = self._note_select() + " WHERE 1=1"
        params: list = []
        if search:
            sql += " AND (n.title LIKE ? OR n.body LIKE ? OR n.tags LIKE ?)"
            params += [f"%{search}%"] * 3
        if category:
            sql += " AND n.category = ?"
            params.append(category)
        if pinned_only:
            sql += " AND n.pinned = 1"
        sql += " ORDER BY n.pinned DESC, n.updated_at DESC, n.id DESC"
        if limit:
            sql += " LIMIT ?"
            params.append(limit)
        return [dict(r) for r in self.conn.execute(sql, params)]

    @staticmethod
    def _note_select() -> str:
        return ("SELECT n.*, (SELECT COUNT(*) FROM task_notes tn WHERE tn.note_id = n.id)"
                " AS task_count FROM notes n")

    # ------------------------------------------------------------------ links
    def link(self, task_id: int, note_id: int) -> None:
        self.conn.execute("INSERT OR IGNORE INTO task_notes (task_id, note_id) VALUES (?, ?)",
                          (task_id, note_id))
        self.conn.commit()

    def unlink(self, task_id: int, note_id: int) -> None:
        self.conn.execute("DELETE FROM task_notes WHERE task_id = ? AND note_id = ?",
                          (task_id, note_id))
        self.conn.commit()

    def notes_for_task(self, task_id: int) -> list[dict]:
        rows = self.conn.execute(
            "SELECT n.* FROM notes n JOIN task_notes tn ON tn.note_id = n.id"
            " WHERE tn.task_id = ? ORDER BY n.updated_at DESC", (task_id,))
        return [dict(r) for r in rows]

    def tasks_for_note(self, note_id: int) -> list[dict]:
        rows = self.conn.execute(
            f"SELECT t.* FROM tasks t JOIN task_notes tn ON tn.task_id = t.id"
            f" WHERE tn.note_id = ? ORDER BY {_STATUS_RANK}, {_PRIORITY_RANK}", (note_id,))
        return [dict(r) for r in rows]

    # ------------------------------------------------------------------ stats
    def stats(self) -> dict:
        today = date.today().isoformat()
        q = lambda sql, *p: self.conn.execute(sql, p).fetchone()[0]  # noqa: E731
        total = q("SELECT COUNT(*) FROM tasks")
        done = q("SELECT COUNT(*) FROM tasks WHERE status = 'Done'")
        return {
            "total": total,
            "open": q("SELECT COUNT(*) FROM tasks WHERE status = 'Open'"),
            "in_progress": q("SELECT COUNT(*) FROM tasks WHERE status = 'In Progress'"),
            "done": done,
            "overdue": q("SELECT COUNT(*) FROM tasks WHERE status != 'Done'"
                         " AND due_date IS NOT NULL AND due_date < ?", today),
            "critical": q("SELECT COUNT(*) FROM tasks WHERE status != 'Done'"
                          " AND priority = 'Critical'"),
            "done_today": q("SELECT COUNT(*) FROM tasks WHERE status = 'Done'"
                            " AND substr(completed_at, 1, 10) = ?", today),
            "notes": q("SELECT COUNT(*) FROM notes"),
            "completion": (done / total) if total else 0.0,
        }

    # ----------------------------------------------------------------- backup
    def backup(self, dest: str | Path) -> None:
        target = sqlite3.connect(dest)
        with target:
            self.conn.backup(target)
        target.close()
