from __future__ import annotations

from typing import TextIO

import tkinter as tk

from .iobasesignal import IOBaseSignal


class OutputSignal(IOBaseSignal):

    def __init__(self, name: str) -> None:
        super().__init__(name, sig_type="output")

        self.rclk_outputdly_max: str | None = None
        self.rclk_outputdly_min: str | None = None
        self.fclk_outputdly_max: str | None = None
        self.fclk_outputdly_min: str | None = None

        self.outdly: dict[str, float] = {}
        self.lat: dict[str, float] = {}

    def write(self, fileref: TextIO) -> None:
        fileref.write(f"\ncreate_output -name {self.name}  \\\n")
        fileref.write(f"   -specify {self.specify}  \\\n")
        if self.refclock is not None:
            fileref.write(f"   -refclock {self.refclock.name}  \\\n")

        for i in ("outputdly", "latency"):
            for j in ("rclk", "fclk"):
                for k in ("max", "min"):
                    attr = f"{j}_{i}_{k}"
                    value = getattr(self, attr, None)
                    if value is not None:
                        fileref.write(f"   -{attr} {{{value}}}  \\\n")

        for base in ("data", "hiz", "high", "low", "unknown"):
            attr = f"{base}_edges"
            value = getattr(self, attr, None)
            if value:
                fileref.write(f"   -{attr} {{{' '.join(value)}}}  \\\n")

        self._write_common_args(fileref)

    def draw(self, canvas: tk.Canvas, top: int) -> int:
        super().draw(canvas, top)

        if self.refclock is None:
            if self.console is not None:
                self.console.append_log("[OutputSignal] Missing refclock\n", "error")
            return -999

        slot_height = int(self.amplitude)

        self.outdly = {"rclkmax": 0.0, "rclkmin": 0.0,
                       "fclkmax": 0.0, "fclkmin": 0.0}
        self.lat = {"rclkmax": 0.0, "rclkmin": 0.0,
                    "fclkmax": 0.0, "fclkmin": 0.0}

        period = self.refclk_period
        self.wfstarts_x = self.settings.waveform["left_padding"] + self.settings.waveform["nmargin"]
        self.wfends_x = self.refclock.cycles * period * canvas.scale_factor + self.wfstarts_x

        try:
            for attr, key in (
                (self.rclk_outputdly_max, "rclkmax"),
                (self.fclk_outputdly_max, "fclkmax"),
                (self.rclk_outputdly_min, "rclkmin"),
                (self.fclk_outputdly_min, "fclkmin"),
            ):
                if attr is not None:
                    self.outdly[key] = self._tcl_eval_float(attr, context="OutputSignal")

            for attr, key in (
                (self.rclk_latency_max, "rclkmax"),
                (self.fclk_latency_max, "fclkmax"),
                (self.rclk_latency_min, "rclkmin"),
                (self.fclk_latency_min, "fclkmin"),
            ):
                if attr is not None:
                    self.lat[key] = self._tcl_eval_float(attr, context="OutputSignal")
        except tk.TclError:
            return -999

        self._draw_label(canvas, top)

        opened: str | None = None
        with self._temporarily_unhide_refclock(canvas):
            for edge in self._iter_edge_names():
                mode = self._select_opened(edge)
                if mode is None:
                    continue
                if opened is not None:
                    self.close_method[opened](canvas, top, edge)
                opened = mode
                self.open_method[opened](canvas, top, edge)

            if opened is not None:
                self.close_method[opened](canvas, top, "")

        self._draw_post_style(canvas)

        if self._apply_hidden_state(canvas):
            return 0
        return slot_height

    def _get_output_delays(self, canvas: tk.Canvas, edge_item) -> tuple[float, float]:
        tags = canvas.gettags(edge_item)

        if self.specify == "internal":
            # "Internal" delay spec is straight forward...
            dlymax = self.outdly["fclkmax"] + self.lat["fclkmax"]
            dlymin = self.outdly["fclkmin"] + self.lat["fclkmin"]
            if "Pedges" in tags:
                dlymax = self.outdly["rclkmax"] + self.lat["rclkmax"]
                dlymin = self.outdly["rclkmin"] + self.lat["rclkmin"]
            return (dlymax, dlymin)
                
        else: # External
            capture = ""  # both
            if self.rclk_outputdly_max is None:
                capture = "N"
            if self.fclk_outputdly_max is None:
                capture = "P"

            if "Pedges" in tags and capture == "P":
                return (self.refclk_period - self.outdly["rclkmax"], -self.outdly["rclkmin"])
            if "Nedges" in tags and capture == "N":
                return (self.refclk_period - self.outdly["fclkmax"], -self.outdly["fclkmin"])
            if "Pedges" in tags and capture in ("N", ""):
                return (self.refclk_period / 2.0 - self.outdly["fclkmax"], -self.outdly["fclkmin"])
            if "Nedges" in tags and capture in ("P", ""):
                return (self.refclk_period / 2.0 - self.outdly["rclkmax"], -self.outdly["rclkmin"])
            return 0.0, 0.0

