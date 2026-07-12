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
        super().draw(canvas, top)
        top += self.top_padding
        if self.refclock is None:
            if self.console is not None:
                self.console.append_log("[OutputSignal] Missing launch/capture clock\n",
                                        "error")
            return -999

        slot_height = int(self.amplitude)

        self.outdly = {"rclkmax": 0.0, "rclkmin": 0.0,
                       "fclkmax": 0.0, "fclkmin": 0.0}
        self.oedly = {"rclkmax": 0.0, "rclkmin": 0.0,
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
        with self._temporarily_unhide_refclock(canvas):
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

        if self.specify == "internal":
            # "Internal" delay spec is straight forward...
            dlymax = self.outdly["fclkmax"] + self.lat["fclkmax"]
            # Adding clock uncertitude contribution.
            dlymax += self.refclk_func / 2.0
            dlymin = self.outdly["fclkmin"] - (self.refclk_func/2.0) + self.lat["fclkmin"]
            dlymin -= self.refclk_func / 2.0
            if "Pedges" in tags:
                dlymax = self.outdly["rclkmax"] + self.lat["rclkmax"]
                dlymax += self.refclk_runc / 2.0
                dlymin = self.outdly["rclkmin"] + self.lat["rclkmin"]
                dlymin -= self.refclk_runc / 2.0

            # Clock topology trim.
            topology = self.refclock.topology
            if topology == "clockin":
                # In this topology output delays get worst. It adds to the latencies.
                dlymax += self.refclk_indly
                dlymin += self.refclk_indly
            elif topology == "clockout" or topology == "clockinout":   
                dlymax += -self.refclk_outdly
                dlymin += -self.refclk_outdly
            
            return (dlymax, dlymin)

        
        else: # External
            # Clock topology does not apply on external delays.
            capture = ""  # both
            if self.rclk_outputdly_max is None:
                capture = "N"
            if self.fclk_outputdly_max is None:
                capture = "P"

            dlymax = 0.0
            dlymin = 0.0
            if "Pedges" in tags and capture == "P":
                dlymax = self.refclk_period - (self.refclk_runc/2.0)
                dlymax += -self.outdly["rclkmax"]
                dlymin = -(self.outdly["rclkmin"] + (self.refclk_runc/2.0))
            if "Nedges" in tags and capture == "N":
                dlymax = self.refclk_period - (self.refclk_func/2.0)
                dlymax += -self.outdly["fclkmax"]
                dlymin = -(self.outdly["fclkmin"] + (self.refclk_func/2.0))
            if "Pedges" in tags and capture in ("N", ""):
                dlymax = self.refclk_period / 2.0  - (self.refclk_runc/2.0)
                dlymax += -self.outdly["fclkmax"]
                dlymin = -(self.outdly["fclkmin"] + (self.refclk_func/2.0))
            if "Nedges" in tags and capture in ("P", ""):
                dlymax = self.refclk_period / 2.0  - (self.refclk_func/2.0)
                dlymax += -self.outdly["rclkmax"]
                dlymin = -(self.outdly["rclkmin"] + (self.refclk_runc/2.0))
                
            return (dlymax, dlymin)

    
    def _get_oe_delays(self, canvas: tk.Canvas, edge_item) -> tuple[float, float]:
        tags = canvas.gettags(edge_item)

        if self.specify == "internal":
            # "Internal" delay spec is straight forward...
            dlymax = self.oedly["fclkmax"] + self.lat["fclkmax"]
            # Adding clock uncertainty contribution...
            dlymax += (self.refclk_func / 2.0)
            
            dlymin = self.oedly["fclkmin"] + self.lat["fclkmin"]
            dlymin -= (self.refclk_func / 2.0)
            if "Pedges" in tags:
                dlymax = self.oedly["rclkmax"] + self.lat["rclkmax"]
                dlymax += (self.refclk_runc / 2.0)
                dlymin = self.oedly["rclkmin"] + self.lat["rclkmin"]
                dlymin -= (self.refclk_runc / 2.0)

            # Clock topology trim.
            topology = self.refclock.topology
            if topology == "clockin":
                # In this topology output delays get worst. It adds to the latencies.
                dlymax += self.refclk_indly
                dlymin += self.refclk_indly
            elif topology == "clockout" or topology == "clockinout":   
                dlymax += -self.refclk_outdly
                dlymin += -self.refclk_outdly
            
            return (dlymax, dlymin)

        
        else: # External : There is no OE delays, they are assume same as output delays (outdly)
            return self._get_output_delays(canvas, edge_item)
