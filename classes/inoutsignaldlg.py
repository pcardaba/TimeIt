# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2024 Pablo Cardaba

"""Dialog of a bidirectional (inout) signal, shown as "Bidir" in the GUI.

The form of an input signal and the one of an output signal put together
would not fit: what belongs to the port (name, style, pull-up, internal or
external delays) is on the left, as in those dialogs (see iodlgside), and
each part has its own tab on the right with its clocks, its delays and its
launch edge lists.
"""

import os
import tkinter as tk
from tkinter import messagebox, ttk

from .inoutsignal import InOutSignal, STATES
from .timingvarmenu import bind_timing_var_menu
from . import dlgplace
from . import iodlgside
from . import uiscale

TITLE = "Bidir Signal"

## Illustrations of the delay specification, one per part and specification:
## the tab on show tells the part (sheets BidirI_in, BidirE_in, BidirI_out
## and BidirE_out of data/timeit_drawings.vsdx).
ILLUSTRATIONS = {
    ("in", "internal"): "inout_in_internal_dly.png",
    ("in", "external"): "inout_in_external_dly.png",
    ("out", "internal"): "inout_out_internal_dly.png",
    ("out", "external"): "inout_out_external_dly.png",
}


class _PartForm:
    """The tab of one part: its clocks, its delays and its edge lists."""

    def __init__(self, dialog, notebook, prefix, title, delay_groups):
        self.dialog = dialog
        self.prefix = prefix            # "in" | "out"
        self.title = title              # "input" | "output"
        ## (group, label, internal delays only?) in display order.
        self.delay_groups = delay_groups

        self.launch_tkvar = tk.StringVar()
        self.capture_tkvar = tk.StringVar()
        self.delay_tkvars = {(group, edge, bound): tk.StringVar()
                             for group, _label, _internal in delay_groups
                             for edge in ("rclk", "fclk")
                             for bound in ("max", "min")}
        self.edges_tkvars = {state: tk.StringVar() for state in STATES}
        ## Widgets of the groups only an internal specification has.
        self.internal_widgets = []

        self.frame = ttk.Frame(notebook, padding=uiscale.px(6))
        self.frame.columnconfigure(0, weight=1)
        self._build_clocks(row=0)
        self._build_delays(row=1)
        self._build_edges(row=2)

    # ------------------------------------------------------------------
    def option(self, group, edge, bound):
        """The create_inout option (and signal attribute) of a delay."""
        if group == "latency":
            return f"{self.prefix}_{edge}_latency_{bound}"
        return f"{edge}_{group}_{bound}"

    def load(self, signal):
        for attr, tkvar in (("launch_clock", self.launch_tkvar),
                            ("capture_clock", self.capture_tkvar)):
            clock = getattr(signal, f"{self.prefix}_{attr}")
            if clock is not None:
                tkvar.set(clock.name)
        for (group, edge, bound), tkvar in self.delay_tkvars.items():
            value = getattr(signal, self.option(group, edge, bound))
            tkvar.set("" if value is None else value)
        for state, tkvar in self.edges_tkvars.items():
            tkvar.set(" ".join(getattr(signal, f"{self.prefix}_{state}_edges")))

    # ------------------------------------------------------------------
    def _build_clocks(self, row):
        """The launch/capture clock choices, on a single row."""
        lf_clocks = ttk.Labelframe(self.frame, text="Clocks")
        lf_clocks.grid(row=row, column=0, sticky="ew", padx=2, pady=2)
        ## Each half takes an end of the row: Launch to the west, Capture east.
        lf_clocks.columnconfigure(0, weight=1)
        lf_clocks.columnconfigure(1, weight=1)

        launch = ttk.Frame(lf_clocks)
        launch.grid(row=0, column=0, sticky="w", padx=2, pady=2)
        ttk.Label(launch, text="Launch").grid(row=0, column=0, sticky="e", padx=2)
        self.cb_launch = ttk.Combobox(launch, textvariable=self.launch_tkvar,
                                      width=12, state="readonly")
        self.cb_launch.grid(row=0, column=1, sticky="e", padx=2)

        capture = ttk.Frame(lf_clocks)
        capture.grid(row=0, column=1, sticky="e", padx=2, pady=2)
        ttk.Label(capture, text="Capture").grid(row=0, column=0, sticky="e", padx=2)
        self.cb_capture = ttk.Combobox(capture, textvariable=self.capture_tkvar,
                                       width=12, state="readonly")
        self.cb_capture.grid(row=0, column=1, sticky="w", padx=2)

        for combo in (self.cb_launch, self.cb_capture):
            combo.bind("<<ComboboxSelected>>", self.dialog._update_clock_choices)

    def _build_delays(self, row):
        """The delays at the clock rising and falling edges, side by side."""
        delays = ttk.Frame(self.frame)
        delays.grid(row=row, column=0, sticky="ew", padx=2, pady=8)
        delays.columnconfigure(0, weight=1)
        delays.columnconfigure(1, weight=1)

        for column, (edge, text) in enumerate((("rclk", "@ Clock Rising"),
                                               ("fclk", "@ Clock Falling"))):
            lf_edge = ttk.Labelframe(delays, text=text)
            lf_edge.grid(row=0, column=column, sticky="nsew",
                         padx=(0, 4) if column == 0 else (4, 0))
            lf_edge.columnconfigure(0, weight=1)
            for line, (group, label, internal) in enumerate(self.delay_groups):
                widgets = self._add_maxmin_group(
                    lf_edge, line, label,
                    self.delay_tkvars[(group, edge, "max")],
                    self.delay_tkvars[(group, edge, "min")])
                if internal:
                    self.internal_widgets.extend(widgets)

    def _add_maxmin_group(self, parent, row, text, max_tkvar, min_tkvar, width=9):
        """Nested delay group: a 'text' Labelframe with 'Max/min [max]/[min]'."""
        lf = ttk.Labelframe(parent, text=text)
        lf.grid(row=row, column=0, sticky="ew", padx=4, pady=2)
        ## Both entries share the extra width evenly.
        lf.columnconfigure(1, weight=1)
        lf.columnconfigure(3, weight=1)
        l_maxmin = ttk.Label(lf, text="Max/min")
        l_maxmin.grid(row=0, column=0, sticky="e", padx=2, pady=2)
        e_max = ttk.Entry(lf, textvariable=max_tkvar, width=width)
        e_max.grid(row=0, column=1, sticky="ew")
        l_sep = ttk.Label(lf, text="/")
        l_sep.grid(row=0, column=2)
        e_min = ttk.Entry(lf, textvariable=min_tkvar, width=width)
        e_min.grid(row=0, column=3, sticky="ew", padx=(0, 2))
        ## Right-click: insert a timing variable.
        bind_timing_var_menu(e_max, self.dialog)
        bind_timing_var_menu(e_min, self.dialog)
        return (lf, l_maxmin, e_max, l_sep, e_min)

    def _build_edges(self, row):
        """The launch clock edges each state is opened at."""
        lf_edges = ttk.Labelframe(self.frame, text="Launch Clock Edges Lists")
        lf_edges.grid(row=row, column=0, sticky="ew", padx=2, pady=2)
        ttk.Label(lf_edges, image=self.dialog.edges_img).grid(
            row=0, column=2, sticky="we", padx=2, rowspan=len(STATES))
        for line, state in enumerate(STATES):
            ttk.Label(lf_edges, image=self.dialog.icon[state]).grid(
                row=line, column=0, sticky="e")
            entry = ttk.Entry(lf_edges, textvariable=self.edges_tkvars[state],
                              width=24)
            entry.grid(row=line, column=1, sticky="w", padx=2, pady=2)

    # ------------------------------------------------------------------
    def set_internal(self, internal):
        """Latencies and enable delays are only known for internal delays."""
        InOutSignalDlg._set_state(self.internal_widgets, internal)
        if internal:
            return
        for (group, _edge, _bound), tkvar in self.delay_tkvars.items():
            if any(group == name and only_internal
                   for name, _label, only_internal in self.delay_groups):
                tkvar.set("")

    def command_args(self, internal):
        """The create_inout options of this part, None when a clock is missing."""
        launch = self.launch_tkvar.get()
        capture = self.capture_tkvar.get()
        if not launch and not capture:
            return None
        args = ""
        if launch:
            args += f" -{self.prefix}_launch_clock {launch}"
        if capture:
            args += f" -{self.prefix}_capture_clock {capture}"

        for group, _label, only_internal in self.delay_groups:
            if only_internal and not internal:
                continue
            for edge in ("rclk", "fclk"):
                dly_max = self.delay_tkvars[(group, edge, "max")].get().strip()
                dly_min = self.delay_tkvars[(group, edge, "min")].get().strip()
                if not dly_max and not dly_min:
                    continue
                ## When only one of both is given: a lone max goes with a
                ## null min, a lone min is the max as well.
                if not dly_max:
                    dly_max = dly_min
                if not dly_min:
                    dly_min = "0"
                args += f" -{self.option(group, edge, 'max')} {{{dly_max}}}"
                args += f" -{self.option(group, edge, 'min')} {{{dly_min}}}"

        for state in STATES:
            edges = self.edges_tkvars[state].get().strip()
            if edges:
                args += f" -{self.prefix}_{state}_edges {{{edges}}}"
        return args


