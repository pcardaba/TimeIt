# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2024 Pablo Cardaba

"""Right-click menu of the expression entries of the signal dialogs.

Every entry that takes a Tcl expression (a period, an edge time, a delay, a
setup) gets a context menu listing the timing variables: picking one inserts
``$name`` at the cursor. The last entry opens the *User Timings* window under
the dialog, where variables are created (see ``TimeItApp.open_timings``).

Usage, from a dialog that has a ``topapp`` attribute::

    bind_timing_var_menu(entry, self)
"""

from __future__ import annotations

import tkinter as tk


class TimingVarMenu:
    """The context menu of one expression entry."""

    def __init__(self, entry: tk.Entry, dialog: tk.Misc) -> None:
        self.entry = entry
        self.dialog = dialog
        self.topapp = dialog.topapp
        entry.bind("<Button-3>", self.popup, add=True)
        ## Keep a handle on the entry so tests (and dialogs) can reach it.
        entry.timing_menu = self

    # ------------------------------------------------------------------
    def build(self) -> tk.Menu:
        """A fresh menu over the current variables (they change at any time)."""
        menu = tk.Menu(self.entry, tearoff=0)
        tvars = self.topapp.timings.tvars
        if not tvars:
            menu.add_command(label="(no timing variables)", state="disabled")
        for name, value in tvars.items():
            menu.add_command(label=f"{name}  =  {value}",
                             command=lambda n=name: self.insert(n))
        menu.add_separator()
        menu.add_command(label="Timings…",
                         command=lambda: self.topapp.open_timings(self.dialog))
        return menu

    def insert(self, name: str) -> None:
        """Insert ``$name`` at the cursor, in place of the selection if any."""
        entry = self.entry
        if entry.selection_present():
            entry.delete("sel.first", "sel.last")
        entry.insert("insert", f"${name}")
        entry.focus_set()

    def popup(self, event: tk.Event) -> str:
        if str(self.entry.cget("state")) == "disabled":
            return "break"
        menu = self.build()
        try:
            ## tk_popup saves and restores the grab in force (the dialog's).
            menu.tk_popup(event.x_root, event.y_root)
        finally:
            menu.grab_release()
        return "break"


def bind_timing_var_menu(entry: tk.Entry, dialog: tk.Misc) -> TimingVarMenu:
    return TimingVarMenu(entry, dialog)
