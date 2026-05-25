import tkinter as tk
from .waveformscanvas import WaveformsCanvas

class WaveformsView(tk.Frame):
    """Container for the waveform canvas + horizontal and vertical scrollbars."""

    def __init__(self, topapp: tk.Misc, **canvas_kwargs):
        super().__init__(topapp)
        self.topapp = topapp

        self.canvas = WaveformsCanvas(self, topapp=self.topapp, **canvas_kwargs)

        self.hbar = tk.Scrollbar(self, orient="horizontal", command=self.canvas.xview)
        self.canvas.configure(xscrollcommand=self._on_xscroll)

        self.vbar = tk.Scrollbar(self, orient="vertical", command=self.canvas.yview)
        self.canvas.configure(yscrollcommand=self._on_yscroll)

        self.canvas.grid(row=0, column=0, sticky="nsew")
        self.hbar.grid(row=1, column=0, sticky="ew")
        self.vbar.grid(row=0, column=1, sticky="ns")

        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=0)

        # start hidden
        self.hbar.grid_remove()
        self.vbar.grid_remove()

    def _on_xscroll(self, first: str, last: str) -> None:
        self.hbar.set(first, last)
        try:
            f = float(first)
            l = float(last)
        except ValueError:
            self.hbar.grid() # safest fallback
            return

        # auto hide if everything fits
        if f <= 0.0 and l >= 1.0:
            self.hbar.grid_remove()
        else:
            self.hbar.grid()

    def _on_yscroll(self, first: str, last: str) -> None:
        self.vbar.set(first, last)
        try:
            f = float(first)
            l = float(last)
        except ValueError:
            self.vbar.grid()
            return

        if f <= 0.0 and l >= 1.0:
            self.vbar.grid_remove()
        else:
            self.vbar.grid()

