import tkinter as tk

class VirtualCanvas(tk.Canvas):
    """ Upscaled fix canvas not visible to keep timing markers accurate
        It mirrors the waveform canvas but it is not shown.
    """
    
    def __init__(self, master=None, **kwargs):
        super().__init__(master, **kwargs)
        self.topapp = master
        self.settings = self.topapp.settings
        self.signals  = self.topapp.signals
        self.scale_factor: float = 1000.0
        self.is_scaled = True
        self.is_virtual = True
        
    def draw_signals(self) -> None:    
        self.delete("all")
        top = self.settings.waveform["top_padding"]       
        for sig in self.signals.values():
            top += sig.draw(self, top)
            if getattr(sig, "visible"):
                top += self.settings.waveform["interslot"]

    def time_to_x(self, t: float) -> float:
        """Convert a waveform time value to a canvas x coordinate.

        Mirrors WaveformsCanvas.time_to_x so signals that draw from times
        (derived signals) can be rendered on either canvas.
        """
        x0 = (self.settings.waveform["left_padding"]
              + self.settings.waveform["nmargin"])
        return x0 + t * self.scale_factor

    def x_to_time(self, x: float) -> float:
        """Convert a canvas x coordinate to a waveform time value."""
        x0 = (self.settings.waveform["left_padding"]
              + self.settings.waveform["nmargin"])
        return (x - x0) / self.scale_factor

    def sec_to_tunits(self, x: float) -> float:
        """Convert seconds to tunit-seconds"""
        if self.settings.waveform["tunits"] == "ms":
            return x * 1e3
        if self.settings.waveform["tunits"] == "us":
            return x * 1e6
        if self.settings.waveform["tunits"] == "ns":
            return x * 1e9
        if self.settings.waveform["tunits"] == "ps":
            return x * 1e12
        return x
    
    def redraw(self) -> None:
        self.draw_signals()

    def remove_all(self):
        self.delete("all")

