from __future__ import annotations

from typing import Any, Dict

from .tclcommandbase import TclCommandBase, OptSpec
from .waveformannotation import WaveformAnnotation


class TclCreateWaveformAnnotation(TclCommandBase):
    """Handler for the ``create_waveform_annotation`` Tcl command."""

    command_name = "create_waveform_annotation"

    _allowed_slants = {"normal", "italic"}
    _allowed_weights = {"normal", "bold"}

    def __init__(self, tcl):
        super().__init__(tcl)
        self.defaults = {}
        self.spec = {
            "-on":          OptSpec("wf_uid",      True, str),
            "-text":        OptSpec("text",         True, str),
            "-font_size":   OptSpec("font_size",    True, int),
            "-font_slant":  OptSpec("font_slant",   True, str),
            "-font_weight": OptSpec("font_weight",  True, str),
            "-font_color":  OptSpec("font_color",   True, str),
            "-fill":        OptSpec("fill",          True, str),
            "-line":        OptSpec("line",          True, str),
            "-rel_x":       OptSpec("rel_x",        True, int),
            "-rel_y":       OptSpec("rel_y",        True, int),
        }

    # ------------------------------------------------------------------
    # Validation
    # ------------------------------------------------------------------

    def validate(self, opts: Dict[str, Any]) -> None:
        self.require(opts, "wf_uid")

        wf_uid = opts["wf_uid"]
        canvas = self.topapp.canvas

        # wf_uid must resolve to exactly one canvas item
        items = canvas.find_withtag(wf_uid)
        if not items:
            raise ValueError(f"-on {wf_uid!r}: no canvas item with that tag")
        if len(items) > 1:
            raise ValueError(
                f"-on {wf_uid!r}: tag matches {len(items)} items; "
                "only a unique waveform item uidtag is accepted"
            )

        # The item must be a waveform element (not a label, marker, grid line …)
        tags = canvas.gettags(items[0])
        if "wf_labels" in tags:
            raise ValueError(f"-on {wf_uid!r}: refers to a label, not a waveform item")
        if "tmarkers" in tags:
            raise ValueError(f"-on {wf_uid!r}: refers to a timing marker, not a waveform item")
        if not any(t.startswith("uid_") for t in tags):
            raise ValueError(f"-on {wf_uid!r}: item is not a signal waveform element")

        self.allow(opts, "font_slant",  self._allowed_slants)
        self.allow(opts, "font_weight", self._allowed_weights)

    # ------------------------------------------------------------------
    # Execution
    # ------------------------------------------------------------------

    def execute(self, opts: Dict[str, Any]) -> str:
        wf_uid = opts["wf_uid"]

        # Derive the signal from the uid prefix ("uid_<sig_uid>_<el_id>")
        parts = wf_uid.split("_")
        if len(parts) < 3:
            self.console.append_log(
                f"Error: malformed wf_uid {wf_uid!r}\n", "error")
            return ""
        sig_uid_str = parts[1]
        signal = self.topapp.signals.find_by_uid(sig_uid_str)
        if signal is None:
            self.console.append_log(
                f"Error: no signal found for uid {sig_uid_str}\n", "error")
            return ""

        # Retrieve existing annotation or create a new one
        annot = signal.annotations.get(wf_uid)
        if annot is None:
            annot = WaveformAnnotation(wf_uid, signal)
            signal.annotations[wf_uid] = annot

        # Apply provided options (command is non-incremental: overrides all)
        for key in ("text", "font_size", "font_slant", "font_weight",
                    "font_color", "fill", "line", "rel_x", "rel_y"):
            if key in opts:
                setattr(annot, key, opts[key])

        annot.redraw(self.topapp.canvas)
        return ""
