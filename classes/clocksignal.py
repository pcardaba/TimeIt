from __future__ import annotations

from typing import TextIO
import tkinter as tk
from .signal import Signal

class ClockSignal(Signal):
    def __init__(self, name):
        super().__init__(name, sig_type="clock")
        
        ## Specific clock member.
        self.topology: str = "clockin" # default topology clock as input
        
        ## Can be numeric or symbolic. They need to be resolved.by Tcl
        ## This is why these vars are 'str', they contain expressions.
        self.period: str | None = None
        self.rise_at: str | None = None
        self.fall_at: str | None = None
        self.rise_uncertainty: str | None = None
        self.fall_uncertainty: str | None = None
        
        self.cycles: int = 10 # Number of cycles to be shown.
        self.input_dly: str | None = None
        self.output_dly: str | None = None
        
        # Edge tag prefix (for edge matching)
        self.edge1tag = "N"
        self.edge2tag = "P"
        
    def write(self, fileref) -> None:
        fileref.write(f"\ncreate_clock -name {self.name}  \\\n")
        fileref.write(f"   -topology {self.topology} \\\n")

        for attr in ("period", "rise_at", "fall_at",
                     "rise_uncertainty", "fall_uncertainty"):
            value = getattr(self, attr, None)
            if value is not None:
                fileref.write(f"   -{attr} {{{value}}}  \\\n")
                
        if self.topology in ("clockin", "clockinout") and self.input_dly is not None:
            fileref.write(f"   -input_dly {{{self.input_dly}}}  \\\n")
        if self.topology in ("clockout", "clockinout") and self.output_dly is not None:
            fileref.write(f"   -output_dly {{{self.output_dly}}}  \\\n")

        fileref.write(f"   -show {self.cycles}  \\\n")
        self._write_common_args(fileref)
  
        
    def draw(self, canvas: tk.Canvas, top: int) -> int:
        super().draw(canvas, top)
        top += self.top_padding
        slot_height = self.amplitude
        
        required = {
            "period": self.period,
            "rise_at": self.rise_at,
            "fall_at": self.fall_at,
        }
        if any(v is None for v in required.values()):
            if self.console is not None:
                missing = [k for k, v in required.items() if v is None]
                self.console.append_log(f"[ClockSignal] Missing attributes: {', '.join(missing)}\n",
                                        "error")
            return -999

        try:
            period = self._tcl_eval_float(self.period, context="ClockSignal")
            rise_at = self._tcl_eval_float(self.rise_at, context="ClockSignal")
            fall_at = self._tcl_eval_float(self.fall_at, context="ClockSignal")
            if self.rise_uncertainty is not None and not self.rise_uncertainty == "":
                rise_unc = self._tcl_eval_float(self.rise_uncertainty, context="ClockSignal")
            else:
                rise_unc = 0.0
            if self.fall_uncertainty is not None and not self.fall_uncertainty == "":
                fall_unc = self._tcl_eval_float(self.fall_uncertainty, context="ClockSignal")
            else:
                fall_unc = 0.0
        except tk.TclError:
            return -999

        self._draw_label(canvas, top)

        if not getattr(canvas, "is_scaled", False):
            width = max(canvas.winfo_width(), 1)
            width -= (
                self.settings.waveform["left_padding"]
                + self.settings.waveform["nmargin"]
                + self.settings.waveform["right_padding"]
            )
            canvas.scale_factor = float(width) / (period * float(self.cycles))
            canvas.is_scaled = True

        scale: float = canvas.scale_factor

        y = top
        sign = -1
        edge1at = fall_at
        edge2at = rise_at
        self.edge1tag, self.edge2tag = "N", "P"

        if rise_at < fall_at:
            y = top + slot_height
            sign = 1
            edge1at = rise_at
            edge2at = fall_at
            self.edge1tag, self.edge2tag = "P", "N"

        x0 = self.settings.waveform["left_padding"] + self.settings.waveform["nmargin"]
        x = x0
        tilt = self.settings.waveform["tilt"]

        for n in range(self.cycles):
            x1 = x0 + round((period * n + edge1at) * scale) - tilt
            x2 = x0 + round((period * n + edge2at) * scale) - tilt

            canvas.create_line(x, y,
                               x1, y,
                               tags=(self.uidtag(),
                                     "waveforms",
                                     f"{self.name}_waveform"))

            # First edge drawing
            canvas.create_line(
                x1, y,
                x1 + (2 * tilt), y - (sign * slot_height),
                tags=(
                    self.uidtag(),
                    "edges",
                    f"{self.edge1tag}edges",
                    f"{self.name}_{self.edge1tag}edges",
                    f"{self.name}_edge_{2*n+1}",
                    f"{self.name}_edge_{n+1}{self.edge1tag}",
                    "waveforms",
                    f"{self.name}_waveform",
                ),
            )
            
            canvas.create_line(
                x1 + (2 * tilt), y - (sign * slot_height),
                x2, y - (sign * slot_height),
                tags=(self.uidtag(),
                      "waveforms",
                      f"{self.name}_waveform"),
            )

            x = x2 + (2 * tilt)
            # Second edge drawing
            canvas.create_line(
                x2, y - (sign * slot_height),
                x, y,
                tags=(
                    self.uidtag(),
                    "edges",
                    f"{self.edge2tag}edges",
                    f"{self.name}_{self.edge2tag}edges",
                    f"{self.name}_edge_{2*n+2}",
                    f"{self.name}_edge_{n+1}{self.edge2tag}",
                    "waveforms",
                    f"{self.name}_waveform",
                ),
            )

            boundary = round(period * scale * (n + 1) + float(x0))
            if x < boundary:
                # Complete drawing until period boundary
                canvas.create_line(x, y,
                                   boundary, y,
                                   tags=(self.uidtag(),
                                         "waveforms",
                                         f"{self.name}_waveform"),
                                   )
                x = boundary

            canvas.itemconfigure(f"{self.name}_waveform",
                             fill=self.color,
                             width=str(self.lwidth),)

        # Drawing edge incertitudes if != 0
        if rise_unc > 0.0:
            for item in canvas.find_withtag(f"{self.name}_Pedges"):
                x1, y1, x2, y2 = canvas.coords(item)
                canvas.create_polygon(
                    x1 - (scale * rise_unc / 2.0), y1,
                    x2 - (scale * rise_unc / 2.0), y2,
                    x2 + (scale * rise_unc / 2.0), y2,
                    x1 + (scale * rise_unc / 2.0), y1,
                    tags=(self.uidtag(), "uncertainties",
                          "rise_uncertainties",
                          f"{self.name}_uncertainties"),
                )

        if fall_unc > 0.0:
            for item in canvas.find_withtag(f"{self.name}_Nedges"):
                x1, y1, x2, y2 = canvas.coords(item)
                canvas.create_polygon(
                    x1 - (scale * fall_unc / 2.0), y1,
                    x2 - (scale * fall_unc / 2.0), y2,
                    x2 + (scale * fall_unc / 2.0), y2,
                    x1 + (scale * fall_unc / 2.0), y1,
                    tags=(self.uidtag(), "uncertainties",
                          "fall_uncertainties",
                          f"{self.name}_uncertainties"),
                )

        canvas.itemconfigure(f"{self.name}_uncertainties",
                             fill="light grey",
                             outline=self.color, width="1",)
        
        canvas.tag_lower(f"{self.name}_uncertainties")

        if self._apply_hidden_state(canvas):
            return 0
        return self.top_padding + slot_height
    
