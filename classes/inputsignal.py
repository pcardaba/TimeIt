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
        self._write_clocks(fileref)

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
        super().write(fileref)

        
    def _resolve_delay_params(self) -> bool:
        """Resolve the input delay/latency expressions into self.indly/lat."""
        self.indly = {"rclkmax": 0.0, "rclkmin": 0.0,
                      "fclkmax": 0.0, "fclkmin": 0.0}
        self.lat = {"rclkmax": 0.0, "rclkmin": 0.0,
                    "fclkmax": 0.0, "fclkmin": 0.0}

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
            return False
        return True

    def draw(self, canvas: tk.Canvas, top: int) -> int:
        if not super().draw(canvas, top):
            return -999
        top += self.top_padding

        slot_height = int(self.amplitude)

        period = self.lclk["period"]
        self.wfstarts_x = self.settings.waveform["left_padding"] + self.settings.waveform["nmargin"]
        self.wfends_x = self.launchclk.cycles * period * canvas.scale_factor + self.wfstarts_x

        if not self._resolve_delay_params():
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


    def _get_input_delays(self, canvas: tk.Canvas, edge_item) -> tuple[float, float]:
        tags = canvas.gettags(edge_item)
        launch_pol = "P" if "Pedges" in tags else "N"

        index = None
        if self.specify != "external":
            ## Only the internal spec needs the edge index (capture offset).
            index = self._launch_edge_index(canvas, edge_item)
        return self._delays_at(index, launch_pol)

    def _delays_at(self, index: int | None, launch_pol: str) -> tuple[float, float]:
        """(dlymax, dlymin) of the transition launched at edge `index`."""
        if self.specify == "external":
            ## The input delays are the ones of the device driving us: they run
            ## forward from the launch edge it uses, and the uncertainty of that
            ## clock inflates the max delay and deflates the min one (the
            ## latest, respectively the earliest, launching edge has to be taken).
            key = "rclk" if launch_pol == "P" else "fclk"
            unc = self.lclk["runc"] if launch_pol == "P" else self.lclk["func"]
            return (self.indly[f"{key}max"] + (unc / 2.0),
                    self.indly[f"{key}min"] - (unc / 2.0))

        ## vvvv Internal spec vvvvvv

        ## The input delays are the ones of our own capturing flip-flops, so
        ## they run backwards from the capturing edge -- the edge lists only
        ## give launching edges, the capturing one has to be derived.
        capture_pol = self._capture_polarity(launch_pol,
                                             self.rclk_inputdly_max,
                                             self.fclk_inputdly_max)
        offset = 0.0
        if index is not None:
            offset = self._capture_offset_at(index, capture_pol)

        key = "rclk" if capture_pol == "P" else "fclk"
        unc = self.cclk["runc"] if capture_pol == "P" else self.cclk["func"]

        # Clock latency compensates internal input delays.
        # Use min latencies over max input delays since that is the worst case.
        # Use max latencies over min input delays since that is the worst case.
        # Clock uncertainty reduces the effective period => less input delay budget
        dlymax = offset - (unc / 2.0) - (self.indly[f"{key}max"] - self.lat[f"{key}min"])
        dlymin = -(self.indly[f"{key}min"] - (unc / 2.0) - self.lat[f"{key}max"])

        # The capture edge is the one seen by the capturing flip-flops, not the
        # one drawn at the pin.
        trim = self._capture_clock_trim()
        return (dlymax + trim, dlymin + trim)

