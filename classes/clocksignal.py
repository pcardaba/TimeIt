import tkinter as tk
from tkinter import ttk
from .signal import Signal

class ClockSignal(Signal):
    def __init__(self, name):
        super().__init__(name, sig_type="clock")
        ## Specific clock member.
        ## Can be numeric or symbolic. They need to be resolved.
        self.topology = "clockin" # default topology clock as input
        self.period = None
        self.rise_at = None
        self.fall_at = None
        self.rise_uncertainty = None
        self.fall_uncertainty = None
        self.cycles = 10 # Number of cycles to be shown.
        self.input_dly = None
        self.output_dly = None
        self.edge1tag = "N"
        self.edge2tag = "P"
        
    def write(self, fileref):
        fileref.write(f"\ncreate_clock -name {self.name}  \\\n")
        for attr in (
                "topology", "period", "rise_at", "fall_at",
                "rise_uncertainty", "fall_uncertainty"
        ):
            if (value := getattr(self, attr, None)) is not None:
                fileref.write(f"   -{attr} {value}  \\\n")
        # Special cases.
        if self.topology == "clockin" or self.topology == "clockinout":
            if self.input_dly is not None:
                fileref.write(f"   -input_dly {self.input_dly}  \\\n")
        elif self.topology == "clockout" or self.topology == "clockinout":
            if self.output_dly is not None:
                fileref.write(f"  -output_dly {self.output_dly}  \\\n")
            
        fileref.write(f"   -show {self.cycles}  \\\n")
        
        for attr in ("color", "amplitude", "lwidth"):
            if (value := getattr(self, attr, None)) is not None:
                fileref.write(f"   -{attr} {value}  \\\n")

        fileref.write(f"   -use_uid {self.uid}  \\\n")
        if self.visible:
            fileref.write(f"   -visible \n")
        
    def draw(self, canvas: tk.Canvas, top: int):
        super().draw(canvas, top)
        slot_height = int(self.amplitude)
        try:
            period = float(self.interp.eval("expr {"+self.period+"}"))
            rise_at = float(self.interp.eval("expr {"+self.rise_at+"}"))
            fall_at = float(self.interp.eval("expr {"+self.fall_at+"}"))
            rise_unc = float(self.interp.eval("expr {"+self.rise_uncertainty+"}"))
            fall_unc = float(self.interp.eval("expr {"+self.fall_uncertainty+"}"))
        except tk.TclError as e:
            self.console.append_log(f"[ClockSignal] Invalid clock attributes expressions:\n {e}",
                                    "error")
            return ""
        canvas.create_text(
            self.settings.waveform["left_padding"], # left margin (x)
            top + (slot_height / 2),
            text=self.name,
            font=self.settings.get_font(self.settings.waveform["font"]),
            anchor="w",
            tags=(self.uidtag(), "wf_labels", self.name+"_label",),
        )
        self.elid += 1 # Do not forget to increment the element Id
        if not canvas.is_scaled:
            width = max(canvas.winfo_width(), 1)
            width -=  ( self.settings.waveform["left_padding"]
                        + self.settings.waveform["nmargin"]
                        + self.settings.waveform["right_padding"])

            canvas.scale_factor = float(width) / (period * float(self.cycles))
            canvas.is_scaled = True

        scale: float = canvas.scale_factor
        y: int = top
        sign = -1
        edge1at: float = fall_at
        edge2at: float = rise_at
        self.edge1tag = "N"
        self.edge2tag = "P"
        if rise_at < fall_at:
            # Means clock starts at 0
            y = top+slot_height
            sign = 1
            edge1at = rise_at
            edge2at = fall_at
            self.edge1tag = "P"
            self.edge2tag = "N"
        # Initial x-coord.
        x0: int = (self.settings.waveform["left_padding"]
             + self.settings.waveform["nmargin"])
        x: int  = x0
        for n in range(self.cycles):
            x1: int = x0 + round((period*n+edge1at)*scale) - self.settings.waveform["tilt"]
            x2: int = x0 + round((period*n+edge2at)*scale) - self.settings.waveform["tilt"]
            canvas.create_line(x, y,
                               x1, y,
                               tags=(self.uidtag(), "waveforms", self.name+"_waveform",))
            canvas.create_line(x1, y,
                               x1+(2*self.settings.waveform["tilt"]),
                               y-(sign*slot_height),
                               tags=(self.uidtag(), "edges", self.edge1tag+"edges",
                                     self.name+"_"+self.edge1tag+"edges",
                                     self.name+"_edge_"+str(2*n+1), # first edge starts with 1
                                     self.name+"_edge_"+str(n+1)+self.edge1tag,
                                     "waveforms", self.name+"_waveform",))
            canvas.create_line(x1+(2*self.settings.waveform["tilt"]),
                               y-(sign*slot_height),
                               x2,y-(sign*slot_height),
                               tags=(self.uidtag(), "waveforms", self.name+"_waveform",))
            x = x2+(2*self.settings.waveform["tilt"])
            canvas.create_line(x2,y-(sign*slot_height),
                               x, y,
                               tags=(self.uidtag(), "edges", self.edge2tag+"edges",
                                     self.name+"_"+self.edge2tag+"edges",
                                     self.name+"_edge_"+str(2*n+2),
                                     self.name+"_edge_"+str(n+1)+self.edge2tag,
                                     "waveforms", self.name+"_waveform",))
            if x < (round(period*scale*(n+1))+float(x0)):
                canvas.create_line(x, y,
                                   round(period*scale*(n+1)+float(x0)), y,
                                   tags=(self.uidtag(), "waveforms", self.name+"_waveform",))
                x = round(period*scale*(n+1) + float(x0))

        canvas.itemconfigure(self.name+"_waveform", fill=self.color, width=str(self.lwidth))
        # Drawing uncertainties.
        if rise_unc is not None and rise_unc>0.0:
            items = canvas.find_withtag(self.name+"_Pedges")
            for item in items:
                (x1,y1,x2,y2) = canvas.coords(item)
                canvas.create_polygon(
                    x1-(scale*rise_unc/2.0),y1,
                    x2-(scale*rise_unc/2.0),y2,
                    x2+(scale*rise_unc/2.0),y2,
                    x1+(scale*rise_unc/2.0),y1,
                    tags=(self.uidtag(),"uncertainties", "rise_uncertainties",
                          self.name+"_uncertainties",),
                )
        if fall_unc is not None and fall_unc>0.0:
            items = canvas.find_withtag(self.name+"_Nedges")
            for item in items:
                (x1,y1,x2,y2) = canvas.coords(item)
                canvas.create_polygon(
                    x1-(scale*fall_unc/2.0),y1,
                    x2-(scale*fall_unc/2.0),y2,
                    x2+(scale*fall_unc/2.0),y2,
                    x1+(scale*fall_unc/2.0),y1,
                    tags=(self.uidtag(),"uncertainties", "fall_uncertainties",
                          self.name+"_uncertainties",),
                )
        canvas.itemconfigure(self.name+"_uncertainties",
                             fill="light grey",
                             outline=self.color,
                             width="1")
        canvas.tag_lower(self.name+"_uncertainties")
        
        if not canvas.is_virtual and not self.visible:
            canvas.itemconfigure(self.name+"_waveform", state="hidden")
            canvas.itemconfigure(self.name+"_uncertainties", state="hidden")
            canvas.itemconfigure(self.name+"_label", state="hidden")
            return 0
        return slot_height
