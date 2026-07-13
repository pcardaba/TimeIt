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
        
        self.rclk_oedly_max: str | None = None
        self.rclk_oedly_min: str | None = None
        self.fclk_oedly_max: str | None = None
        self.fclk_oedly_min: str | None = None

        self.outdly: dict[str, float] = {}
        self.oedly: dict[str, float] = {}
        self.lat: dict[str, float] = {}

    def write(self, fileref: TextIO) -> None:
        fileref.write(f"\ncreate_output -name {self.name}  \\\n")
        fileref.write(f"   -specify {self.specify}  \\\n")
        self._write_clocks(fileref)

        for i in ("outputdly", "oedly", "latency"):
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

        if self.pulled_up:
            fileref.write(f"   -pulled_up  \\\n")
        self._write_common_args(fileref)
        super().write(fileref)

    def draw(self, canvas: tk.Canvas, top: int) -> int:
        if not super().draw(canvas, top):
            return -999
        top += self.top_padding

        slot_height = int(self.amplitude)

        self.outdly = {"rclkmax": 0.0, "rclkmin": 0.0,
                       "fclkmax": 0.0, "fclkmin": 0.0}
        self.oedly = {"rclkmax": 0.0, "rclkmin": 0.0,
                      "fclkmax": 0.0, "fclkmin": 0.0}
        self.lat = {"rclkmax": 0.0, "rclkmin": 0.0,
                    "fclkmax": 0.0, "fclkmin": 0.0}

        period = self.lclk["period"]
        self.wfstarts_x = self.settings.waveform["left_padding"] + self.settings.waveform["nmargin"]
        self.wfends_x = self.launchclk.cycles * period * canvas.scale_factor + self.wfstarts_x

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
                (self.rclk_oedly_max, "rclkmax"),
                (self.fclk_oedly_max, "fclkmax"),
                (self.rclk_oedly_min, "rclkmin"),
                (self.fclk_oedly_min, "fclkmin"),
            ):
                if attr is not None:
                    self.oedly[key] = self._tcl_eval_float(attr, context="OutputSignal")
                    
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
        with self._temporarily_unhide_launchclk(canvas):
            for edge in self._iter_edge_names():
                mode = self._select_opened(edge)
                if mode is None:
                    continue
                if opened is not None:
                    self.close_method[opened](canvas, top, edge)
                    self.last_closed = opened
                opened = mode
                self.open_method[opened](canvas, top, edge)

            if opened is not None:
                self.close_method[opened](canvas, top, "")

        self._draw_post_style(canvas)

        if self._apply_hidden_state(canvas):
            return 0
        return self.top_padding + slot_height

    def _get_output_delays(self, canvas: tk.Canvas, edge_item) -> tuple[float, float]:
        tags = canvas.gettags(edge_item)
        launch_pol = "P" if "Pedges" in tags else "N"

        if self.specify == "internal":
            # "Internal" delay spec is straight forward: our own flip-flops
            # launch the data, the delays run forward from the launching edge.
            return self._internal_delays(self.outdly, launch_pol)

        ## vvvv External spec vvvvvv

        ## The output delays are the setup/hold requirements of the device we
        ## drive, so they run backwards from the edge it captures with -- the
        ## edge lists only give launching edges, the capturing one has to be
        ## derived. Clock topology does not apply on external delays.
        capture_pol = self._capture_polarity(launch_pol,
                                             self.rclk_outputdly_max,
                                             self.fclk_outputdly_max)
        offset = self._capture_offset(canvas, edge_item, capture_pol)

        key = "rclk" if capture_pol == "P" else "fclk"
        unc = self.cclk["runc"] if capture_pol == "P" else self.cclk["func"]

        # Clock uncertainty reduces the effective capture window at both ends.
        dlymax = offset - (unc / 2.0) - self.outdly[f"{key}max"]
        dlymin = -(self.outdly[f"{key}min"] + (unc / 2.0))
        return (dlymax, dlymin)

    def _get_oe_delays(self, canvas: tk.Canvas, edge_item) -> tuple[float, float]:
        tags = canvas.gettags(edge_item)

        if self.specify == "internal":
            launch_pol = "P" if "Pedges" in tags else "N"
            return self._internal_delays(self.oedly, launch_pol)

        # External : There is no OE delays, they are assume same as output delays (outdly)
        return self._get_output_delays(canvas, edge_item)
