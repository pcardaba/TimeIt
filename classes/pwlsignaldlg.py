import tkinter as tk
from tkinter import ttk, filedialog

from .pwlsignal import PWLSignal, PWLTrace


class PWLSignalDlg(tk.Toplevel):
    """Create / edit a PWL (analog) waveform slot: up to MAX_ROWS traces."""

    MAX_ROWS = 5
    COLORS = ("black", "red", "blue", "green", "orange", "purple",
              "brown", "magenta", "cyan", "gray")
    ## Default color of every row: distinct traces out of the box.
    ROW_COLORS = ("black", "red", "blue", "green", "orange")
    LINE_STYLES = tuple(PWLTrace.LINE_STYLES)
    FILE_TYPES = [("PWL files", "*.pwl"), ("CSV files", "*.csv"),
                  ("Text files", "*.txt"), ("All files", "*.*")]

    def __init__(self, parent, signal=None):
        super().__init__(parent, padx=10)
        self.topapp = parent
        self._signal = signal
        self.title("PWL Signal")
        self._build_dlg()
        self.resizable(False, False)
        self.protocol("WM_DELETE_WINDOW", self.dismiss)
        self.transient(parent)
        self.wait_visibility()
        self.grab_set()
        self.wait_window()

    # -------------------------------------------------------------------
    # UI construction
    # -------------------------------------------------------------------
    def _build_dlg(self):
        self.height_tkvar = tk.IntVar(value=PWLSignal.DEFAULT_HEIGHT)
        self.lwidth_tkvar = tk.IntVar(value=2)
        self.visible_tkvar = tk.BooleanVar(value=True)
        self.rows = []

        self.grid_rowconfigure(0, minsize=10)
        crow = 1
        ## -> Slot-wide settings
        top = ttk.Frame(self)
        top.grid(row=crow, column=0, sticky="we")
        ttk.Label(top, text="Height").grid(row=0, column=0, sticky="e")
        ttk.Spinbox(top, from_=10, to=600, textvariable=self.height_tkvar,
                    width=4).grid(row=0, column=1, sticky="w", padx=2, pady=2)
        ttk.Label(top, text="Line width").grid(row=0, column=2, sticky="e",
                                               padx=(10, 0))
        ttk.Spinbox(top, from_=1, to=20, textvariable=self.lwidth_tkvar,
                    width=2).grid(row=0, column=3, sticky="w", padx=2, pady=2)
        ttk.Checkbutton(top, text="Visible", variable=self.visible_tkvar).grid(
            row=0, column=4, sticky="w", padx=(10, 2), pady=2)

        ## -> One label frame per trace
        for i in range(self.MAX_ROWS):
            crow += 1
            self.rows.append(self._build_row(crow, i))

        ## -> Buttons
        crow += 1
        b_frame = ttk.Frame(self)
        b_frame.grid(row=crow, column=0, sticky="nswe")
        b_frame.grid_rowconfigure(0, minsize=20)
        b_frame.grid_rowconfigure(2, minsize=10)
        b_frame.grid_columnconfigure(0, weight=1)
        ttk.Button(b_frame, text="Cancel", command=self.dismiss).grid(
            row=1, column=1, sticky="we")
        ttk.Button(b_frame, text="Apply", command=self.apply).grid(
            row=1, column=2)
        ttk.Button(b_frame, text="Ok", command=self.ok).grid(
            row=1, column=3, sticky="we")

        self._load_signal()
        for row in self.rows:
            self._update_row_state(row)
        self._align_bg_colors()

    def _build_row(self, grid_row: int, index: int) -> dict:
        row = {
            "enabled": tk.BooleanVar(value=index == 0),
            "name": tk.StringVar(),
            "file": tk.StringVar(),
            "color": tk.StringVar(value=self.ROW_COLORS[index % len(self.ROW_COLORS)]),
            "lstyle": tk.StringVar(value="solid"),
            "scale": tk.DoubleVar(value=1.0),
            "offset": tk.DoubleVar(value=0.0),
        }
        lf = ttk.Labelframe(self, text=f"Signal {index + 1}")
        lf.grid(row=grid_row, column=0, sticky="we", padx=2, pady=3)

        chk = ttk.Checkbutton(lf, variable=row["enabled"],
                              command=lambda r=row: self._update_row_state(r))
        chk.grid(row=0, column=0, rowspan=2, sticky="w", padx=(2, 6))

        ttk.Label(lf, text="Name").grid(row=0, column=1, sticky="e")
        e_name = ttk.Entry(lf, textvariable=row["name"], width=14)
        e_name.grid(row=0, column=2, sticky="w", padx=2, pady=2)
        ttk.Label(lf, text="File").grid(row=0, column=3, sticky="e")
        e_file = ttk.Entry(lf, textvariable=row["file"], width=34)
        e_file.grid(row=0, column=4, columnspan=5, sticky="we", padx=2, pady=2)
        b_browse = ttk.Button(lf, text="…", width=2,
                              command=lambda r=row: self._browse(r))
        b_browse.grid(row=0, column=9, sticky="w", padx=(0, 2))

        ttk.Label(lf, text="Color").grid(row=1, column=1, sticky="e")
        cb_color = ttk.Combobox(lf, textvariable=row["color"],
                                values=self.COLORS, width=8, state="readonly")
        cb_color.grid(row=1, column=2, sticky="w", padx=2, pady=2)
        ttk.Label(lf, text="Line style").grid(row=1, column=3, sticky="e")
        cb_lstyle = ttk.Combobox(lf, textvariable=row["lstyle"],
                                 values=self.LINE_STYLES, width=8,
                                 state="readonly")
        cb_lstyle.grid(row=1, column=4, sticky="w", padx=2, pady=2)
        ttk.Label(lf, text="Scale").grid(row=1, column=5, sticky="e")
        sp_scale = ttk.Spinbox(lf, from_=0.1, to=10.0, increment=0.1,
                               format="%.2f", textvariable=row["scale"],
                               width=5)
        sp_scale.grid(row=1, column=6, sticky="w", padx=2, pady=2)
        ttk.Label(lf, text="Offset").grid(row=1, column=7, sticky="e")
        sp_offset = ttk.Spinbox(lf, from_=-5.0, to=5.0, increment=0.1,
                                format="%.2f", textvariable=row["offset"],
                                width=5)
        sp_offset.grid(row=1, column=8, sticky="w", padx=2, pady=2)

        row["widgets"] = (e_name, e_file, b_browse, sp_scale, sp_offset)
        row["combos"] = (cb_color, cb_lstyle)
        return row

    def _load_signal(self):
        """Fill the form with the edited slot."""
        s = self._signal
        if s is None:
            return
        self.height_tkvar.set(s.height)
        self.lwidth_tkvar.set(s.lwidth)
        self.visible_tkvar.set(s.visible)
        for row in self.rows:
            row["enabled"].set(False)
        for row, trace in zip(self.rows, s.traces):
            row["enabled"].set(True)
            row["name"].set(trace.name)
            row["file"].set(trace.file)
            row["color"].set(trace.color)
            row["lstyle"].set(trace.lstyle)
            row["scale"].set(trace.scale)
            row["offset"].set(trace.offset)

    def _update_row_state(self, row):
        enabled = row["enabled"].get()
        for w in row["widgets"]:
            w.configure(state="normal" if enabled else "disabled")
        for w in row["combos"]:
            w.configure(state="readonly" if enabled else "disabled")

    def _browse(self, row):
        path = filedialog.askopenfilename(parent=self, title="PWL file",
                                          filetypes=self.FILE_TYPES)
        if path:
            row["file"].set(path)

    def _align_bg_colors(self):
        frame = ttk.Frame(self)
        style = ttk.Style()
        ttk_frame_bg = style.lookup(frame.winfo_class(), "background")
        self.config(bg=ttk_frame_bg)

    # -------------------------------------------------------------------
    # Commands
    # -------------------------------------------------------------------
    def _build_commands(self) -> list[str]:
        """The create_pwl command followed by the per-trace set_attribute."""
        traces = []
        for row in self.rows:
            if not row["enabled"].get():
                continue
            name = row["name"].get().strip()
            file = row["file"].get().strip()
            if name == "" or file == "":
                continue
            traces.append((name, file, row))
        if not traces:
            return []

        names = " ".join(f"{{{name}}}" for name, _, _ in traces)
        files = " ".join(f"{{{file}}}" for _, file, _ in traces)
        cmd = f"create_pwl -names {{{names}}} -files {{{files}}}"

        height = self.height_tkvar.get()
        if height is None or height < 10:
            height = PWLSignal.DEFAULT_HEIGHT
        cmd += f" -height {height}"
        lwidth = self.lwidth_tkvar.get()
        if lwidth is None or lwidth < 1:
            lwidth = 2
        cmd += f" -lwidth {lwidth}"
        if self._signal is not None:
            ## Keeps the slot in place (and its markers) when a name changes.
            cmd += f" -use_uid {self._signal.uid}"
        if self.visible_tkvar.get():
            cmd += " -visible"

        cmds = [cmd]
        for name, _, row in traces:
            for attr in ("color", "lstyle", "scale", "offset"):
                try:
                    value = row[attr].get()
                except tk.TclError:
                    value = PWLTrace.DEFAULTS[attr]
                cmds.append(f"set_attribute -signal {{{name}}} "
                            f"-name {attr} -value {{{value}}}")
        return cmds

    def dismiss(self):
        self.grab_release()
        self.destroy()

    def apply(self):
        cmds = self._build_commands()
        if not cmds:
            return
        first_name = self.rows and [
            r["name"].get().strip() for r in self.rows
            if r["enabled"].get() and r["name"].get().strip()][0]
        with self.topapp.undo.transaction():
            self.topapp.console.execute(cmds[0])
            slot = self.topapp.signals.find(first_name)
            ## The attributes only make sense when the slot was created.
            if slot is not None and slot.type == "pwl":
                for cmd in cmds[1:]:
                    self.topapp.console.execute(cmd)
                self._signal = slot

    def ok(self):
        self.apply()
        self.dismiss()