class InOutSignalDlg(tk.Toplevel):
    def __init__(self, parent, signal=None):
        super().__init__(parent, padx=10)
        self.topapp = parent
        self._signal = signal
        self.title(TITLE)
        self._build_dlg()
        # Disable resizing in both directions
        self.resizable(False, False)
        self.protocol("WM_DELETE_WINDOW", self.dismiss) # intercept close button
        self.transient(parent)   # dialog window is related to main
        dlgplace.place(self, parent)  # open over the main window
        self.wait_visibility() # can't grab until window appears, so we wait
        self.grab_set()        # ensure all input goes to our window
        self.wait_window()     # block until window is destroyed

    def _build_dlg(self):
        # -- tkvars of what belongs to the port
        self.name_tkvar       = tk.StringVar()
        self.visible_tkvar    = tk.BooleanVar(value=True)
        self.color_tkvar      = tk.StringVar(value="black")
        self.lwidth_tkvar     = tk.IntVar(value=2)
        self.amplitude_tkvar  = tk.IntVar(value=40)
        self.topology_tkvar   = tk.StringVar(value="internal")
        self.pulled_up_tkvar  = tk.BooleanVar(value=False)
        self.contention_tkvar = tk.BooleanVar(value=True)
        ## Every clock is a candidate. Once a clock is chosen, only the clocks
        ## related to it remain candidates for the three others.
        self._clock_names = [name for name, sig in self.topapp.signals.items()
                             if sig.type == "clock"]

        src_dir = os.path.dirname(os.path.abspath(__file__))
        base_path = os.path.join(src_dir, "../data")
        self.icon = {
            "data": uiscale.load_image(base_path+"/data_validx20.png"),
            "hiz": uiscale.load_image(base_path+"/data_hizx20.png"),
            "low": uiscale.load_image(base_path+"/data_lowx20.png"),
            "high": uiscale.load_image(base_path+"/data_highx20.png"),
            "unknown": uiscale.load_image(base_path+"/data_unknownx20.png"),
        }
        self.edges_img = uiscale.load_image(base_path+"/edge_nomenclature.png")
        self.images = {
            key: uiscale.load_image(os.path.join(base_path, filename))
            for key, filename in ILLUSTRATIONS.items()
        }

        self.grid_rowconfigure(0, minsize=10)
        ## -> Left: the port, then how the delays of both parts are specified.
        ## The illustration shows the part on show, see _update_illustration().
        self.lbimg_topo = iodlgside.build_side(
            self,
            checks=(("Visible", self.visible_tkvar),
                    ("Mark contention", self.contention_tkvar),
                    ("Pulled-up", self.pulled_up_tkvar)),
            delay_text="Input and output delays as",
            images=self.images.values(),
            image=self.images[("in", "internal")],
            choices=(("Internal delays", "internal"),
                     ("External delays", "external")))
        ## -> Right: one tab per part.
        self.notebook = ttk.Notebook(self)
        self.notebook.grid(row=1, column=1, sticky="nsew", padx=2)
        self.in_form = _PartForm(
            self, self.notebook, "in", "input",
            (("inputdly", "Input delay", False),
             ("latency", "Clock Latency", True)))
        self.out_form = _PartForm(
            self, self.notebook, "out", "output",
            (("outputdly", "Output delay", False),
             ("oedly", "Output Enable Delay", True),
             ("latency", "Clock Latency", True)))
        self.forms = (self.in_form, self.out_form)
        self.notebook.add(self.in_form.frame, text="Input part")
        self.notebook.add(self.out_form.frame, text="Output part")
        self.notebook.bind("<<NotebookTabChanged>>", self._update_illustration)

        if self._signal is not None:
            s = self._signal
            self.name_tkvar.set(s.name)
            self.visible_tkvar.set(s.visible)
            self.color_tkvar.set(s.color)
            self.amplitude_tkvar.set(s.amplitude)
            self.lwidth_tkvar.set(s.lwidth)
            self.topology_tkvar.set(s.specify)
            self.pulled_up_tkvar.set(s.pulled_up)
            self.contention_tkvar.set(not s.hide_contention)
            for form in self.forms:
                form.load(s)

        ## Cancel, Apply, OK
        b_frame=ttk.Frame(self)
        b_frame.grid(row=2, column=0, columnspan=2, sticky="nswe")
        b_frame.grid_rowconfigure(0, minsize=20)
        b_frame.grid_rowconfigure(2, minsize=10)
        b_frame.grid_columnconfigure(0, minsize=100)
        b_frame.grid_columnconfigure(1, weight=1)
        ## The User Timings window, opened under this dialog so that it stays
        ## usable while the dialog holds the grab (see TimeItApp.open_timings).
        self.b_timings=ttk.Button(b_frame, text="Timings…",
                                  command=lambda: self.topapp.open_timings(self))
        self.b_timings.grid(row=1,column=0,sticky="w")
        b_cancel=ttk.Button(b_frame, text="Cancel", command=self.dismiss)
        b_cancel.grid(row=1,column=2,sticky="e")
        b_apply=ttk.Button(b_frame, text="Apply", command=self.apply)
        b_apply.grid(row=1,column=3)
        b_ok=ttk.Button(b_frame, text="Ok", command=self.ok)
        b_ok.grid(row=1,column=4,sticky="e")

        self._update_clock_choices()
        self._update_topology()
        self._align_bg_colors()

    # -------------------------------------------------------------------
    # Launch / Capture clocks
    # -------------------------------------------------------------------
    def _clock_fields(self):
        """(combobox, tkvar) of the four clock choices."""
        return [(combo, tkvar)
                for form in self.forms
                for combo, tkvar in ((form.cb_launch, form.launch_tkvar),
                                     (form.cb_capture, form.capture_tkvar))]

    def _related_clock_names(self, names):
        """Clocks that may go with every clock of `names` (same source clock)."""
        candidates = self._clock_names
        for name in names:
            clock = self.topapp.signals.find(name)
            if clock is None or clock.type != "clock":
                continue
            candidates = [n for n in candidates
                          if clock.is_related_to(self.topapp.signals.find(n))]
        return candidates

    def _update_clock_choices(self, event=None):
        """The four clocks of a bidirectional signal are related clocks."""
        fields = self._clock_fields()
        ## The clock just chosen prevails: the unrelated ones are dropped.
        chosen = next((tkvar.get() for combo, tkvar in fields
                       if event is not None and combo is event.widget), "")
        if chosen:
            related = self._related_clock_names([chosen])
            for _combo, tkvar in fields:
                if tkvar.get() and tkvar.get() not in related:
                    tkvar.set("")
        ## Each choice restricts the choices left for the three others.
        for combo, tkvar in fields:
            others = [other.get() for _c, other in fields
                      if other is not tkvar and other.get()]
            combo["values"] = self._related_clock_names(others)

    @staticmethod
    def _set_state(widgets, enabled):
        """Enable/disable a group of widgets. A Labelframe has no -state."""
        for w in widgets:
            if isinstance(w, ttk.Labelframe):
                w.state(["!disabled"] if enabled else ["disabled"])
            else:
                w.configure(state="normal" if enabled else "disabled")

    def _align_bg_colors(self):
        ## In Windows the bg color of the dlg window is different from ttk.Frames
        ## In Linux they are aligned but not in Windows and that creates color.
        ## discrepancies.
        frame = ttk.Frame(self)
        style = ttk.Style()
        frame_class = frame.winfo_class()
        ttk_frame_bg = style.lookup(frame_class, "background")
        self.config(bg=ttk_frame_bg)

    def _update_topology(self):
        selected = self.topology_tkvar.get()
        self._update_illustration()
        for form in self.forms:
            form.set_internal(selected == "internal")

    def _update_illustration(self, event=None):
        """Show the delays of the part on show, as they are specified."""
        shown = self.notebook.select()
        form = next((f for f in self.forms if str(f.frame) == shown),
                    self.in_form)
        image = self.images[(form.prefix, self.topology_tkvar.get())]
        self.lbimg_topo.configure(image=image)

    def _prompt(self, func, *args, **kwargs):
        """Run a modal message box and give the grab back to the dialog.

        A message box sets its own grab and Tk leaves none at all once it is
        destroyed: the dialog would lose its modality.
        """
        try:
            return func(*args, parent=self, **kwargs)
        finally:
            if self.winfo_exists():
                self.grab_set()

    # -------------------------------------------------------------------
    # Sync model from Tk variables
    # -------------------------------------------------------------------
    def _build_command(self):
        """The create_inout command of the form, "" when it is incomplete."""
        name = self.name_tkvar.get().strip()
        if not name:
            self._prompt(messagebox.showerror, TITLE,
                         "The signal needs a name.")
            return ""
        topology = self.topology_tkvar.get()
        cmd = f"create_inout -name {name} -specify {topology}"

        for form in self.forms:
            args = form.command_args(topology == "internal")
            if args is None:
                self.notebook.select(form.frame)
                self._prompt(messagebox.showerror, TITLE,
                             f"Select the launch and/or the capture clock of "
                             f"the {form.title} part.")
                return ""
            cmd += args

        if self.pulled_up_tkvar.get():
            cmd += " -pulled_up"
        if not self.contention_tkvar.get():
            cmd += " -hide_contention"
        cmd += " -color " + self.color_tkvar.get()
        amplitude = self.amplitude_tkvar.get()
        if amplitude is None or amplitude <= 2:
            amplitude = 40
        cmd += " -amplitude " + str(amplitude)
        lwidth = self.lwidth_tkvar.get()
        if lwidth is None or lwidth <= 0:
            lwidth = 2
        cmd += " -lwidth " + str(lwidth)
        if self.visible_tkvar.get():
            cmd += " -visible"
        return cmd

    def _warn(self):
        """Tell what looks wrong in the definition just applied.

        Only a warning: the signal is created as given, the diagram may be
        there to show a contention.
        """
        signal = self.topapp.signals.find(self.name_tkvar.get().strip())
        if not isinstance(signal, InOutSignal):
            return
        warnings = signal.definition_warnings()
        if warnings:
            text = "\n\n".join(w[0].upper() + w[1:] + "." for w in warnings)
            self._prompt(messagebox.showwarning, TITLE,
                         f"{signal.name}:\n\n{text}")

    def dismiss(self):
        self.grab_release()
        self.destroy()

    def cancel(self):
        ## The dialog windows was cancelled therefore created signal is not taken.
        self.dismiss()

    def apply(self):
        cmd = self._build_command()
        if cmd == "":
            return False
        with self.topapp.undo.transaction():
            self.topapp.console.execute(cmd)
        self._warn()
        return True

    def ok(self):
        ## An incomplete form stays open: its message says what is missing.
        if self.apply():
            self.dismiss()
