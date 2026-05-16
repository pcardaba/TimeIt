from __future__ import annotations

from typing import TextIO

import tkinter as tk

from .iobasesignal import IOBaseSignal


class InputSignal(IOBaseSignal):
    def __init__(self, name: str) -> None:
        super().__init__(name, sig_type="input")

        self.rclk_inputdly_max: str | None = None
        self.rclk_inputdly_min: str | None = None
        self.fclk_inputdly_max: str | None = None
        self.fclk_inputdly_min: str | None = None

        self.indly: dict[str, float] = {}
        self.lat: dict[str, float] = {}

    def write(self, fileref: TextIO) -> None:
        fileref.write(f"\ncreate_input -name {self.name}  \\\n")
        fileref.write(f"   -specify {self.specify}  \\\n")
        if self.refclock is not None:
            fileref.write(f"   -refclock {self.refclock.name}  \\\n")

        for i in ("inputdly", "latency"):
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

        
    def draw(self, canvas: tk.Canvas, top: int) -> int:
        super().draw(canvas, top)

        if self.refclock is None:
            if self.console is not None:
                self.console.append_log("[InputSignal] Missing refclock\n", "error")
            return -999

        slot_height = int(self.amplitude)

        self.indly = {"rclkmax": 0.0, "rclkmin": 0.0,
                      "fclkmax": 0.0, "fclkmin": 0.0}
        self.lat = {"rclkmax": 0.0, "rclkmin": 0.0,
                    "fclkmax": 0.0, "fclkmin": 0.0}

        period = self.refclk_period
        self.wfstarts_x = self.settings.waveform["left_padding"] + self.settings.waveform["nmargin"]
        self.wfends_x = self.refclock.cycles * period * canvas.scale_factor + self.wfstarts_x

        try:
            for attr, key in (
                (self.rclk_inputdly_max, "rclkmax"),
                (self.fclk_inputdly_max, "fclkmax"),
                (self.rclk_inputdly_min, "rclkmin"),
                (self.fclk_inputdly_min, "fclkmin"),
            ):
                if attr is not None:
                    self.indly[key] = self._tcl_eval_float(attr, context="InputSignal")

            for attr, key in (
                (self.rclk_latency_max, "rclkmax"),
                (self.fclk_latency_max, "fclkmax"),
                (self.rclk_latency_min, "rclkmin"),
                (self.fclk_latency_min, "fclkmin"),
            ):
                if attr is not None:
                    self.lat[key] = self._tcl_eval_float(attr, context="InputSignal")
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
        return slot_height


    def _get_input_delays(self, canvas: tk.Canvas, edge_item) -> tuple[float, float]:
        tags = canvas.gettags(edge_item)

        ## When external spec (input delay is on launching virtual DFF)
        ## ... a clock uncertiture inflates the max delay and deflates min delay
        ## since you need to consider the latest launching edge.
        dlymax = self.indly["fclkmax"] + (self.refclk_func/2.0)
        dlymin = self.indly["fclkmin"] - (self.refclk_func/2.0)
        if "Pedges" in tags:
            dlymax = self.indly["rclkmax"] + (self.refclk_runc/2.0)
            dlymin = self.indly["rclkmin"] - (self.refclk_runc/2.0)

        # Determine if spec is "internal" or "external"
        # Ref clock topology does not apply on "external" spec
        if self.specify == "external":
            return dlymax, dlymin

        ## vvvv Internal spec vvvvvv
        
        # If you reach here is because delay spec is "internal".
        # Remember edges list assumes data launching edges...
        # Capture is the next edge with r/fclk spec.
        capture = ""  # both
        if self.rclk_inputdly_max is None:
            capture = "N"
        if self.fclk_inputdly_max is None:
            capture = "P"

        dlymax = 0.0
        dlymin = 0.0
        if "Pedges" in tags and capture == "P":
            # If a clock latency is specified...
            # Clock latency compensates internal input delays.
            # Use min latencies over max input delays since that is the worst case.
            # Use max latencies over min input delays since that is the worst case.
            # Clock uncertainty reduces the effective period => less input delay budget
            dlymax = (self.refclk_period - (self.refclk_runc/2.0))
            dlymax += -(self.indly["rclkmax"] - self.lat["rclkmin"])
            dlymin = -(self.indly["rclkmin"] - (self.refclk_runc/2.0) - self.lat["rclkmax"])
        if "Nedges" in tags and capture == "N":
            dlymax = self.refclk_period - (self.refclk_func/2.0)
            dlymax += -(self.indly["fclkmax"] - self.lat["fclkmin"])
            dlymin = -(self.indly["fclkmin"]  - (self.refclk_func/2.0) - self.lat["fclkmax"])
        if "Pedges" in tags and capture in ("N", ""):
            dlymax = (self.refclk_period / 2.0) - (self.refclk_runc/2.0)
            dlymax += -(self.indly["fclkmax"] - self.lat["fclkmin"])
            dlymin = -(self.indly["fclkmin"]  - (self.refclk_func/2.0) - self.lat["fclkmax"])
        if "Nedges" in tags and capture in ("P", ""):
            dlymax = (self.refclk_period / 2.0)  - (self.refclk_func/2.0)
            dlymax += -(self.indly["rclkmax"] - self.lat["rclkmin"])
            dlymin = -(self.indly["rclkmin"] - (self.refclk_runc/2.0) - self.lat["rclkmax"])
            
        # Clock topology trim.
        # Do not forget that internal input delay is a "capture" capture
        topology = self.refclock.topology
        if topology == "clockin" or topology == "clockinout":
            # In this topology it compensates the input delays. It adds to the latencies.
            dlymax += self.refclk_indly
            dlymin += self.refclk_indly
        elif topology == "clockout":
            dlymax += -self.refclk_outdly
            dlymin += -self.refclk_outdly
            
        return (dlymax, dlymin)


        


