"""Main window: sidebar navigation that ties the To-Do and Notes parts together."""

from __future__ import annotations

import sys
from datetime import datetime
from pathlib import Path
from tkinter import filedialog

import customtkinter as ctk

from netops_desk import APP_NAME, __version__
from netops_desk.db import Database
from netops_desk.theme import COLORS
from netops_desk.ui.dashboard import DashboardPage
from netops_desk.ui.notes import NotesPage
from netops_desk.ui.subnet_page import SubnetPage
from netops_desk.ui.tasks import TaskDialog, TasksPage, TaskViewDialog
from netops_desk.ui.widgets import Toast, confirm, font

SHORTCUTS = "SHORTCUTS\n" + "\n".join(f"{k:<14}{v}" for k, v in (
    ("Ctrl+N", "new task"), ("Ctrl+Shift+N", "new note"),
    ("Ctrl+E", "edit note"), ("Ctrl+F", "search"), ("Ctrl+1..4", "switch page")))

NAV = [
    ("dashboard", "◉   Dashboard", "Ctrl+1"),
    ("tasks", "☑   To-Do List", "Ctrl+2"),
    ("notes", "✎   Notes", "Ctrl+3"),
    ("subnet", "⌗   Subnet Tool", "Ctrl+4"),
]


def resource_path(name: str) -> Path:
    base = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parents[2]))
    return base / "assets" / name


