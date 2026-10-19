"""Dashboard: an at-a-glance 'NOC wall' of tasks and notes."""

from __future__ import annotations

from datetime import datetime

import customtkinter as ctk

from netops_desk.theme import CATEGORY_COLORS, COLORS
from netops_desk.ui.tasks import TaskCard
from netops_desk.ui.widgets import Dot, clear, font, ghost_button, relative_time


class StatCard(ctk.CTkFrame):
    def __init__(self, master, label: str, color: str, command):
        super().__init__(master, fg_color=COLORS["card"], corner_radius=14, border_width=1,
                         border_color=COLORS["border"], cursor="hand2")
        ctk.CTkFrame(self, height=4, fg_color=color, corner_radius=2).pack(fill="x", padx=16, pady=(12, 0))
        self.value = ctk.CTkLabel(self, text="0", font=font("stat", "bold"), text_color=color)
        self.value.pack(anchor="w", padx=18, pady=(6, 0))
        self.label = ctk.CTkLabel(self, text=label.upper(), font=font("small", "bold"),
                                  text_color=COLORS["muted"])
        self.label.pack(anchor="w", padx=18, pady=(0, 14))
        for w in (self, self.value, self.label):
            w.bind("<Button-1>", lambda e: command())
            w.bind("<Enter>", lambda e: self.configure(border_color=color))
            w.bind("<Leave>", lambda e: self.configure(border_color=COLORS["border"]))

    def set(self, value):
        self.value.configure(text=str(value))


