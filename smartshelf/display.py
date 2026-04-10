"""
SmartShelf Display
------------------
White theme, fullscreen, large fonts.
2-tab menu: Weight | Expiry
Navigate with mouse clicks or ← → arrow keys.
Refreshes every 2 seconds.
"""

import tkinter as tk
from tkinter import ttk
from datetime import date, datetime

import sensor
ITEMS = sensor.ITEMS

# ── Colors – white theme ─────────────────────────────────────────────────────
BG_PAGE   = "#ffffff"   # page background
BG_TITLE  = "#1a73e8"   # title bar (blue)
BG_HEADER = "#e8f0fe"   # column header row (light blue)
BG_ROW    = "#f8f9fa"   # item row background
BG_ROW_ALT= "#ffffff"   # alternating row background

FG_DARK   = "#1f1f1f"   # main text (near black)
FG_HEAD   = "#1a73e8"   # column header text (blue)
FG_GREEN  = "#188038"   # OK / plenty of days
FG_YELLOW = "#e37400"   # expiring soon (≤ 7 days)
FG_RED    = "#c5221f"   # LOW / expired

TAB_BG       = "#e8f0fe"   # inactive tab
TAB_SELECTED = "#1a73e8"   # active tab
TAB_FG       = "#1a73e8"   # inactive tab text
TAB_FG_SEL   = "#ffffff"   # active tab text

# ── Fonts – deliberately oversized so user can dial them back ─────────────────
FONT_TITLE = ("Helvetica", 36, "bold")   # main title
FONT_TAB   = ("Helvetica", 26, "bold")   # tab labels
FONT_HEAD  = ("Helvetica", 22, "bold")   # column headers
FONT_BODY  = ("Helvetica", 28)           # data rows


def days_until(expiry_str: str) -> int:
    expiry = datetime.strptime(expiry_str, "%Y-%m-%d").date()
    return (expiry - date.today()).days


class SmartShelfApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("SmartShelf")
        self.configure(bg=BG_PAGE)

        # Start fullscreen – press Escape to exit fullscreen
        self.attributes("-fullscreen", True)
        self.bind("<Escape>", lambda e: self.attributes("-fullscreen", False))

        # ── Title bar ────────────────────────────────────────────────────────
        title_bar = tk.Frame(self, bg=BG_TITLE)
        title_bar.pack(fill="x")
        tk.Label(
            title_bar,
            text="SmartShelf",
            font=FONT_TITLE,
            bg=BG_TITLE,
            fg="#ffffff",
            pady=12,
        ).pack()

        # ── Tab notebook ─────────────────────────────────────────────────────
        style = ttk.Style()
        style.theme_use("clam")

        style.configure("TNotebook",
                        background=BG_PAGE,
                        borderwidth=0,
                        tabmargins=0)
        style.configure("TNotebook.Tab",
                        background=TAB_BG,
                        foreground=TAB_FG,
                        font=FONT_TAB,
                        padding=(50, 14))
        style.map("TNotebook.Tab",
                  background=[("selected", TAB_SELECTED)],
                  foreground=[("selected", TAB_FG_SEL)])

        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill="both", expand=True, padx=0, pady=0)

        # ── Tab 1: Weight ─────────────────────────────────────────────────────
        wf = tk.Frame(self.notebook, bg=BG_PAGE)
        self.notebook.add(wf, text="  Weight  ")
        self._header(wf, ["Item", "Weight (g)", "Status"])
        self.weight_rows = [self._weight_row(wf, it, i) for i, it in enumerate(ITEMS)]

        # ── Tab 2: Expiry ─────────────────────────────────────────────────────
        ef = tk.Frame(self.notebook, bg=BG_PAGE)
        self.notebook.add(ef, text="  Expiry  ")
        self._header(ef, ["Item", "Expiry Date", "Days Left"])
        self.expiry_rows = [self._expiry_row(ef, it, i) for i, it in enumerate(ITEMS)]

        # ── Keyboard navigation ───────────────────────────────────────────────
        self.bind("<Left>",  self._prev_tab)
        self.bind("<Right>", self._next_tab)

        self._refresh()

    def _prev_tab(self, _=None):
        self.notebook.select(max(0, self.notebook.index("current") - 1))

    def _next_tab(self, _=None):
        self.notebook.select(min(self.notebook.index("end") - 1, self.notebook.index("current") + 1))

    def _header(self, parent, labels):
        frame = tk.Frame(parent, bg=BG_HEADER)
        frame.pack(fill="x", padx=0, pady=(0, 4))
        weights = [3, 2, 2]
        for col, (text, w) in enumerate(zip(labels, weights)):
            tk.Label(frame, text=text, font=FONT_HEAD,
                     bg=BG_HEADER, fg=FG_HEAD, anchor="w", pady=10, padx=16
                     ).grid(row=0, column=col, sticky="ew")
            frame.grid_columnconfigure(col, weight=w)

    def _weight_row(self, parent, item, index):
        bg = BG_ROW if index % 2 == 0 else BG_ROW_ALT
        card = tk.Frame(parent, bg=bg)
        card.pack(fill="x", padx=0, pady=2)

        def lbl(col, text, fg=FG_DARK, w=1):
            l = tk.Label(card, text=text, font=FONT_BODY,
                         bg=bg, fg=fg, anchor="w", pady=14, padx=16)
            l.grid(row=0, column=col, sticky="ew")
            card.grid_columnconfigure(col, weight=w)
            return l

        lbl(0, item["name"], w=3)
        weight_lbl = lbl(1, "--", w=2)
        status_lbl = lbl(2, "--", w=2)

        return {"weight": weight_lbl, "status": status_lbl}

    def _expiry_row(self, parent, item, index):
        bg = BG_ROW if index % 2 == 0 else BG_ROW_ALT
        card = tk.Frame(parent, bg=bg)
        card.pack(fill="x", padx=0, pady=2)

        def lbl(col, text, fg=FG_DARK, w=1):
            l = tk.Label(card, text=text, font=FONT_BODY,
                         bg=bg, fg=fg, anchor="w", pady=14, padx=16)
            l.grid(row=0, column=col, sticky="ew")
            card.grid_columnconfigure(col, weight=w)
            return l

        lbl(0, item["name"],   w=3)
        lbl(1, item["expiry"], w=2)
        days_lbl = lbl(2, "--", w=2)

        return {"days": days_lbl}

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
                txt, clr = "EXPIRED",      FG_RED
            elif days <= 7:
                txt, clr = f"{days}d left", FG_YELLOW
            else:
                txt, clr = f"{days} days",  FG_GREEN
            self.expiry_rows[i]["days"].config(text=txt, fg=clr)

        self.after(2000, self._refresh)


if __name__ == "__main__":
    app = SmartShelfApp()
    app.mainloop()
