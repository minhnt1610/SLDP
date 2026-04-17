"""
SmartShelf Display
------------------
White theme, fullscreen, large fonts for 480×320 LCD.
4 tabs: Weight | Expiry | Manage | Camera
"""

import threading
import tkinter as tk
from tkinter import ttk, messagebox
from datetime import date, datetime
import sensor
import door
import nfc_reader

try:
    import cv2
    _CV2 = True
except ImportError:
    _CV2 = False

try:
    from PIL import Image, ImageTk
    _PIL = True
except ImportError:
    _PIL = False

CAMERA_AVAILABLE = _CV2 and _PIL

# ── Colors ────────────────────────────────────────────────────────────────────
BG_PAGE    = "#ffffff"
BG_TITLE   = "#1a73e8"
BG_HEADER  = "#e8f0fe"
BG_ROW     = "#f8f9fa"
BG_ROW_ALT = "#ffffff"
BG_ADD     = "#188038"
BG_EDIT    = "#1a73e8"
BG_DEL     = "#c5221f"
BG_CANCEL  = "#9e9e9e"

FG_DARK   = "#1f1f1f"
FG_HEAD   = "#1a73e8"
FG_GREEN  = "#188038"
FG_YELLOW = "#e37400"
FG_RED    = "#c5221f"
FG_WHITE  = "#ffffff"

TAB_BG       = "#e8f0fe"
TAB_SELECTED = "#1a73e8"
TAB_FG       = "#1a73e8"
TAB_FG_SEL   = "#ffffff"

# ── Fonts ─────────────────────────────────────────────────────────────────────
FONT_TITLE  = ("Helvetica", 36, "bold")
FONT_TAB    = ("Helvetica", 22, "bold")
FONT_HEAD   = ("Helvetica", 22, "bold")
FONT_BODY   = ("Helvetica", 28)
FONT_MANAGE = ("Helvetica", 20)
FONT_BTN    = ("Helvetica", 18, "bold")
FONT_DLG    = ("Helvetica", 20)
FONT_DLG_SM = ("Helvetica", 17)


def days_until(expiry_str: str) -> int:
    return (datetime.strptime(expiry_str, "%Y-%m-%d").date() - date.today()).days


# ── Item dialog ───────────────────────────────────────────────────────────────

class ItemDialog(tk.Toplevel):
    """Modal dialog for adding or editing a shelf item."""

    def __init__(self, parent, title, item=None):
        super().__init__(parent)
        self.title(title)
        self.configure(bg=BG_PAGE)
        self.resizable(False, False)
        self.result = None
        self.transient(parent)
        self.grab_set()

        pad = {"padx": 14, "pady": 8}

        # Name
        tk.Label(self, text="Item Name:", font=FONT_DLG_SM,
                 bg=BG_PAGE, fg=FG_DARK).grid(row=0, column=0, sticky="w", **pad)
        self.name_var = tk.StringVar(value=item["name"] if item else "")
        name_entry = tk.Entry(self, textvariable=self.name_var, font=FONT_DLG, width=18)
        name_entry.grid(row=0, column=1, sticky="ew", **pad)
        if item:
            name_entry.config(state="disabled")

        # Threshold
        tk.Label(self, text="Low Threshold (g):", font=FONT_DLG_SM,
                 bg=BG_PAGE, fg=FG_DARK).grid(row=1, column=0, sticky="w", **pad)
        self.threshold_var = tk.StringVar(value=str(item["threshold"]) if item else "")
        tk.Entry(self, textvariable=self.threshold_var, font=FONT_DLG, width=18
                 ).grid(row=1, column=1, sticky="ew", **pad)

        # Expiry
        tk.Label(self, text="Expiry (YYYY-MM-DD):", font=FONT_DLG_SM,
                 bg=BG_PAGE, fg=FG_DARK).grid(row=2, column=0, sticky="w", **pad)
        self.expiry_var = tk.StringVar(value=item["expiry"] if item else "")
        tk.Entry(self, textvariable=self.expiry_var, font=FONT_DLG, width=18
                 ).grid(row=2, column=1, sticky="ew", **pad)

        # Buttons
        btn_frame = tk.Frame(self, bg=BG_PAGE)
        btn_frame.grid(row=3, column=0, columnspan=2, pady=14)
        tk.Button(btn_frame, text="Save", font=FONT_BTN, bg=BG_ADD, fg=FG_WHITE,
                  relief="flat", padx=20, pady=8, command=self._save
                  ).pack(side="left", padx=8)
        tk.Button(btn_frame, text="Cancel", font=FONT_BTN, bg=BG_CANCEL, fg=FG_WHITE,
                  relief="flat", padx=20, pady=8, command=self.destroy
                  ).pack(side="left", padx=8)

        self.grid_columnconfigure(1, weight=1)
        self.wait_window()

    def _save(self):
        name = self.name_var.get().strip()
        expiry = self.expiry_var.get().strip()
        threshold_str = self.threshold_var.get().strip()

        if not name:
            messagebox.showerror("Error", "Item name is required.", parent=self)
            return
        try:
            threshold = int(threshold_str)
        except ValueError:
            messagebox.showerror("Error", "Threshold must be a whole number.", parent=self)
            return
        try:
            datetime.strptime(expiry, "%Y-%m-%d")
        except ValueError:
            messagebox.showerror("Error", "Expiry must be YYYY-MM-DD.", parent=self)
            return

        self.result = {"name": name, "threshold": threshold, "expiry": expiry}
        self.destroy()


