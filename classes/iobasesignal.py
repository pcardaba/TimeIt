from __future__ import annotations

from contextlib import contextmanager
from typing import Iterable

import tkinter as tk
import math

from .signal import Signal


class IOBaseSignal(Signal):
    """Shared behavior for InputSignal and OutputSignal."""
    ## You can see 5 as the times Rpullup*Cbusline required to reach high.
    ## Use higher value (8) to look sharper,
    K = 5
    NORM = 1.0 - math.exp(-K)
    N_PTS = 8
    
    def __init__(self, name: str, sig_type: str) -> None:
        super().__init__(name, sig_type=sig_type)
        self.specify: str = "internal"
        self.refclock: ClockSignal = None
        self.refclk_period: float = 0.0
        self.refclk_runc: float = 0.0
        self.refclk_func: float = 0.0
        self.refclk_outdly: float = 0.0
        self.refclk_indly: float = 0.0

        self.data_edges: list[str] = []
        self.hiz_edges: list[str] = []
        self.high_edges: list[str] = []
        self.low_edges: list[str] = []
        self.unknown_edges: list[str] = []
        
        self.rclk_latency_max: str | None = None
        self.rclk_latency_min: str | None = None
        self.fclk_latency_max: str | None = None
        self.fclk_latency_min: str | None = None

        self.pulled_up: bool = False

        self.open_method = {
            "data": self._draw_data_open,
            "hiz": self._draw_hiz_open,
            "high": self._draw_high_open,
            "low": self._draw_low_open,
            "unknown": self._draw_unknown_open,
        }
        self.close_method = {
            "data": self._draw_data_close,
            "hiz": self._draw_hiz_close,
            "high": self._draw_high_close,
            "low": self._draw_low_close,
            "unknown": self._draw_unknown_close,
        }
        self.last_closed: str | None = None
        self.last_x: float | None = None
        self.wfstarts_x: float | None = None
        self.wfends_x: float | None = None

    @contextmanager
    def _temporarily_unhide_refclock(self, canvas: tk.Canvas):
        """Temporarily force the refclock waveform to normal state for bbox()."""
        if canvas.is_virtual:
            yield
            return
        if self.refclock is None or getattr(self.refclock, "visible", True):
            yield
            return

        tag = f"{self.refclock.name}_waveform"
        try:
            canvas.itemconfigure(tag, state="normal")
            yield
        finally:
            canvas.itemconfigure(tag, state="hidden")

    def _get_edge_item(self, canvas: tk.Canvas, edge: str):
        item = canvas.find_withtag(f"{self.refclock.name}_edge_{edge}")
        if not item:
            if self.console is not None:
                self.console.append_log(f"[{self.__class__.__name__}] Edge not found: {edge}\n",
                                        "error")
            return None
        return item

    def _draw_post_style(self, canvas: tk.Canvas) -> None:
        canvas.itemconfigure(f"{self.name}_transition",
                             fill="light grey",
                             outline=self.color,
                             width="1")
        canvas.itemconfigure(f"{self.name}_valid",
                             fill="white",
                             outline=self.color,
                             width=self.lwidth)
        canvas.itemconfigure(f"{self.name}_unknown",
                             stipple="gray50",
                             outline=self.color,
                             width=self.lwidth)
        canvas.itemconfigure(f"{self.name}_hizvalid",
                             fill=self.color,
                             width=self.lwidth)
        canvas.itemconfigure(f"{self.name}_pu_transition",
                             fill=self.color,
                             width=self.lwidth)
        canvas.itemconfigure(f"{self.name}_pulledup",
                             fill=self.color,
                             width=self.lwidth)
        canvas.itemconfigure(f"{self.name}_highvalid",
                             fill=self.color,
                             width=self.lwidth)
        canvas.itemconfigure(f"{self.name}_lowvalid",
                             fill=self.color,
                             width=self.lwidth)

    def _iter_edge_names(self) -> Iterable[str]:
        e1tag = self.refclock.edge1tag
        e2tag = self.refclock.edge2tag
        for n in range(self.refclock.cycles * 2):
            if n == 0:
                yield "0"
                continue
            yield str(n)
            yield f"{(n + 1) // 2}{e1tag if n % 2 else e2tag}"

    def _select_opened(self, edge: str) -> str | None:
        if edge in self.data_edges:
            return "data"
        if edge in self.hiz_edges:
            return "hiz"
        if edge in self.high_edges:
            return "high"
        if edge in self.low_edges:
            return "low"
        if edge in self.unknown_edges:
            return "unknown"
        return None

    def _draw_data_open(self, canvas: tk.Canvas, top: int, edge: str) -> None:
        slot_height = int(self.amplitude)
        if edge == "0":
            self.last_x = self.wfstarts_x
            return

        eitem = self._get_edge_item(canvas, edge)
        if eitem is None:
            return

        ulx, uly, brx, bry = canvas.bbox(eitem)
        if self.type == "input":
            dlymax, dlymin = self._get_input_delays(canvas, eitem)
        elif self.type == "output": 
            dlymax, dlymin = self._get_output_delays(canvas, eitem)
            if self.last_closed == "hiz":
                oedlymax, oedlymin = self._get_oe_delays(canvas, eitem)
                dlymin = oedlymin
                if oedlymax > dlymax:
                    dlymax = oedlymax
        else:
            raise NotImplementedError("Wrong type signal")
        
        mx = ulx + (brx - ulx) / 2
        sx = mx + canvas.scale_factor * dlymin
        sy = top + (slot_height / 2)
        fx = mx + canvas.scale_factor * dlymax
        fy = sy
        tilt = self.settings.waveform["tilt"]

        canvas.create_polygon(
            sx, sy,
            sx + tilt, sy + (slot_height / 2),
            fx + tilt, sy + (slot_height / 2),
            fx, fy,
            fx + tilt, sy - (slot_height / 2),
            sx + tilt, sy - (slot_height / 2),
            tags=(self.uidtag(), f"{self.name}_transition", f"{self.name}_waveform"),
        )
        self.last_x = fx

    def _draw_generic_close(self, canvas: tk.Canvas, top: int, edge: str, tag: str) -> None:
        slot_height = int(self.amplitude)

        ulx = self.wfends_x
        brx = self.wfends_x
        if edge:
            eitem = self._get_edge_item(canvas, edge)
            if eitem is None:
                return
            ulx, uly, brx, bry = canvas.bbox(eitem)
            if self.type == "input":
                dlymax, dlymin = self._get_input_delays(canvas, eitem)
            elif self.type == "output": 
                dlymax, dlymin = self._get_output_delays(canvas, eitem)
                # If opened is "hiz" the oe delays prevail over output delays
                oedlymax = dlymax
                oedlymin = dlymin
                if self._select_opened(edge) == "hiz":
                    oedlymax, oedlymin = self._get_oe_delays(canvas, eitem)
                    if  oedlymin < dlymin:
                        dlymin = oedlymin
            else:
                raise NotImplementedError("Wrong type signal")
        else:
            dlymax, dlymin = 0.0, 0.0

        sx = float(self.last_x or self.wfstarts_x)
        sy = top + (slot_height / 2)
        mx = ulx + (brx - ulx) / 2
        fx = mx + canvas.scale_factor * dlymin
        fy = sy
        tilt = self.settings.waveform["tilt"]

        canvas.create_polygon(
            sx, sy,
            sx + tilt, sy + (slot_height / 2),
            fx - tilt, sy + (slot_height / 2),
            fx, fy,
            fx - tilt, sy - (slot_height / 2),
            sx + tilt, sy - (slot_height / 2),
            tags=(self.uidtag(), f"{self.name}{tag}", f"{self.name}_waveform"),
        )
        if self.last_x == self.wfstarts_x:
            bgcolor = canvas.cget("background")
            canvas.create_line(self.last_x+tilt, top+slot_height,
                               self.last_x, top+(slot_height/2),
                               self.last_x+tilt, top,
                               fill=bgcolor,
                               width=self.lwidth+2,
                               tags=(self.uidtag(), self.name+"_waveform",),
                               )
        if edge=="":
            bgcolor = canvas.cget("background")
            canvas.create_line(fx-tilt, sy+(slot_height/2),
                               fx,fy,
                               fx-tilt, sy-(slot_height/2),
                               fill=bgcolor,
                               width=self.lwidth+2,
                               tags=(self.uidtag(), self.name+"_waveform",),
                               )

            
    def _draw_data_close(self, canvas: tk.Canvas, top: int, edge: str) -> None:
        self._draw_generic_close(canvas, top, edge, "_valid")

    def _draw_hiz_open(self, canvas: tk.Canvas, top: int, edge: str) -> None:
        slot_height = int(self.amplitude)
        if edge == "0":
            self.last_x = self.wfstarts_x
            return

        eitem = self._get_edge_item(canvas, edge)
        if eitem is None:
            return

        ulx, uly, brx, bry = canvas.bbox(eitem)
        if self.type == "input":
            dlymax, dlymin = self._get_input_delays(canvas, eitem)
        elif self.type == "output": 
            dlymax, dlymin = self._get_oe_delays(canvas, eitem)
            _, odlymin = self._get_output_delays(canvas, eitem)
            if odlymin < dlymin:
                dlymin = odlymin
        else:
            raise NotImplementedError("Wrong type signal")
        
        mx = ulx + (brx - ulx) / 2
        sx = mx + canvas.scale_factor * dlymin
        sy = top + (slot_height / 2)
        fx = mx + canvas.scale_factor * dlymax
        print(f"{edge} {self.last_closed}")
        if self.last_closed == "hiz" or self.last_closed == "high":
            self.last_x = fx
            return
        fy = sy
        tilt = self.settings.waveform["tilt"]

        if not self.pulled_up:
            canvas.create_polygon(
                sx, sy,
                sx + tilt, sy + (slot_height / 2),
                fx - tilt, sy + (slot_height / 2),
                fx, fy,
                fx - tilt, sy - (slot_height / 2),
                sx + tilt, sy - (slot_height / 2),
                tags=(self.uidtag(), f"{self.name}_transition", f"{self.name}_waveform"),
            )
        else:
            sy = top + slot_height
            fx = self._draw_pullup_rising(canvas, sx, sy)
            
        self.last_x = fx

    def _draw_pullup_rising(self, canvas: tk.Canvas, sx: int, sy: int) -> int:
        ampl = int(self.amplitude)
        rtime = self.settings.waveform["line_pullup"] * self.settings.waveform["line_cap"]
        rtime = self.K * rtime
        rtime = canvas.sec_to_tunits(rtime)
        deltax = rtime * canvas.scale_factor
        pts = []
        for i in range(self.N_PTS + 1):
            t = i / self.N_PTS
            x = sx + deltax * t
            y = sy - ampl * (1.0 - math.exp(-self.K * t)) / self.NORM
            pts.extend([x, y])

        canvas.create_line(*pts,
                           tags=(self.uidtag(),
                                 f"{self.name}_pu_transition", f"{self.name}_waveform"),
                           )
        return sx + deltax

        
    def _draw_hiz_close(self, canvas: tk.Canvas, top: int, edge: str) -> None:
        slot_height = int(self.amplitude)

        ulx = self.wfends_x
        brx = self.wfends_x
        if edge:
            eitem = self._get_edge_item(canvas, edge)
            if eitem is None:
                return
            ulx, uly, brx, bry = canvas.bbox(eitem)
            if self.type == "input":
                dlymax, dlymin = self._get_input_delays(canvas, eitem)
            elif self.type == "output": 
                dlymax, dlymin = self._get_oe_delays(canvas, eitem)
            else:
                raise NotImplementedError("Wrong type signal")
        else:
            dlymax, dlymin = 0.0, 0.0

        sx = float(self.last_x or self.wfstarts_x)
        sy = top 
        sy += slot_height / 2 if not self.pulled_up else 0
        mx = ulx + (brx - ulx) / 2
        fx = mx + canvas.scale_factor * dlymin
        fy = sy

        canvas.create_line(sx, sy,
                           fx, fy,
                           tags=(self.uidtag(),
                                 f"{self.name}_hizvalid",
                                 f"{self.name}_waveform"),)

    def _draw_high_open(self, canvas: tk.Canvas, top: int, edge: str) -> None:
        slot_height = int(self.amplitude)
        if edge == "0":
            self.last_x = self.wfstarts_x
            return

        eitem = self._get_edge_item(canvas, edge)
        if eitem is None:
            return
        ulx, uly, brx, bry = canvas.bbox(eitem)
        if self.type == "input":
            dlymax, dlymin = self._get_input_delays(canvas, eitem)
        elif self.type == "output": 
            dlymax, dlymin = self._get_output_delays(canvas, eitem)
            if self.last_closed == "hiz":
                oedlymax, oedlymin = self._get_oe_delays(canvas, eitem)
                dlymin = oedlymin
                if oedlymax > dlymax:
                    dlymax = oedlymax           
        else:
            raise NotImplementedError("Wrong type signal")

        tilt = self.settings.waveform["tilt"]
        mx = ulx + (brx - ulx) / 2
        sx = mx + canvas.scale_factor * dlymin - tilt
        sy = top + slot_height
        fx = mx + canvas.scale_factor * dlymax - tilt
        fy = sy

        canvas.create_polygon(
            sx, sy,
            sx + 2 * tilt, sy - slot_height,
            fx + 2 * tilt, sy - slot_height,
            fx, fy,
            tags=(self.uidtag(),
                  f"{self.name}_transition",
                  f"{self.name}_waveform"),
        )
        self.last_x = fx + tilt

    def _draw_high_close(self, canvas: tk.Canvas, top: int, edge: str) -> None:
        slot_height = int(self.amplitude)
        tilt = self.settings.waveform["tilt"]
        
        ulx = self.wfends_x
        brx = self.wfends_x
        if edge:
            eitem = self._get_edge_item(canvas, edge)
            if eitem is None:
                return
            ulx, uly, brx, bry = canvas.bbox(eitem)

            if self.type == "input":
                dlymax, dlymin = self._get_input_delays(canvas, eitem)
            elif self.type == "output": 
                dlymax, dlymin = self._get_output_delays(canvas, eitem)
                # If opened is "hiz" the oe delays prevail over output delays
                oedlymax = dlymax
                oedlymin = dlymin
                if self._select_opened(edge) == "hiz":
                    oedlymax, oedlymin = self._get_oe_delays(canvas, eitem)
                    if  oedlymin < dlymin:
                        dlymin = oedlymin               
            else:
                raise NotImplementedError("Wrong type signal")
        else:
            dlymax, dlymin = 0.0, 0.0

        sx = float(self.last_x or self.wfstarts_x) - tilt
        sy = top + slot_height
        mx = ulx + (brx - ulx) / 2
        fx = mx + canvas.scale_factor * dlymin
        fy = sy - (slot_height / 2)
        fy -= slot_height / 2 if self._select_opened(edge) == "hiz" else 0

        canvas.create_line(
            sx, sy,
            sx + 2 * tilt, sy - slot_height,
            fx - tilt, sy - slot_height,
            fx, fy,
            tags=(self.uidtag(),
                  f"{self.name}_highvalid",
                  f"{self.name}_waveform"),
        )
        if self.last_x == self.wfstarts_x:
            bgcolor = canvas.cget("background")
            canvas.create_line(sx,sy,
                               sx + 2 * tilt, sy - slot_height,
                               fill=bgcolor,
                               width=self.lwidth+2,
                               tags=(self.uidtag(),
                                     self.name+"_waveform",),
                               )
        if edge=="":
            bgcolor = canvas.cget("background")
            canvas.create_line( fx - tilt, sy - slot_height,
                                fx,fy,
                                fill=bgcolor,
                                width=self.lwidth+2,
                                tags=(self.uidtag(),
                                      self.name+"_waveform",),
                               )

    def _draw_low_open(self, canvas: tk.Canvas, top: int, edge: str) -> None:
        slot_height = int(self.amplitude)
        if edge == "0":
            self.last_x = self.wfstarts_x
            return

        eitem = self._get_edge_item(canvas, edge)
        if eitem is None:
            return
        ulx, uly, brx, bry = canvas.bbox(eitem)
        if self.type == "input":
            dlymax, dlymin = self._get_input_delays(canvas, eitem)
        elif self.type == "output": 
            dlymax, dlymin = self._get_output_delays(canvas, eitem)
            if self.last_closed == "hiz":
                oedlymax, oedlymin = self._get_oe_delays(canvas, eitem)
                dlymin = oedlymin
                if oedlymax > dlymax:
                    dlymax = oedlymax
        else:
            raise NotImplementedError("Wrong type signal")

        tilt = self.settings.waveform["tilt"]
        mx = ulx + (brx - ulx) / 2
        sx = mx + canvas.scale_factor * dlymin - tilt
        sy = top
        fx = mx + canvas.scale_factor * dlymax - tilt
        fy = sy

        canvas.create_polygon(
            sx, sy,
            sx + 2 * tilt, sy + slot_height,
            fx + 2 * tilt, sy + slot_height,
            fx, fy,
            tags=(self.uidtag(),
                  f"{self.name}_transition",
                  f"{self.name}_waveform"),
        )
        self.last_x = fx + tilt

    def _draw_low_close(self, canvas: tk.Canvas, top: int, edge: str) -> None:
        slot_height = int(self.amplitude)
        tilt = self.settings.waveform["tilt"]

        ulx = self.wfends_x
        brx = self.wfends_x
        if edge:
            eitem = self._get_edge_item(canvas, edge)
            if eitem is None:
                return
            ulx, uly, brx, bry = canvas.bbox(eitem)
            if self.type == "input":
                dlymax, dlymin = self._get_input_delays(canvas, eitem)
            elif self.type == "output": 
                dlymax, dlymin = self._get_output_delays(canvas, eitem)
                # If opened is "hiz" the oe delays prevail over output delays
                oedlymax = dlymax
                oedlymin = dlymin
                if self._select_opened(edge) == "hiz":
                    oedlymax, oedlymin = self._get_oe_delays(canvas, eitem)
                    if  oedlymin < dlymin:
                        dlymin = oedlymin  
            else:
                raise NotImplementedError("Wrong type signal")
        else:
            dlymax, dlymin = 0.0, 0.0

        sx = float(self.last_x or self.wfstarts_x) - tilt
        sy = top
        mx = ulx + (brx - ulx) / 2
        fx = mx + canvas.scale_factor * dlymin
        fy = sy + (slot_height / 2)
        fy += slot_height / 2 if self._select_opened(edge) == "hiz" else 0 
        
        canvas.create_line(
            sx, sy,
            sx + 2 * tilt, sy + slot_height,
            fx - tilt, sy + slot_height,
            fx, fy,
            tags=(self.uidtag(),
                  f"{self.name}_lowvalid",
                  f"{self.name}_waveform"),
        )
        if self.last_x == self.wfstarts_x:
            bgcolor = canvas.cget("background")
            canvas.create_line(sx,sy,
                               sx + 2 * tilt,sy + slot_height,
                               fill=bgcolor,
                               width=self.lwidth+2,
                               tags=(self.uidtag(), self.name+"_waveform",),
                               )
        if edge=="":
            bgcolor = canvas.cget("background")
            canvas.create_line(fx - tilt, sy + slot_height,
                               fx,fy,
                               fill=bgcolor,
                               width=self.lwidth + 2,
                               tags=(self.uidtag(), self.name+"_waveform",),
                               )
        

    def _draw_unknown_open(self, canvas: tk.Canvas, top: int, edge: str) -> None:
        self._draw_data_open(canvas, top, edge)

    def _draw_unknown_close(self, canvas: tk.Canvas, top: int, edge: str) -> None:
        self._draw_generic_close(canvas, top, edge, "_unknown")

    def _get_input_delays(self):
        raise NotImplementedError

    def _get_output_delays(self):
        raise NotImplementedError

    def draw(self, canvas: tk.Canvas, top: int) -> None:
        super().draw(canvas, top)
        refclk = self.refclock
        try:
            self.refclk_period = self._tcl_eval_float(self.refclock.period,
                                                      context="IOSignal")
            if refclk.rise_uncertainty is not None and not refclk.rise_uncertainty == "":
                self.refclk_runc = self._tcl_eval_float(refclk.rise_uncertainty,
                                                        context="IOSignal")
            if refclk.fall_uncertainty is not None and not refclk.fall_uncertainty == "":
                self.refclk_func = self._tcl_eval_float(refclk.fall_uncertainty,
                                                        context="IOSignal")
            if refclk.input_dly is not None and not refclk.input_dly == "":
                self.refclk_indly = self._tcl_eval_float(refclk.input_dly,
                                                         context="IOSignal")
            if refclk.output_dly is not None and not refclk.output_dly == "":
                self.refclk_outdly = self._tcl_eval_float(refclk.output_dly,
                                                          context="IOSignal")
        except tk.TclError:
            return

        
