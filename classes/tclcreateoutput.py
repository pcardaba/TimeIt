from __future__ import annotations

from typing import Any, Dict

from .signal import Signal
from .outputsignal import OutputSignal
from .tclcommandbase import TclCommandBase, OptSpec


class TclCreateOutput(TclCommandBase):
    command_name = "create_output"

    _allowed_specify = {"internal", "external"}
    _allowed_colors = {"black", "green", "red", "blue", "orange", "purple"}

    def __init__(self, tcl):
        super().__init__(tcl)

        self.defaults = {"visible": False}

        self.spec = {
            "-name": OptSpec("name", True, str),
            "-specify": OptSpec("specify", True, str),
            "-refclock": OptSpec("refclock", True, self._resolve_refclock),

            # Output delays (must match OutputSignal attributes)
            "-rclk_outputdly_max": OptSpec("rclk_outputdly_max", True, str),
            "-rclk_outputdly_min": OptSpec("rclk_outputdly_min", True, str),
            "-fclk_outputdly_max": OptSpec("fclk_outputdly_max", True, str),
            "-fclk_outputdly_min": OptSpec("fclk_outputdly_min", True, str),

            # Latencies
            "-rclk_latency_max": OptSpec("rclk_latency_max", True, str),
            "-rclk_latency_min": OptSpec("rclk_latency_min", True, str),
            "-fclk_latency_max": OptSpec("fclk_latency_max", True, str),
            "-fclk_latency_min": OptSpec("fclk_latency_min", True, str),

            # Edge lists (parsed using BaseTclCommand._split_edges)
            "-data_edges": OptSpec("data_edges", True, self._split_edges),
            "-hiz_edges": OptSpec("hiz_edges", True, self._split_edges),
            "-high_edges": OptSpec("high_edges", True, self._split_edges),
            "-low_edges": OptSpec("low_edges", True, self._split_edges),
            "-unknown_edges": OptSpec("unknown_edges", True, self._split_edges),

            # Visual
            "-color": OptSpec("color", True, str),
            "-amplitude": OptSpec("amplitude", True, int),
            "-lwidth": OptSpec("lwidth", True, int),
            "-use_uid": OptSpec("uid", True, int),
            "-visible": OptSpec("visible", False, lambda _: True),
        }

    # -------------------------------------------------
    # Validation
    # -------------------------------------------------

    def validate(self, opts: Dict[str, Any]) -> None:
        self.require(opts, "name", "refclock")
        self.allow(opts, "specify", self._allowed_specify)
        self.allow(opts, "color", self._allowed_colors)

    # -------------------------------------------------
    # Execution
    # -------------------------------------------------

    def execute(self, opts: Dict[str, Any]) -> str:
        name: str = opts["name"]
        refclk = opts["refclock"]

        # Find or create signal
        signal = self.topapp.signals.find(name)
        if signal is None:
            signal = OutputSignal(name)
            signal.set_tcl_console(self.console)
        else:
            self._reset_optional_fields(signal)

        # Maintain UID semantics from the original implementation
        uid = opts.get("uid")
        if uid is not None and Signal.static_id < uid:
            # If using user_uids Signal static UID must be highest
            Signal.static_id = uid + 1
            
        # Apply attributes automatically where possible
        # (do not overwrite name; refclock handled explicitly)
        self.apply_attrs(signal, opts, skip={"name", "refclock"})

        # Explicit refclock wiring
        signal.refclock = refclk
        refclk.add_related_obj(signal)

        signal.direction = "output"
        # Always add the signal to the topapp catalog last.
        self.topapp.signals.add(name, signal)

        self.topapp.redraw()
        return ""

    # -------------------------------------------------
    # Internal helpers
    # -------------------------------------------------

    def _reset_optional_fields(self, signal: OutputSignal) -> None:
        """
        Clear optional attributes so they are not emitted if not set.
        """
        for group in ("outputdly", "latency"):
            for clk in ("rclk", "fclk"):
                for bound in ("max", "min"):
                    setattr(signal, f"{clk}_{group}_{bound}", None)

        for base in ("data", "hiz", "high", "low", "unknown"):
            setattr(signal, f"{base}_edges", [])

