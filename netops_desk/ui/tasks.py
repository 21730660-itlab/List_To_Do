"""The To-Do part of the app: task list, filters, quick add, the read-only task view
and the task editor."""

from __future__ import annotations

from datetime import date, timedelta

import customtkinter as ctk

from netops_desk.db import PRIORITIES, STATUSES
from netops_desk.theme import CATEGORIES, CATEGORY_COLORS, COLORS, PRIORITY_COLORS, STATUS_COLORS
from netops_desk.ui.widgets import (Badge, center_on, clear, due_label, entry, font, ghost_button,
                                    option_menu, parse_due, primary_button)

ALL_CATEGORIES = "All categories"
NEXT_STATUS = {"Open": "In Progress", "In Progress": "Done", "Done": "Open"}
STATUS_ACTION = {"Open": "▶  Start", "In Progress": "✓  Finish", "Done": "↺  Reopen"}


class TaskCard(ctk.CTkFrame):
    def __init__(self, master, app, task: dict, compact: bool = False):
        super().__init__(master, fg_color=COLORS["card"], corner_radius=12,
                         border_width=1, border_color=COLORS["border"])
        self.app, self.task = app, task
        done = task["status"] == "Done"
        prio_color = PRIORITY_COLORS.get(task["priority"], COLORS["accent"])

        self.grid_columnconfigure(2, weight=1)
        strip = ctk.CTkFrame(self, width=6, height=1, corner_radius=3,
                             fg_color=COLORS["faint"] if done else prio_color)
        strip.grid(row=0, column=0, rowspan=2, sticky="ns", padx=(8, 4), pady=10)

        self.check_var = ctk.BooleanVar(value=done)
        ctk.CTkCheckBox(self, text="", variable=self.check_var, width=28, checkbox_width=26,
                        checkbox_height=26, corner_radius=8, border_color=COLORS["border"],
                        fg_color=COLORS["green"], hover_color=COLORS["green"],
                        checkmark_color="#001018", command=self._toggle_done
                        ).grid(row=0, column=1, rowspan=2, padx=(8, 6))

        title = ctk.CTkLabel(self, text=task["title"], anchor="w", justify="left",
                             font=font("label", "bold", overstrike=done),
                             text_color=COLORS["faint"] if done else COLORS["text"])
        title.grid(row=0, column=2, sticky="w", padx=8, pady=(12, 0))

        meta = ctk.CTkFrame(self, fg_color="transparent")
        meta.grid(row=1, column=2, sticky="w", padx=8, pady=(4, 12))
        cat = task["category"]
        Badge(meta, cat, CATEGORY_COLORS.get(cat, COLORS["muted"])).pack(side="left")
        Badge(meta, task["priority"], prio_color).pack(side="left", padx=6)
        if not compact:
            Badge(meta, task["status"], STATUS_COLORS[task["status"]]).pack(side="left")
        due_text, due_color = due_label(task["due_date"], done)
        if due_text:
            ctk.CTkLabel(meta, text=f"◷ {due_text}", text_color=due_color,
                         font=font("small", "bold")).pack(side="left", padx=10)
        if task.get("note_count"):
            n = task["note_count"]
            ctk.CTkLabel(meta, text=f"✎ {n} note{'s' if n > 1 else ''}",
                         text_color=COLORS["purple"], font=font("small", "bold")).pack(side="left", padx=4)

        if not compact:
            actions = ctk.CTkFrame(self, fg_color="transparent")
            actions.grid(row=0, column=3, rowspan=2, padx=10)
            ghost_button(actions, STATUS_ACTION[task["status"]], self._advance, width=110,
                         color=STATUS_COLORS[NEXT_STATUS[task["status"]]]).pack(side="left", padx=4)
            ghost_button(actions, "✎  Edit", lambda: self.app.open_task(self.task["id"]),
                         width=90).pack(side="left", padx=4)
            ghost_button(actions, "✕", self._delete, width=40, color=COLORS["red"]).pack(side="left", padx=4)

        # Clicking a card shows the task read-only; editing is a deliberate extra step.
        for w in (self, title, meta):
            w.bind("<Button-1>", lambda e: self.app.view_task(self.task["id"]))
            w.bind("<Enter>", lambda e: self.configure(border_color=COLORS["accent"]))
            w.bind("<Leave>", lambda e: self.configure(border_color=COLORS["border"]))
        title.configure(cursor="hand2")

    def _toggle_done(self):
        status = "Done" if self.check_var.get() else "Open"
        self.app.db.set_task_status(self.task["id"], status)
        if status == "Done":
            self.app.toast(f"Completed: {self.task['title']}")
        self.app.refresh_all()

    def _advance(self):
        new = NEXT_STATUS[self.task["status"]]
        self.app.db.set_task_status(self.task["id"], new)
        self.app.toast(f"{self.task['title']} → {new}", STATUS_COLORS[new])
        self.app.refresh_all()

    def _delete(self):
        self.app.delete_task(self.task["id"])


