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

    ## Clock values the delay computations are made of.
    CLK_PARAMS = {"period": 0.0, "runc": 0.0, "func": 0.0,
                  "indly": 0.0, "outdly": 0.0}

    def __init__(self, name: str, sig_type: str) -> None:
        super().__init__(name, sig_type=sig_type)
        self.specify: str = "internal"
        ## The clock that launches the data and the clock that captures it.
        ## They are always related (same source clock), but they may have
        ## different periods.
        self.launch_clock: ClockSignal = None
        self.capture_clock: ClockSignal = None

        ## Resolved values of the launch (lclk) and of the capture (cclk)
        ## clock, refreshed on every draw().
        self.lclk: dict[str, float] = dict(self.CLK_PARAMS)
        self.cclk: dict[str, float] = dict(self.CLK_PARAMS)

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

    @property
    def launchclk(self) -> ClockSignal | None:
        """The clock the data transitions are drawn against.

        The edge lists (-data_edges, ...) always name launch clock edges.
        Giving a single clock means it both launches and captures the data.
        """
        return self.launch_clock if self.launch_clock is not None else self.capture_clock

    @property
    def captureclk(self) -> ClockSignal | None:
        """The clock the data is captured by at the receiving flip-flops."""
        return self.capture_clock if self.capture_clock is not None else self.launch_clock

    def related_clocks(self) -> tuple:
        """The clocks this signal depends on (launch and capture)."""
        return tuple(c for c in (self.launch_clock, self.capture_clock) if c is not None)

    def _write_clocks(self, fileref) -> None:
        for attr in ("launch_clock", "capture_clock"):
            clock = getattr(self, attr)
            if clock is not None:
                fileref.write(f"   -{attr} {clock.name}  \\\n")

    @contextmanager
    def _temporarily_unhide_launchclk(self, canvas: tk.Canvas):
        """Temporarily force the launch clock waveform to normal for bbox()."""
        if canvas.is_virtual:
            yield
            return
        if self.launchclk is None or getattr(self.launchclk, "visible", True):
            yield
            return

        tag = f"{self.launchclk.name}_waveform"
        try:
            canvas.itemconfigure(tag, state="normal")
            yield
        finally:
            canvas.itemconfigure(tag, state="hidden")

    def _get_edge_item(self, canvas: tk.Canvas, edge: str):
        item = canvas.find_withtag(f"{self.launchclk.name}_edge_{edge}")
        if not item:
            if self.console is not None:
                self.console.append_log(f"[{self.__class__.__name__}] Edge not found: {edge}\n",
                                        "error")
            return None
        return item

    # ------------------------------------------------------------------
    # Launch edge -> capture edge
    # ------------------------------------------------------------------
    def _launch_edge_index(self, canvas: tk.Canvas, edge_item) -> int | None:
        """Index (1 based) of the launch clock edge `edge_item` is drawing."""
        prefix = f"{self.launchclk.name}_edge_"
        for tag in canvas.gettags(edge_item):
            ## Edges carry both an absolute ("clk_edge_3") and a cycle tag
            ## ("clk_edge_2P"): only the absolute one ends with a number.
            if tag.startswith(prefix) and tag[len(prefix):].isdigit():
                return int(tag[len(prefix):])

        if self.console is not None:
            self.console.append_log(
                f"[{self.__class__.__name__}] {self.name}: unidentified "
                f"{self.launchclk.name} edge\n", "error")
        return None

    @staticmethod
    def _capture_polarity(launch_pol: str, rclk_dly, fclk_dly) -> str:
        """The capture clock edge polarity the data launched at `launch_pol` lands on.

        The capturing flip-flops are the ones the delays were specified for:
        rising ("P") when only rclk delays are given, falling ("N") when only
        fclk ones are. When both are given (both edges capture) the data is
        taken by the edge that does not have the polarity it was launched with.
        """
        if fclk_dly is None:
            return "P"
        if rclk_dly is None:
            return "N"
        return "N" if launch_pol == "P" else "P"

    def _capture_offset(self, canvas: tk.Canvas, edge_item, capture_pol: str) -> float:
        """Time from the launch edge `edge_item` to its capture edge."""
        index = self._launch_edge_index(canvas, edge_item)
        if index is None:
            return 0.0
        return self._capture_offset_at(index, capture_pol)

    def _capture_offset_at(self, index: int, capture_pol: str) -> float:
        """Time from launch clock edge `index` to its capture edge.

        The launch and the capture clock are related but may run at different
        rates, so the capturing edge has to be looked up in the capture clock
        waveform:

        - Capture clock not faster than the launch clock: the capturing edge is
          simply the first `capture_pol` capture clock edge after the launch one.
        - Capture clock faster: the launch clock is then a slow clock generated
          from it, and the capturing edge is the one *generating* the next
          `capture_pol` edge of the launch clock -- that is, that launch edge
          brought back by the delay the launch clock takes to come out.

        Both clocks are compared where their edges are generated and not where
        they come out, so that the output delay of a generated clock does not
        turn the edge coinciding with the launch one into its capturing edge.
        """
        try:
            launch_at = self.launchclk.edge_time(index)
            if self.cclk["period"] < self.lclk["period"] * (1.0 - 1e-9):
                capture_at = (self.launchclk.next_edge_time(launch_at, capture_pol)
                              - self.lclk["outdly"] + self.cclk["outdly"])
            else:
                generated_at = launch_at - self.lclk["outdly"] + self.cclk["outdly"]
                capture_at = self.captureclk.next_edge_time(generated_at, capture_pol)
        except (tk.TclError, ValueError):
            return 0.0

        return capture_at - launch_at

    def _capture_clock_trim(self) -> float:
        """From the capture clock at the pin to the capturing flip-flops.

        A clock coming in reaches the flip-flops its input delay later. A clock
        going out is seen at the pin its output delay after the flip-flops
        already got it. A "clockinout" clock goes out and comes back in: the
        capturing flip-flops are clocked by the returning one.
        """
        topology = self.captureclk.topology
        if topology in ("clockin", "clockinout"):
            return self.cclk["indly"]
        if topology == "clockout":
            return -self.cclk["outdly"]
        return 0.0

    def _launch_clock_trim(self) -> float:
        """From the launch clock at the pin to the launching flip-flops.

        Mirrors _capture_clock_trim(): a "clockinout" clock is generated
        inside, so the launching flip-flops are clocked by the outgoing one.
        """
        topology = self.launchclk.topology
        if topology == "clockin":
            return self.lclk["indly"]
        if topology in ("clockout", "clockinout"):
            return -self.lclk["outdly"]
        return 0.0

    def _internal_delays(self, delays: dict, launch_pol: str) -> tuple[float, float]:
        """Delays of data launched by our flip-flops, seen at the pin.

        The launching flip-flops clock latency adds up to the propagation delay
        and the launch clock uncertainty widens the transition at both ends.
        """
        key = "rclk" if launch_pol == "P" else "fclk"
        unc = self.lclk["runc"] if launch_pol == "P" else self.lclk["func"]
        trim = self._launch_clock_trim()

        dlymax = delays[f"{key}max"] + self.lat[f"{key}max"] + (unc / 2.0) + trim
        dlymin = delays[f"{key}min"] + self.lat[f"{key}min"] - (unc / 2.0) + trim
        return (dlymax, dlymin)

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
        e1tag = self.launchclk.edge1tag
        e2tag = self.launchclk.edge2tag
        for n in range(self.launchclk.cycles * 2):
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

    # ------------------------------------------------------------------
    # Analytic state timeline (used by clock gating)
    # ------------------------------------------------------------------
    def _delays_at(self, index: int | None, launch_pol: str) -> tuple[float, float]:
        """(dlymax, dlymin) of the transition launched at edge `index`."""
        raise NotImplementedError

    def state_intervals(self) -> list[tuple[float, float, str]] | None:
        """Analytic (start, end, state) timeline of this signal at the pin.

        Mirrors what draw() renders, but in time units and without any canvas:
        each state opened by the edge lists runs from the end of its opening
        transition (edge time + max delay) to the beginning of the next one
        (edge time + min delay). The first/last states extend to -/+ infinity.

        None when the signal can not be resolved. States positioned by the
        plain input/output delays (no output-enable special casing): a signal
        used as a clock enable should be a plain high/low waveform.
        """
        if not self.resolve_clock_params():
            return None
        if not self._resolve_delay_params():
            return None

        try:
            _, rise_at, fall_at = self.launchclk._waveform()
        except tk.TclError:
            return None
        ## Polarity of the launch clock edges: odd absolute indexes are the
        ## first edge of a cycle (computed from the waveform, not from the
        ## drawn tags: the launch clock may not have been drawn yet).
        e1tag, e2tag = ("P", "N") if rise_at < fall_at else ("N", "P")

        ## The state-opening events, walked in the same order as draw().
        events: list[tuple[float, float, str]] = []  # (begin, established, state)
        try:
            for n in range(self.launchclk.cycles * 2):
                if n == 0:
                    if self._select_opened("0") is not None:
                        events.append((-math.inf, -math.inf,
                                       self._select_opened("0")))
                    continue
                names = (str(n), f"{(n + 1) // 2}{e1tag if n % 2 else e2tag}")
                for name in names:
                    state = self._select_opened(name)
                    if state is None:
                        continue
                    t = self.launchclk.edge_time(n)
                    dlymax, dlymin = self._delays_at(n, e1tag if n % 2 else e2tag)
                    events.append((t + dlymin, t + dlymax, state))
        except (tk.TclError, ValueError):
            return None

        intervals: list[tuple[float, float, str]] = []
        opened: str | None = None
        opened_at = -math.inf
        for begin, established, state in events:
            if opened is not None:
                intervals.append((opened_at, begin, opened))
            opened = state
            opened_at = established
        if opened is not None:
            intervals.append((opened_at, math.inf, opened))
        return intervals

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
        
        if self.pulled_up:
            if self.last_closed in ("hiz","high"):
                self.last_x = mx
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
        sy = top + (slot_height / 2)
        mx = ulx + (brx - ulx) / 2
        fx = mx + canvas.scale_factor * dlymin
        fy = sy
        tilt = self.settings.waveform["tilt"]
        if not self.pulled_up:
            canvas.create_line(sx, sy,
                               fx, fy,
                               tags=(self.uidtag(),
                                     f"{self.name}_hizvalid",
                                     f"{self.name}_waveform"),)
        else: # When pulled_up
            canvas.create_line(sx, top,
                               fx - tilt, top,
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
        if self.last_closed == "high" or (self.pulled_up and self.last_closed == "hiz"):
            self.last_x = mx
            return
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
        if self.pulled_up and self._select_opened(edge) == "hiz":
            canvas.create_line(
                sx, top,
                fx, top,
                tags=(self.uidtag(),
                      f"{self.name}_highvalid",
                      f"{self.name}_waveform"),
            )
        else:
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
        if self.pulled_up and self._select_opened(edge) == "hiz":
            fy += slot_height / 2 
        
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

    def _resolve_delay_params(self) -> bool:
        raise NotImplementedError

    def _eval_or_zero(self, expr: str | None) -> float:
        if expr is None or expr == "":
            return 0.0
        return self._tcl_eval_float(expr, context="IOSignal")

    def draw(self, canvas: tk.Canvas, top: int) -> bool:
        """Resolve the clock values the delays are computed from.

        False when the signal can not be drawn, the subclasses then give up.
        """
        super().draw(canvas, top)
        return self.resolve_clock_params()

    def resolve_clock_params(self) -> bool:
        """Resolve the launch/capture clock values the delays are computed from.

        False when they can not be resolved (the signal is then not drawable).
        """
        if self.launchclk is None or self.captureclk is None:
            if self.console is not None:
                self.console.append_log(
                    f"[{self.__class__.__name__}] {self.name}: missing "
                    f"launch/capture clock\n", "error")
            return False

        for clock, params in ((self.launchclk, self.lclk),
                              (self.captureclk, self.cclk)):
            ## A generated clock used as capture clock may not have been drawn
            ## (hence resolved) yet when we get here.
            if not clock.ensure_resolved():
                return False
            try:
                params["period"] = self._tcl_eval_float(clock.period, context="IOSignal")
                params["runc"] = self._eval_or_zero(clock.rise_uncertainty)
                params["func"] = self._eval_or_zero(clock.fall_uncertainty)
                # Only a generated clock carries input/output delays.
                params["indly"] = self._eval_or_zero(getattr(clock, "input_dly", None))
                params["outdly"] = self._eval_or_zero(getattr(clock, "output_dly", None))
            except tk.TclError:
                return False

        return True
