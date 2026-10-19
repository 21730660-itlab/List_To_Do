"""The Notes part of the app: searchable note list, editor with autosave, templates
and links to tasks."""

from __future__ import annotations

from datetime import datetime
from tkinter import filedialog

import customtkinter as ctk

from netops_desk.templates import TEMPLATES
from netops_desk.theme import CATEGORIES, CATEGORY_COLORS, COLORS, STATUS_COLORS
from netops_desk.ui.widgets import (Dot, clear, entry, font, ghost_button, option_menu,
                                    primary_button, relative_time)

ALL_CATEGORIES = "All notes"
AUTOSAVE_MS = 700


class NoteItem(ctk.CTkFrame):
    def __init__(self, master, page, note: dict, selected: bool):
        super().__init__(master, corner_radius=12, border_width=1,
                         fg_color=COLORS["card_hover"] if selected else COLORS["card"],
                         border_color=COLORS["accent"] if selected else COLORS["border"])
        self.page, self.note_id = page, note["id"]
        self.grid_columnconfigure(1, weight=1)
        Dot(self, CATEGORY_COLORS.get(note["category"], COLORS["muted"])).grid(
            row=0, column=0, padx=(14, 8), pady=(14, 0), sticky="n")
        self.title_lbl = ctk.CTkLabel(self, text="", font=font("label", "bold"),
                                      text_color=COLORS["text"], anchor="w")
        self.title_lbl.grid(row=0, column=1, sticky="ew", pady=(8, 0))
        if note["pinned"]:
            ctk.CTkLabel(self, text="★", text_color=COLORS["amber"], font=font("label")).grid(
                row=0, column=2, padx=12, pady=(8, 0))
        self.snippet_lbl = ctk.CTkLabel(self, text="", font=font("small"), text_color=COLORS["muted"],
                                        anchor="w", justify="left")
        self.snippet_lbl.grid(row=1, column=1, columnspan=2, sticky="ew", padx=(0, 12))
        meta = f"{note['category']}  ·  {relative_time(note['updated_at'])}"
        if note.get("task_count"):
            meta += f"  ·  ⛓ {note['task_count']} task{'s' if note['task_count'] > 1 else ''}"
        self.meta_lbl = ctk.CTkLabel(self, text=meta, font=font("small"), text_color=COLORS["faint"],
                                     anchor="w")
        self.meta_lbl.grid(row=2, column=1, columnspan=2, sticky="ew", pady=(0, 10))
        self.update_text(note["title"], note["body"])
        for w in (self, self.title_lbl, self.snippet_lbl, self.meta_lbl):
            w.bind("<Button-1>", lambda e: self.page.select(self.note_id))
            w.configure(cursor="hand2")

    def update_text(self, title: str, body: str):
        snippet = " ".join(body.split())[:46] or "Empty note"
        self.title_lbl.configure(text=(title[:30] + "…") if len(title) > 31 else title)
        self.snippet_lbl.configure(text=snippet + ("…" if len(body) > 46 else ""))