class TasksPage(ctk.CTkFrame):
    def __init__(self, master, app):
        super().__init__(master, fg_color=COLORS["bg"])
        self.app = app
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(3, weight=1)

        head = ctk.CTkFrame(self, fg_color="transparent")
        head.grid(row=0, column=0, sticky="ew", padx=32, pady=(28, 4))
        ctk.CTkLabel(head, text="To-Do List", font=font("h1", "bold"),
                     text_color=COLORS["text"]).pack(side="left")
        self.count_label = ctk.CTkLabel(head, text="", font=font("body"), text_color=COLORS["muted"])
        self.count_label.pack(side="left", padx=16, pady=(8, 0))
        primary_button(head, "+  New Task", lambda: self.app.open_task(None), width=150).pack(side="right")

        # Quick add bar
        quick = ctk.CTkFrame(self, fg_color=COLORS["panel"], corner_radius=14)
        quick.grid(row=1, column=0, sticky="ew", padx=32, pady=12)
        quick.grid_columnconfigure(0, weight=1)
        self.quick_entry = entry(quick, "Quick add a task and press Enter…   e.g. Replace switch in rack B2",
                                 height=44)
        self.quick_entry.grid(row=0, column=0, sticky="ew", padx=(14, 8), pady=14)
        self.quick_entry.bind("<Return>", lambda e: self._quick_add())
        self.quick_cat = ctk.StringVar(value="Network")
        option_menu(quick, CATEGORIES, variable=self.quick_cat, width=130).grid(row=0, column=1, padx=4)
        self.quick_prio = ctk.StringVar(value="Medium")
        option_menu(quick, list(PRIORITIES), variable=self.quick_prio, width=120).grid(row=0, column=2, padx=4)
        self.quick_due = ctk.StringVar(value="No due date")
        option_menu(quick, ["No due date", "Today", "Tomorrow", "Next week"],
                    variable=self.quick_due, width=140).grid(row=0, column=3, padx=4)
        primary_button(quick, "Add", self._quick_add, width=80, height=44).grid(row=0, column=4, padx=(4, 14))

        # Filters
        filters = ctk.CTkFrame(self, fg_color="transparent")
        filters.grid(row=2, column=0, sticky="ew", padx=32, pady=(0, 8))
        self.status_filter = ctk.CTkSegmentedButton(
            filters, values=["Active", "All", "Open", "In Progress", "Done"], command=lambda v: self.refresh(),
            font=font("body", "bold"), height=38, selected_color=COLORS["accent"],
            selected_hover_color=COLORS["accent_hover"], unselected_color=COLORS["panel"],
            unselected_hover_color=COLORS["card_hover"], fg_color=COLORS["panel"],
            text_color=COLORS["text"], corner_radius=10)
        self.status_filter.set("Active")
        self.status_filter.pack(side="left")
        self.cat_filter = ctk.StringVar(value=ALL_CATEGORIES)
        option_menu(filters, [ALL_CATEGORIES] + CATEGORIES, command=lambda v: self.refresh(),
                    variable=self.cat_filter, width=170).pack(side="left", padx=12)
        self.search = entry(filters, "⌕  Search tasks…", width=260)
        self.search.pack(side="right")
        self.search.bind("<KeyRelease>", lambda e: self._debounced_refresh())
        self._search_job = None

        self.list = ctk.CTkScrollableFrame(self, fg_color="transparent",
                                           scrollbar_button_color=COLORS["border"])
        self.list.grid(row=3, column=0, sticky="nsew", padx=24, pady=(0, 20))
        self.list.grid_columnconfigure(0, weight=1)

    def set_filter(self, status: str = "Active") -> None:
        self.status_filter.set(status)
        self.cat_filter.set(ALL_CATEGORIES)
        self.search.delete(0, "end")

    def focus_search(self):
        self.search.focus_set()

    def _debounced_refresh(self):
        if self._search_job:
            self.after_cancel(self._search_job)
        self._search_job = self.after(250, self.refresh)

    def _quick_add(self):
        title = self.quick_entry.get().strip()
        if not title:
            self.quick_entry.focus_set()
            return
        due = {"Today": date.today(), "Tomorrow": date.today() + timedelta(days=1),
               "Next week": date.today() + timedelta(days=7)}.get(self.quick_due.get())
        self.app.db.add_task(title, category=self.quick_cat.get(), priority=self.quick_prio.get(),
                             due_date=due.isoformat() if due else None)
        self.quick_entry.delete(0, "end")
        self.app.toast(f"Task added: {title}")
        self.app.refresh_all()

    def refresh(self):
        cat = self.cat_filter.get()
        status = self.status_filter.get()
        tasks = self.app.db.list_tasks(status=None if status == "All" else status,
                                       category=None if cat == ALL_CATEGORIES else cat,
                                       search=self.search.get().strip() or None)
        clear(self.list)
        self.count_label.configure(text=f"{len(tasks)} task{'s' if len(tasks) != 1 else ''}")
        if not tasks:
            empty = ctk.CTkFrame(self.list, fg_color="transparent")
            empty.grid(row=0, column=0, pady=80)
            ctk.CTkLabel(empty, text="◎", font=font(64), text_color=COLORS["border"]).pack()
            ctk.CTkLabel(empty, text="No tasks here — all systems green.", font=font("title", "bold"),
                         text_color=COLORS["muted"]).pack(pady=4)
            ctk.CTkLabel(empty, text="Use the quick add bar above or press Ctrl+N.",
                         font=font("body"), text_color=COLORS["faint"]).pack()
            return
        for i, task in enumerate(tasks):
            TaskCard(self.list, self.app, task).grid(row=i, column=0, sticky="ew", padx=8, pady=5)


