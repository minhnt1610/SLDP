"""
SmartShelf Display  –  targeted at the UCTRONICS 3.5" HDMI LCD (480 x 320 px)
------------------------------------------------------------------------------
2-tab menu navigable with mouse clicks or ← → arrow keys.
  Tab 1 – Weight : item name / live weight in grams / LOW or OK status
  Tab 2 – Expiry : item name / expiry date / days remaining

Run from the smartshelf/ folder:
    python display.py

The display refreshes every 2 seconds automatically.
"""

import tkinter as tk
from tkinter import ttk
from datetime import date, datetime

# Pull the shared ITEMS list from sensor.py.
# Importing sensor also starts the background thread that updates weights.
import sensor
ITEMS = sensor.ITEMS   # same list object – live updates show up here

# ── Screen target ────────────────────────────────────────────────────────────
# UCTRONICS 3.5" HDMI LCD: 480 × 320 pixels (landscape)
SCREEN_W = 480
SCREEN_H = 320

# ── Color palette ────────────────────────────────────────────────────────────
BG_DARK   = "#1e1e2e"   # window / page background
BG_CARD   = "#313244"   # item row background
FG_WHITE  = "#cdd6f4"   # normal text
FG_GREEN  = "#a6e3a1"   # OK / plenty of days left
FG_YELLOW = "#f9e2af"   # expiring soon (≤ 7 days)
FG_RED    = "#f38ba8"   # LOW stock / already expired
ACCENT    = "#89b4fa"   # title + active tab + column headings

# ── Fonts – sized for 480 × 320 so every character is easy to read ───────────
FONT_TITLE = ("Helvetica", 16, "bold")   # "SmartShelf" title strip
FONT_TAB   = ("Helvetica", 13, "bold")   # tab labels
FONT_HEAD  = ("Helvetica", 11, "bold")   # column headers
FONT_BODY  = ("Helvetica", 13)           # data rows  ← big enough to read at 3.5"


def days_until(expiry_str: str) -> int:
    """Days until expiry_str (YYYY-MM-DD). Negative means already expired."""
    expiry = datetime.strptime(expiry_str, "%Y-%m-%d").date()
    return (expiry - date.today()).days


class SmartShelfApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("SmartShelf")
        self.configure(bg=BG_DARK)

        # Lock window to the exact screen size – no scrollbars, no resizing
        self.geometry(f"{SCREEN_W}x{SCREEN_H}")
        self.resizable(False, False)

        # ── Title strip ──────────────────────────────────────────────────────
        title = tk.Label(
            self,
            text="SmartShelf",
            font=FONT_TITLE,
            bg=BG_DARK,
            fg=ACCENT,
        )
        title.pack(pady=(6, 2))

        # ── Tab notebook ─────────────────────────────────────────────────────
        style = ttk.Style()
        style.theme_use("clam")

        style.configure("TNotebook",         background=BG_DARK, borderwidth=0)
        style.configure("TNotebook.Tab",
                        background=BG_CARD,
                        foreground=FG_WHITE,
                        font=FONT_TAB,
                        padding=(28, 6))      # wide padding → easy to click
        style.map("TNotebook.Tab",
                  background=[("selected", ACCENT)],
                  foreground=[("selected", BG_DARK)])

        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill="both", expand=True, padx=6, pady=(2, 4))

        # ── Tab 1: Weight ─────────────────────────────────────────────────────
        wf = tk.Frame(self.notebook, bg=BG_DARK)
        self.notebook.add(wf, text="  Weight  ")
        self._header(wf, ["Item", "Weight (g)", "Status"])
        self.weight_rows = [self._weight_row(wf, it) for it in ITEMS]

        # ── Tab 2: Expiry ─────────────────────────────────────────────────────
        ef = tk.Frame(self.notebook, bg=BG_DARK)
        self.notebook.add(ef, text="  Expiry  ")
        self._header(ef, ["Item", "Expiry Date", "Days Left"])
        self.expiry_rows = [self._expiry_row(ef, it) for it in ITEMS]

        # ── Keyboard navigation: ← → switch tabs ─────────────────────────────
        self.bind("<Left>",  self._prev_tab)
        self.bind("<Right>", self._next_tab)

        # ── Start live refresh ────────────────────────────────────────────────
        self._refresh()

    # ── Tab switching ─────────────────────────────────────────────────────────
    def _prev_tab(self, _event=None):
        cur = self.notebook.index("current")
        self.notebook.select(max(0, cur - 1))

    def _next_tab(self, _event=None):
        cur = self.notebook.index("current")
        self.notebook.select(min(self.notebook.index("end") - 1, cur + 1))

    # ── Column header row ─────────────────────────────────────────────────────
    def _header(self, parent, labels):
        frame = tk.Frame(parent, bg=BG_DARK)
        frame.pack(fill="x", padx=6, pady=(4, 1))
        weights = [3, 2, 2]   # item name column gets more space
        for col, (text, w) in enumerate(zip(labels, weights)):
            tk.Label(frame, text=text, font=FONT_HEAD,
                     bg=BG_DARK, fg=ACCENT, anchor="w"
                     ).grid(row=0, column=col, sticky="ew", padx=6)
            frame.grid_columnconfigure(col, weight=w)

    # ── Weight data row ───────────────────────────────────────────────────────
    def _weight_row(self, parent, item):
        card = tk.Frame(parent, bg=BG_CARD)
        card.pack(fill="x", padx=6, pady=3)

        def lbl(col, text, fg=FG_WHITE, weight=1):
            l = tk.Label(card, text=text, font=FONT_BODY,
                         bg=BG_CARD, fg=fg, anchor="w", pady=6)
            l.grid(row=0, column=col, sticky="ew", padx=8)
            card.grid_columnconfigure(col, weight=weight)
            return l

        lbl(0, item["name"], weight=3)
        weight_lbl = lbl(1, "--", weight=2)
        status_lbl = lbl(2, "--", weight=2)

        return {"weight": weight_lbl, "status": status_lbl}

    # ── Expiry data row ───────────────────────────────────────────────────────
    def _expiry_row(self, parent, item):
        card = tk.Frame(parent, bg=BG_CARD)
        card.pack(fill="x", padx=6, pady=3)

        def lbl(col, text, fg=FG_WHITE, weight=1):
            l = tk.Label(card, text=text, font=FONT_BODY,
                         bg=BG_CARD, fg=fg, anchor="w", pady=6)
            l.grid(row=0, column=col, sticky="ew", padx=8)
            card.grid_columnconfigure(col, weight=weight)
            return l

        lbl(0, item["name"],   weight=3)
        lbl(1, item["expiry"], weight=2)   # expiry date is fixed text
        days_lbl = lbl(2, "--", weight=2)

        return {"days": days_lbl}

    # ── Live update – called every 2 s ────────────────────────────────────────
    def _refresh(self):
        for i, item in enumerate(ITEMS):
            # Weight tab
            wr = self.weight_rows[i]
            wr["weight"].config(text=f"{item['weight']:.1f} g")
            if item["status"] == "LOW":
                wr["status"].config(text="LOW !", fg=FG_RED)
            else:
                wr["status"].config(text="OK",    fg=FG_GREEN)

            # Expiry tab
            days = days_until(item["expiry"])
            if days < 0:
                txt, clr = "EXPIRED", FG_RED
            elif days <= 7:
                txt, clr = f"{days}d left", FG_YELLOW
            else:
                txt, clr = f"{days} days",  FG_GREEN
            self.expiry_rows[i]["days"].config(text=txt, fg=clr)

        self.after(2000, self._refresh)   # schedule next refresh


if __name__ == "__main__":
    app = SmartShelfApp()
    app.mainloop()
