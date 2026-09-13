# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2024 Pablo Cardaba

"""Dialog creating or editing a sampled signal.

Like every other signal dialog, it never touches the signal object: it builds
a `create_sampled` command and runs it through the console inside an undo
transaction, so that the session log stays a script that replays the diagram
exactly and the change can be undone.
"""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk


class SampledSignalDlg(tk.Toplevel):
    def __init__(self, parent, signal=None, preset=None):
        super().__init__(parent, padx=10)
        self.topapp = parent
        self._signal = signal
        ## Name of the signal that was right-clicked: the likely source.
        self._preset = preset
        self.title("Sampled Signal")
        self._build_dlg()
        # Disable resizing in both directions
        self.resizable(False, False)
        self.protocol("WM_DELETE_WINDOW", self.dismiss) # intercept close button
        self.transient(parent)   # dialog window is related to main
        self.wait_visibility() # can't grab until window appears, so we wait
        self.grab_set()        # ensure all input goes to our window
        self.wait_window()     # block until window is destroyed

    def _build_dlg(self):

        # -- tkvars
        self.name_tkvar      = tk.StringVar()
        self.source_tkvar    = tk.StringVar()
        self.clock_tkvar     = tk.StringVar()
        self.edge_tkvar      = tk.StringVar(value="rising")
        self.setup_tkvar     = tk.StringVar()
        self.hold_tkvar      = tk.StringVar()
        self.tco_max_tkvar   = tk.StringVar()
        self.tco_min_tkvar   = tk.StringVar()
        self.visible_tkvar   = tk.BooleanVar(value=True)
        self.color_tkvar     = tk.StringVar(value="black")
        self.lwidth_tkvar    = tk.IntVar(value=2)
        self.amplitude_tkvar = tk.IntVar(value=40)
        self._clock_names = [name for name, sig in self.topapp.signals.items()
                             if sig.type == "clock"]

        if self._signal is not None:
            s = self._signal
            self.name_tkvar.set(s.name)
            if s.source is not None:
                self.source_tkvar.set(s.source.name)
            if s.clock is not None:
                self.clock_tkvar.set(s.clock.name)
            self.edge_tkvar.set(s.edge)
            for tkvar, value in ((self.setup_tkvar, s.setup),
                                 (self.hold_tkvar, s.hold),
                                 (self.tco_max_tkvar, s.tco_max),
                                 (self.tco_min_tkvar, s.tco_min)):
                tkvar.set("" if value is None else value)
            self.visible_tkvar.set(s.visible)
            self.color_tkvar.set(s.color)
            self.amplitude_tkvar.set(s.amplitude)
            self.lwidth_tkvar.set(s.lwidth)
        else:
            if self._preset is not None:
                preset = self.topapp.signals.find(self._preset)
                if preset is not None and preset.type == "clock":
                    self.clock_tkvar.set(self._preset)
                else:
                    self.source_tkvar.set(self._preset)
            if not self.clock_tkvar.get() and self._clock_names:
                self.clock_tkvar.set(self._clock_names[0])

        # ---
        self.grid_rowconfigure(0, minsize=10)
        crow = 1
        ## -> Source, clock and edge.
        lf_sample = ttk.Labelframe(self, text="Sampling")
        lf_sample.grid(row=crow, column=0, columnspan=99,
                       sticky="nswe", padx=2, pady=4)
        ttk.Label(lf_sample, text="Source").grid(row=0, column=0, sticky="e", padx=2)
        self.cb_source = ttk.Combobox(lf_sample, textvariable=self.source_tkvar,
                                      width=14, state="readonly")
        self.cb_source.grid(row=0, column=1, sticky="w", padx=2, pady=2)
        ttk.Label(lf_sample, text="Clock").grid(row=1, column=0, sticky="e", padx=2)
        self.cb_clock = ttk.Combobox(lf_sample, textvariable=self.clock_tkvar,
                                     values=tuple(self._clock_names),
                                     width=14, state="readonly")
        self.cb_clock.grid(row=1, column=1, sticky="w", padx=2, pady=2)
        ttk.Label(lf_sample, text="Edge").grid(row=2, column=0, sticky="e", padx=2)
        ttk.Radiobutton(lf_sample, text="Rising", value="rising",
                        variable=self.edge_tkvar,
                        ).grid(row=2, column=1, sticky="w", padx=2)
        ttk.Radiobutton(lf_sample, text="Falling", value="falling",
                        variable=self.edge_tkvar,
                        ).grid(row=2, column=2, sticky="w", padx=2)

        crow += 1
        ## -> Flip-flop timings: Tcl expressions, kept as text.
        lf_timing = ttk.Labelframe(self, text="Flip-flop timings")
        lf_timing.grid(row=crow, column=0, columnspan=99,
                       sticky="nswe", padx=2, pady=4)
        for row, column, text, tkvar in (
                (0, 0, "Setup", self.setup_tkvar),
                (0, 2, "Hold", self.hold_tkvar),
                (1, 0, "Tco max", self.tco_max_tkvar),
                (1, 2, "Tco min", self.tco_min_tkvar)):
            ttk.Label(lf_timing, text=text).grid(row=row, column=column,
                                                 sticky="e", padx=2)
            ttk.Entry(lf_timing, textvariable=tkvar, width=12,
                      ).grid(row=row, column=column + 1, sticky="w", padx=2, pady=2)

        crow += 1
        self.grid_rowconfigure(crow, minsize=10)
        crow += 1
        ## -> Row : Name, Color, Line width, Visible
        ttk.Label(self, text="Name").grid(row=crow, column=0, sticky="e")
        e_name = ttk.Entry(self, textvariable=self.name_tkvar, width=12)
        e_name.grid(row=crow, column=1, sticky="w", padx=2, pady=2)
        ttk.Label(self, text="Color").grid(row=crow, column=2, sticky="e")
        cb_color = ttk.Combobox(
            self, textvariable=self.color_tkvar,
            values=("black", "green", "red", "blue", "orange", "purple"),
            width=10, state="readonly",
        )
        cb_color.grid(row=crow, column=3, sticky="w", padx=2, pady=2)
        ttk.Label(self, text="Line width").grid(row=crow, column=4, sticky="e")
        sp_lw = ttk.Spinbox(
            self, from_=1, to=20, textvariable=self.lwidth_tkvar, width=2
        )
        sp_lw.grid(row=crow, column=5, sticky="w", padx=2, pady=2)
        chk_visible = ttk.Checkbutton(
            self, text="Visible", variable=self.visible_tkvar
        )
        chk_visible.grid(row=crow, column=6, sticky="w", padx=2, pady=2)
        ## -> Row : Amplitude
        crow += 1
        ttk.Label(self, text="Amplitude").grid(row=crow, column=4, sticky="e")
        sp_amp = ttk.Spinbox(
            self, from_=10, to=300, textvariable=self.amplitude_tkvar, width=3
        )
        sp_amp.grid(row=crow, column=5, sticky="w", padx=2, pady=2)

        crow += 1
        ## Cancel, Apply, OK
        b_frame=ttk.Frame(self)
        b_frame.grid(row=crow, column=0, columnspan=7, sticky="nswe")
        b_frame.grid_rowconfigure(0, minsize=20)
        b_frame.grid_rowconfigure(2, minsize=10)
        b_frame.grid_columnconfigure(0, minsize=100)
        b_cancel=ttk.Button(b_frame, text="Cancel", command=self.dismiss)
        b_cancel.grid(row=1,column=2,sticky="we")
        b_apply=ttk.Button(b_frame, text="Apply", command=self.apply)
        b_apply.grid(row=1,column=3)
        b_ok=ttk.Button(b_frame, text="Ok", command=self.ok)
        b_ok.grid(row=1,column=4,sticky="we")

        self._update_sources()
        ## The name decides which signals would close a dependency loop, so the
        ## source list has to follow whatever is typed in the name entry.
        self.name_tkvar.trace_add("write", self._update_sources)
        self._align_bg_colors()

    # -------------------------------------------------------------------
    # Source choices
    # -------------------------------------------------------------------
    @staticmethod
    def _depends_on(candidate, name):
        """True when `candidate` is `name` or already reads it, at any depth."""
        pending = [candidate]
        seen = set()
        while pending:
            operand = pending.pop()
            if id(operand) in seen:
                continue
            seen.add(id(operand))
            if getattr(operand, "name", None) == name:
                return True
            pending.extend(getattr(operand, "operands", tuple)())
        return False

    def _candidate_sources(self):
        """The signals create_sampled would accept as a source.

        A clock is the sampling reference, never the sampled data, and a PWL
        trace is analog. A signal never samples itself, and neither does it
        sample anything that already reads it: that would close a loop.
        """
        name = self.name_tkvar.get().strip()
        names = []
        for signame, sig in self.topapp.signals.items():
            if sig.type in ("clock", "pwl"):
                continue
            if sig is self._signal or (name and self._depends_on(sig, name)):
                continue
            names.append(signame)
        return tuple(names)

    def _update_sources(self, *_):
        candidates = self._candidate_sources()
        self.cb_source["values"] = candidates
        ## A choice that just became invalid must not survive in the entry.
        if self.source_tkvar.get() and self.source_tkvar.get() not in candidates:
            self.source_tkvar.set("")

    def _align_bg_colors(self):
        ## In Windows the bg color of the dlg window is different from ttk.Frames
        ## In Linux they are aligned but not in Windows and that creates color.
        ## discrepancies.
        frame = ttk.Frame(self)
        style = ttk.Style()
        frame_class = frame.winfo_class()
        ttk_frame_bg = style.lookup(frame_class, "background")
        self.config(bg=ttk_frame_bg)

    # -------------------------------------------------------------------
    # Sync model from Tk variables
    # -------------------------------------------------------------------
    def _build_command(self):
        cmd = "create_sampled"
        # A sampled signal requires a name. If no name is given nothing happens.
        name = self.name_tkvar.get()
        if name is None or name.strip() == "":
            return ""
        cmd += " -name "+name.strip()

        # The sampled signal and the sampling clock are both required.
        source = self.source_tkvar.get()
        if source is None or source == "":
            return ""
        cmd += " -source "+source
        clock = self.clock_tkvar.get()
        if clock is None or clock == "":
            return ""
        cmd += " -clock "+clock
        cmd += " -edge "+self.edge_tkvar.get()

        ## The flip-flop timings are Tcl expressions: brace-quoted and passed
        ## on as typed, never resolved here, so the diagram stays parametric.
        for token, tkvar in (("setup", self.setup_tkvar),
                             ("hold", self.hold_tkvar),
                             ("tco_max", self.tco_max_tkvar),
                             ("tco_min", self.tco_min_tkvar)):
            value = tkvar.get()
            if value is not None and value.strip() != "":
                cmd += " -"+token+" {"+value.strip()+"}"

        # Trace color:
        color = self.color_tkvar.get()
        cmd += " -color "+color
        # Amplitude:
        amplitude = self.amplitude_tkvar.get()
        if amplitude is None or amplitude <= 2:
            amplitude = 40
        cmd += " -amplitude "+str(amplitude)
        # Line width:
        lwidth = self.lwidth_tkvar.get()
        if lwidth is None or lwidth <= 0:
            lwidth = 2
        cmd += " -lwidth "+str(lwidth)
        # Visible.
        if self.visible_tkvar.get():
            cmd += " -visible"
        return cmd

    def dismiss(self):
        self.grab_release()
        self.destroy()

    def cancel(self):
        ## The dialog windows was cancelled therefore created signal is not taken.
        self.dismiss()

    def apply(self):
        cmd = self._build_command()
        if cmd != "":
            with self.topapp.undo.transaction():
                self.topapp.console.execute(cmd)

    def ok(self):
        self.apply()
        self.dismiss()
