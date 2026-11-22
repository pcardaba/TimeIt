# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2024 Pablo Cardaba

from __future__ import annotations

from typing import Any, Dict

from .signal import Signal
from .inoutsignal import InOutSignal, IN_OPTIONS, OUT_OPTIONS
from .tclcommandbase import TclCommandBase, OptSpec


class TclCreateInout(TclCommandBase):
    """create_inout: a bidirectional signal, an input and an output in one.

    The options of the two parts are the ones of create_input and
    create_output. The delay options name their part by themselves
    (-rclk_inputdly_max, -rclk_outputdly_max, -rclk_oedly_max); the ones
    both commands share take an "in_" / "out_" prefix (-in_launch_clock,
    -out_data_edges, ...). What belongs to the port is given once.
    """

    command_name = "create_inout"

    _allowed_specify = {"internal", "external"}
    _allowed_colors = {"black", "green", "red", "blue", "orange", "purple"}

    def __init__(self, tcl):
        super().__init__(tcl)

        self.defaults = {"visible": False, "pulled_up": False,
                         "hide_contention": False}

        casters = {"clock": self._resolve_clock, "expr": str,
                   "edges": self._split_edges}
        self.spec = {
            "-name": OptSpec("name", True, str),
            "-specify": OptSpec("specify", True, str),
        }
        for option, _attr, kind in IN_OPTIONS + OUT_OPTIONS:
            self.spec[f"-{option}"] = OptSpec(option, True, casters[kind])
        self.spec.update({
            "-pulled_up": OptSpec("pulled_up", False, lambda _: True),
            "-hide_contention": OptSpec("hide_contention", False,
                                        lambda _: True),

            # Display
            "-color": OptSpec("color", True, str),
            "-amplitude": OptSpec("amplitude", True, int),
            "-lwidth": OptSpec("lwidth", True, int),
            "-use_uid": OptSpec("uid", True, int),
            "-visible": OptSpec("visible", False, lambda _: True),
        })

    # -------- Validation / execution --------

    def _check_part_clocks(self, opts: Dict[str, Any], prefix: str) -> None:
        """check_io_clocks() on the clocks of one part.

        Its messages name the options of that part.
        """
        part = {"launch_clock": opts.get(f"{prefix}_launch_clock"),
                "capture_clock": opts.get(f"{prefix}_capture_clock")}
        try:
            self.check_io_clocks(part)
        except ValueError as exc:
            message = str(exc)
            for option in ("launch_clock", "capture_clock"):
                message = message.replace(f"-{option}", f"-{prefix}_{option}")
            raise ValueError(message) from None
        opts[f"{prefix}_launch_clock"] = part["launch_clock"]
        opts[f"{prefix}_capture_clock"] = part["capture_clock"]

    def validate(self, opts: Dict[str, Any]) -> None:
        self.require(opts, "name")
        self.check_replaceable(opts["name"], InOutSignal)
        self._check_part_clocks(opts, "in")
        self._check_part_clocks(opts, "out")

        ## One port, one clock domain: what it receives and what it sends
        ## are timed by related clocks.
        receive, send = opts["in_launch_clock"], opts["out_launch_clock"]
        if not receive.is_related_to(send):
            raise ValueError(
                f"{receive.name} (input part) and {send.name} (output part) "
                f"are not related: the clocks of a bidirectional signal must "
                f"all share the same source clock")

        self.allow(opts, "specify", self._allowed_specify)
        self.allow(opts, "color", self._allowed_colors)

    def execute(self, opts: Dict[str, Any]) -> str:
        name: str = opts["name"]

        signal = self.topapp.signals.find(name)
        if not isinstance(signal, InOutSignal):
            if signal is not None:
                ## The signal changes class (e.g. it was an output): it goes
                ## with the markers measuring it.
                self.topapp.canvas.remove_signal(signal)
            signal = InOutSignal(name)
            signal.set_tcl_console(self.console)
        else:
            self._set_defaults(signal)

        uid = opts.get("uid")
        if uid is not None and Signal.static_id < uid:
            # If using user_uids Signal static UID must be highest
            Signal.static_id = uid + 1

        ## The part options are attributes of the signal (see InOutSignal).
        self.apply_attrs(signal, opts, skip={"name"})
        for clock in signal.related_clocks():
            clock.add_related_obj(signal)

        # Always add the signal to the topapp catalog last.
        self.topapp.signals.add(name, signal)

        self.topapp.redraw()
        return ""

    # -------- Helpers --------

    @staticmethod
    def _set_defaults(signal: InOutSignal) -> None:
        """Clear what this invocation may not mention, on an existing signal."""
        ## The clocks are about to be given again: the signal no longer goes
        ## with the ones it leaves.
        for clock in signal.related_clocks():
            clock.remove_related_obj(signal)

        for option, _attr, kind in IN_OPTIONS + OUT_OPTIONS:
            if kind == "expr":
                setattr(signal, option, None)
            elif kind == "edges":
                setattr(signal, option, [])
