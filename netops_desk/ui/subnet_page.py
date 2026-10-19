"""Subnet calculator - a small built-in network tool that can save results to notes."""

from __future__ import annotations

import customtkinter as ctk

from netops_desk import subnet
from netops_desk.theme import COLORS
from netops_desk.ui.widgets import clear, entry, font, ghost_button, option_menu, primary_button

FIELDS = [
    ("Network", "network"), ("Netmask", "netmask"), ("Wildcard", "wildcard"),
    ("Broadcast", "broadcast"), ("First host", "first_host"), ("Last host", "last_host"),
    ("Usable hosts", "usable_hosts"), ("Class", "ip_class"), ("Scope", "scope"),
    ("Binary mask", "binary_mask"),
]


class SubnetPage(ctk.CTkFrame):
    def __init__(self, master, app):
        super().__init__(master, fg_color=COLORS["bg"])
        self.app = app
        self.info: dict | None = None
        self.split_rows: list[dict] = []
        self.grid_columnconfigure((0, 1), weight=1)
        self.grid_rowconfigure(3, weight=1)

        ctk.CTkLabel(self, text="Subnet Calculator", font=font("h1", "bold"),
                     text_color=COLORS["text"]).grid(row=0, column=0, columnspan=2, sticky="w",
                                                     padx=32, pady=(28, 0))
        ctk.CTkLabel(self, text="Plan addressing for labs and real networks, then save the result to a note.",
                     font=font("body"), text_color=COLORS["muted"]).grid(row=1, column=0, columnspan=2,
                                                                          sticky="w", padx=32)

        bar = ctk.CTkFrame(self, fg_color=COLORS["panel"], corner_radius=14)
        bar.grid(row=2, column=0, columnspan=2, sticky="ew", padx=32, pady=16)
        bar.grid_columnconfigure(0, weight=1)
        self.cidr = entry(bar, "IP/prefix  e.g. 192.168.10.37/26", height=46)
        self.cidr.configure(font=font("title", mono=True))
        self.cidr.grid(row=0, column=0, sticky="ew", padx=(14, 8), pady=14)
        self.cidr.bind("<Return>", lambda e: self.calculate())
        primary_button(bar, "Calculate", self.calculate, width=130, height=46).grid(row=0, column=1, padx=4)
        ghost_button(bar, "✎  Save to note", self.save_note, width=150, height=46).grid(row=0, column=2, padx=(4, 14))
        self.error = ctk.CTkLabel(bar, text="", text_color=COLORS["red"], font=font("body", "bold"))
        self.error.grid(row=1, column=0, columnspan=3, sticky="w", padx=18)

        left = ctk.CTkFrame(self, fg_color=COLORS["panel"], corner_radius=14)
        left.grid(row=3, column=0, sticky="nsew", padx=(32, 8), pady=(0, 28))
        left.grid_columnconfigure(1, weight=1)
        ctk.CTkLabel(left, text="Network details", font=font("title", "bold"),
                     text_color=COLORS["text"]).grid(row=0, column=0, columnspan=2, sticky="w", padx=18, pady=(16, 8))
        self.values = {}
        for i, (label, key) in enumerate(FIELDS, start=1):
            ctk.CTkLabel(left, text=label.upper(), font=font("small", "bold"),
                         text_color=COLORS["muted"]).grid(row=i, column=0, sticky="w", padx=18, pady=5)
            val = ctk.CTkLabel(left, text="—", font=font("label", "bold", mono=True),
                               text_color=COLORS["accent"], anchor="w")
            val.grid(row=i, column=1, sticky="w", padx=8)
            self.values[key] = val

        right = ctk.CTkFrame(self, fg_color=COLORS["panel"], corner_radius=14)
        right.grid(row=3, column=1, sticky="nsew", padx=(8, 32), pady=(0, 28))
        right.grid_columnconfigure(0, weight=1)
        right.grid_rowconfigure(1, weight=1)
        top = ctk.CTkFrame(right, fg_color="transparent")
        top.grid(row=0, column=0, sticky="ew", padx=18, pady=(14, 6))
        ctk.CTkLabel(top, text="Split into subnets", font=font("title", "bold"),
                     text_color=COLORS["text"]).pack(side="left")
        self.split_var = ctk.StringVar(value="/26")
        self.split_menu = option_menu(top, [f"/{p}" for p in range(8, 33)], variable=self.split_var,
                                      command=lambda v: self._render_split(), width=90)
        self.split_menu.pack(side="right")
        self.split_list = ctk.CTkScrollableFrame(right, fg_color="transparent",
                                                 scrollbar_button_color=COLORS["border"])
        self.split_list.grid(row=1, column=0, sticky="nsew", padx=8, pady=(0, 10))
        self.split_list.grid_columnconfigure(1, weight=1)

    def refresh(self):
        pass

    def calculate(self):
        try:
            self.info = subnet.calculate(self.cidr.get())
        except ValueError:
            self.info = None
            self.error.configure(text="Enter a valid IPv4 address with prefix, e.g. 10.0.0.1/24")
            return
        self.error.configure(text="")
        for key, label in self.values.items():
            v = self.info[key]
            label.configure(text=f"{v:,}" if isinstance(v, int) else v)
        prefix = int(self.info["network"].split("/")[1])
        if int(self.split_var.get()[1:]) < prefix:
            self.split_var.set(f"/{min(prefix + 2, 32)}")
        self._render_split()

    def _render_split(self):
        clear(self.split_list)
        self.split_rows = []
        if not self.info:
            return
        try:
            self.split_rows = subnet.split(self.info["network"], int(self.split_var.get()[1:]))
        except ValueError as exc:
            ctk.CTkLabel(self.split_list, text=str(exc), text_color=COLORS["amber"],
                         font=font("body")).grid(row=0, column=0, columnspan=3, pady=20)
            return
        for i, row in enumerate(self.split_rows):
            bg = COLORS["card"] if i % 2 == 0 else "transparent"
            cells = (f"{i + 1:>3}", row["subnet"], f"{row['usable_hosts']:,} hosts")
            for c, text in enumerate(cells):
                ctk.CTkLabel(self.split_list, text=text, fg_color=bg, anchor="w",
                             font=font("body", mono=True),
                             text_color=COLORS["accent"] if c == 1 else COLORS["muted"]).grid(
                    row=i, column=c, sticky="ew", ipady=4, ipadx=8)
        if len(self.split_rows) == 256:
            ctk.CTkLabel(self.split_list, text="Showing first 256 subnets", text_color=COLORS["faint"],
                         font=font("small")).grid(row=257, column=0, columnspan=3, pady=8)

    def save_note(self):
        if not self.info:
            self.calculate()
            if not self.info:
                return
        body = subnet.format_report(self.info)
        if self.split_rows:
            body += f"\n\nSUBNETS ({self.split_var.get()})\n" + "-" * 40 + "\n"
            body += "\n".join(f"{r['subnet']:<20} {r['range']:<33} {r['usable_hosts']} hosts"
                              for r in self.split_rows)
        note_id = self.app.db.add_note(f"Subnet plan {self.info['network']}", body, "Network",
                                       "subnet, ip plan")
        self.app.toast("Saved subnet plan to notes", COLORS["purple"])
        self.app.open_note(note_id)
