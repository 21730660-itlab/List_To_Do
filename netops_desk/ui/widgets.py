"""Small reusable widgets and helpers shared by the pages."""

from __future__ import annotations

from datetime import date, datetime, timedelta

import customtkinter as ctk

from netops_desk.theme import COLORS, MONO_FONT, SIZE, UI_FONT


def font(size: str | int = "body", weight: str = "normal", mono: bool = False,
         overstrike: bool = False) -> ctk.CTkFont:
    px = SIZE[size] if isinstance(size, str) else size
    return ctk.CTkFont(family=MONO_FONT if mono else UI_FONT, size=px, weight=weight,
                       overstrike=overstrike)


def clear(frame) -> None:
    for child in frame.winfo_children():
        child.destroy()


def due_label(due: str | None, done: bool = False) -> tuple[str, str]:
    """Human friendly due text and the color to show it in."""
    if not due:
        return "", COLORS["muted"]
    try:
        d = date.fromisoformat(due)
    except ValueError:
        return due, COLORS["muted"]
    delta = (d - date.today()).days
    if done:
        return f"Due {d:%b %d}", COLORS["faint"]
    if delta < 0:
        return f"Overdue {-delta}d", COLORS["red"]
    if delta == 0:
        return "Due today", COLORS["amber"]
    if delta == 1:
        return "Due tomorrow", COLORS["amber"]
    if delta < 7:
        return f"Due {d:%A}", COLORS["text"]
    return f"Due {d:%b %d}", COLORS["muted"]


def relative_time(iso: str) -> str:
    try:
        then = datetime.fromisoformat(iso)
    except (TypeError, ValueError):
        return ""
    secs = (datetime.now() - then).total_seconds()
    if secs < 60:
        return "just now"
    if secs < 3600:
        return f"{int(secs // 60)} min ago"
    if secs < 86400:
        return f"{int(secs // 3600)} h ago"
    if secs < 7 * 86400:
        return f"{int(secs // 86400)} d ago"
    return then.strftime("%b %d, %Y")


def parse_due(text: str) -> str | None:
    """Accept YYYY-MM-DD plus a few shortcuts (today, tomorrow, +3)."""
    text = text.strip().lower()
    if not text:
        return None
    if text == "today":
        return date.today().isoformat()
    if text == "tomorrow":
        return (date.today() + timedelta(days=1)).isoformat()
    if text.startswith("+") and text[1:].isdigit():
        return (date.today() + timedelta(days=int(text[1:]))).isoformat()
    return date.fromisoformat(text).isoformat()


def center_on(win, parent, width: int, height: int) -> None:
    """Size ``win`` and center it over ``parent``."""
    parent.update_idletasks()
    x = parent.winfo_rootx() + max((parent.winfo_width() - width) // 2, 0)
    y = parent.winfo_rooty() + max((parent.winfo_height() - height) // 2, 0)
    win.geometry(f"{width}x{height}+{x}+{y}")


class Badge(ctk.CTkLabel):
    """A small rounded colored tag."""

    def __init__(self, master, text: str, color: str, **kw):
        super().__init__(master, text=f" {text} ", text_color=color, fg_color=COLORS["input"],
                         corner_radius=8, font=font("small", "bold"), height=24, **kw)


class Dot(ctk.CTkFrame):
    def __init__(self, master, color: str, size: int = 10):
        super().__init__(master, width=size, height=size, corner_radius=size // 2,
                         fg_color=color)


def primary_button(master, text, command, **kw) -> ctk.CTkButton:
    kw.setdefault("height", 40)
    return ctk.CTkButton(master, text=text, command=command, fg_color=COLORS["accent"],
                         hover_color=COLORS["accent_hover"], text_color="#001018",
                         font=font("body", "bold"), corner_radius=10, **kw)


def ghost_button(master, text, command, color: str | None = None, **kw) -> ctk.CTkButton:
    kw.setdefault("height", 36)
    return ctk.CTkButton(master, text=text, command=command, fg_color="transparent",
                         hover_color=COLORS["card_hover"], border_width=1,
                         border_color=COLORS["border"], text_color=color or COLORS["text"],
                         font=font("body"), corner_radius=10, **kw)


def option_menu(master, values, command=None, variable=None, width=150) -> ctk.CTkOptionMenu:
    return ctk.CTkOptionMenu(master, values=values, command=command, variable=variable,
                             width=width, height=38, fg_color=COLORS["input"],
                             button_color=COLORS["border"], button_hover_color=COLORS["card_hover"],
                             dropdown_fg_color=COLORS["panel"], dropdown_hover_color=COLORS["card_hover"],
                             dropdown_font=font("body"), font=font("body"), corner_radius=10)


def entry(master, placeholder: str = "", **kw) -> ctk.CTkEntry:
    kw.setdefault("height", 40)
    return ctk.CTkEntry(master, placeholder_text=placeholder, fg_color=COLORS["input"],
                        border_color=COLORS["border"], text_color=COLORS["text"],
                        placeholder_text_color=COLORS["faint"], font=font("body"),
                        corner_radius=10, **kw)


class Toast:
    """Non-blocking notification that slides in at the bottom right."""

    def __init__(self, root, message: str, color: str = COLORS["green"], ms: int = 2200):
        self.frame = ctk.CTkFrame(root, fg_color=COLORS["card"], border_color=color,
                                  border_width=2, corner_radius=12)
        ctk.CTkLabel(self.frame, text=f"●  {message}", text_color=COLORS["text"],
                     font=font("body", "bold")).pack(padx=18, pady=12)
        self.frame.place(relx=1.0, rely=1.0, x=-24, y=-24, anchor="se")
        self.frame.lift()
        root.after(ms, self.frame.destroy)


def confirm(root, title: str, message: str) -> bool:
    """Themed yes/no modal dialog."""
    result = {"ok": False}
    win = ctk.CTkToplevel(root)
    win.title(title)
    win.configure(fg_color=COLORS["panel"])
    win.resizable(False, False)
    win.transient(root)
    center_on(win, root, 480, 220)
    ctk.CTkLabel(win, text=title, font=font("title", "bold"),
                 text_color=COLORS["text"]).pack(padx=28, pady=(24, 6), anchor="w")
    ctk.CTkLabel(win, text=message, font=font("body"), text_color=COLORS["muted"],
                 wraplength=420, justify="left").pack(padx=28, pady=(0, 20), anchor="w")
    row = ctk.CTkFrame(win, fg_color="transparent")
    row.pack(fill="x", padx=28, pady=(0, 24))

    def done(value: bool):
        result["ok"] = value
        win.destroy()

    ctk.CTkButton(row, text="Delete", command=lambda: done(True), fg_color=COLORS["red"],
                  hover_color="#D93A55", font=font("body", "bold"), height=40,
                  corner_radius=10, width=120).pack(side="right")
    ghost_button(row, "Cancel", lambda: done(False), width=120, height=40).pack(side="right", padx=10)
    win.bind("<Escape>", lambda e: done(False))
    win.after(120, lambda: (win.grab_set(), win.focus_force()))
    root.wait_window(win)
    return result["ok"]
