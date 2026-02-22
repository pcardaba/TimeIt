import tkinter as tk
from .settings import Settings

class Signal:
    # Static data
    static_id = 0
    def __init__(self, name="", sig_type="clock"):
        self.console = None
        self.interp = None
        # sig_type: "clock", "input", "output"
        self.type      = sig_type
        self._related  = set() # Related objects.
        self.settings  = None
        self.name      = name
        self.direction = None
        self.visible   = False
        self.amplitude = 40
        self.color     = "black"
        self.lwidth    = 2
        self.uid = Signal.static_id
        Signal.static_id += 1
        self.elid = 0 # Element unique id.
        
    def uidtag(self) -> str:
        uidtag = "uid_"+str(self.uid)+"_"+str(self.elid)
        self.elid += 1
        return uidtag
        
    def draw(self, canvas: tk.Canvas, top: int):
        self.elid = 0
        self.settings = canvas.settings

    def write(self, fileref):
        pass
    
    def get_related_objs(self):
        return self._related

    def add_related_obj(self, obj):
        self._related.add(obj)

    def remove_related_obj(self, obj):
        self._related.discard(obj)

    def set_tcl_console(self, console):
        self.console = console
        self.interp = self.console.interp
