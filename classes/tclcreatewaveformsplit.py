from __future__ import annotations

from .tclcommandbase import TclCommandBase, OptSpec
from .waveformsplit import WaveformSplit


class TclCreateWaveformSplit(TclCommandBase):
    """Implements the ``create_waveform_split`` Tcl command.

    Syntax
    ------
    create_waveform_split  -at <time>  \\
       [-amplitude <float>]            \\
       [-gap       <float>]            \\
       [-overflow  <float>]            \\
       [-lwidth    <int>]

    Parameters
    ----------
    -at          Time value (in the diagram's time units) at which the
                 split symbol is placed.  Converted to canvas x-coords
                 via WaveformsCanvas.time_to_x().
    -amplitude   Half-width of each sinusoid's x-oscillation (pixels).
    -gap         Half-distance between the three curve centres (pixels).
    -overflow    Fraction of slot height to overflow above/below each
                 individual segment (default 0.15).
    -lwidth      Stroke width of the two black curves (default 2).
    """

    command_name = "create_waveform_split"

    defaults = {
        "amplitude": 6.0,
        "gap":       5.0,
        "overflow":  0.15,
        "lwidth":    2,
    }

    spec = {
        "-at":        OptSpec("t",         True, float),
        "-amplitude": OptSpec("amplitude", True, float),
        "-gap":       OptSpec("gap",       True, float),
        "-overflow":  OptSpec("overflow",  True, float),
        "-lwidth":    OptSpec("lwidth",    True, int),
        "-use_uid":   OptSpec("uid",       True, int),
    }

    def validate(self, opts):
        ## -at is what places a new split; updating an existing one (-use_uid)
        ## may well touch only its look.
        if opts.get("uid") not in self.topapp.canvas.splits and "t" not in opts:
            raise ValueError("-at is required")

    def execute(self, opts):
        canvas = self.topapp.canvas
        uid = opts.get("uid")

        split = canvas.splits.get(uid) if uid is not None else None
        if split is not None:
            ## A split already carrying this uid is updated in place: this is
            ## how a split that is dragged to another time is expressed as a
            ## command (a plain create would add a second split).
            self.apply_given(split, opts, skip={"uid"})
            split.redraw()
            return ""

        split = WaveformSplit(
            canvas,
            opts["t"],
            amplitude=opts["amplitude"],
            gap=opts["gap"],
            overflow=opts["overflow"],
            lwidth=opts["lwidth"],
            uid=uid,
        )

        canvas.splits[split.uid] = split
        return ""
