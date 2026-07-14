import tkinter as tk
from tkinter import ttk, simpledialog, messagebox


class TimingsDlg(tk.Toplevel):
    def __init__(self, parent, timings):
        super().__init__(parent)
        self.title("User Timings")
        self.transient(parent)
        ## Make this dialog not modal. Remove grab_set()
        ## self.grab_set()
        # Keep it above the main window
        self.attributes("-topmost", True)
        
        self.topapp = parent
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
        self.tree.bind("<Button-1>", self._on_single_click, add=True)

        self.protocol("WM_DELETE_WINDOW", self.destroy)
        self._get_timings()


    # ---- Update timings from top app timings.
    def _get_timings(self):
        for k in self.timings.tvars:
            val = self.timings.tvars[k]
            desc = ""
            if k in self.timings.tvars_desc:
                desc = self.timings.tvars_desc[k]
            self.tree.insert(
                "", "end",
                text=k,
                values=(val, desc)
            )

    # ---------- Add / Remove ----------
    def add_node(self):
        name = simpledialog.askstring("Add timing", "Name:", parent=self)
        if not name:
            return

        for child in self.tree.get_children(""):
            if self.tree.item(child, "text") == name:
                messagebox.showerror("Add timing",
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
        self.timings.tvars.pop(name)
        if name in  self.timings.tvars_desc:
            self.timings.tvars_desc.pop(name)
        try:
            self.console.interp.eval("unset "+name)
        except tk.TclError as e:
            self.console.append_log(f"Error: Unable to unset {name} {e}\n", "error")
            
        self._destroy_editor()
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
        # The command sets the variable both in the model and in the TCL env.
        tclcmd=f"set_app_var -name timings.{name} "
        tclcmd+=f"-value {{{values[0]}}} -desc {{{values[1]}}}"
        self.console.execute(tclcmd)
        self.topapp.redraw()

        self._destroy_editor()

    def _destroy_editor(self):
        if self._editor:
            self._editor.destroy()
            self._editor = None

    def _close(self):
        self.timings.evaluate()
        self.destroy()

        
