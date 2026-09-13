# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2024 Pablo Cardaba

from __future__ import annotations

from typing import Any, Dict

from .signal import Signal
from .sampledsignal import SampledSignal
from .tclcommandbase import TclCommandBase, OptSpec


class TclCreateSampled(TclCommandBase):
    command_name = "create_sampled"

    _allowed_edges = {"rising", "falling"}
    _allowed_colors = {"black", "green", "red", "blue", "orange", "purple"}

    def __init__(self, tcl):
        super().__init__(tcl)

        self.defaults = {"visible": False, "edge": "rising"}

        self.spec = {
            "-name": OptSpec("name", True, str),
            "-source": OptSpec("source", True, self._resolve_source),
            "-clock": OptSpec("clock", True, self._resolve_clock),
            "-edge": OptSpec("edge", True, str),

            "-setup": OptSpec("setup", True, str),
            "-hold": OptSpec("hold", True, str),
            "-tco_max": OptSpec("tco_max", True, str),
            "-tco_min": OptSpec("tco_min", True, str),

            "-color": OptSpec("color", True, str),
            "-amplitude": OptSpec("amplitude", True, int),
            "-lwidth": OptSpec("lwidth", True, int),
            "-use_uid": OptSpec("uid", True, int),
            "-visible": OptSpec("visible", False, lambda _: True),
        }

    # -------- Helpers --------

    def _resolve_source(self, name: Any):
        """Resolve the sampled signal. A bus is allowed; a clock is not."""
        signal = self.topapp.signals.find(str(name))
        if signal is None:
            raise ValueError(f"{name} signal not found")
        if signal.type == "clock":
            raise ValueError(f"{name} is a clock and cannot be sampled")
        if signal.type == "pwl":
            raise ValueError(f"{name} is an analog (PWL) signal")
        return signal

    # -------- Validation / execution --------

    def validate(self, opts: Dict[str, Any]) -> None:
        self.require(opts, "name", "source", "clock")
        self.check_replaceable(opts["name"], SampledSignal)
        self.allow(opts, "edge", self._allowed_edges)
        self.allow(opts, "color", self._allowed_colors)
        self.check_no_cycle(opts["name"], [opts.get("source")])

    def execute(self, opts: Dict[str, Any]) -> str:
        name: str = opts["name"]

        signal = self.topapp.signals.find(name)
        if not isinstance(signal, SampledSignal):
            if signal is not None:
                ## The signal changes class (e.g. it was an input): replace it.
                self.topapp.signals.remove(name)
            signal = SampledSignal(name)
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
        for attr in ("setup", "hold", "tco_max", "tco_min"):
            setattr(signal, attr, None)
