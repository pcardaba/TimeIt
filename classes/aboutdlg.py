# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2024 Pablo Cardaba

from __future__ import annotations

import webbrowser
from pathlib import Path

import tkinter as tk
from tkinter import ttk
import tkinter.font as tkfont

from ._version import __version__

CONTACT_EMAIL = "timeit.oss+contact@gmail.com"
REPO_BASE = "https://github.com/pcardaba/TimeIt"


def _docs_url() -> str:
    """Build the user-manual URL, pointing at the running version when possible.

    `__version__` comes from `git describe` (e.g. ``v1.0.0`` for an exact tag or
    ``v1.0.0-7-g055292e`` when commits followed the tag). For an exact tag we
    link to that tag's docs; otherwise we fall back to ``main``.
    """
    ref = "main"
    ver = __version__.strip()
    if ver and "-" not in ver:
        ref = ver
    return f"{REPO_BASE}/tree/{ref}/docs"


class AboutDlg(tk.Toplevel):
    """Modal 'About TimeIt' informational dialog."""

    def __init__(self, parent: tk.Misc):
        super().__init__(parent)
        self.title("About TimeIt")
        self.transient(parent)
        self.resizable(False, False)

        frame = ttk.Frame(self, padding=20)
        frame.grid(row=0, column=0, sticky="nsew")

        # ---- Icon ----
        icon_path = Path(__file__).parent.parent / "data" / "timeit_icon.png"
        if icon_path.exists():
            self._icon = tk.PhotoImage(file=str(icon_path))
            ttk.Label(frame, image=self._icon).grid(row=0, column=0, pady=(0, 10))

        # ---- Title & version ----
        ttk.Label(frame, text="TimeIt",
                  font=("TkDefaultFont", 16, "bold")).grid(row=1, column=0)
        ttk.Label(frame, text="Timing diagram editor for digital hardware") \
            .grid(row=2, column=0, pady=(0, 10))
        ttk.Label(frame, text=f"Version: {__version__}") \
            .grid(row=3, column=0, pady=(0, 10))

        # ---- User manual link ----
        docs_url = _docs_url()
        self._add_link(frame, row=4, text="User manual (documentation)", url=docs_url)

        # ---- Contact ----
        contact_row = ttk.Frame(frame)
        contact_row.grid(row=5, column=0, pady=(10, 0))
        ttk.Label(contact_row, text="Contact: ").grid(row=0, column=0)
        self._add_link(contact_row, row=0, column=1,
                       text=CONTACT_EMAIL, url=f"mailto:{CONTACT_EMAIL}")

        # ---- Close button ----
        ttk.Button(frame, text="Close", command=self.destroy) \
            .grid(row=6, column=0, pady=(20, 0))

        self.bind("<Escape>", lambda _e: self.destroy())
        self.grab_set()
        self._center_on(parent)
        self.wait_window()

    def _add_link(self, parent: tk.Misc, row: int, text: str, url: str,
                  column: int = 0) -> None:
        link = ttk.Label(parent, text=text, foreground="#1a73e8", cursor="hand2")
        link.grid(row=row, column=column)
        font = tkfont.Font(link, link.cget("font"))
        font.configure(underline=True)
        link.configure(font=font)
        link.bind("<Button-1>", lambda _e: webbrowser.open(url))

    def _center_on(self, parent: tk.Misc) -> None:
        self.update_idletasks()
        try:
            px = parent.winfo_rootx()
            py = parent.winfo_rooty()
            pw = parent.winfo_width()
            ph = parent.winfo_height()
            w = self.winfo_width()
            h = self.winfo_height()
            self.geometry(f"+{px + (pw - w) // 2}+{py + (ph - h) // 2}")
        except tk.TclError:
            pass
