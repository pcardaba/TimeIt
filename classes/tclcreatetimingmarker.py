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
        if "from_sel" not in opts:
            raise ValueError("-from is required")
        if "to_sel" not in opts:
            raise ValueError("-to is required")

        self.allow(opts, "style", self._allowed_styles)

    # ----------------------------
    # Execution
    # ----------------------------

    def execute(self, opts: Dict[str, Any]) -> str:
        from_at, from_uid = opts["from_sel"]
        to_at, to_uid = opts["to_sel"]

        marker = TimingMarker(
            name=opts.get("name", ""),
            from_uid=from_uid,
            from_at=from_at,
            to_uid=to_uid,
            to_at=to_at,
        )

        # Optional attributes: only set if present
        for k in ("style", "anchor", "y", "label_relx", "label_rely"):
            if k in opts:
                setattr(marker, k, opts[k])

        self.topapp.canvas.create_timing_marker(marker)
        marker.update_timings_dict()

        return marker.uidtag()

    