# ── Main app ──────────────────────────────────────────────────────────────────

class SmartShelfApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("SmartShelf")
        self.configure(bg=BG_PAGE)
        self.attributes("-fullscreen", True)
        self.bind("<Escape>", lambda e: self.attributes("-fullscreen", False))

        self._item_count = len(sensor.ITEMS)
        self._weight_content = None
        self._expiry_content = None
        self._manage_content = None
        self._door_content = None
        self.cap = None
        self._cam_img = None
        self._cam_label = None
        self._door_status_label = None
        self._nfc_log_label = None

        # ── Door / NFC setup ──────────────────────────────────────────────────
        door.setup()
        nfc_reader.start_polling(
            on_valid=self._on_valid_card,
            on_invalid=self._on_invalid_card,
        )

        # ── Title bar ─────────────────────────────────────────────────────────
        tk.Frame(self, bg=BG_TITLE, height=2).pack(fill="x")
        title_bar = tk.Frame(self, bg=BG_TITLE)
        title_bar.pack(fill="x")
        tk.Label(title_bar, text="SmartShelf", font=FONT_TITLE,
                 bg=BG_TITLE, fg=FG_WHITE, pady=10).pack()

        # ── Notebook ──────────────────────────────────────────────────────────
        style = ttk.Style()
        style.theme_use("clam")
        style.configure("TNotebook", background=BG_PAGE, borderwidth=0, tabmargins=0)
        style.configure("TNotebook.Tab", background=TAB_BG, foreground=TAB_FG,
                        font=FONT_TAB, padding=(24, 12))
        style.map("TNotebook.Tab",
                  background=[("selected", TAB_SELECTED)],
                  foreground=[("selected", TAB_FG_SEL)])

        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill="both", expand=True)

        self.weight_frame = tk.Frame(self.notebook, bg=BG_PAGE)
        self.expiry_frame = tk.Frame(self.notebook, bg=BG_PAGE)
        self.manage_frame = tk.Frame(self.notebook, bg=BG_PAGE)
        self.door_frame   = tk.Frame(self.notebook, bg=BG_PAGE)
        self.camera_frame = tk.Frame(self.notebook, bg="black")

        self.notebook.add(self.weight_frame, text="Weight")
        self.notebook.add(self.expiry_frame, text="Expiry")
        self.notebook.add(self.manage_frame, text="Manage")
        self.notebook.add(self.door_frame,   text="Door")
        self.notebook.add(self.camera_frame, text="Camera")

        self.bind("<Left>",  self._prev_tab)
        self.bind("<Right>", self._next_tab)
        self.notebook.bind("<<NotebookTabChanged>>", self._on_tab_change)

        self._build_weight_tab()
        self._build_expiry_tab()
        self._build_manage_tab()
        self._build_door_tab()
        self._build_camera_tab()

        self._refresh()

    # ── Navigation ────────────────────────────────────────────────────────────

    def _prev_tab(self, _=None):
        self.notebook.select(max(0, self.notebook.index("current") - 1))

    def _next_tab(self, _=None):
        self.notebook.select(min(self.notebook.index("end") - 1,
                                 self.notebook.index("current") + 1))

    def _on_tab_change(self, _=None):
        if self.notebook.index("current") == 4:
            self._start_camera()
        else:
            self._stop_camera()

    # ── Shared helper ─────────────────────────────────────────────────────────

    def _header(self, parent, labels, col_weights):
        frame = tk.Frame(parent, bg=BG_HEADER)
        frame.pack(fill="x")
        for col, (text, w) in enumerate(zip(labels, col_weights)):
            tk.Label(frame, text=text, font=FONT_HEAD,
                     bg=BG_HEADER, fg=FG_HEAD, anchor="w", pady=10, padx=16
                     ).grid(row=0, column=col, sticky="ew")
            frame.grid_columnconfigure(col, weight=w)

    # ── Weight tab ────────────────────────────────────────────────────────────

    def _build_weight_tab(self):
        if self._weight_content:
            self._weight_content.destroy()
        self._weight_content = tk.Frame(self.weight_frame, bg=BG_PAGE)
        self._weight_content.pack(fill="both", expand=True)
        self._header(self._weight_content, ["Item", "Weight (g)", "Status"], [3, 2, 2])
        self.weight_rows = [
            self._weight_row(self._weight_content, it, i)
            for i, it in enumerate(sensor.ITEMS)
        ]

    def _weight_row(self, parent, item, index):
        bg = BG_ROW if index % 2 == 0 else BG_ROW_ALT
        card = tk.Frame(parent, bg=bg)
        card.pack(fill="x", pady=2)

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

    # ── Expiry tab ────────────────────────────────────────────────────────────

    def _build_expiry_tab(self):
        if self._expiry_content:
            self._expiry_content.destroy()
        self._expiry_content = tk.Frame(self.expiry_frame, bg=BG_PAGE)
        self._expiry_content.pack(fill="both", expand=True)
        self._header(self._expiry_content, ["Item", "Expiry Date", "Days Left"], [3, 2, 2])
        self.expiry_rows = [
            self._expiry_row(self._expiry_content, it, i)
            for i, it in enumerate(sensor.ITEMS)
        ]

    def _expiry_row(self, parent, item, index):
        bg = BG_ROW if index % 2 == 0 else BG_ROW_ALT
        card = tk.Frame(parent, bg=bg)
        card.pack(fill="x", pady=2)

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

    # ── Manage tab ────────────────────────────────────────────────────────────

    def _build_manage_tab(self):
        if self._manage_content:
            self._manage_content.destroy()
        self._manage_content = tk.Frame(self.manage_frame, bg=BG_PAGE)
        self._manage_content.pack(fill="both", expand=True)

        # Add button bar
        top = tk.Frame(self._manage_content, bg=BG_PAGE)
        top.pack(fill="x", padx=16, pady=(10, 4))
        tk.Button(top, text="+ Add Item", font=FONT_BTN, bg=BG_ADD, fg=FG_WHITE,
                  relief="flat", padx=18, pady=8, command=self._add_item).pack(side="left")

        # Scrollable item list
        canvas = tk.Canvas(self._manage_content, bg=BG_PAGE, highlightthickness=0)
        scrollbar = tk.Scrollbar(self._manage_content, orient="vertical", command=canvas.yview)
        scroll_frame = tk.Frame(canvas, bg=BG_PAGE)
        scroll_frame.bind("<Configure>",
                          lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=scroll_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        for i, item in enumerate(sensor.ITEMS):
            self._manage_row(scroll_frame, item, i)

    def _manage_row(self, parent, item, index):
        bg = BG_ROW if index % 2 == 0 else BG_ROW_ALT
        row = tk.Frame(parent, bg=bg)
        row.pack(fill="x", pady=2)

        tk.Label(row, text=item["name"], font=FONT_MANAGE,
                 bg=bg, fg=FG_DARK, anchor="w", padx=16, pady=14
                 ).grid(row=0, column=0, sticky="ew")

        tk.Button(row, text="Edit", font=FONT_BTN, bg=BG_EDIT, fg=FG_WHITE,
                  relief="flat", padx=14, pady=6,
                  command=lambda it=item: self._edit_item(it)
                  ).grid(row=0, column=1, padx=4, pady=4)

        tk.Button(row, text="Delete", font=FONT_BTN, bg=BG_DEL, fg=FG_WHITE,
                  relief="flat", padx=14, pady=6,
                  command=lambda it=item: self._delete_item(it)
                  ).grid(row=0, column=2, padx=4, pady=4)

        row.grid_columnconfigure(0, weight=1)

    def _add_item(self):
        dlg = ItemDialog(self, "Add Item")
        if dlg.result:
            r = dlg.result
            sensor.add_item(r["name"], r["threshold"], r["expiry"])
            self._rebuild_all()

    def _edit_item(self, item):
        dlg = ItemDialog(self, "Edit Item", item=item)
        if dlg.result:
            r = dlg.result
            sensor.update_item(item["name"], threshold=r["threshold"], expiry=r["expiry"])
            self._rebuild_all()

    def _delete_item(self, item):
        if messagebox.askyesno("Delete", f"Remove '{item['name']}'?", parent=self):
            sensor.remove_item(item["name"])
            self._rebuild_all()

    def _rebuild_all(self):
        self._item_count = len(sensor.ITEMS)
        self._build_weight_tab()
        self._build_expiry_tab()
        self._build_manage_tab()

    # ── Door tab ──────────────────────────────────────────────────────────────

    def _build_door_tab(self):
        f = self.door_frame

        # Door status
        status_frame = tk.Frame(f, bg=BG_PAGE)
        status_frame.pack(fill="x", padx=20, pady=(20, 8))
        tk.Label(status_frame, text="Door Status:", font=FONT_HEAD,
                 bg=BG_PAGE, fg=FG_DARK).pack(side="left")
        self._door_status_label = tk.Label(status_frame, text="CLOSED",
                                           font=FONT_HEAD, bg=BG_PAGE, fg=FG_GREEN)
        self._door_status_label.pack(side="left", padx=10)

        # Last NFC event
        tk.Label(f, text="Last card scanned:", font=FONT_MANAGE,
                 bg=BG_PAGE, fg=FG_DARK).pack(anchor="w", padx=20)
        self._nfc_log_label = tk.Label(f, text="—", font=FONT_MANAGE,
                                       bg=BG_PAGE, fg=FG_DARK, wraplength=440, justify="left")
        self._nfc_log_label.pack(anchor="w", padx=20, pady=4)

        # Manual override buttons
        btn_frame = tk.Frame(f, bg=BG_PAGE)
        btn_frame.pack(pady=20)
        tk.Button(btn_frame, text="Open Door", font=FONT_BTN, bg=BG_ADD, fg=FG_WHITE,
                  relief="flat", padx=24, pady=10,
                  command=self._manual_open).pack(side="left", padx=10)
        tk.Button(btn_frame, text="Close Door", font=FONT_BTN, bg=BG_DEL, fg=FG_WHITE,
                  relief="flat", padx=24, pady=10,
                  command=self._manual_close).pack(side="left", padx=10)

        # Authorised cards list
        tk.Label(f, text="Authorised cards:", font=FONT_MANAGE,
                 bg=BG_PAGE, fg=FG_DARK).pack(anchor="w", padx=20, pady=(16, 4))
        self._cards_frame = tk.Frame(f, bg=BG_PAGE)
        self._cards_frame.pack(fill="x", padx=20)
        self._refresh_cards_list()

    def _refresh_cards_list(self):
        for w in self._cards_frame.winfo_children():
            w.destroy()
        cards = nfc_reader.get_cards()
        if not cards:
            tk.Label(self._cards_frame, text="No cards registered.",
                     font=FONT_MANAGE, bg=BG_PAGE, fg=FG_DARK).pack(anchor="w")
        for uid in cards:
            row = tk.Frame(self._cards_frame, bg=BG_PAGE)
            row.pack(fill="x", pady=2)
            tk.Label(row, text=uid, font=FONT_MANAGE,
                     bg=BG_PAGE, fg=FG_DARK).pack(side="left")
            tk.Button(row, text="Remove", font=FONT_BTN, bg=BG_DEL, fg=FG_WHITE,
                      relief="flat", padx=10, pady=4,
                      command=lambda u=uid: self._remove_card(u)
                      ).pack(side="right", padx=4)

    def _remove_card(self, uid: str):
        nfc_reader.remove_card(uid)
        self._refresh_cards_list()

    def _manual_open(self):
        threading.Thread(target=door.open_door, daemon=True).start()
        self._update_door_status()

    def _manual_close(self):
        threading.Thread(target=door.close_door, daemon=True).start()
        self._update_door_status()

    def _update_door_status(self):
        if door.is_open():
            self._door_status_label.config(text="OPEN", fg=FG_RED)
        else:
            self._door_status_label.config(text="CLOSED", fg=FG_GREEN)

    def _on_valid_card(self, uid: str):
        """Called from NFC background thread — must use after() to touch GUI."""
        self.after(0, lambda: self._handle_valid_card(uid))

    def _on_invalid_card(self, uid: str):
        self.after(0, lambda: self._nfc_log_label.config(
            text=f"Denied: {uid}", fg=FG_RED))

    def _handle_valid_card(self, uid: str):
        self._nfc_log_label.config(text=f"Access granted: {uid}", fg=FG_GREEN)
        threading.Thread(target=door.toggle_door, daemon=True).start()
        self.after(600, self._update_door_status)

    # ── Camera tab ────────────────────────────────────────────────────────────

    def _build_camera_tab(self):
        if CAMERA_AVAILABLE:
            self._cam_label = tk.Label(self.camera_frame, bg="black")
            self._cam_label.pack(fill="both", expand=True)
        else:
            tk.Label(self.camera_frame,
                     text="Camera unavailable\n\nInstall dependencies:\npip install opencv-python Pillow",
                     font=FONT_MANAGE, bg="black", fg=FG_WHITE, justify="center"
                     ).pack(expand=True)

    def _start_camera(self):
        if not CAMERA_AVAILABLE:
            return
        if self.cap is None or not self.cap.isOpened():
            self.cap = cv2.VideoCapture(0)
        self._update_camera()

    def _stop_camera(self):
        if self.cap and self.cap.isOpened():
            self.cap.release()
            self.cap = None

    def _update_camera(self):
        if self.notebook.index("current") != 4:
            return
        if not CAMERA_AVAILABLE or self.cap is None or not self.cap.isOpened():
            return
        ret, frame = self.cap.read()
        if ret:
            frame = cv2.rotate(frame, cv2.ROTATE_180)
            frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            w = self._cam_label.winfo_width()  or 480
            h = self._cam_label.winfo_height() or 240
            frame = cv2.resize(frame, (w, h))
            img = Image.fromarray(frame)
            self._cam_img = ImageTk.PhotoImage(img)
            self._cam_label.config(image=self._cam_img)
        self.after(100, self._update_camera)   # ~10 fps

    # ── Periodic data refresh ─────────────────────────────────────────────────

    def _refresh(self):
        if len(sensor.ITEMS) != self._item_count:
            self._rebuild_all()

        for i, item in enumerate(sensor.ITEMS):
            # Weight tab
            if i < len(self.weight_rows):
                wr = self.weight_rows[i]
                wr["weight"].config(text=f"{item['weight']:.1f} g")
                if item["status"] == "LOW":
                    wr["status"].config(text="LOW !", fg=FG_RED)
                else:
                    wr["status"].config(text="OK",    fg=FG_GREEN)

            # Expiry tab
            if i < len(self.expiry_rows):
                days = days_until(item["expiry"])
                if days < 0:
                    txt, clr = "EXPIRED",      FG_RED
                elif days <= 7:
                    txt, clr = f"{days}d left", FG_YELLOW
                else:
                    txt, clr = f"{days} days",  FG_GREEN
                self.expiry_rows[i]["days"].config(text=txt, fg=clr)

        self.after(2000, self._refresh)

    def destroy(self):
        self._stop_camera()
        door.cleanup()
        super().destroy()


if __name__ == "__main__":
    app = SmartShelfApp()
    app.mainloop()
