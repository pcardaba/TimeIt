from __future__ import annotations

from typing import Any, Dict, Tuple

from .tclcommandbase import TclCommandBase, OptSpec
from .timingmarker import TimingMarker


class TclCreateTimingMarker(TclCommandBase):
    command_name = "create_timing_marker"

    _allowed_styles = {"outer", "inner_both", "inner_left", "inner_right"}
    _allowed_points = {"full", "start", "middle", "end"}

    def __init__(self, tcl):
        super().__init__(tcl)

        # Defaults: name may be empty string and is valid
        self.defaults = {
            "name": "",
            "style": "inner_both",
            "anchor": "none",
        }

        self.spec = {
            "-name": OptSpec("name", True, str),

            # from/to are "select:uid" (uid optional -> defaults as in old code)
            "-from": OptSpec("from_sel", True, self._parse_endpoint),
            "-to": OptSpec("to_sel", True, self._parse_endpoint),

            "-at": OptSpec("y", True, int),
            "-style": OptSpec("style", True, str),
            "-anchor": OptSpec("anchor", True, str),
            "-label_x": OptSpec("label_relx", True, int),
            "-label_y": OptSpec("label_rely", True, int),
            "-use_uid": OptSpec("uid", True, int),
        }

    # ----------------------------
    # Parsing helpers
    # ----------------------------

    def _parse_endpoint(self, raw: Any) -> Tuple[str, str]:
        """
        Parse 'select:uid' where select in {full,start,middle,end}.
          - If only 'uid' is given: treat as 'full:uid'
        Returns: (at, uid)
        """
        s = str(raw)
        parts = s.split(":", 1)

        if len(parts) == 1:
            # Old behavior: 'uid' alone means "full" and uid=uid
            at = "full"
            uid = parts[0]
        else:
            at, uid = parts[0], parts[1] if parts[1] != "" else parts[0]

        if at not in self._allowed_points:
            raise ValueError(f"{at} is not recognized point of measure")

        return at, uid

    # ----------------------------
    # Validation
    # ----------------------------

    def validate(self, opts: Dict[str, Any]) -> None:
        # -name is allowed to be "" so do NOT call require("name")
        # But -from and -to are mandatory per spec.
        updating = self._find_marker(opts.get("uid")) is not None

        if not updating:
            ## What a marker measures is fixed when it is created; updating one
            ## (-use_uid) only ever changes how it looks or where it sits.
            if "from_sel" not in opts:
                raise ValueError("-from is required")
            if "to_sel" not in opts:
                raise ValueError("-to is required")

        for option in ("-from", "-to"):
            key = "from_sel" if option == "-from" else "to_sel"
            if key in opts:
                self._check_endpoint_signal(option, opts[key][1])

        self.allow(opts, "style", self._allowed_styles)

    def _find_marker(self, uid: Any):
        if uid is None:
            return None
        return self.topapp.canvas.markers.get(f"tmarker_uid_{uid}")

    def _check_endpoint_signal(self, option: str, uid: str) -> None:
        """The signal a marker measures on must exist.

        A signal that can not be drawn (an unresolvable delay expression, a
        missing clock, ...) is dropped by the renderer, and the markers a
        script anchors on it would then measure nothing.
        """
        ## A signal element uid tag is "uid_<signal_uid>_<element_id>".
        parts = str(uid).split("_")
        if len(parts) < 2 or not parts[1].isdigit():
            raise ValueError(f"{option} {uid} is not a valid element")

        if self.topapp.signals.find_by_uid(parts[1]) is None:
            raise ValueError(
                f"{option} {uid}: no signal with uid {parts[1]} (it may have "
                f"been dropped because it could not be drawn)")

    # ----------------------------
    # Execution
    # ----------------------------

    def execute(self, opts: Dict[str, Any]) -> str:
        marker = self._find_marker(opts.get("uid"))
        if marker is not None:
            ## A marker already carrying this uid is updated in place: this is
            ## how the GUI expresses a style/anchor/label/position change (a
            ## plain create would stack a second marker on top of it).
            self.apply_given(marker, opts, skip={"uid"})
            marker.update_timings_dict()
            marker.redraw()
            return marker.uidtag()

        from_at, from_uid = opts["from_sel"]
        to_at, to_uid = opts["to_sel"]

        marker = TimingMarker(
            name=opts.get("name", ""),
            from_uid=from_uid,
            from_at=from_at,
            to_uid=to_uid,
            to_at=to_at,
            uid=opts.get("uid"),
        )

        # Optional attributes: only set if present
        for k in ("style", "anchor", "y", "label_relx", "label_rely"):
            if k in opts:
                setattr(marker, k, opts[k])

        self.topapp.canvas.create_timing_marker(marker)
        marker.update_timings_dict()

        return marker.uidtag()

    
