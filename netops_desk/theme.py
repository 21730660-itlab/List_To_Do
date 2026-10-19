"""'NOC dark' theme: a network-operations-center look with neon status colors."""

import sys

COLORS = {
    "bg": "#0A0F1C",
    "sidebar": "#0D1424",
    "panel": "#111A2E",
    "card": "#16213A",
    "card_hover": "#1D2B4A",
    "input": "#0E1628",
    "border": "#243352",
    "text": "#E6EDF7",
    "muted": "#8A9BB8",
    "faint": "#56688A",
    "accent": "#00D4FF",
    "accent_hover": "#00A8CC",
    "green": "#00E5A0",
    "amber": "#FFB020",
    "red": "#FF4D6A",
    "purple": "#A78BFA",
}

PRIORITY_COLORS = {
    "Critical": COLORS["red"],
    "High": COLORS["amber"],
    "Medium": COLORS["accent"],
    "Low": COLORS["green"],
}

STATUS_COLORS = {
    "Open": COLORS["muted"],
    "In Progress": COLORS["amber"],
    "Done": COLORS["green"],
}

CATEGORY_COLORS = {
    "Network": "#00D4FF",
    "Server": "#A78BFA",
    "Security": "#FF4D6A",
    "Helpdesk": "#FFB020",
    "Hardware": "#F472B6",
    "Cloud": "#38BDF8",
    "Study": "#00E5A0",
    "General": "#8A9BB8",
}
CATEGORIES = list(CATEGORY_COLORS)

if sys.platform == "win32":
    UI_FONT, MONO_FONT = "Segoe UI", "Consolas"
else:
    UI_FONT, MONO_FONT = "DejaVu Sans", "DejaVu Sans Mono"

# Font sizes are deliberately generous so everything is easy to read.
SIZE = {"small": 13, "body": 15, "label": 16, "title": 18, "h2": 22, "h1": 28, "stat": 38}