class App(ctk.CTk):
    def __init__(self, db: Database):
        ctk.set_appearance_mode("dark")
        super().__init__(fg_color=COLORS["bg"])
        self.db = db
        self.title(f"{APP_NAME}  —  IT & Network Workspace")
        self.geometry("1400x880")
        self.minsize(1150, 720)
        icon = resource_path("icon.ico")
        if sys.platform == "win32" and icon.exists():
            self.iconbitmap(str(icon))

        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)
        self._build_sidebar()

        self.pages = {
            "dashboard": DashboardPage(self, self),
            "tasks": TasksPage(self, self),
            "notes": NotesPage(self, self),
            "subnet": SubnetPage(self, self),
        }
        self.current = None
        self._bind_keys()
        self.protocol("WM_DELETE_WINDOW", self.on_close)
        self.show_page("dashboard")

    # ---------------------------------------------------------------- sidebar
    def _build_sidebar(self):
        side = ctk.CTkFrame(self, fg_color=COLORS["sidebar"], corner_radius=0, width=260)
        side.grid(row=0, column=0, sticky="nsew")
        side.grid_propagate(False)
        side.grid_rowconfigure(6, weight=1)
        side.grid_columnconfigure(0, weight=1)

        logo = ctk.CTkFrame(side, fg_color="transparent")
        logo.grid(row=0, column=0, sticky="ew", padx=22, pady=(28, 30))
        ctk.CTkLabel(logo, text="◈", font=font(34, "bold"), text_color=COLORS["accent"]).pack(side="left")
        txt = ctk.CTkFrame(logo, fg_color="transparent")
        txt.pack(side="left", padx=10)
        ctk.CTkLabel(txt, text=APP_NAME, font=font("title", "bold"), text_color=COLORS["text"]).pack(anchor="w")
        ctk.CTkLabel(txt, text="IT & NETWORK OPS", font=font(11, "bold"),
                     text_color=COLORS["muted"]).pack(anchor="w")

        self.nav_buttons = {}
        self.nav_badges = {}
        for i, (key, label, shortcut) in enumerate(NAV, start=1):
            row = ctk.CTkFrame(side, fg_color="transparent")
            row.grid(row=i, column=0, sticky="ew", padx=14, pady=3)
            row.grid_columnconfigure(0, weight=1)
            btn = ctk.CTkButton(row, text=label, anchor="w", height=48, corner_radius=12,
                                font=font("label", "bold"), fg_color="transparent",
                                hover_color=COLORS["card"], text_color=COLORS["muted"],
                                command=lambda k=key: self.show_page(k))
            btn.grid(row=0, column=0, sticky="ew")
            self.nav_buttons[key] = btn
            if key in ("tasks", "notes"):
                badge = ctk.CTkLabel(row, text="", font=font("small", "bold"), fg_color=COLORS["input"],
                                     text_color=COLORS["accent"], corner_radius=8, width=34, height=24)
                badge.grid(row=0, column=0, sticky="e", padx=(0, 12))
                badge.bind("<Button-1>", lambda e, k=key: self.show_page(k))
                self.nav_badges[key] = badge

        ctk.CTkLabel(side, text=SHORTCUTS,
                     font=font(12, mono=True), text_color=COLORS["faint"], justify="left").grid(
            row=5, column=0, sticky="w", padx=26, pady=(24, 0))

        bottom = ctk.CTkFrame(side, fg_color=COLORS["panel"], corner_radius=12)
        bottom.grid(row=7, column=0, sticky="ew", padx=14, pady=18)
        status = ctk.CTkFrame(bottom, fg_color="transparent")
        status.pack(fill="x", padx=14, pady=(12, 4))
        self.led = ctk.CTkLabel(status, text="●", text_color=COLORS["green"], font=font("label"))
        self.led.pack(side="left")
        ctk.CTkLabel(status, text="Database online", font=font("small", "bold"),
                     text_color=COLORS["text"]).pack(side="left", padx=6)
        self._blink()
        ctk.CTkButton(bottom, text="⇩  Backup database", command=self.backup, height=36,
                      fg_color=COLORS["card"], hover_color=COLORS["card_hover"],
                      font=font("small", "bold"), corner_radius=10).pack(fill="x", padx=12, pady=6)
        ctk.CTkLabel(bottom, text=f"v{__version__}  ·  SQLite", font=font(12),
                     text_color=COLORS["faint"]).pack(pady=(0, 10))

    def _blink(self, on=True):
        self.led.configure(text_color=COLORS["green"] if on else COLORS["panel"])
        self.after(900 if on else 300, lambda: self._blink(not on))

    def refresh_sidebar(self):
        s = self.db.stats()
        self.nav_badges["tasks"].configure(text=str(s["open"] + s["in_progress"]),
                                           text_color=COLORS["red"] if s["overdue"] else COLORS["accent"])
        self.nav_badges["notes"].configure(text=str(s["notes"]), text_color=COLORS["purple"])

    # ------------------------------------------------------------- navigation
    def show_page(self, key: str):
        if self.current == "notes" and key != "notes":
            self.pages["notes"].save_now()
        for name, page in self.pages.items():
            if name != key:
                page.grid_forget()
        for name, btn in self.nav_buttons.items():
            active = name == key
            btn.configure(fg_color=COLORS["card"] if active else "transparent",
                          text_color=COLORS["accent"] if active else COLORS["muted"])
        self.pages[key].grid(row=0, column=1, sticky="nsew")
        self.current = key
        self.pages[key].refresh()
        self.refresh_sidebar()

    def show_tasks(self, status: str = "Active"):
        self.pages["tasks"].set_filter(status)
        self.show_page("tasks")

    def refresh_all(self):
        self.refresh_sidebar()
        if self.current:
            self.pages[self.current].refresh()

    def open_task(self, task_id: int | None):
        """Open the task editor (task_id=None creates a new task)."""
        if self.current == "notes":
            self.pages["notes"].save_now()
        return TaskDialog(self, task_id)

    def view_task(self, task_id: int):
        """Show a task read-only; it has an Edit button for changes."""
        if self.current == "notes":
            self.pages["notes"].save_now()
        return TaskViewDialog(self, task_id)

    def open_note(self, note_id: int, edit: bool = False):
        """Show a note on the Notes page, read-only unless edit=True."""
        self.show_page("notes")
        self.pages["notes"].select(note_id, edit=edit)

    def delete_task(self, task_id: int):
        task = self.db.get_task(task_id)
        if task and confirm(self, "Delete task?", f"“{task['title']}” will be permanently deleted. "
                                                   "Linked notes are kept."):
            self.db.delete_task(task_id)
            self.toast("Task deleted", COLORS["red"])
            self.refresh_all()

    def delete_note(self, note_id: int):
        note = self.db.get_note(note_id)
        if note and confirm(self, "Delete note?", f"“{note['title']}” will be permanently deleted. "
                                                   "Linked tasks are kept."):
            self.db.delete_note(note_id)
            self.toast("Note deleted", COLORS["red"])
            self.refresh_all()

    def toast(self, message: str, color: str = COLORS["green"]):
        Toast(self, message, color)

    # ----------------------------------------------------------------- extras
    def backup(self):
        default = f"netops-backup-{datetime.now():%Y%m%d-%H%M}.db"
        path = filedialog.asksaveasfilename(parent=self, defaultextension=".db", initialfile=default,
                                            filetypes=[("SQLite database", "*.db")])
        if path:
            self.db.backup(path)
            self.toast("Backup saved")

    def _bind_keys(self):
        self.bind("<Control-n>", lambda e: self.open_task(None))
        self.bind("<Control-N>", lambda e: self._new_note())
        self.bind("<Control-f>", lambda e: self._focus_search())
        self.bind("<Control-e>", lambda e: self.pages["notes"].toggle_edit() if self.current == "notes" else None)
        for i, (key, _, _) in enumerate(NAV, start=1):
            self.bind(f"<Control-Key-{i}>", lambda e, k=key: self.show_page(k))

    def _new_note(self):
        self.show_page("notes")
        self.pages["notes"].new_note()

    def _focus_search(self):
        if self.current not in ("tasks", "notes"):
            self.show_page("tasks")
        self.pages[self.current].focus_search()

    def on_close(self):
        self.pages["notes"].save_now()
        self.db.close()
        self.destroy()
