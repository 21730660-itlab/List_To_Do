"""Application start-up: open the database, seed a first-run welcome, launch the UI."""

from __future__ import annotations

import sys
import tempfile
from datetime import date, timedelta
from pathlib import Path

from netops_desk.db import Database

WELCOME_NOTE = """Welcome to NetOps Desk!
========================================

The app has two connected parts:

  ☑  TO-DO LIST  - tasks with category, priority, status and due date
  ✎  NOTES       - configs, commands, incident logs, study notes

They are linked: open any task and press "+ New linked note",
or use "Link a task…" at the top of a note. Linked items are
one click away from each other.

TIPS
----
[ ] Ctrl+N          new task
[ ] Ctrl+Shift+N    new note
[ ] Ctrl+F          search
[ ] Ctrl+1..4       switch page
[ ] Notes save automatically while you type
[ ] Try a template: Incident Report, Device Config, OSI Troubleshooting
[ ] Subnet Tool can save a full IP plan straight into a note

Your data is stored locally in a single SQLite file
(%APPDATA%\\NetOpsDesk\\netops.db). Use "Backup database" in the
sidebar to make a copy.
"""


def seed(db: Database) -> None:
    today = date.today()
    t1 = db.add_task("Configure VLAN 20 on core switch", "Add VLAN 20 (Voice) and trunk it to access switches.",
                     "Network", "High", (today + timedelta(days=1)).isoformat())
    db.add_task("Renew SSL certificate for intranet", "", "Security", "Critical", today.isoformat())
    db.add_task("Patch Windows Server 2022 (monthly updates)", "", "Server", "Medium",
                (today + timedelta(days=5)).isoformat(), status="In Progress")
    db.add_task("Study OSPF multi-area for CCNA", "", "Study", "Low")
    db.add_task("Label patch panel in rack A1", "", "Hardware", "Low", status="Done")
    welcome = db.add_note("Welcome to NetOps Desk", WELCOME_NOTE, "General", "help", pinned=True)
    vlan = db.add_note("VLAN 20 config", "```\nvlan 20\n name VOICE\n!\ninterface Gi0/1\n"
                       " switchport mode trunk\n switchport trunk allowed vlan add 20\n```\n",
                       "Network", "vlan, cisco")
    db.link(t1, vlan)
    db.link(t1, welcome)


def selftest() -> int:
    """Start the full UI against a throw-away database, exercise it, then exit."""
    from netops_desk.ui.app import App

    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
        db = Database(Path(tmp) / "selftest.db")
        seed(db)
        app = App(db)
        for page in ("tasks", "notes", "subnet", "dashboard"):
            app.show_page(page)
            app.update()
        notes = app.pages["notes"]
        note = db.list_notes()[0]
        app.open_note(note["id"])
        assert not notes.editing, "notes must open read-only"
        before = db.get_note(note["id"])["updated_at"]
        app.open_note(db.list_notes()[1]["id"])
        assert db.get_note(note["id"])["updated_at"] == before, "viewing must not modify a note"
        notes.toggle_edit()
        assert notes.editing
        notes.body.insert("end", "\nselftest")
        notes._schedule_save()
        notes.toggle_edit()
        assert not notes.editing and db.get_note(notes.current_id)["body"].endswith("selftest")
        notes.new_note()
        assert notes.editing, "a new note must open ready to type"
        task_id = db.list_tasks()[0]["id"]
        app.view_task(task_id).destroy()
        app.open_task(None).destroy()
        app.pages["subnet"].cidr.insert(0, "10.0.0.1/24")
        app.pages["subnet"].calculate()
        app.update()
        app.on_close()
    return 0


def main() -> None:
    if "--selftest" in sys.argv:
        sys.exit(selftest())
    from netops_desk.ui.app import App

    db = Database()
    if db.is_new:
        seed(db)
    App(db).mainloop()
