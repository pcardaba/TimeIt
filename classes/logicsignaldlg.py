# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2024 Pablo Cardaba

"""Dialog creating or editing a logic signal.

Like every other signal dialog, it never touches the signal object: it builds
a `create_logic` command and runs it through the console inside an undo
transaction, so that the session log stays a script that replays the diagram
exactly and the change can be undone.
"""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk

from . import timeline as tline


class LogicSignalDlg(tk.Toplevel):
    def __init__(self, parent, signal=None, preset=None):
        super().__init__(parent, padx=10)
        self.topapp = parent
        self._signal = signal
        ## Name of the signal that was right-clicked: the likely first input.
        self._preset = preset
        self.title("Logic Signal")
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
        self.op_tkvar        = tk.StringVar(value="and")
        self.candidate_tkvar = tk.StringVar()
        self.tpd_max_tkvar   = tk.StringVar()
        self.tpd_min_tkvar   = tk.StringVar()
        self.visible_tkvar   = tk.BooleanVar(value=True)
        self.color_tkvar     = tk.StringVar(value="black")
        self.lwidth_tkvar    = tk.IntVar(value=2)
        self.amplitude_tkvar = tk.IntVar(value=40)
        ## The chosen inputs, in order (a Tcl list in the command).
        self.inputs: list[str] = []

        if self._signal is not None:
            s = self._signal
            self.name_tkvar.set(s.name)
            self.op_tkvar.set(s.op)
            self.inputs = [op.name for op in s.operands()]
            self.tpd_max_tkvar.set("" if s.tpd_max is None else s.tpd_max)
            self.tpd_min_tkvar.set("" if s.tpd_min is None else s.tpd_min)
            self.visible_tkvar.set(s.visible)
            self.color_tkvar.set(s.color)
            self.amplitude_tkvar.set(s.amplitude)
            self.lwidth_tkvar.set(s.lwidth)
        elif self._preset is not None:
            self.inputs = [self._preset]

        # ---
        self.grid_rowconfigure(0, minsize=10)
        crow = 1
        ## -> Operator.
        lf_op = ttk.Labelframe(self, text="Logic function")
        lf_op.grid(row=crow, column=0, columnspan=99, sticky="nswe", padx=2, pady=4)
        for column, op in enumerate(tline.OPERATORS):
            ttk.Radiobutton(lf_op, text=op, value=op, variable=self.op_tkvar,
                            command=self._update_op,
                            ).grid(row=0, column=column, sticky="w", padx=6, pady=2)

        crow += 1
        ## -> Inputs: the chosen list on the left, a picker on the right.
        lf_in = ttk.Labelframe(self, text="Inputs")
        lf_in.grid(row=crow, column=0, columnspan=99, sticky="nswe", padx=2, pady=4)
        self.lb_inputs = tk.Listbox(lf_in, height=4, width=18,
                                    exportselection=False, activestyle="none")
        self.lb_inputs.grid(row=0, column=0, rowspan=4, sticky="nswe", padx=4, pady=4)
        ttk.Label(lf_in, text="Signal").grid(row=0, column=1, sticky="e", padx=2)
        self.cb_candidate = ttk.Combobox(lf_in, textvariable=self.candidate_tkvar,
                                         width=14, state="readonly")
        self.cb_candidate.grid(row=0, column=2, sticky="w", padx=2, pady=2)
        ttk.Button(lf_in, text="Add", command=self._add_input,
                   ).grid(row=1, column=2, sticky="we", padx=2, pady=2)
        ttk.Button(lf_in, text="Remove", command=self._remove_input,
                   ).grid(row=2, column=2, sticky="we", padx=2, pady=2)
        self.lb_inputs.bind("<Double-Button-1>", lambda _e: self._remove_input())

        crow += 1
        ## -> Propagation delay: Tcl expressions, kept as text.
        lf_tpd = ttk.Labelframe(self, text="Propagation delay")
        lf_tpd.grid(row=crow, column=0, columnspan=99, sticky="nswe", padx=2, pady=4)
        ttk.Label(lf_tpd, text="Tpd max").grid(row=0, column=0, sticky="e", padx=2)
        ttk.Entry(lf_tpd, textvariable=self.tpd_max_tkvar, width=12,
                  ).grid(row=0, column=1, sticky="w", padx=2, pady=2)
        ttk.Label(lf_tpd, text="Tpd min").grid(row=0, column=2, sticky="e", padx=2)
        ttk.Entry(lf_tpd, textvariable=self.tpd_min_tkvar, width=12,
                  ).grid(row=0, column=3, sticky="w", padx=2, pady=2)
        ttk.Label(lf_tpd, text="(min defaults to max)").grid(row=0, column=4, sticky="w", padx=6)

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

        self._refresh_inputs()
        self._update_op()
        ## The name decides which signals would close a dependency loop, so the
        ## candidate list has to follow whatever is typed in the name entry.
        self.name_tkvar.trace_add("write", self._update_candidates)
        self._align_bg_colors()

    # -------------------------------------------------------------------
    # Input choices
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

    def _candidate_inputs(self):
        """The signals create_logic would accept as an input, not yet chosen.

        A clock has no scalar level to combine, a bus carries data rather
        than a 0/1 value and a PWL trace is analog: the command rejects all
        three. A signal is never its own input, and neither is anything that
        already reads it: that would close a dependency loop.
        """
        return tuple(signame for signame in self.topapp.signals.names()
                     if signame not in self.inputs and self._acceptable(signame))

    def _acceptable(self, signame: str) -> bool:
        """Whether create_logic would accept `signame` as an input now."""
        sig = self.topapp.signals.find(signame)
        if sig is None or sig.type in ("clock", "pwl") \
           or getattr(sig, "data_edges", None) or sig is self._signal:
            return False
        name = self.name_tkvar.get().strip()
        return not (name and self._depends_on(sig, name))

    def _update_candidates(self, *_):
        ## A chosen input that just became invalid (the typed name now matches
        ## one of its readers) must not survive in the list.
        kept = [n for n in self.inputs if self._acceptable(n)]
        if kept != self.inputs:
            self.inputs = kept
            self._refresh_inputs()
            return
        candidates = self._candidate_inputs()
        self.cb_candidate["values"] = candidates
        if self.candidate_tkvar.get() not in candidates:
            self.candidate_tkvar.set(candidates[0] if candidates else "")

    def _refresh_inputs(self):
        self.lb_inputs.delete(0, "end")
        for name in self.inputs:
            self.lb_inputs.insert("end", name)
        self._update_candidates()

    def _add_input(self):
        name = self.candidate_tkvar.get()
        if not name or name in self.inputs:
            return
        ## "not" takes a single input: adding replaces it.
        if self.op_tkvar.get() in tline.UNARY_OPERATORS:
            self.inputs = []
        self.inputs.append(name)
        self._refresh_inputs()

    def _remove_input(self):
        selection = self.lb_inputs.curselection()
        if not selection:
            return
        del self.inputs[selection[0]]
        self._refresh_inputs()

    def _update_op(self):
        ## "not" takes exactly one input: keep the first chosen one only.
        if self.op_tkvar.get() in tline.UNARY_OPERATORS and len(self.inputs) > 1:
            self.inputs = self.inputs[:1]
            self._refresh_inputs()

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
        cmd = "create_logic"
        # A logic signal requires a name. If no name is given nothing happens.
        name = self.name_tkvar.get()
        if name is None or name.strip() == "":
            return ""
        cmd += " -name "+name.strip()

        # The logic operator.
        cmd += " -op "+self.op_tkvar.get()

        # The inputs: at least one (the command checks the count per operator).
        if not self.inputs:
            return ""
        cmd += " -inputs {"+" ".join(self.inputs)+"}"

        ## The gate delays are Tcl expressions: brace-quoted and passed on as
        ## typed, never resolved here, so the diagram stays parametric.
        for token, tkvar in (("tpd_max", self.tpd_max_tkvar),
                             ("tpd_min", self.tpd_min_tkvar)):
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
