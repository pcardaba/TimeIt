# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2024 Pablo Cardaba

from __future__ import annotations

import tkinter as tk
from tkinter import ttk, messagebox

from .vcdconvert import (CLOCK_TOPOLOGIES, GENERATED_TOPOLOGIES,
                         SignalChoice, VCDConverter, propose_choices)


class ImportVCDCharDlg(tk.Toplevel):
    """Signal characterization step of File -> Import VCDs.

    Lists the signals found in the VCD pair with their proposed roles and
    lets the user adjust them: clock / input / output, the clock topology
    and master for clocks, the launch / capture clocks for I/O signals.

    After wait_window(), `result` is the VCDConverter whose commands
    reproduce the waveforms, or None when the dialog was cancelled.
    """

    def __init__(self, parent: tk.Misc, analysis):
        super().__init__(parent)
        self.title("Import VCDs — Signal Characterization")
        self.transient(parent)
        self.grab_set()

        self.analysis = analysis
        self.result: VCDConverter | None = None

        ## Display names (same naming the converter will use) and the
        ## reverse map the comboboxes rely on.
        self._names = VCDConverter(analysis, {}).tcl_names
        self._full = {v: k for k, v in self._names.items()}

        proposals = propose_choices(analysis)

        self.columnconfigure(0, weight=1)
        self.rowconfigure(1, weight=1)

        ttk.Label(
            self,
            text=("Complete the role of each imported signal. Inputs are "
                  "imported with external delays and outputs with internal "
                  "delays,\nboth measured from the launching clock edges "
                  "observed in the VCDs (min file → min delays, max file → "
                  "max delays)."),
            justify="left",
        ).grid(row=0, column=0, sticky="w", padx=10, pady=(10, 6))

        body = self._build_scrollable_body()
        self._build_rows(body, proposals)

        btns = ttk.Frame(self)
        btns.grid(row=2, column=0, sticky="e", padx=10, pady=(6, 10))
        ttk.Button(btns, text="Import", command=self._ok).grid(
            row=0, column=0, padx=6)
        ttk.Button(btns, text="Cancel", command=self._cancel).grid(
            row=0, column=1)

        self.bind("<Escape>", lambda e: self._cancel())
        self.protocol("WM_DELETE_WINDOW", self._cancel)

        self._refresh()

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------
    def _build_scrollable_body(self) -> ttk.Frame:
        holder = ttk.Frame(self)
        holder.grid(row=1, column=0, sticky="nsew", padx=10)
        holder.columnconfigure(0, weight=1)
        holder.rowconfigure(0, weight=1)

        canvas = tk.Canvas(holder, highlightthickness=0)
        ysb = ttk.Scrollbar(holder, orient="vertical", command=canvas.yview)
        canvas.configure(yscrollcommand=ysb.set)
        canvas.grid(row=0, column=0, sticky="nsew")
        ysb.grid(row=0, column=1, sticky="ns")

        inner = ttk.Frame(canvas)
        window = canvas.create_window((0, 0), window=inner, anchor="nw")

        def on_configure(_event=None):
            canvas.configure(scrollregion=canvas.bbox("all"))
            req_w = inner.winfo_reqwidth()
            req_h = min(inner.winfo_reqheight(), 400)
            canvas.configure(width=req_w, height=req_h)
            canvas.itemconfigure(window, width=req_w)

        inner.bind("<Configure>", on_configure)
        return inner

    def _build_rows(self, body: ttk.Frame,
                    proposals: dict[str, SignalChoice]) -> None:
        headers = ("Signal", "Found as", "Type", "Topology", "Master",
                   "Launch clk", "Capture clk")
        for col, text in enumerate(headers):
            ttk.Label(body, text=text, font=("TkDefaultFont", 0, "bold")
                      ).grid(row=0, column=col, sticky="w", padx=4, pady=(0, 4))

        self._rows: dict[str, dict] = {}
        for r, sig in enumerate(self.analysis.signals, start=1):
            choice = proposals[sig.name]
            row: dict = {"sig": sig}
            self._rows[sig.name] = row

            ttk.Label(body, text=self._names[sig.name]).grid(
                row=r, column=0, sticky="w", padx=4, pady=1)
            ttk.Label(body, text=self._info_text(sig)).grid(
                row=r, column=1, sticky="w", padx=4, pady=1)

            kinds = ("clock", "input", "output") if sig.is_clock_candidate \
                else ("input", "output")
            row["kind"] = self._combo(body, r, 2, kinds, choice.kind)
            row["topology"] = self._combo(body, r, 3, CLOCK_TOPOLOGIES,
                                          choice.topology or "clockin")
            row["master"] = self._combo(
                body, r, 4, (),
                self._names.get(choice.master, "") if choice.master else "")
            row["launch"] = self._combo(
                body, r, 5, (),
                self._names.get(choice.launch, "") if choice.launch else "")
            row["capture"] = self._combo(
                body, r, 6, (),
                self._names.get(choice.capture, "") if choice.capture else "")

            row["kind"].bind("<<ComboboxSelected>>", lambda e: self._refresh())
            row["topology"].bind("<<ComboboxSelected>>",
                                 lambda e: self._refresh())

    def _combo(self, parent, row: int, col: int, values, current: str
               ) -> ttk.Combobox:
        cb = ttk.Combobox(parent, state="readonly", width=11, values=values)
        cb.set(current)
        cb.grid(row=row, column=col, sticky="w", padx=4, pady=1)
        return cb

    def _info_text(self, sig) -> str:
        if sig.is_clock_candidate:
            ck = sig.clock
            text = f"clock, {self.analysis._fmt_ns(ck.period_fs)}"
            if ck.master is not None:
                text += f", /{ck.ratio} of {self._names[ck.master]}"
            return text
        bits = f"{sig.width} bit" + ("s" if sig.width > 1 else "")
        return f"{bits}, {len(sig.changes_min)} changes"

    # ------------------------------------------------------------------
    # Dynamic state
    # ------------------------------------------------------------------
    def _refresh(self) -> None:
        """Enable/disable the per-row knobs according to the chosen roles."""
        clock_names = [self._names[n] for n, row in self._rows.items()
                       if row["kind"].get() == "clock"]
        source_names = [self._names[n] for n, row in self._rows.items()
                        if row["kind"].get() == "clock"
                        and row["topology"].get() not in GENERATED_TOPOLOGIES]

        for name, row in self._rows.items():
            is_clock = row["kind"].get() == "clock"
            generated = row["topology"].get() in GENERATED_TOPOLOGIES

            row["topology"].configure(
                state="readonly" if is_clock else "disabled")

            masters = [d for d in source_names if d != self._names[name]]
            row["master"].configure(values=masters)
            if is_clock and generated:
                row["master"].configure(state="readonly")
                if row["master"].get() not in masters:
                    row["master"].set(masters[0] if masters else "")
            else:
                row["master"].configure(state="disabled")

            for key in ("launch", "capture"):
                cb = row[key]
                cb.configure(values=clock_names)
                if is_clock:
                    cb.set("")
                    cb.configure(state="disabled")
                else:
                    cb.configure(state="readonly")
                    if cb.get() not in clock_names:
                        cb.set(clock_names[0] if clock_names else "")

    # ------------------------------------------------------------------
    # Submit
    # ------------------------------------------------------------------
    def _choices(self) -> dict[str, SignalChoice]:
        out: dict[str, SignalChoice] = {}
        for name, row in self._rows.items():
            kind = row["kind"].get()
            if kind == "clock":
                out[name] = SignalChoice(
                    kind="clock",
                    topology=row["topology"].get(),
                    master=self._full.get(row["master"].get()) or None)
            else:
                out[name] = SignalChoice(
                    kind=kind,
                    launch=self._full.get(row["launch"].get()) or None,
                    capture=self._full.get(row["capture"].get()) or None)
        return out

    def _ok(self) -> None:
        converter = VCDConverter(self.analysis, self._choices())
        if not converter.run():
            messagebox.showerror(
                "Import VCDs",
                "The characterization is not consistent:\n\n"
                + "\n".join(converter.errors),
                parent=self)
            return
        self.result = converter
        self.destroy()

    def _cancel(self) -> None:
        self.result = None
        self.destroy()
