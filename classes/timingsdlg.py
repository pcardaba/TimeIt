import tkinter as tk
from tkinter import ttk, simpledialog, messagebox


class TimingsDlg(tk.Toplevel):
    """The *User Timings* window: the table of timing variables.

    It is not modal. ``parent`` is the Tk window it is opened under and
    ``topapp`` the application (defaults to ``parent``, the historical use
    from the Edit menu). The two differ when a modal signal dialog opens the
    window: a Tk grab only reaches the grab window and its descendants, so a
    timings window parented to the main window would be frozen while the
    dialog is up, whereas one parented to the dialog stays usable next to it
    (see ``TimeItApp.open_timings``).
    """

    def __init__(self, parent, timings, topapp=None):
        super().__init__(parent)
        self.title("User Timings")
        self.transient(parent)
        ## Make this dialog not modal. Remove grab_set()
        ## self.grab_set()
        # Keep it above the main window
        self.attributes("-topmost", True)

        self.topapp = topapp if topapp is not None else parent
        self.console = self.topapp.console
        self.timings = timings
        # ---- Tree ----
        self.tree = ttk.Treeview(
            self,
            columns=("value", "description"),
            show="tree headings",
            selectmode="browse",
            height=10,
        )

        self.tree.heading("#0", text="User Timing")
        self.tree.heading("value", text="Value")
        self.tree.heading("description", text="Description")

        self.tree.column("#0", width=100, stretch=True)
        self.tree.column("value", width=100, stretch=True)
        self.tree.column("description", width=250, stretch=True)

        self.tree.grid(row=0, column=0, columnspan=3, sticky="nsew", padx=10, pady=10)

        yscroll = ttk.Scrollbar(self, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=yscroll.set)
        yscroll.grid(row=0, column=3, sticky="ns", pady=10)

        self.rowconfigure(0, weight=1)
        self.columnconfigure(0, weight=1)

        # ---- Buttons ----
        ttk.Button(self, text="Add…", command=self.add_node).grid(row=1, column=0,
                                                                  sticky="w",
                                                                  padx=10, pady=(0, 10))
        ttk.Button(self, text="Remove", command=self.remove_node).grid(row=1, column=1,
                                                                       sticky="w",
                                                                       padx=10, pady=(0, 10))
        ttk.Button(self, text="Close", command=self._close).grid(row=1, column=2,
                                                                 sticky="e",
                                                                 padx=10, pady=(0, 10))

        # Inline editor
        self._editor = None
        self._editing_item = None
        self.tree.bind("<Button-1>", self._on_single_click, add=True)

        self.protocol("WM_DELETE_WINDOW", self._close)
        self.refresh()

    # ---- Rows <-> model -------------------------------------------------
    def _rows(self) -> dict[str, str]:
        """Variable name -> tree item id, in display order."""
        return {self.tree.item(i, "text"): i for i in self.tree.get_children("")}

    def refresh(self) -> None:
        """Bring the table in line with the model.

        Called at construction and from ``TimeItApp.redraw``, so a variable
        set from the console, a load or an undo shows up in an open window.
        Only rows that differ are touched: an inline editor on an unchanged
        row survives. A row added with *Add…* but not committed yet has no
        variable behind it and is kept.
        """
        rows = self._rows()
        for name, item in rows.items():
            if name in self.timings.tvars:
                continue
            values = self.tree.item(item, "values")
            if tuple(values) == ("", ""):
                continue  # pending row: added, nothing committed yet
            if self._editor is not None and self._editing_item == item:
                self._destroy_editor()
            self.tree.delete(item)
        for name, val in self.timings.tvars.items():
            desc = self.timings.tvars_desc.get(name, "")
            item = rows.get(name)
            if item is None or not self.tree.exists(item):
                self.tree.insert("", "end", text=name, values=(val, desc))
            elif tuple(self.tree.item(item, "values")) != (str(val), str(desc)):
                self.tree.item(item, values=(val, desc))

    def names(self) -> list[str]:
        """The variable names listed, in display order."""
        return list(self._rows())

    # ---- Prompts under a grab -----------------------------------------
    def _prompt(self, func, *args, **kwargs):
        """Run a modal prompt (askstring, showerror) and give the grab back.

        A prompt sets its own grab and Tk leaves none at all when the prompt
        is destroyed: a signal dialog that owns this window would lose its
        modality. Re-assert the grab that was in force before the prompt.
        """
        holder = self.grab_current()
        try:
            return func(*args, **kwargs)
        finally:
            if holder is not None and holder.winfo_exists():
                holder.grab_set()

    # ---------- Add / Remove ----------
    def add_node(self):
        name = self._prompt(simpledialog.askstring, "Add timing", "Name:", parent=self)
        if not name:
            return

        if name in self._rows():
            self._prompt(messagebox.showerror, "Add timing",
                         f'A node named "{name}" already exists.',
                         parent=self)
            return

        item_id = self.tree.insert(
            "", "end",
            text=name,
            values=("", "")
        )
        self.tree.selection_set(item_id)
        self.tree.see(item_id)

    def remove_node(self):
        sel = self.tree.selection()
        if not sel:
            return

        item_id = sel[0]

        name = self.tree.item(item_id, "text")
        # The command drops the variable from the model and unsets it in TCL.
        # A row added but never committed has no variable behind it yet.
        if name in self.timings.tvars:
            ## A GUI entry point: undoable, as any other edit of the diagram.
            with self.topapp.undo.transaction():
                self.console.execute(f"remove -timing_var {{{name}}}")

        self._destroy_editor()
        if self.tree.exists(item_id):
            self.tree.delete(item_id)

    # ---------- Single-click editing ----------
    def _on_single_click(self, event):
        self.after_idle(lambda: self._maybe_edit(event))

    def _maybe_edit(self, event):
        region = self.tree.identify("region", event.x, event.y)
        if region != "cell":
            self._destroy_editor()
            return

        item_id = self.tree.identify_row(event.y)
        column = self.tree.identify_column(event.x)  # "#1" value, "#2" description

        if not item_id:
            self._destroy_editor()
            return

        # Allow editing only value or description
        if column not in ("#1", "#2"):
            self._destroy_editor()
            return

        self._begin_edit(item_id, column)

    def _begin_edit(self, item_id, column):
        self._destroy_editor()

        bbox = self.tree.bbox(item_id, column)
        if not bbox:
            return
        x, y, w, h = bbox

        col_index = int(column.replace("#", "")) - 1
        current = self.tree.item(item_id, "values")[col_index]

        self._editor = ttk.Entry(self.tree)
        self._editing_item = item_id
        self._editor.insert(0, current)
        self._editor.select_range(0, "end")
        self._editor.focus_set()
        self._editor.place(x=x, y=y, width=w, height=h)

        self._editor.bind("<Return>",
                          lambda e: self._commit(item_id, col_index))
        self._editor.bind("<Escape>",
                          lambda e: self._destroy_editor())
        self._editor.bind("<FocusOut>",
                          lambda e: self._commit(item_id, col_index))

    def _commit(self, item_id, col_index):
        if not self._editor:
            return

        values = list(self.tree.item(item_id, "values"))
        values[col_index] = self._editor.get()
        self.tree.item(item_id, values=values)
        name = self.tree.item(item_id, "text")
        self._destroy_editor()
        self.set_variable(name, values[0], values[1])

    def set_variable(self, name: str, value: str, desc: str = "") -> None:
        """Create or update a timing variable, as the table editor does.

        The command sets the variable both in the model and in the TCL env.
        A GUI entry point: wrapped in an undo transaction, so undoing an
        earlier action can not silently drop a variable created later.
        """
        tclcmd = f"set_app_var -name timings.{name} "
        tclcmd += f"-value {{{value}}} -desc {{{desc}}}"
        with self.topapp.undo.transaction():
            self.console.execute(tclcmd)
            self.topapp.redraw()

    def _destroy_editor(self):
        if self._editor:
            self._editor.destroy()
            self._editor = None
            self._editing_item = None

    def _close(self):
        self.timings.evaluate()
        self.destroy()
