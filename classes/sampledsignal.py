# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2024 Pablo Cardaba

"""A signal produced by resampling another one on a clock edge."""

from __future__ import annotations

from typing import TextIO

import tkinter as tk

from . import timeline as tline
from .derivedsignal import DerivedSignal

## Timing attributes, whose names are also the option tokens written back.
_TIMING_ATTRS = ("setup", "hold", "tco_max", "tco_min")


class SampledSignal(DerivedSignal):
    """One flip-flop: samples `source` on each `edge` of `clock`.

    The output holds each captured value until the next sampling edge, so a
    captured unknown persists at least that long. A transition window
    overlapping the setup/hold aperture captures as unknown, which is how a
    setup or hold violation shows up on the diagram.
    """

    def __init__(self, name: str) -> None:
        super().__init__(name, sig_type="sampled")
        self.source = None
        self.clock = None
        self.edge: str = "rising"
        ## Tcl expressions, resolved at draw time.
        self.setup: str | None = None
        self.hold: str | None = None
        self.tco_max: str | None = None
        self.tco_min: str | None = None

    def operands(self) -> tuple:
        return tuple(op for op in (self.source, self.clock) if op is not None)

    def sampling_edges(self) -> list[float] | None:
        """Times of the clock edges of the requested polarity.

        Polarity comes from the clock's resolved waveform rather than from
        drawn canvas tags: the sampling clock may not have been drawn yet.
        ``edge_time()`` already accounts for gating, so a suppressed pulse
        simply provides no sampling edge.
        """
        if self.clock is None:
            self._log("no sampling clock")
            return None

        ## A generated clock derives its waveform from its master and may not
        ## have been resolved yet.
        ensure = getattr(self.clock, "ensure_resolved", None)
        if ensure is not None and not ensure():
            self._log(f"{self.clock.name} cannot be resolved")
            return None

        try:
            _, rise_at, fall_at = self.clock._waveform()
        except (tk.TclError, ValueError, TypeError):
            self._log(f"{getattr(self.clock, 'name', '?')} cannot be resolved")
            return None

        ## Odd edge indexes are the first edge of a cycle. Which polarity
        ## that is depends on which of rise/fall comes first.
        first_is_rising = rise_at < fall_at
        want_rising = self.edge == "rising"
        want_odd = first_is_rising == want_rising

        times: list[float] = []
        for index in range(1, int(self.clock.cycles) * 2 + 1):
            if (index % 2 == 1) != want_odd:
                continue
            try:
                times.append(self.clock.edge_time(index))
            except (tk.TclError, ValueError):
                ## Past the last enabled pulse of a gated clock.
                break
        return times

    def recompute(self):
        source = self.operand_timeline(self.source)
        if source is None:
            return None

        edges = self.sampling_edges()
        if edges is None:
            return None

        tco_max = self._eval_or_zero(self.tco_max)
        tco_min = self._eval_or_zero(self.tco_min)
        if tco_min > tco_max:
            raise ValueError("tco_min can not exceed tco_max")

        return tline.sample(
            source, edges,
            setup=self._eval_or_zero(self.setup),
            hold=self._eval_or_zero(self.hold),
            tco_max=tco_max, tco_min=tco_min)

    def write(self, fileref: TextIO) -> None:
        fileref.write(f"\ncreate_sampled -name {self.name}  \\\n")
        if self.source is not None:
            fileref.write(f"   -source {self.source.name}  \\\n")
        if self.clock is not None:
            fileref.write(f"   -clock {self.clock.name}  \\\n")
        fileref.write(f"   -edge {self.edge}  \\\n")
        for attr in _TIMING_ATTRS:
            value = getattr(self, attr, None)
            if value is not None and str(value).strip() != "":
                fileref.write(f"   -{attr} {{{value}}}  \\\n")
        self._write_common_args(fileref)
        super(DerivedSignal, self).write(fileref)
