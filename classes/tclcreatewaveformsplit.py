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
    }

    def validate(self, opts):
        self.require(opts, "t")

    def execute(self, opts):
        canvas = self.topapp.canvas

        split = WaveformSplit(
            canvas,
            opts["t"],
            amplitude=opts["amplitude"],
            gap=opts["gap"],
            overflow=opts["overflow"],
            lwidth=opts["lwidth"],
        )

        canvas.splits[split.uid] = split
        return ""
