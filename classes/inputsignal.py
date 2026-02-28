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

        try:
            period = self._tcl_eval_float(self.refclock.period, context="InputSignal")
        except tk.TclError:
            return -999

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
        dlymax = self.indly["fclkmax"]
        dlymin = self.indly["fclkmin"]
        if "Pedges" in tags:
            dlymax = self.indly["rclkmax"]
            dlymin = self.indly["rclkmin"]
        return dlymax, dlymin


