import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
import tkinter.font as tkfont

class SettingsDlg(tk.Toplevel):
    """
    Tree editor for Settings:
    Levels:
       Waveform, Marker, Selection, Timings 

    Columns: 
      Value | Description
    """
    
    def __init__(self, parent: tk.Misc, settings):
        super().__init__(parent)
        self.title("Settings Editor")
        self.transient(parent)
        self.grab_set()

        self.topapp = parent
        self.settings = settings

        # leaf item -> (container_dict, key)
        self._leaf_binding: dict[str, tuple[dict, str]] = {}

        # keep node ids
        self._timings_node_id: str | None = None

        # ---- UI ----
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)

        self.tree = ttk.Treeview(self, columns=("value", "desc"),
                                 show="tree headings")
        self.tree.heading("value", text="Value")
        self.tree.heading("desc", text="Description")
        
        self.tree.column("#0", width=160, stretch=False) 
        self.tree.column("value", width=120, stretch=True)
        self.tree.column("desc", width=340, stretch=True)

        ysb = ttk.Scrollbar(self, orient="vertical", command=self.tree.yview)
        xsb = ttk.Scrollbar(self, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=ysb.set, xscrollcommand=xsb.set)

        self.tree.grid(row=0, column=0, sticky="nsew")
        ysb.grid(row=0, column=1, sticky="ns")
        xsb.grid(row=1, column=0, sticky="ew")

        btns = ttk.Frame(self)
        btns.grid(row=2, column=0, columnspan=2, sticky="ew", pady=(8, 6))
        btns.columnconfigure(0, weight=1)

        ttk.Button(btns, text="Apply", command=self._apply).grid(row=0, column=3, padx=6)
        ttk.Button(btns, text="Close", command=self._close).grid(row=0, column=4, padx=6)

        # inline editor
        self._edit_entry = ttk.Entry(self)

        # inline combobox
        self._combo_entry = ttk.Combobox(self, state="readonly")

        # Default entry is Edit.
        self._entry = self._edit_entry
        self._item_id: str | None = None
        
        # bindings
        self.tree.bind("<Button-1>", self._on_click)

        self.build_tree()

    # ---------------------------
    # Build / refresh tree
    # ---------------------------
    def build_tree(self):
        self._end_edit()
        self.tree.delete(*self.tree.get_children())
        self._leaf_binding.clear()
        self._timings_node_id = None

        # Explicit top-level dicts
        for dict_name in ("waveform", "selection", "marker","timings"):
            d = getattr(self.settings, dict_name, None)
            if isinstance(d, dict):
                node_id = self.tree.insert("", "end", text=dict_name, values=("", ""),
                                           open=False)
                self._insert_dict_contents(node_id, d, dict_name)

    def _insert_dict_contents(self, parent_id: str, d: dict, dict_name: str):
        if dict_name!="":
            desc_dict = getattr(self.settings, dict_name+"_desc",None)
        else:
            desc_dict = {}
        for k in sorted(d.keys(), key=str):
            v = d[k]
            desc = desc_dict.get(k, "")
            v_str = "" if isinstance(v, dict) else self._format_value(v)
            item_id = self.tree.insert(
                parent_id,
                "end",
                text=k,
                values=(v_str, desc),
            )
            self._leaf_binding[item_id] = (d, k)
            if isinstance(v, dict):
                 self._insert_dict_contents(item_id, v, "")

    def _format_value(self, v):
        if isinstance(v, str):
            return v
        return repr(v)

    # ---------------------------
    # Editing leaf values
    # ---------------------------
    def _end_edit(self, event=None):
        if self._entry.winfo_ismapped():
            self._entry.place_forget()
        self._item_id = None
        
    def _on_click(self, event):
        self._end_edit()

        item_id = self.tree.identify_row(event.y)
        col = self.tree.identify_column(event.x)

        # only leaf rows editable
        if not item_id or item_id not in self._leaf_binding:
            return

        # only edit Value column (#1)
        if col != "#1":
            return

        container, key = self._leaf_binding[item_id]
        old_value = container[key]

        insert_combo = False
        node_text = self.tree.item(item_id, "text")
        if node_text == "family": 
            insert_combo = True
            self._combo_entry["values"] = self._font_families()
            self._combo_entry.set(old_value)
            
        if node_text == "slant": 
            insert_combo = True
            self._combo_entry["values"] = ("roman", "italic")
            self._combo_entry.set(old_value)

        if node_text == "weight": 
            insert_combo = True
            self._combo_entry["values"] = ("normal", "bold")
            self._combo_entry.set(old_value)
        
        bbox = self.tree.bbox(item_id, col)
        if not bbox:
            return

        x, y, w, h = bbox
        abs_x = self.tree.winfo_rootx() - self.winfo_rootx() + x
        abs_y = self.tree.winfo_rooty() - self.winfo_rooty() + y

        current_txt = self.tree.set(item_id, "value")

        self._item_id = item_id
        self._entry = self._edit_entry
        if insert_combo:
            self._entry = self._combo_entry

        if not insert_combo:
            self._entry.delete(0, tk.END)
            self._entry.insert(0, current_txt)
        self._entry.place(x=abs_x, y=abs_y, width=w, height=h)
        self._entry.focus_set()
        self._entry.selection_range(0, tk.END)

        # Remove previous bindings so they don't pile up across edits
        self._entry.unbind("<Return>")
        self._entry.unbind("<FocusOut>")
        self._entry.unbind("<<ComboboxSelected>>")
        self._entry.unbind("<Escape>")
        
        self._entry.bind("<Return>", lambda e: self._commit_edit())
        if insert_combo:
            # Commit ONLY when the user actually selects an item
            self._entry.bind("<<ComboboxSelected>>", lambda e: self._commit_edit())
            self._entry.bind("<Escape>", lambda e: self._end_edit())
        else:
            self._entry.bind("<FocusOut>", lambda e: self._commit_edit())
            self._entry.bind("<Escape>", lambda e: self._end_edit())

    def _commit_edit(self):
        if not self._item_id or self._item_id not in self._leaf_binding:
            self._end_edit()
            return

        item_id = self._item_id
        container, key = self._leaf_binding[item_id]
        old_value = container[key]
        new_text = self._entry.get().strip()

        try:
            new_value = self._convert_text(new_text, old_value)
        except ValueError as exc:
            messagebox.showerror("Invalid value", str(exc))
            self._entry.focus_set()
            return

        container[key] = new_value
        self.tree.set(item_id, "value", self._format_value(new_value))
        self._end_edit()

        
    def _convert_text(self, txt: str, old_value):
        t = type(old_value)

        if t is bool:
            lowered = txt.lower()
            if lowered in ("true", "1", "yes", "y", "on"):
                return True
            if lowered in ("false", "0", "no", "n", "off"):
                return False
            raise ValueError("Expected a boolean (true/false, yes/no, 1/0).")

        if t is int:
            return int(txt, 10)

        if t is float:
            return float(txt)

        if t is str:
            return txt

        if t is tuple:
            raw = txt.strip()
            if raw.startswith("(") and raw.endswith(")"):
                raw = raw[1:-1]
            parts = []
            for p in raw.split(","):
                cleaned = p.strip()
                if cleaned:
                    parts.append(int(cleaned))
            if not parts:
                return tuple([6,4]) # default

            return tuple(parts)
        
        raise ValueError(f"Editing values of type '{t.__name__}' is not supported.")

    def _font_families(self):
        families = tkfont.families(self.topapp)
        # Remove duplicates while preserving order
        seen = set()
        unique = []
        for f in families:
            if f not in seen:
                seen.add(f)
                unique.append(f)
        return sorted(unique)

    def _close(self):
        self.topapp.redraw()
        self.destroy()

    def _apply(self):
        self.topapp.redraw()
