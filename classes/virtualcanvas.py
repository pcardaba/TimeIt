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
                
    def redraw(self) -> None:
        self.draw_signals()

