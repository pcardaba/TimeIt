from __future__ import annotations

from typing import Any, Dict

from .signal import Signal
from .inputsignal import InputSignal
from .tclcommandbase import TclCommandBase, OptSpec


class TclCreateInput(TclCommandBase):
    command_name = "create_input"

    _allowed_specify = {"internal", "external"}
    _allowed_colors = {"black", "green", "red", "blue", "orange", "purple"}

    def __init__(self, tcl):
        super().__init__(tcl)

        # Defaults (match prior behavior)
        self.defaults = {"visible": False, "pulled_up": False}

        # Build spec here so we can reference bound methods (self._resolve_clock, etc.)
        self.spec = {
            "-name": OptSpec("name", True, str),
            "-specify": OptSpec("specify", True, str),
            "-launch_clock": OptSpec("launch_clock", True, self._resolve_clock),
            "-capture_clock": OptSpec("capture_clock", True, self._resolve_clock),

            # Delay/latency expressions (strings)
            "-rclk_inputdly_max": OptSpec("rclk_inputdly_max", True, str),
            "-rclk_inputdly_min": OptSpec("rclk_inputdly_min", True, str),
            "-fclk_inputdly_max": OptSpec("fclk_inputdly_max", True, str),
            "-fclk_inputdly_min": OptSpec("fclk_inputdly_min", True, str),

            "-rclk_latency_max": OptSpec("rclk_latency_max", True, str),
            "-rclk_latency_min": OptSpec("rclk_latency_min", True, str),
            "-fclk_latency_max": OptSpec("fclk_latency_max", True, str),
            "-fclk_latency_min": OptSpec("fclk_latency_min", True, str),

            # Edge lists
            "-data_edges": OptSpec("data_edges", True, self._split_edges),
            "-hiz_edges": OptSpec("hiz_edges", True, self._split_edges),
            "-high_edges": OptSpec("high_edges", True, self._split_edges),
            "-low_edges": OptSpec("low_edges", True, self._split_edges),
            "-unknown_edges": OptSpec("unknown_edges", True, self._split_edges),

            # Display
            "-color": OptSpec("color", True, str),
            "-amplitude": OptSpec("amplitude", True, int),
            "-lwidth": OptSpec("lwidth", True, int),
            "-use_uid": OptSpec("uid", True, int),
            "-visible": OptSpec("visible", False, lambda _: True),
            "-pulled_up": OptSpec("pulled_up", False, lambda _: True),
        }

    # -------- Validation / execution --------

    def validate(self, opts: Dict[str, Any]) -> None:
        self.require(opts, "name")
        self.check_io_clocks(opts)
        self.allow(opts, "specify", self._allowed_specify)
        self.allow(opts, "color", self._allowed_colors)

    def execute(self, opts: Dict[str, Any]) -> str:
        name: str = opts["name"]

        # Find or create the signal
        signal = self.topapp.signals.find(name)
        if signal is None:
            signal = InputSignal(name)
            signal.set_tcl_console(self.console)
        else:
            # Clear defaults on an existing signal
            self._set_defaults(signal)

        # Maintain UID semantics from the original implementation
        uid = opts.get("uid")
        if uid is not None and Signal.static_id < uid:
            # If using user_uids Signal static UID must be highest
            Signal.static_id = uid + 1

        # Apply parsed options to signal
        self.apply_attrs(signal, opts,
                         skip={"name", "launch_clock", "capture_clock"})

        # Relationships / direction
        self.wire_io_clocks(signal, opts)
        signal.direction = "input"
        # Always add the signal to the topapp catalog last.
        self.topapp.signals.add(name, signal)
                    
        self.topapp.redraw()
        return ""

    # -------- Helpers --------

    def _set_defaults(self, signal):
        """
        clear attributes that may be empty and therefore not generated.
        """
        for i in ("inputdly", "latency"):
            for j in ("rclk", "fclk"):
                for k in ("max", "min"):
                    setattr(signal, f"{j}_{i}_{k}", None)

        for i in ("data", "hiz", "high", "low", "unknown"):
            setattr(signal, f"{i}_edges", [])