class TaskDialog(ctk.CTkToplevel):
    """Create or edit a task, and manage the notes linked to it."""

    def __init__(self, app, task_id: int | None):
        super().__init__(app)
        self.app, self.task_id = app, task_id
        task = app.db.get_task(task_id) if task_id else None
        self.title("Edit Task" if task else "New Task")
        center_on(self, app, 680, 800)
        self.minsize(560, 640)
        self.configure(fg_color=COLORS["panel"])
        self.transient(app)
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        body = ctk.CTkScrollableFrame(self, fg_color="transparent")
        body.grid(row=0, column=0, sticky="nsew", padx=10, pady=(10, 0))
        body.grid_columnconfigure((0, 1), weight=1)

        ctk.CTkLabel(body, text="Edit Task" if task else "New Task", font=font("h2", "bold"),
                     text_color=COLORS["text"]).grid(row=0, column=0, columnspan=2, sticky="w",
                                                     padx=16, pady=(12, 16))

        self._label(body, "Title", 1, span=2)
        self.title_entry = entry(body, "What needs to be done?", height=44)
        self.title_entry.grid(row=2, column=0, columnspan=2, sticky="ew", padx=16)

        self._label(body, "Description", 3, span=2)
        self.desc = ctk.CTkTextbox(body, height=120, fg_color=COLORS["input"], border_width=1,
                                   border_color=COLORS["border"], font=font("body"), corner_radius=10,
                                   wrap="word")
        self.desc.grid(row=4, column=0, columnspan=2, sticky="ew", padx=16)

        self._label(body, "Category", 5, 0)
        self._label(body, "Priority", 5, 1)
        self.cat = ctk.StringVar(value=task["category"] if task else "Network")
        option_menu(body, CATEGORIES, variable=self.cat).grid(row=6, column=0, sticky="ew", padx=16)
        self.prio = ctk.StringVar(value=task["priority"] if task else "Medium")
        option_menu(body, list(PRIORITIES), variable=self.prio).grid(row=6, column=1, sticky="ew", padx=16)

        self._label(body, "Status", 7, span=2)
        self.status = ctk.CTkSegmentedButton(
            body, values=list(STATUSES), font=font("body", "bold"), height=40,
            selected_color=COLORS["accent"], selected_hover_color=COLORS["accent_hover"],
            unselected_color=COLORS["input"], fg_color=COLORS["input"], text_color=COLORS["text"])
        self.status.set(task["status"] if task else "Open")
        self.status.grid(row=8, column=0, columnspan=2, sticky="ew", padx=16)
        self._label(body, "Due date", 9, span=2)
        self.due = entry(body, "YYYY-MM-DD  ·  today  ·  tomorrow  ·  +3")
        self.due.grid(row=10, column=0, sticky="ew", padx=16)
        quick_dates = ctk.CTkFrame(body, fg_color="transparent")
        quick_dates.grid(row=10, column=1, sticky="w", padx=(0, 16))
        for text, days in (("Today", 0), ("Tomorrow", 1), ("+1 week", 7), ("Clear", None)):
            ctk.CTkButton(quick_dates, text=text, width=10, height=36, fg_color=COLORS["input"],
                          hover_color=COLORS["card_hover"], font=font("small"), corner_radius=8,
                          command=lambda d=days: self._set_due(d)).pack(side="left", padx=(0, 4))

        # Linked notes - the bridge between the To-Do and Notes parts
        self._label(body, "Linked notes", 11, span=2)
        self.notes_box = ctk.CTkFrame(body, fg_color=COLORS["input"], corner_radius=10)
        self.notes_box.grid(row=12, column=0, columnspan=2, sticky="ew", padx=16)
        self.notes_box.grid_columnconfigure(0, weight=1)

        self.error = ctk.CTkLabel(self, text="", text_color=COLORS["red"], font=font("body", "bold"))
        self.error.grid(row=1, column=0, sticky="w", padx=28)

        footer = ctk.CTkFrame(self, fg_color="transparent")
        footer.grid(row=2, column=0, sticky="ew", padx=26, pady=(4, 20))
        primary_button(footer, "Save  (Ctrl+S)", self._save, width=160).pack(side="right")
        ghost_button(footer, "Cancel", self.destroy, width=110, height=40).pack(side="right", padx=10)
        if task:
            ghost_button(footer, "✕  Delete", self._delete, color=COLORS["red"], width=110,
                         height=40).pack(side="left")

        if task:
            self.title_entry.insert(0, task["title"])
            self.desc.insert("1.0", task["description"])
            if task["due_date"]:
                self.due.insert(0, task["due_date"])
        self._render_notes()

        self.bind("<Control-s>", lambda e: self._save())
        self.bind("<Escape>", lambda e: self.destroy())
        self.title_entry.bind("<Return>", lambda e: self._save())
        self.after(150, self._grab)

    def _grab(self):
        try:
            self.grab_set()
        except Exception:  # window may not be viewable yet on some platforms
            pass
        self.focus_force()
        self.title_entry.focus_set()

    @staticmethod
    def _label(master, text, row, col=0, span=1):
        ctk.CTkLabel(master, text=text.upper(), font=font("small", "bold"),
                     text_color=COLORS["muted"]).grid(row=row, column=col, columnspan=span,
                                                      sticky="w", padx=16, pady=(14, 4))

    def _set_due(self, days):
        self.due.delete(0, "end")
        if days is not None:
            self.due.insert(0, (date.today() + timedelta(days=days)).isoformat())

    def _render_notes(self):
        clear(self.notes_box)
        # A brand-new task has no id yet; linking or creating a note saves it first.
        linked = self.app.db.notes_for_task(self.task_id) if self.task_id else []
        for i, note in enumerate(linked):
            row = ctk.CTkFrame(self.notes_box, fg_color=COLORS["card"], corner_radius=8)
            row.grid(row=i, column=0, sticky="ew", padx=10, pady=(10 if i == 0 else 4, 0))
            row.grid_columnconfigure(0, weight=1)
            ctk.CTkLabel(row, text=f"✎  {note['title']}", font=font("body", "bold"),
                         text_color=COLORS["purple"], anchor="w").grid(row=0, column=0, sticky="ew", padx=12, pady=8)
            ghost_button(row, "Open", lambda n=note["id"]: self._open_note(n), width=70, height=30).grid(row=0, column=1, padx=4)
            ghost_button(row, "Unlink", lambda n=note["id"]: self._unlink(n), width=70, height=30,
                         color=COLORS["muted"]).grid(row=0, column=2, padx=(0, 8))

        bar = ctk.CTkFrame(self.notes_box, fg_color="transparent")
        bar.grid(row=len(linked), column=0, sticky="ew", padx=10, pady=10)
        linked_ids = {n["id"] for n in linked}
        others = [n for n in self.app.db.list_notes() if n["id"] not in linked_ids]
        self._link_choices = {f"{n['title']}  (#{n['id']})": n["id"] for n in others}
        if self._link_choices:
            option_menu(bar, ["Link existing note…"] + list(self._link_choices), width=260,
                        command=self._link_existing).pack(side="left")
        primary_button(bar, "+  New linked note", self._new_note, width=170, height=36).pack(side="right")

    def _link_existing(self, choice):
        note_id = self._link_choices.get(choice)
        if not note_id:
            return
        if not self.task_id and not self._save(close=False):
            return
        self.app.db.link(self.task_id, note_id)
        self.app.toast("Note linked to task", COLORS["purple"])
        # Re-render after the option menu's own callback has finished.
        self.after(10, self._render_notes)
        self.app.refresh_all()

    def _unlink(self, note_id):
        self.app.db.unlink(self.task_id, note_id)
        self._render_notes()
        self.app.refresh_all()

    def _new_note(self):
        if not self._save(close=False, toast=False):
            return
        task = self.app.db.get_task(self.task_id)
        note_id = self.app.db.add_note(f"Notes: {task['title']}", category=task["category"])
        self.app.db.link(self.task_id, note_id)
        self.destroy()
        self.app.open_note(note_id, edit=True)
        self.app.toast("New note linked to task - start typing", COLORS["purple"])

    def _open_note(self, note_id):
        if self._save(close=True, toast=False):
            self.app.open_note(note_id)

    def _save(self, close: bool = True, toast: bool = True) -> bool:
        title = self.title_entry.get().strip()
        if not title:
            self.error.configure(text="Please enter a title.")
            self.title_entry.focus_set()
            return False
        try:
            due = parse_due(self.due.get())
        except ValueError:
            self.error.configure(text="Due date must look like 2026-12-31 (or today / tomorrow / +3).")
            return False
        fields = dict(title=title, description=self.desc.get("1.0", "end-1c").strip(),
                      category=self.cat.get(), priority=self.prio.get(),
                      status=self.status.get(), due_date=due)
        if self.task_id:
            self.app.db.update_task(self.task_id, **fields)
            if toast:
                self.app.toast("Task saved")
        else:
            self.task_id = self.app.db.add_task(**fields)
            if toast:
                self.app.toast(f"Task created: {title}")
        self.app.refresh_all()
        if close:
            self.destroy()
        else:
            self._render_notes()
        return True

    def _delete(self):
        self.destroy()
        self.app.delete_task(self.task_id)


