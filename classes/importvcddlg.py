# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2024 Pablo Cardaba

from __future__ import annotations

from pathlib import Path

import tkinter as tk
from tkinter import ttk, filedialog, messagebox


class ImportVCDDlg(tk.Toplevel):
    """Modal form asking for the pair of VCD dump files to import.

    min: dump from the best-case simulation (minimum delays).
    max: dump from the worst-case simulation (maximum delays).
    A user not interested in min/max representation gives the same
    file on both entries.

    After wait_window(), `result` holds (min_path, max_path) as strings,
    or None when the dialog was cancelled.
    """

    _FILETYPES = [("VCD dump", "*.vcd"), ("All files", "*.*")]

    def __init__(self, parent: tk.Misc):
        super().__init__(parent)
        self.title("Import VCDs")
        self.transient(parent)
        self.grab_set()
        self.resizable(True, False)

        self.result: tuple[str, str] | None = None

        self._min_var = tk.StringVar(self)
        self._max_var = tk.StringVar(self)

        frm = ttk.Frame(self, padding=10)
        frm.grid(row=0, column=0, sticky="nsew")
        self.columnconfigure(0, weight=1)
        frm.columnconfigure(1, weight=1)

        ttk.Label(
            frm,
            text=("Select the VCD dump files of the simulation interval "
                  "to import.\n"
                  "Give the same file on both entries when no min/max "
                  "distinction is needed."),
            justify="left",
        ).grid(row=0, column=0, columnspan=3, sticky="w", pady=(0, 10))

        ttk.Label(frm, text="Min. (best case) VCD:").grid(
            row=1, column=0, sticky="w", padx=(0, 6), pady=2)
        min_entry = ttk.Entry(frm, textvariable=self._min_var, width=50)
        min_entry.grid(row=1, column=1, sticky="ew", pady=2)
        ttk.Button(frm, text="Browse…",
                   command=lambda: self._browse(self._min_var, "Min. (best case) VCD file")
                   ).grid(row=1, column=2, sticky="ew", padx=(6, 0), pady=2)

        ttk.Label(frm, text="Max. (worst case) VCD:").grid(
            row=2, column=0, sticky="w", padx=(0, 6), pady=2)
        max_entry = ttk.Entry(frm, textvariable=self._max_var, width=50)
        max_entry.grid(row=2, column=1, sticky="ew", pady=2)
        ttk.Button(frm, text="Browse…",
                   command=lambda: self._browse(self._max_var, "Max. (worst case) VCD file")
                   ).grid(row=2, column=2, sticky="ew", padx=(6, 0), pady=2)

        btns = ttk.Frame(frm)
        btns.grid(row=3, column=0, columnspan=3, sticky="e", pady=(12, 0))
        ttk.Button(btns, text="Import", command=self._ok).grid(row=0, column=0, padx=6)
        ttk.Button(btns, text="Cancel", command=self._cancel).grid(row=0, column=1)

        self.bind("<Return>", lambda e: self._ok())
        self.bind("<Escape>", lambda e: self._cancel())
        self.protocol("WM_DELETE_WINDOW", self._cancel)
        min_entry.focus_set()

    def _browse(self, var: tk.StringVar, title: str) -> None:
        ## Start in the directory of whichever path is already filled in,
        ## so the second pick lands next to the first.
        initial = ""
        for candidate in (var.get(), self._min_var.get(), self._max_var.get()):
            if candidate.strip():
                initial = str(Path(candidate.strip()).parent)
                break
        path_str = filedialog.askopenfilename(
            parent=self,
            title=title,
            initialdir=initial or None,
            filetypes=self._FILETYPES,
        )
        if path_str:
            var.set(path_str)

    def _ok(self) -> None:
        min_path = self._min_var.get().strip()
        max_path = self._max_var.get().strip()

        if not min_path or not max_path:
            messagebox.showerror(
                "Import VCDs",
                "Both VCD files are required.\n"
                "Give the same file on both entries when no min/max "
                "distinction is needed.",
                parent=self)
            return

        for label, p in (("Min.", min_path), ("Max.", max_path)):
            if not Path(p).is_file():
                messagebox.showerror(
                    "Import VCDs",
                    f"{label} VCD file not found:\n{p}",
                    parent=self)
                return

        self.result = (min_path, max_path)
        self.destroy()

    def _cancel(self) -> None:
        self.result = None
        self.destroy()
