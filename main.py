import tkinter as tk
from tkinter import ttk
import subprocess
import threading
import os



REPO_URL  = "https://github.com/minhnt1610/SLDP"
REPO_NAME = "SLDP"
CLONE_DIR = os.path.join(os.path.expanduser("~"), REPO_NAME)

SHELF_ITEMS = [
    ("Whole Milk",      "1.89 L",   "2026-04-01"),
    ("Cheddar Cheese",  "200 g",    "2026-05-15"),
    ("Greek Yogurt",    "500 g",    "2026-03-30"),
    ("Orange Juice",    "1.0 L",    "2026-04-10"),
]


# ---------------------------------------------------------------------------
# Splash / Init screen
# ---------------------------------------------------------------------------

class SplashScreen(tk.Frame):
    def __init__(self, master, on_done, sw, sh):
        super().__init__(master, bg="#1a1a2e", width=sw, height=sh)
        self.on_done = on_done
        self.sw = sw
        self.sh = sh
        self._build()
        self.after(100, self._run_git)

    def _build(self):
        sw, sh = self.sw, self.sh

        tk.Label(
            self,
            text="SMART SHELF",
            font=("Helvetica", sw // 16, "bold"),
            fg="#e94560",
            bg="#1a1a2e",
        ).place(relx=0.5, rely=0.26, anchor=tk.CENTER)

        tk.Label(
            self,
            text="SLDP",
            font=("Helvetica", sw // 36),
            fg="#a0a0c0",
            bg="#1a1a2e",
        ).place(relx=0.5, rely=0.42, anchor=tk.CENTER)

        self.status_var = tk.StringVar(value="Initializing...")
        tk.Label(
            self,
            textvariable=self.status_var,
            font=("Helvetica", sw // 44),
            fg="#e0e0e0",
            bg="#1a1a2e",
        ).place(relx=0.5, rely=0.59, anchor=tk.CENTER)

        self.progress = ttk.Progressbar(
            self, mode="indeterminate", length=int(sw * 0.72)
        )
        self.progress.place(relx=0.5, rely=0.73, anchor=tk.CENTER)

        tk.Label(
            self,
            text=REPO_URL,
            font=("Helvetica", sw // 72),
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
    def __init__(self, master, sw, sh):
        super().__init__(master, bg="#1a1a2e", width=sw, height=sh)
        self.sw = sw
        self.sh = sh
        self._build()

    def _build(self):
        sw, sh = self.sw, self.sh

        HEADER_H  = sh // 8
        font_size = sh // 22
        row_h     = (sh - HEADER_H) // (len(SHELF_ITEMS) + 1)

        # Header
        header = tk.Frame(self, bg="#16213e", height=HEADER_H)
        header.pack(fill=tk.X)
        header.pack_propagate(False)

        tk.Label(
            header,
            text="SMART SHELF",
            font=("Helvetica", sh // 18, "bold"),
            fg="#e0e0e0",
            bg="#16213e",
        ).pack(side=tk.LEFT, padx=sw // 48, pady=HEADER_H // 6)

        tk.Label(
            header,
            text="Inventory",
            font=("Helvetica", sh // 26),
            fg="#a0a0c0",
            bg="#16213e",
        ).pack(side=tk.RIGHT, padx=sw // 48, pady=HEADER_H // 4)

        # Table
        style = ttk.Style()
        style.theme_use("clam")
        style.configure(
            "Shelf.Treeview",
            background="#0f3460",
            foreground="#e0e0e0",
            fieldbackground="#0f3460",
            rowheight=row_h,
            font=("Helvetica", font_size),
        )
        style.configure(
            "Shelf.Treeview.Heading",
            background="#e94560",
            foreground="white",
            font=("Helvetica", font_size, "bold"),
            relief="flat",
        )
        style.map("Shelf.Treeview", background=[("selected", "#533483")])

        columns = ("item", "weight", "expiration")
        tree = ttk.Treeview(
            self,
            columns=columns,
            show="headings",
            style="Shelf.Treeview",
        )

        tree.heading("item",       text="Item")
        tree.heading("weight",     text="Weight / Vol.")
        tree.heading("expiration", text="Expires")

        # Column widths proportional to screen width
        tree.column("item",       width=sw * 42 // 100, anchor=tk.W)
        tree.column("weight",     width=sw * 28 // 100, anchor=tk.CENTER)
        tree.column("expiration", width=sw * 30 // 100, anchor=tk.CENTER)

        for i, row in enumerate(SHELF_ITEMS):
            tag = "even" if i % 2 == 0 else "odd"
            tree.insert("", tk.END, values=row, tags=(tag,))

        tree.tag_configure("even", background="#0f3460")
        tree.tag_configure("odd",  background="#162447")
        tree.pack(fill=tk.BOTH, expand=True)


# ---------------------------------------------------------------------------
# App controller
# ---------------------------------------------------------------------------

def main():
    root = tk.Tk()
    root.attributes("-fullscreen", True)

    # Read actual screen dimensions after fullscreen is applied
    root.update_idletasks()
    sw = root.winfo_screenwidth()
    sh = root.winfo_screenheight()

    # Press Escape to exit fullscreen
    root.bind("<Escape>", lambda e: root.destroy())

    def show_shelf():
        splash.pack_forget()
        shelf = ShelfScreen(root, sw, sh)
        shelf.pack(fill=tk.BOTH, expand=True)

    splash = SplashScreen(root, on_done=show_shelf, sw=sw, sh=sh)
    splash.pack(fill=tk.BOTH, expand=True)

    root.mainloop()


if __name__ == "__main__":
    main()