class TaskViewDialog(ctk.CTkToplevel):
    """Read-only view of a task. Changes are only made after pressing Edit."""

    def __init__(self, app, task_id: int):
        super().__init__(app)
        self.app, self.task_id = app, task_id
        self.title("View Task")
        center_on(self, app, 680, 720)
        self.minsize(560, 560)
        self.configure(fg_color=COLORS["panel"])
        self.transient(app)
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self.body = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self.body.grid(row=0, column=0, sticky="nsew", padx=10, pady=(10, 0))
        self.body.grid_columnconfigure(0, weight=1)

        self.footer = ctk.CTkFrame(self, fg_color="transparent")
        self.footer.grid(row=1, column=0, sticky="ew", padx=26, pady=(8, 20))

        self.bind("<Escape>", lambda e: self.destroy())
        self.bind("<Control-e>", lambda e: self._edit())
        self.render()
        self.after(150, self._grab)

    def _grab(self):
        try:
            self.grab_set()
        except Exception:
            pass
        self.focus_force()

    def render(self):
        task = self.app.db.get_task(self.task_id)
        if not task:
            self.destroy()
            return
        clear(self.body)
        clear(self.footer)
        done = task["status"] == "Done"

        ctk.CTkLabel(self.body, text="◉  VIEW MODE  ·  press Edit to make changes",
                     font=font("small", "bold"), text_color=COLORS["faint"]).grid(
            row=0, column=0, sticky="w", padx=16, pady=(12, 4))
        ctk.CTkLabel(self.body, text=task["title"], font=font("h2", "bold", overstrike=done),
                     text_color=COLORS["faint"] if done else COLORS["text"], anchor="w",
                     justify="left", wraplength=580).grid(row=1, column=0, sticky="ew", padx=16)

        badges = ctk.CTkFrame(self.body, fg_color="transparent")
        badges.grid(row=2, column=0, sticky="w", padx=16, pady=(10, 4))
        Badge(badges, task["category"], CATEGORY_COLORS.get(task["category"], COLORS["muted"])).pack(side="left")
        Badge(badges, task["priority"], PRIORITY_COLORS.get(task["priority"], COLORS["accent"])).pack(side="left", padx=6)
        Badge(badges, task["status"], STATUS_COLORS[task["status"]]).pack(side="left")

        info = ctk.CTkFrame(self.body, fg_color=COLORS["input"], corner_radius=10)
        info.grid(row=3, column=0, sticky="ew", padx=16, pady=12)
        info.grid_columnconfigure(1, weight=1)
        due_text, due_color = due_label(task["due_date"], done)
        rows = [("Due", due_text or "No due date", due_color if due_text else COLORS["faint"]),
                ("Created", task["created_at"].replace("T", "  "), COLORS["text"])]
        if task["completed_at"]:
            rows.append(("Completed", task["completed_at"].replace("T", "  "), COLORS["green"]))
        for i, (k, v, color) in enumerate(rows):
            ctk.CTkLabel(info, text=k.upper(), font=font("small", "bold"), text_color=COLORS["muted"]).grid(
                row=i, column=0, sticky="w", padx=14, pady=6)
            ctk.CTkLabel(info, text=v, font=font("body", "bold"), text_color=color).grid(
                row=i, column=1, sticky="w", padx=8)

        self._section("Description", 4)
        ctk.CTkLabel(self.body, text=task["description"] or "No description.", font=font("body"),
                     text_color=COLORS["text"] if task["description"] else COLORS["faint"],
                     anchor="w", justify="left", wraplength=580).grid(row=5, column=0, sticky="ew", padx=16)

        self._section("Linked notes", 6)
        notes = self.app.db.notes_for_task(self.task_id)
        box = ctk.CTkFrame(self.body, fg_color=COLORS["input"], corner_radius=10)
        box.grid(row=7, column=0, sticky="ew", padx=16, pady=(0, 10))
        box.grid_columnconfigure(0, weight=1)
        if not notes:
            ctk.CTkLabel(box, text="No linked notes. Press Edit to add one.", font=font("body"),
                         text_color=COLORS["faint"]).grid(row=0, column=0, sticky="w", padx=14, pady=14)
        for i, note in enumerate(notes):
            row = ctk.CTkFrame(box, fg_color=COLORS["card"], corner_radius=8)
            row.grid(row=i, column=0, sticky="ew", padx=10, pady=(10 if i == 0 else 4, 10 if i == len(notes) - 1 else 0))
            row.grid_columnconfigure(0, weight=1)
            ctk.CTkLabel(row, text=f"✎  {note['title']}", font=font("body", "bold"),
                         text_color=COLORS["purple"], anchor="w").grid(row=0, column=0, sticky="ew", padx=12, pady=8)
            ghost_button(row, "Open", lambda n=note["id"]: self._open_note(n), width=70,
                         height=30).grid(row=0, column=1, padx=8)

        ghost_button(self.footer, "✕  Delete", self._delete, color=COLORS["red"], width=110,
                     height=40).pack(side="left")
        primary_button(self.footer, "✎  Edit  (Ctrl+E)", self._edit, width=160).pack(side="right")
        ghost_button(self.footer, STATUS_ACTION[task["status"]], self._advance, width=120, height=40,
                     color=STATUS_COLORS[NEXT_STATUS[task["status"]]]).pack(side="right", padx=10)
        ghost_button(self.footer, "Close", self.destroy, width=90, height=40).pack(side="right")

    def _section(self, text, row):
        ctk.CTkLabel(self.body, text=text.upper(), font=font("small", "bold"),
                     text_color=COLORS["muted"]).grid(row=row, column=0, sticky="w", padx=16, pady=(14, 4))

    def _advance(self):
        task = self.app.db.get_task(self.task_id)
        new = NEXT_STATUS[task["status"]]
        self.app.db.set_task_status(self.task_id, new)
        self.app.toast(f"{task['title']} → {new}", STATUS_COLORS[new])
        self.app.refresh_all()
        self.render()

    def _edit(self):
        self.destroy()
        self.app.open_task(self.task_id)

    def _open_note(self, note_id):
        self.destroy()
        self.app.open_note(note_id)

    def _delete(self):
        self.destroy()
        self.app.delete_task(self.task_id)
