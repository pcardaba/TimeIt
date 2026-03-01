# This class implements the TimeIt create_clock TCL command.

from __future__ import annotations

from .signal import Signal
from .clocksignal import ClockSignal
from .tclcommandbase import TclCommandBase, OptSpec


class TclCreateClock(TclCommandBase):
    command_name = "create_clock"

    defaults = {"visible": False}
    
    _allowed_topologies = {"clockin", "clockout", "clockinout"}

    spec = {
        "-topology": OptSpec("topology", True, str),
        "-name": OptSpec("name", True, str),
        "-period": OptSpec("period", True, str),
        "-rise_at": OptSpec("rise_at", True, str),
        "-fall_at": OptSpec("fall_at", True, str),
        "-rise_uncertainty": OptSpec("rise_uncertainty", True, str),
        "-fall_uncertainty": OptSpec("fall_uncertainty", True, str),
        "-input_dly": OptSpec("input_dly", True, str),
        "-output_dly": OptSpec("output_dly", True, str),
        "-color": OptSpec("color", True, str),
        "-amplitude": OptSpec("amplitude", True, int),
        "-lwidth": OptSpec("lwidth", True, int),
        "-show": OptSpec("cycles", True, int),
        "-use_uid": OptSpec("uid", True, int),
        "-visible": OptSpec("visible", False, lambda _v: True),
    }


    def validate(self, opts):
        # Required
        self.require(opts, "name")
        # Allowed values
        self.allow(opts, "topology", self._allowed_topologies)

    def execute(self, opts):
        name = opts["name"]

        signal = self.topapp.signals.find(name)
        if signal is None:
            signal = ClockSignal(name)
            signal.set_tcl_console(self.console)
            self.topapp.signals.add(name, signal)

        # Maintain UID semantics from the original implementation
        uid = opts.get("uid")
        if uid is not None and Signal.static_id < uid:
            # If using user_uids Signal static UID must be highest
            Signal.static_id = uid + 1

        # Apply parsed options to the signal object
        self.apply_attrs(signal, opts)

        # Derive direction from topology
        topo = getattr(signal, "topology", None)
        if topo == "clockin":
            signal.direction = "input"
        elif topo == "clockout":
            signal.direction = "output"
        else:
            signal.direction = "inout"

        self.topapp.redraw()
        return ""
