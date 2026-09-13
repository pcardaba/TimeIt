# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2024 Pablo Cardaba

from __future__ import annotations

from typing import Any, Dict

from .signal import Signal
from .logicsignal import LogicSignal
from .tclcommandbase import TclCommandBase, OptSpec
from . import timeline as tline


class TclCreateLogic(TclCommandBase):
    command_name = "create_logic"

    _allowed_ops = set(tline.OPERATORS)
    _allowed_colors = {"black", "green", "red", "blue", "orange", "purple"}

    def __init__(self, tcl):
        super().__init__(tcl)

        self.defaults = {"visible": False, "op": "and"}

        self.spec = {
            "-name": OptSpec("name", True, str),
            "-op": OptSpec("op", True, str),
            "-inputs": OptSpec("inputs", True, self._resolve_operands),
            "-tpd_max": OptSpec("tpd_max", True, str),
            "-tpd_min": OptSpec("tpd_min", True, str),

            "-color": OptSpec("color", True, str),
            "-amplitude": OptSpec("amplitude", True, int),
            "-lwidth": OptSpec("lwidth", True, int),
            "-use_uid": OptSpec("uid", True, int),
            "-visible": OptSpec("visible", False, lambda _: True),
        }

    # -------- Helpers --------

    def _resolve_operands(self, raw: Any) -> list:
        """Resolve the -inputs Tcl list into signals usable as logic inputs."""
        return [self._resolve_operand(name) for name in self._split_edges(raw)]

    def _resolve_operand(self, name: str):
        signal = self.topapp.signals.find(name)
        if signal is None:
            raise ValueError(f"{name} signal not found")
        if signal.type == "clock":
            raise ValueError(
                f"{name} is a clock: use its waveform through an "
                f"input/output signal instead")
        if signal.type == "pwl":
            raise ValueError(f"{name} is an analog (PWL) signal")
        if getattr(signal, "data_edges", None):
            raise ValueError(
                f"{name} carries bus data: it has no scalar value to combine")
        return signal

    @staticmethod
    def _check_no_cycle(name: str, operands: list) -> None:
        """Refuse a definition that would make `name` depend on itself.

        The error names the direct operand through which the loop closes,
        which is the one the user has to change.
        """
        for direct in operands:
            if direct is None:
                continue
            pending = [direct]
            seen = set()
            while pending:
                operand = pending.pop()
                if id(operand) in seen:
                    continue
                seen.add(id(operand))
                if getattr(operand, "name", None) == name:
                    raise ValueError(
                        f"{name} would depend on itself through {direct.name}")
                pending.extend(getattr(operand, "operands", tuple)())

    # -------- Validation / execution --------

    def validate(self, opts: Dict[str, Any]) -> None:
        self.require(opts, "name")
        self.allow(opts, "op", self._allowed_ops)
        self.allow(opts, "color", self._allowed_colors)

        inputs = opts.get("inputs") or []
        op = opts["op"]
        if op in tline.UNARY_OPERATORS:
            if len(inputs) != 1:
                raise ValueError(f"-op {op} takes exactly one input")
        elif len(inputs) < 2:
            raise ValueError(f"-op {op} needs at least two inputs")

        self._check_no_cycle(opts["name"], inputs)

    def execute(self, opts: Dict[str, Any]) -> str:
        name: str = opts["name"]

        signal = self.topapp.signals.find(name)
        if not isinstance(signal, LogicSignal):
            if signal is not None:
                ## The signal changes class (e.g. it was an input): replace it.
                self.topapp.signals.remove(name)
            signal = LogicSignal(name)
            signal.set_tcl_console(self.console)
        else:
            self._set_defaults(signal)

        uid = opts.get("uid")
        if uid is not None and Signal.static_id < uid:
            Signal.static_id = uid + 1

        self.apply_attrs(signal, opts, skip={"name"})
        self.topapp.signals.add(name, signal)

        self.topapp.redraw()
        return ""

    @staticmethod
    def _set_defaults(signal) -> None:
        """Clear attributes that may be absent from this invocation."""
        signal.tpd_max = None
        signal.tpd_min = None
