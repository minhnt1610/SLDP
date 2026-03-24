import tkinter as tk
from tkinter import ttk
import subprocess
import threading
import os

# UC-649 3.5" LCD resolution
SCREEN_WIDTH  = 480
SCREEN_HEIGHT = 320

REPO_URL  = "https://github.com/minhnt1610/SLDP"
REPO_NAME = "SLDP"
CLONE_DIR = os.path.join(os.path.expanduser("~"), REPO_NAME)

SHELF_ITEMS = [
    ("Whole Milk",      "1.89 L",   "2026-04-01"),
    ("Cheddar Cheese",  "200 g",    "2026-05-15"),
    ("Greek Yogurt",    "500 g",    "2026-03-30"),
    ("Orange Juice",    "1.0 L",    "2026-04-10"),
    ("Butter",          "250 g",    "2026-06-20"),
    ("Eggs (12 pack)",  "680 g",    "2026-04-05"),
    ("Cream Cheese",    "340 g",    "2026-04-18"),
    ("Almond Milk",     "946 mL",   "2026-05-02"),
]


# ---------------------------------------------------------------------------
# Splash / Init screen
# ---------------------------------------------------------------------------

class SplashScreen(tk.Frame):
    def __init__(self, master, on_done):
        super().__init__(master, bg="#1a1a2e",
                         width=SCREEN_WIDTH, height=SCREEN_HEIGHT)
        self.on_done = on_done
        self._build()
        self.after(100, self._run_git)

    def _build(self):
        tk.Label(
            self,
            text="SMART SHELF",
            font=("Helvetica", 30, "bold"),
            fg="#e94560",
            bg="#1a1a2e",
        ).place(relx=0.5, rely=0.26, anchor=tk.CENTER)

        tk.Label(
            self,
            text="SLDP",
            font=("Helvetica", 14),
            fg="#a0a0c0",
            bg="#1a1a2e",
        ).place(relx=0.5, rely=0.42, anchor=tk.CENTER)

        self.status_var = tk.StringVar(value="Initializing...")
        tk.Label(
            self,
            textvariable=self.status_var,
            font=("Helvetica", 12),
            fg="#e0e0e0",
            bg="#1a1a2e",
        ).place(relx=0.5, rely=0.59, anchor=tk.CENTER)

        self.progress = ttk.Progressbar(
            self, mode="indeterminate", length=360
        )
        self.progress.place(relx=0.5, rely=0.73, anchor=tk.CENTER)

        tk.Label(
            self,
            text=REPO_URL,
            font=("Helvetica", 9),
            fg="#555577",
            bg="#1a1a2e",
        ).place(relx=0.5, rely=0.90, anchor=tk.CENTER)

    def _run_git(self):
        self.progress.start(12)
        threading.Thread(target=self._git_worker, daemon=True).start()

    def _git_worker(self):
        try:
            if os.path.isdir(os.path.join(CLONE_DIR, ".git")):
                self._set_status("Repository found — pulling latest...")
                result = subprocess.run(
                    ["git", "-C", CLONE_DIR, "pull"],
                    capture_output=True, text=True, timeout=60
                )
            else:
                self._set_status("Cloning repository...")
                result = subprocess.run(
                    ["git", "clone", REPO_URL, CLONE_DIR],
                    capture_output=True, text=True, timeout=120
                )

            if result.returncode == 0:
                self._set_status("Done!")
            else:
                self._set_status(f"Git error: {result.stderr.strip()[:55]}")
        except FileNotFoundError:
            self._set_status("git not found — skipping sync")
        except subprocess.TimeoutExpired:
            self._set_status("Timeout — check network connection")
        except Exception as e:
            self._set_status(f"Error: {str(e)[:55]}")

        self.after(1200, self._finish)

    def _set_status(self, msg):
        self.after(0, lambda: self.status_var.set(msg))

    def _finish(self):
        self.progress.stop()
        self.on_done()


# ---------------------------------------------------------------------------
# Main shelf screen
# ---------------------------------------------------------------------------

class ShelfScreen(tk.Frame):
    def __init__(self, master):
        super().__init__(master, bg="#1a1a2e",
                         width=SCREEN_WIDTH, height=SCREEN_HEIGHT)
        self._build()

    def _build(self):
        # Header
        header = tk.Frame(self, bg="#16213e", height=52)
        header.pack(fill=tk.X)
        header.pack_propagate(False)

        tk.Label(
            header,
            text="SMART SHELF",
            font=("Helvetica", 20, "bold"),
            fg="#e0e0e0",
            bg="#16213e",
        ).pack(side=tk.LEFT, padx=12, pady=8)

        tk.Label(
            header,
            text="Inventory",
            font=("Helvetica", 12),
            fg="#a0a0c0",
            bg="#16213e",
        ).pack(side=tk.RIGHT, padx=12, pady=14)

        # Table
        table_frame = tk.Frame(self, bg="#1a1a2e")
        table_frame.pack(fill=tk.BOTH, expand=True, padx=4, pady=(4, 0))

        style = ttk.Style()
        style.theme_use("clam")
        style.configure(
            "Shelf.Treeview",
            background="#0f3460",
            foreground="#e0e0e0",
            fieldbackground="#0f3460",
            rowheight=33,
            font=("Helvetica", 11),
        )
        style.configure(
            "Shelf.Treeview.Heading",
            background="#e94560",
            foreground="white",
            font=("Helvetica", 11, "bold"),
            relief="flat",
        )
        style.map("Shelf.Treeview", background=[("selected", "#533483")])

        columns = ("item", "weight", "expiration")
        tree = ttk.Treeview(
            table_frame,
            columns=columns,
            show="headings",
            style="Shelf.Treeview",
            height=7,
        )

        tree.heading("item",       text="Item")
        tree.heading("weight",     text="Weight / Vol.")
        tree.heading("expiration", text="Expires")

        # Columns fill full 480px width
        tree.column("item",       width=200, anchor=tk.W)
        tree.column("weight",     width=130, anchor=tk.CENTER)
        tree.column("expiration", width=150, anchor=tk.CENTER)

        for i, row in enumerate(SHELF_ITEMS):
            tag = "even" if i % 2 == 0 else "odd"
            tree.insert("", tk.END, values=row, tags=(tag,))

        tree.tag_configure("even", background="#0f3460")
        tree.tag_configure("odd",  background="#162447")
        tree.pack(fill=tk.BOTH, expand=True)

        # Status bar
        status = tk.Frame(self, bg="#16213e", height=34)
        status.pack(fill=tk.X, side=tk.BOTTOM)
        status.pack_propagate(False)

        tk.Label(
            status,
            text=f"Items: {len(SHELF_ITEMS)}",
            font=("Helvetica", 11),
            fg="#a0a0c0",
            bg="#16213e",
        ).pack(side=tk.LEFT, padx=12)

        tk.Label(
            status,
            text="SLDP v0.1",
            font=("Helvetica", 11),
            fg="#a0a0c0",
            bg="#16213e",
        ).pack(side=tk.RIGHT, padx=12)


# ---------------------------------------------------------------------------
# App controller
# ---------------------------------------------------------------------------

def main():
    root = tk.Tk()
    root.title("Smart Shelf")
    root.geometry(f"{SCREEN_WIDTH}x{SCREEN_HEIGHT}")
    root.resizable(False, False)

    def show_shelf():
        splash.pack_forget()
        shelf = ShelfScreen(root)
        shelf.pack(fill=tk.BOTH, expand=True)

    splash = SplashScreen(root, on_done=show_shelf)
    splash.pack(fill=tk.BOTH, expand=True)

    root.mainloop()


if __name__ == "__main__":
    main()
