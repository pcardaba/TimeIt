# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2024 Pablo Cardaba

"""A signal computed by applying a logic operator to other signals."""

from __future__ import annotations

from typing import TextIO

from . import timeline as tline
from .derivedsignal import DerivedSignal


class LogicSignal(DerivedSignal):
    """and / or / xor / nand / nor of any number of signals, or not of one.

    Operands are read at recompute time, so the result follows any edit to
    them. Unknown windows propagate except where a controlling value masks
    them: 0 AND X is 0, and 1 OR X is 1.
    """

    def __init__(self, name: str) -> None:
        super().__init__(name, sig_type="logic")
        self.op: str = "and"
        ## The operand signal objects, in the order given by -inputs.
        self.inputs: list = []
        ## Gate propagation delay, Tcl expressions resolved at draw time so
        ## the diagram stays parametric. An absent minimum equals the maximum.
        self.tpd_max: str | None = None
        self.tpd_min: str | None = None

    def operands(self) -> tuple:
        return tuple(op for op in self.inputs if op is not None)

    def recompute(self):
        timelines = []
        for operand in self.inputs:
            flat = self.operand_timeline(operand)
            if flat is None:
                return None
            timelines.append(flat)

        combined = tline.combine(self.op, timelines)

        dmax = self._eval_or_zero(self.tpd_max)
        dmin = dmax if self.tpd_min is None or str(self.tpd_min).strip() == "" \
            else self._eval_or_zero(self.tpd_min)
        return tline.shift(combined, dmax, dmin)

    def write(self, fileref: TextIO) -> None:
        fileref.write(f"\ncreate_logic -name {self.name}  \\\n")
        fileref.write(f"   -op {self.op}  \\\n")
        names = " ".join(op.name for op in self.operands())
        fileref.write(f"   -inputs {{{names}}}  \\\n")
        for attr in ("tpd_max", "tpd_min"):
            value = getattr(self, attr)
            if value is not None and str(value).strip() != "":
                fileref.write(f"   -{attr} {{{value}}}  \\\n")
        self._write_common_args(fileref)
        super(DerivedSignal, self).write(fileref)