class DashboardPage(ctk.CTkFrame):
    def __init__(self, master, app):
        super().__init__(master, fg_color=COLORS["bg"])
        self.app = app
        self.grid_columnconfigure((0, 1), weight=1)
        self.grid_rowconfigure(3, weight=1)

        head = ctk.CTkFrame(self, fg_color="transparent")
        head.grid(row=0, column=0, columnspan=2, sticky="ew", padx=32, pady=(28, 8))
        left = ctk.CTkFrame(head, fg_color="transparent")
        left.pack(side="left")
        self.greeting = ctk.CTkLabel(left, text="", font=font("h1", "bold"), text_color=COLORS["text"])
        self.greeting.pack(anchor="w")
        self.subtitle = ctk.CTkLabel(left, text="", font=font("body"), text_color=COLORS["muted"])
        self.subtitle.pack(anchor="w")
        self.clock = ctk.CTkLabel(head, text="", font=font("h2", "bold", mono=True),
                                  text_color=COLORS["accent"])
        self.clock.pack(side="right")
        self._tick()

        stats = ctk.CTkFrame(self, fg_color="transparent")
        stats.grid(row=1, column=0, columnspan=2, sticky="ew", padx=26, pady=8)
        stats.grid_columnconfigure(tuple(range(5)), weight=1, uniform="s")
        go = self.app.show_tasks
        self.cards = {
            "open": StatCard(stats, "Open", COLORS["accent"], lambda: go("Open")),
            "in_progress": StatCard(stats, "In progress", COLORS["amber"], lambda: go("In Progress")),
            "overdue": StatCard(stats, "Overdue", COLORS["red"], lambda: go("Active")),
            "done_today": StatCard(stats, "Done today", COLORS["green"], lambda: go("Done")),
            "notes": StatCard(stats, "Notes", COLORS["purple"], lambda: self.app.show_page("notes")),
        }
        for i, card in enumerate(self.cards.values()):
            card.grid(row=0, column=i, sticky="ew", padx=6)

        prog = ctk.CTkFrame(self, fg_color=COLORS["panel"], corner_radius=14)
        prog.grid(row=2, column=0, columnspan=2, sticky="ew", padx=32, pady=10)
        prog.grid_columnconfigure(1, weight=1)
        ctk.CTkLabel(prog, text="COMPLETION", font=font("small", "bold"),
                     text_color=COLORS["muted"]).grid(row=0, column=0, padx=18, pady=16)
        self.bar = ctk.CTkProgressBar(prog, height=14, corner_radius=7, fg_color=COLORS["input"],
                                      progress_color=COLORS["green"])
        self.bar.grid(row=0, column=1, sticky="ew", padx=8)
        self.pct = ctk.CTkLabel(prog, text="", font=font("title", "bold"), text_color=COLORS["green"])
        self.pct.grid(row=0, column=2, padx=18)

        self.queue = self._column(0, "Priority queue", "View all tasks →", lambda: go("Active"))
        self.notes = self._column(1, "Pinned & recent notes", "Open notes →",
                                  lambda: self.app.show_page("notes"))

    def _column(self, col, title, link, command):
        box = ctk.CTkFrame(self, fg_color=COLORS["panel"], corner_radius=14)
        box.grid(row=3, column=col, sticky="nsew", padx=(32 if col == 0 else 8, 8 if col == 0 else 32),
                 pady=(4, 28))
        box.grid_columnconfigure(0, weight=1)
        box.grid_rowconfigure(1, weight=1)
        ctk.CTkLabel(box, text=title, font=font("title", "bold"), text_color=COLORS["text"]).grid(
            row=0, column=0, sticky="w", padx=18, pady=(16, 6))
        ctk.CTkButton(box, text=link, command=command, fg_color="transparent", hover_color=COLORS["card"],
                      text_color=COLORS["accent"], font=font("body", "bold"), width=10).grid(
            row=0, column=1, padx=12, pady=(16, 6))
        inner = ctk.CTkScrollableFrame(box, fg_color="transparent", scrollbar_button_color=COLORS["border"])
        inner.grid(row=1, column=0, columnspan=2, sticky="nsew", padx=6, pady=(0, 10))
        inner.grid_columnconfigure(0, weight=1)
        return inner

    def _tick(self):
        now = datetime.now()
        self.clock.configure(text=now.strftime("%H:%M:%S"))
        hour = now.hour
        part = "morning" if hour < 12 else "afternoon" if hour < 18 else "evening"
        self.greeting.configure(text=f"Good {part}")
        self.after(1000, self._tick)

    def refresh(self):
        s = self.app.db.stats()
        for key, card in self.cards.items():
            card.set(s[key])
        self.bar.set(s["completion"])
        self.pct.configure(text=f"{s['completion'] * 100:.0f}%")
        parts = [f"{datetime.now():%A, %d %B %Y}"]
        if s["critical"]:
            parts.append(f"⚠ {s['critical']} critical task{'s' if s['critical'] > 1 else ''} open")
        elif s["open"] + s["in_progress"] == 0:
            parts.append("All systems green ✓")
        self.subtitle.configure(text="   ·   ".join(parts),
                                text_color=COLORS["red"] if s["critical"] else COLORS["muted"])

        clear(self.queue)
        tasks = self.app.db.list_tasks(status="Active", limit=8)
        if not tasks:
            ctk.CTkLabel(self.queue, text="Nothing in the queue. Nice work!", font=font("body"),
                         text_color=COLORS["faint"]).grid(row=0, column=0, pady=30)
        for i, t in enumerate(tasks):
            TaskCard(self.queue, self.app, t, compact=True).grid(row=i, column=0, sticky="ew", padx=6, pady=4)

        clear(self.notes)
        notes = self.app.db.list_notes(limit=8)
        if not notes:
            ctk.CTkLabel(self.notes, text="No notes yet.", font=font("body"),
                         text_color=COLORS["faint"]).grid(row=0, column=0, pady=30)
        for i, n in enumerate(notes):
            row = ctk.CTkFrame(self.notes, fg_color=COLORS["card"], corner_radius=12, cursor="hand2")
            row.grid(row=i, column=0, sticky="ew", padx=6, pady=4)
            row.grid_columnconfigure(1, weight=1)
            Dot(row, CATEGORY_COLORS.get(n["category"], COLORS["muted"])).grid(row=0, column=0, padx=(14, 10))
            title = ctk.CTkLabel(row, text=("★ " if n["pinned"] else "") + n["title"], anchor="w",
                                 font=font("label", "bold"),
                                 text_color=COLORS["amber"] if n["pinned"] else COLORS["text"])
            title.grid(row=0, column=1, sticky="ew", pady=12)
            when = ctk.CTkLabel(row, text=relative_time(n["updated_at"]), font=font("small"),
                                text_color=COLORS["faint"])
            when.grid(row=0, column=2, padx=14)
            for w in (row, title, when):
                w.bind("<Button-1>", lambda e, nid=n["id"]: self.app.open_note(nid))
