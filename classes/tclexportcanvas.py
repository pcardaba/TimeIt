from __future__ import annotations

import os

from .tclcommandbase import TclCommandBase, OptSpec
from .canvasexporter import CanvasExporter


class TclExportCanvas(TclCommandBase):
    """Implements the ``export_canvas`` Tcl command.

    Syntax
    ------
    export_canvas  -file <path>                    \\
       [-format auto|png|jpg|svg|pdf|ps|eps]       \\
       [-dpi        <int>]                         \\
       [-quality    <int>]                         \\
       [-background <color>]

    Exports the visible waveform canvas, exactly as File->Export Canvas...
    does. This is an action, not model state: it is never written back by
    TimeItApp.write_script and takes no undo snapshot.
    """

    command_name = "export_canvas"

    defaults = {
        "format":     "auto",
        "dpi":        300,
        "quality":    95,
        "background": "white",
    }

    spec = {
        "-file":       OptSpec("file",       True, str),
        "-format":     OptSpec("format",     True, lambda v: str(v).strip().lower()),
        "-dpi":        OptSpec("dpi",        True, int),
        "-quality":    OptSpec("quality",    True, int),
        "-background": OptSpec("background", True, str),
    }

    ## Extension -> format. "auto" deduces the format from the -file extension.
    _extensions = {
        ".png":  "png",
        ".jpg":  "jpg",
        ".jpeg": "jpg",
        ".svg":  "svg",
        ".pdf":  "pdf",
        ".ps":   "ps",
        ".eps":  "eps",
    }
    _allowed_formats = {"auto", "png", "jpg", "jpeg", "svg", "pdf", "ps", "eps"}

    def validate(self, opts):
        self.require(opts, "file")
        self.allow(opts, "format", self._allowed_formats)

        if opts["dpi"] <= 0:
            raise ValueError("-dpi must be a positive number")
        if not 1 <= opts["quality"] <= 100:
            raise ValueError("-quality must be in the 1..100 range")

        opts["format"] = self._resolve_format(opts)

    def _resolve_format(self, opts) -> str:
        fmt = opts["format"]
        if fmt != "auto":
            return "jpg" if fmt == "jpeg" else fmt

        ext = os.path.splitext(str(opts["file"]))[1].lower()
        fmt = self._extensions.get(ext)
        if fmt is None:
            raise ValueError(
                f"Cannot deduce the export format from {opts['file']}: "
                f"give a known extension or use -format"
            )
        return fmt

    def execute(self, opts):
        path = str(opts["file"])
        fmt = opts["format"]
        exporter = CanvasExporter(self.topapp.canvas)

        exports = {
            "png": lambda: exporter.export_png(path, bg=opts["background"],
                                               dpi=opts["dpi"]),
            "jpg": lambda: exporter.export_jpg(path, bg=opts["background"],
                                               dpi=opts["dpi"],
                                               quality=opts["quality"]),
            "svg": lambda: exporter.export_svg(path),
            "pdf": lambda: exporter.export_pdf(path),
            "ps":  lambda: exporter.export_ps(path),
            "eps": lambda: exporter.export_eps(path),
        }

        try:
            exports[fmt]()
        except ValueError:
            ## An empty canvas: the message is already meaningful as-is.
            raise
        except (RuntimeError, OSError) as exc:
            ## A missing optional dependency (pycairo/Pillow) or an unwritable
            ## file must be reported in the console, not raised at the user.
            raise ValueError(f"{path}: {exc}") from exc

        self.console.append_log(f"Canvas exported to {path}\n", "result")
        return ""
