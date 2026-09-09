from __future__ import annotations

from typing import Any, Dict

from .tclcommandbase import TclCommandBase, OptSpec
from .valuemarker import ValueMarker


class TclCreateValueMarker(TclCommandBase):
    """create_value_marker: a value read-out on a point of a PWL trace."""

    command_name = "create_value_marker"

    def __init__(self, tcl):
        super().__init__(tcl)
        self.defaults = {}
        self.spec = {
            "-signal":  OptSpec("signal", True, str),
            "-at":      OptSpec("at", True, float),
            "-text":    OptSpec("text", True, str),
            "-label_x": OptSpec("label_relx", True, int),
            "-label_y": OptSpec("label_rely", True, int),
            "-use_uid": OptSpec("uid", True, int),
        }

    # ----------------------------
    # Helpers
    # ----------------------------
    def _find_marker(self, uid: Any) -> ValueMarker | None:
        if uid is None:
            return None
        for sig in self.topapp.signals.values():
            if sig.type == "pwl" and int(uid) in sig.vmarkers:
                return sig.vmarkers[int(uid)]
        return None

    def _find_slot(self, trace_name: str):
        """The PWL slot owning the trace named `trace_name`."""
        for sig in self.topapp.signals.values():
            if sig.type == "pwl" and sig.find_trace(trace_name) is not None:
                return sig
        return None

    # ----------------------------
    # Validation / execution
    # ----------------------------
    def validate(self, opts: Dict[str, Any]) -> None:
        marker = self._find_marker(opts.get("uid"))
        if marker is None:
            ## What the marker measures is fixed at creation: updating one
            ## (-use_uid) only changes its label or where the label sits.
            self.require(opts, "signal")
            if opts.get("at") is None:
                raise ValueError("-at is required")
            slot = self._find_slot(opts["signal"])
            if slot is None:
                raise ValueError(
                    f"{opts['signal']} is not a PWL trace (value markers "
                    f"are only possible on PWL signals)")
            trace = slot.find_trace(opts["signal"])
            if trace.value_at(opts["at"]) is None:
                raise ValueError(
                    f"-at {opts['at']:g} is outside the time range of "
                    f"{opts['signal']} [{trace.t_start:g}, {trace.t_end:g}]")

    def execute(self, opts: Dict[str, Any]) -> str:
        marker = self._find_marker(opts.get("uid"))
        if marker is not None:
            self.apply_given(marker, opts, skip={"uid", "signal"})
            marker.redraw()
            return marker.uidtag()

        slot = self._find_slot(opts["signal"])
        marker = ValueMarker(slot, opts["signal"], opts["at"],
                             uid=opts.get("uid"))
        for key in ("text", "label_relx", "label_rely"):
            if key in opts:
                setattr(marker, key, opts[key])
        slot.vmarkers[marker.uid] = marker
        marker.draw(self.topapp.canvas)
        return marker.uidtag()