class NotesPage(ctk.CTkFrame):
    def __init__(self, master, app):
        super().__init__(master, fg_color=COLORS["bg"])
        self.app = app
        self.current_id: int | None = None
        self._save_job = None
        self._loading = False
        self.items: dict[int, NoteItem] = {}

        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)
        self._build_list_pane()
        self._build_editor()
        self._show_editor(False)

    # ----------------------------------------------------------------- layout
    def _build_list_pane(self):
        pane = ctk.CTkFrame(self, fg_color=COLORS["panel"], corner_radius=0, width=380)
        pane.grid(row=0, column=0, sticky="nsew")
        pane.grid_propagate(False)
        pane.grid_columnconfigure(0, weight=1)
        pane.grid_rowconfigure(4, weight=1)

        head = ctk.CTkFrame(pane, fg_color="transparent")
        head.grid(row=0, column=0, sticky="ew", padx=20, pady=(28, 10))
        ctk.CTkLabel(head, text="Notes", font=font("h1", "bold"), text_color=COLORS["text"]).pack(side="left")
        primary_button(head, "+ New", self.new_note, width=90).pack(side="right")

        self.search = entry(pane, "⌕  Search notes, tags, commands…")
        self.search.grid(row=1, column=0, sticky="ew", padx=20, pady=4)
        self.search.bind("<KeyRelease>", lambda e: self._debounced_list())
        self._list_job = None

        row = ctk.CTkFrame(pane, fg_color="transparent")
        row.grid(row=2, column=0, sticky="ew", padx=20, pady=6)
        row.grid_columnconfigure((0, 1), weight=1)
        self.cat_filter = ctk.StringVar(value=ALL_CATEGORIES)
        option_menu(row, [ALL_CATEGORIES] + CATEGORIES, variable=self.cat_filter,
                    command=lambda v: self.refresh_list(), width=10).grid(row=0, column=0, sticky="ew", padx=(0, 4))
        option_menu(row, ["+ From template"] + list(TEMPLATES), command=self._new_from_template,
                    width=10).grid(row=0, column=1, sticky="ew", padx=(4, 0))

        self.count_label = ctk.CTkLabel(pane, text="", font=font("small"), text_color=COLORS["faint"])
        self.count_label.grid(row=3, column=0, sticky="w", padx=22)

        self.list = ctk.CTkScrollableFrame(pane, fg_color="transparent",
                                           scrollbar_button_color=COLORS["border"])
        self.list.grid(row=4, column=0, sticky="nsew", padx=10, pady=(4, 12))
        self.list.grid_columnconfigure(0, weight=1)

    def _build_editor(self):
        self.editor = ed = ctk.CTkFrame(self, fg_color="transparent")
        ed.grid_columnconfigure(0, weight=1)
        ed.grid_rowconfigure(4, weight=1)

        self.title_entry = ctk.CTkEntry(ed, placeholder_text="Note title", font=font("h2", "bold"),
                                        fg_color="transparent", border_width=0, height=52,
                                        text_color=COLORS["text"], placeholder_text_color=COLORS["faint"])
        self.title_entry.grid(row=0, column=0, sticky="ew", padx=28, pady=(24, 0))
        self.title_entry.bind("<KeyRelease>", lambda e: self._schedule_save())

        meta = ctk.CTkFrame(ed, fg_color="transparent")
        meta.grid(row=1, column=0, sticky="ew", padx=32, pady=(4, 8))
        self.cat_var = ctk.StringVar(value="General")
        option_menu(meta, CATEGORIES, variable=self.cat_var, width=140,
                    command=lambda v: self.save_now()).pack(side="left")
        self.tags_entry = entry(meta, "tags: vlan, cisco, dhcp", width=260)
        self.tags_entry.pack(side="left", padx=10)
        self.tags_entry.bind("<KeyRelease>", lambda e: self._schedule_save())
        self.pin_btn = ghost_button(meta, "☆  Pin", self._toggle_pin, width=90)
        self.pin_btn.pack(side="left")
        ghost_button(meta, "✕", self.delete_current, color=COLORS["red"], width=44).pack(side="right")
        ghost_button(meta, "⇩  Export", self._export, width=100).pack(side="right", padx=8)

        # Linked tasks bar - the bridge back to the To-Do list
        self.links = ctk.CTkFrame(ed, fg_color=COLORS["panel"], corner_radius=12)
        self.links.grid(row=2, column=0, sticky="ew", padx=28, pady=(0, 10))

        tools = ctk.CTkFrame(ed, fg_color="transparent")
        tools.grid(row=3, column=0, sticky="ew", padx=28, pady=(0, 6))
        for text, fn in (("◷  Timestamp", self._ins_time), ("☐  Checklist", lambda: self._ins("[ ] ")),
                         ("{ }  Code block", lambda: self._ins("```\n\n```\n")),
                         ("―  Divider", lambda: self._ins("\n" + "-" * 40 + "\n"))):
            ctk.CTkButton(tools, text=text, command=fn, height=32, fg_color=COLORS["panel"],
                          hover_color=COLORS["card_hover"], font=font("small", "bold"),
                          text_color=COLORS["muted"], corner_radius=8, width=10).pack(side="left", padx=(0, 6))
        option_menu(tools, ["Insert template…"] + list(TEMPLATES), command=self._insert_template,
                    width=170).pack(side="left", padx=(4, 0))

        self.body = ctk.CTkTextbox(ed, fg_color=COLORS["input"], border_width=1,
                                   border_color=COLORS["border"], font=font("body", mono=True),
                                   corner_radius=12, wrap="word", undo=True, text_color=COLORS["text"])
        self.body.grid(row=4, column=0, sticky="nsew", padx=28)
        self.body.bind("<KeyRelease>", lambda e: self._schedule_save())

        self.status_lbl = ctk.CTkLabel(ed, text="", font=font("small"), text_color=COLORS["faint"])
        self.status_lbl.grid(row=5, column=0, sticky="e", padx=32, pady=(6, 16))

        self.empty = ctk.CTkFrame(self, fg_color="transparent")
        ctk.CTkLabel(self.empty, text="✎", font=font(72), text_color=COLORS["border"]).pack()
        ctk.CTkLabel(self.empty, text="Select a note or create a new one", font=font("h2", "bold"),
                     text_color=COLORS["muted"]).pack(pady=6)
        ctk.CTkLabel(self.empty, text="Keep configs, commands, incident logs and study notes here.\n"
                                      "Link notes to tasks so the context is always one click away.",
                     font=font("body"), text_color=COLORS["faint"], justify="center").pack()
        primary_button(self.empty, "+  New note  (Ctrl+Shift+N)", self.new_note, width=260).pack(pady=20)

    def _show_editor(self, show: bool):
        if show:
            self.empty.grid_forget()
            self.editor.grid(row=0, column=1, sticky="nsew")
        else:
            self.editor.grid_forget()
            self.empty.grid(row=0, column=1)

    # ------------------------------------------------------------------- list
    def _debounced_list(self):
        if self._list_job:
            self.after_cancel(self._list_job)
        self._list_job = self.after(250, self.refresh_list)

    def refresh(self):
        self.refresh_list()
        if self.current_id and not self.app.db.get_note(self.current_id):
            self.current_id = None
        if self.current_id:
            self._render_links()
        self._show_editor(self.current_id is not None)

    def refresh_list(self):
        cat = self.cat_filter.get()
        notes = self.app.db.list_notes(search=self.search.get().strip() or None,
                                       category=None if cat == ALL_CATEGORIES else cat)
        clear(self.list)
        self.items = {}
        self.count_label.configure(text=f"{len(notes)} note{'s' if len(notes) != 1 else ''}")
        if not notes:
            ctk.CTkLabel(self.list, text="No notes found", font=font("body"),
                         text_color=COLORS["faint"]).grid(row=0, column=0, pady=40)
        for i, note in enumerate(notes):
            item = NoteItem(self.list, self, note, note["id"] == self.current_id)
            item.grid(row=i, column=0, sticky="ew", padx=6, pady=4)
            self.items[note["id"]] = item

    def focus_search(self):
        self.search.focus_set()

    # ----------------------------------------------------------------- editor
    def select(self, note_id: int):
        self.save_now()
        note = self.app.db.get_note(note_id)
        if not note:
            return
        self.current_id = note_id
        self._loading = True
        self.title_entry.delete(0, "end")
        self.title_entry.insert(0, note["title"])
        self.tags_entry.delete(0, "end")
        self.tags_entry.insert(0, note["tags"])
        self.cat_var.set(note["category"])
        self.body.delete("1.0", "end")
        self.body.insert("1.0", note["body"])
        self.body.edit_reset()
        self._loading = False
        self._update_pin(note["pinned"])
        self.status_lbl.configure(text=f"Last edited {relative_time(note['updated_at'])}  ·  "
                                       f"{self._word_count()} words")
        self._show_editor(True)
        self.refresh_list()
        self._render_links()

    def new_note(self, title: str = "Untitled note", body: str = "", category: str = "General",
                 tags: str = ""):
        self.save_now()
        note_id = self.app.db.add_note(title, body, category, tags)
        self.app.refresh_sidebar()
        self.select(note_id)
        self.title_entry.focus_set()
        self.title_entry.select_range(0, "end")

    def _new_from_template(self, name):
        if name in TEMPLATES:
            cat, tags, make = TEMPLATES[name]
            self.new_note(name, make(), cat, tags)
            self.app.toast(f"New note from template: {name}")

    def _schedule_save(self):
        if self._loading or self.current_id is None:
            return
        self.status_lbl.configure(text="Editing…", text_color=COLORS["amber"])
        if self._save_job:
            self.after_cancel(self._save_job)
        self._save_job = self.after(AUTOSAVE_MS, self.save_now)

    def save_now(self):
        if self._save_job:
            self.after_cancel(self._save_job)
            self._save_job = None
        if self.current_id is None or not self.app.db.get_note(self.current_id):
            return
        title = self.title_entry.get().strip() or "Untitled note"
        body = self.body.get("1.0", "end-1c")
        self.app.db.update_note(self.current_id, title=title, body=body, category=self.cat_var.get(),
                                tags=self.tags_entry.get().strip())
        item = self.items.get(self.current_id)
        if item:
            item.update_text(title, body)
        self.status_lbl.configure(text=f"✓ Saved {datetime.now():%H:%M:%S}  ·  {self._word_count()} words",
                                  text_color=COLORS["green"])

    def _word_count(self) -> int:
        return len(self.body.get("1.0", "end-1c").split())

    def _toggle_pin(self):
        note = self.app.db.get_note(self.current_id)
        self.app.db.update_note(self.current_id, pinned=not note["pinned"])
        self._update_pin(not note["pinned"])
        self.refresh_list()

    def _update_pin(self, pinned):
        self.pin_btn.configure(text="★  Pinned" if pinned else "☆  Pin",
                               text_color=COLORS["amber"] if pinned else COLORS["text"])

    def delete_current(self):
        if self.current_id is not None:
            self.app.delete_note(self.current_id)

    def _export(self):
        self.save_now()
        note = self.app.db.get_note(self.current_id)
        safe = "".join(c if c.isalnum() or c in " -_" else "_" for c in note["title"]).strip() or "note"
        path = filedialog.asksaveasfilename(parent=self, defaultextension=".txt", initialfile=safe,
                                            filetypes=[("Text file", "*.txt"), ("Markdown", "*.md")])
        if path:
            with open(path, "w", encoding="utf-8") as f:
                f.write(f"{note['title']}\n{'=' * len(note['title'])}\n\n{note['body']}\n")
            self.app.toast("Note exported")

    # ---------------------------------------------------------------- inserts
    def _ins(self, text):
        self.body.insert("insert", text)
        self.body.focus_set()
        self._schedule_save()

    def _ins_time(self):
        self._ins(f"[{datetime.now():%Y-%m-%d %H:%M}] ")

    def _insert_template(self, name):
        if name in TEMPLATES:
            self._ins(TEMPLATES[name][2]())

    # ------------------------------------------------------------ task links
    def _render_links(self):
        clear(self.links)
        if self.current_id is None:
            return
        ctk.CTkLabel(self.links, text="⛓  LINKED TASKS", font=font("small", "bold"),
                     text_color=COLORS["muted"]).pack(side="left", padx=(14, 8), pady=10)
        linked = self.app.db.tasks_for_note(self.current_id)
        if not linked:
            ctk.CTkLabel(self.links, text="none yet", font=font("small"),
                         text_color=COLORS["faint"]).pack(side="left")
        for task in linked[:4]:
            color = STATUS_COLORS[task["status"]]
            title = task["title"] if len(task["title"]) <= 24 else task["title"][:23] + "…"
            label = ("✓ " if task["status"] == "Done" else "● ") + title
            ctk.CTkButton(self.links, text=label, height=30, width=10, fg_color=COLORS["card"],
                          hover_color=COLORS["card_hover"], text_color=color, corner_radius=8,
                          font=font("small", "bold"),
                          command=lambda t=task["id"]: self.app.open_task(t)).pack(side="left", padx=3)
        if len(linked) > 4:
            ctk.CTkLabel(self.links, text=f"+{len(linked) - 4}", text_color=COLORS["muted"],
                         font=font("small")).pack(side="left", padx=4)

        ghost_button(self.links, "+ Task from note", self._task_from_note, width=10,
                     height=30).pack(side="right", padx=(4, 10), pady=8)
        linked_ids = {t["id"] for t in linked}
        others = [t for t in self.app.db.list_tasks() if t["id"] not in linked_ids]
        self._link_choices = {f"{t['title'][:40]}  (#{t['id']})": t["id"] for t in others}
        if self._link_choices:
            option_menu(self.links, ["Link a task…"] + list(self._link_choices), width=180,
                        command=self._link_task).pack(side="right", padx=4)

    def _link_task(self, choice):
        task_id = self._link_choices.get(choice)
        if task_id:
            self.app.db.link(task_id, self.current_id)
            self.app.toast("Task linked to note", COLORS["purple"])
            self._render_links()
            self.refresh_list()

    def _task_from_note(self):
        self.save_now()
        note = self.app.db.get_note(self.current_id)
        task_id = self.app.db.add_task(note["title"], category=note["category"])
        self.app.db.link(task_id, self.current_id)
        self.app.toast("Task created from note", COLORS["purple"])
        self._render_links()
        self.refresh_list()
        self.app.refresh_sidebar()
        self.app.open_task(task_id)
