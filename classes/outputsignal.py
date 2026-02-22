import tkinter as tk
from tkinter import ttk
from .signal import Signal

class OutputSignal(Signal):
    def __init__(self, name):
        super().__init__(name, sig_type="output")
        ## Specific clock member.
        ## Can be numeric or symbolic. They need to be resolved.
        self.specify = "internal" 
        self.refclock = None
        self.rclk_outputdly_max = None
        self.rclk_outputdly_min = None
        self.fclk_outputdly_max = None
        self.fclk_outputdly_min = None
        self.rclk_latency_max = None
        self.rclk_latency_min = None
        self.fclk_latency_max = None
        self.fclk_latency_min = None
        ## Edges are considered as launching edges.
        self.data_edges = []
        self.hiz_edges = []
        self.high_edges = []
        self.low_edges = []
        self.unknown_edges = []
        self.last_x = None
        self.wfstarts_x = None # Waveform starts at
        self.wfends_x = None  # Waveform ends at
        self.outdly = {}
        self.lat = {}
        self.refclk_period = 0.0

    def write(self, fileref):
        fileref.write(f"\ncreate_output -name {self.name}  \\\n")
        fileref.write(f"   -specify {self.specify}  \\\n")
        fileref.write(f"   -refclock {self.refclock.name}  \\\n")
        for i in ("outputdly", "latency"):
            for j in ("rclk", "fclk"):
                for k in ("max", "min"):
                    attr = j+"_"+i+"_"+k
                    if (value := getattr(self, attr, None)) is not None:
                        fileref.write(f"   -{attr} {value}  \\\n")
        for i in ("data", "hiz", "high", "low", "unknown"):
            attr = i+"_edges"
            if (value := getattr(self, attr, None)) is not None:
                if len(value) != 0:
                    value = " ".join(value)
                    fileref.write(f"   -{attr} {{{value}}}  \\\n")
                
        for attr in ("color", "amplitude", "lwidth"):
            if (value := getattr(self, attr, None)) is not None:
                fileref.write(f"   -{attr} {value}  \\\n")

        fileref.write(f"   -use_uid {self.uid}  \\\n")
        if self.visible:
            fileref.write(f"   -visible \n")

        
    def draw(self, canvas: tk.Canvas,  top: int):
        super().draw(canvas, top)
        slot_height = int(self.amplitude)
        self.settings = canvas.settings
        self.outdly = { "rclkmax" : 0.0,
                       "rclkmin" : 0.0,
                       "fclkmax" : 0.0,
                       "fclkmin" : 0.0 }
        self.lat = { "rclkmax" : 0.0,
                     "rclkmin" : 0.0,
                     "fclkmax" : 0.0,
                     "fclkmin" : 0.0 }

        try:
            period = float(self.interp.eval("expr {"+self.refclock.period+"}"))
        except tk.TclError as e:
            self.console.append_log(f"[OutputSignal] Invalid refclock period expression:\n {e}",
                                    "error")
            return ""
        self.refclk_period = period
        self.wfstarts_x = self.settings.waveform["left_padding"] + self.settings.waveform["nmargin"]
        self.wfends_x = self.refclock.cycles*period*canvas.scale_factor + self.wfstarts_x 
        try:
            for attr, key in (
                    (self.rclk_outputdly_max, "rclkmax"),
                    (self.fclk_outputdly_max, "fclkmax"),
                    (self.rclk_outputdly_min, "rclkmin"),
                    (self.fclk_outputdly_min, "fclkmin"),
            ):
                if attr is not None:
                    self.outdly[key] = float(self.interp.eval("expr {"+attr+"}"))
        except tk.TclError as e:
            self.console.append_log(f"[OutputSignal] Invalid output delay attributes expressions:\n {e}",
                                    "error")
            return ""
        try:
            for attr, key in (
                    (self.rclk_latency_max, "rclkmax"),
                    (self.fclk_latency_max, "fclkmax"),
                    (self.rclk_latency_min, "rclkmin"),
                    (self.fclk_latency_min, "fclkmin"),
            ):
                if attr is not None:
                    self.lat[key] = float(self.interp.eval("expr {"+attr+"}"))
        except tk.TclError:
            self.console.append_log(f"[OutputSignal] Invalid latency attributes expressions:\n {e}",
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

        open_method = {
            "data" : self._draw_data_open,
            "hiz"  : self._draw_hiz_open,
            "high" : self._draw_high_open,
            "low" : self._draw_low_open,
            "unknown" : self._draw_unknown_open,
        }
        close_method = {
            "data" : self._draw_data_close,
            "hiz"  : self._draw_hiz_close,
            "high" : self._draw_high_close,
            "low" : self._draw_low_close,
            "unknown" : self._draw_unknown_close,
        }
        edgeslist = {
            "data" : self.data_edges,
            "hiz"  : self.hiz_edges,
            "high" : self.high_edges,
            "low" : self.low_edges,
            "unknown" : self.unknown_edges,
        }
        opened = ""
        e1tag = self.refclock.edge1tag
        e2tag = self.refclock.edge2tag
        for n in range(self.refclock.cycles*2):
            for edge in (
                    ["0"] if n == 0
                    else [str(n), f"{(n+1)//2}{e1tag if n%2 else e2tag}"]
            ):
                for what in edgeslist:
                    if edge in edgeslist[what]:
                        if opened != "":
                            close_method.get(opened)(canvas, top, edge)
                        opened = what
                        open_method.get(opened)(canvas, top, edge)
        if opened != "":
            # Close wafeform drawing ... edge=""
            close_method.get(opened)(canvas, top, "")
                        
        canvas.itemconfigure(self.name+"_transition",
                             fill="light grey",
                             outline=self.color,
                             width="1")
        canvas.itemconfigure(self.name+"_valid",
                             fill="white",
                             outline=self.color,
                             width=self.lwidth)
        canvas.itemconfigure(self.name+"_unknown",
                             stipple="gray50",
                             outline=self.color,
                             width=self.lwidth)
        canvas.itemconfigure(self.name+"_hizvalid",
                             fill=self.color,
                             width=self.lwidth)
        canvas.itemconfigure(self.name+"_highvalid",
                             fill=self.color,
                             width=self.lwidth)
        canvas.itemconfigure(self.name+"_lowvalid",
                             fill=self.color,
                             width=self.lwidth)
        if not canvas.is_virtual and not self.visible:
            canvas.itemconfigure(self.name+"_waveform", state="hidden")
            canvas.itemconfigure(self.name+"_uncertainties", state="hidden")
            canvas.itemconfigure(self.name+"_label", state="hidden")
            return 0
        return slot_height

    def _get_edge_item(self, canvas, edge):
        item = canvas.find_withtag(self.refclock.name+"_edge_"+edge)
        if not item:
            print("TODO: what to do if edge is not found ?.")
            return None
        return item

    ## Only external delays supported... TODO: add also internal delay option.
    def _get_output_delays(self, canvas, edge_item):
        # Find is edge is Postive or negative.
        tags = canvas.gettags(edge_item)
        # Determine if capture edge is positive, negative or both.

        capture = "" # both edges
        if self.rclk_outputdly_max is None:
            # Capturing egde is negedge
            capture = "N"
        if self.fclk_outputdly_max is None:
            capture = "P"
 
        if "Pedges" in tags and capture == "P":
            dlymax = self.refclk_period - self.outdly["rclkmax"]
            dlymin = -self.outdly["rclkmin"]
            return (dlymax, dlymin)
        if "Nedges" in tags and capture == "N":
            dlymax = self.refclk_period - self.outdly["fclkmax"]
            dlymin = -self.outdly["fclkmin"]
            return (dlymax, dlymin)
        if "Pedges" in tags and (capture == "N" or capture == ""):
            dlymax = self.refclk_period/2.0 - self.outdly["fclkmax"]
            dlymin = -self.outdly["fclkmin"]
            return (dlymax, dlymin)
        if "Nedges" in tags and (capture == "P" or capture == ""):
            dlymax = self.refclk_period/2.0 - self.outdly["rclkmax"]
            dlymin = -self.outdly["rclkmin"]
            return (dlymax, dlymin)
    
    def _draw_data_open(self, canvas: tk.Canvas,  top: int, edge : str):
        # Special case when edge is 0.
        slot_height = int(self.amplitude)
        if edge == "0":
            self.last_x = self.wfstarts_x
            return
        eitem = self._get_edge_item(canvas, edge)
        (ulx, uly, brx, bry) = canvas.bbox(eitem)
        (dlymax, dlymin) = self._get_output_delays(canvas, eitem)
        # mid points:
        mx = ulx + (brx - ulx)/2
        sx = mx + canvas.scale_factor*dlymin
        sy = top + (slot_height / 2)
        fx = mx + canvas.scale_factor*dlymax
        fy = sy
        tilt = self.settings.waveform["tilt"]
        # Draw polygon:
        canvas.create_polygon(
            sx,sy,
            sx+tilt, sy+(slot_height/2),
            fx+tilt, sy+(slot_height/2),
            fx,fy,
            fx+tilt, sy-(slot_height/2),
            sx+tilt, sy-(slot_height/2),
            tags=(self.uidtag(),self.name+"_transition",self.name+"_waveform",),
        )
        
        self.last_x = fx
        return

    
    def _draw_generic_close(self, canvas: tk.Canvas,  top: int, edge : str, tag : str):
        slot_height = int(self.amplitude)
        # Default is waveform close ...
        (ulx, uly, brx, bry) = (self.wfends_x,top,self.wfends_x,top)
        (dlymax, dlymin) = (0,0)
        if edge!="": # If not closing end of waveform...
            eitem = self._get_edge_item(canvas, edge)
            (ulx, uly, brx, bry) = canvas.bbox(eitem)
            (dlymax, dlymin) = self._get_output_delays(canvas, eitem)
        # mid points:
        sx = self.last_x
        sy = top + (slot_height / 2)
        mx = ulx + (brx - ulx)/2
        fx = mx + canvas.scale_factor*dlymin
        fy = sy
        tilt = self.settings.waveform["tilt"]
        # Draw polygon:
        canvas.create_polygon(
            sx,sy,
            sx+tilt, sy+(slot_height/2),
            fx-tilt, sy+(slot_height/2),
            fx,fy,
            fx-tilt, sy-(slot_height/2),
            sx+tilt, sy-(slot_height/2),
            tags=(self.uidtag(),self.name+tag, self.name+"_waveform",),
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
        return

    def _draw_data_close(self, canvas: tk.Canvas,  top: int, edge : str):
        self._draw_generic_close(canvas,top,edge,"_valid")
        
    def _draw_hiz_open(self, canvas: tk.Canvas,  top: int, edge : str):
        # Special case when edge is 0.
        slot_height = int(self.amplitude)
        if edge == "0":
            self.last_x = self.wfstarts_x
            return
        eitem = self._get_edge_item(canvas, edge)
        (ulx, uly, brx, bry) = canvas.bbox(eitem)
        (dlymax, dlymin) = self._get_output_delays(canvas, eitem)
        # mid points:
        mx = ulx + (brx - ulx)/2
        sx = mx + canvas.scale_factor*dlymin
        sy = top + (slot_height / 2)
        fx = mx + canvas.scale_factor*dlymax
        fy = sy
        tilt = self.settings.waveform["tilt"]
        # Draw polygon:
        canvas.create_polygon(
            sx,sy,
            sx+tilt, sy+(slot_height/2),
            fx-tilt, sy+(slot_height/2),
            fx,fy,
            fx-tilt, sy-(slot_height/2),
            sx+tilt, sy-(slot_height/2),
            tags=(self.uidtag(),self.name+"_transition", self.name+"_waveform",),
        )
        
        self.last_x = fx
        return
    

    def _draw_hiz_close(self, canvas: tk.Canvas,  top: int, edge : str):
        slot_height = int(self.amplitude)
        # Default is waveform close ...
        (ulx, uly, brx, bry) = (self.wfends_x,top,self.wfends_x,top)
        (dlymax, dlymin) = (0,0)
        if edge!="": # If not closing end of waveform...
            eitem = self._get_edge_item(canvas, edge)
            (ulx, uly, brx, bry) = canvas.bbox(eitem)
            (dlymax, dlymin) = self._get_output_delays(canvas, eitem)
        # mid points:
        sx = self.last_x
        sy = top + (slot_height / 2)
        mx = ulx + (brx - ulx)/2
        fx = mx + canvas.scale_factor*dlymin
        fy = sy
        # Draw polygon:
        canvas.create_line(
            sx,sy,
            fx,fy,
            tags=(self.uidtag(),self.name+"_hizvalid",self.name+"_waveform",),
        )

        return

    def _draw_high_open(self, canvas: tk.Canvas,  top: int, edge : str):
        # Special case when edge is 0.
        slot_height = int(self.amplitude)
        if edge == "0":
            self.last_x = self.wfstarts_x
            return
        eitem = self._get_edge_item(canvas, edge)
        (ulx, uly, brx, bry) = canvas.bbox(eitem)
        (dlymax, dlymin) = self._get_output_delays(canvas, eitem)
        # mid points:
        tilt = self.settings.waveform["tilt"]
        mx = ulx + (brx - ulx)/2
        sx = mx + canvas.scale_factor*dlymin - tilt
        sy = top + slot_height
        fx = mx + canvas.scale_factor*dlymax - tilt
        fy = sy
        # Draw polygon:
        canvas.create_polygon(
            sx,sy,
            sx+2*tilt, sy-slot_height,
            fx+2*tilt, sy-slot_height,
            fx,fy,
            tags=(self.uidtag(),self.name+"_transition",self.name+"_waveform",),
        )
        self.last_x = fx + tilt
        return

    def _draw_high_close(self, canvas: tk.Canvas,  top: int, edge : str):
        slot_height = int(self.amplitude)
        # Default is waveform close ...
        (ulx, uly, brx, bry) = (self.wfends_x,top,self.wfends_x,top)
        (dlymax, dlymin) = (0,0)
        if edge!="": # If not closing end of waveform...
            eitem = self._get_edge_item(canvas, edge)
            (ulx, uly, brx, bry) = canvas.bbox(eitem)
            (dlymax, dlymin) = self._get_output_delays(canvas, eitem)
        # mid points:
        tilt = self.settings.waveform["tilt"]
        sx = self.last_x - tilt
        sy = top + slot_height
        mx = ulx + (brx - ulx)/2
        fx = mx + canvas.scale_factor*dlymin
        fy = sy - (slot_height/2)
        # Draw line:
        canvas.create_line(
            sx,sy,
            sx+2*tilt,sy-slot_height,
            fx-tilt,sy-slot_height,
            fx,fy,
            tags=(self.uidtag(),self.name+"_highvalid",self.name+"_waveform",),
        )
        
        if self.last_x == self.wfstarts_x:
            bgcolor = canvas.cget("background")
            canvas.create_line(sx,sy,
                               sx+2*tilt,sy-slot_height,
                               fill=bgcolor,
                               width=self.lwidth+2,
                               tags=(self.uidtag(),self.name+"_waveform",),
                               )
        if edge=="":
            bgcolor = canvas.cget("background")
            canvas.create_line( fx-tilt,sy-slot_height,
                                fx,fy,
                                fill=bgcolor,
                                width=self.lwidth+2,
                                tags=(self.uidtag(),self.name+"_waveform",),
                               )
        return        

    def _draw_low_open(self, canvas: tk.Canvas,  top: int, edge : str):
        # Special case when edge is 0.
        slot_height = int(self.amplitude)
        if edge == "0":
            self.last_x = self.wfstarts_x
            return
        eitem = self._get_edge_item(canvas, edge)
        (ulx, uly, brx, bry) = canvas.bbox(eitem)
        (dlymax, dlymin) = self._get_output_delays(canvas, eitem)
        # mid points:
        tilt = self.settings.waveform["tilt"]
        mx = ulx + (brx - ulx)/2
        sx = mx + canvas.scale_factor*dlymin - tilt
        sy = top 
        fx = mx + canvas.scale_factor*dlymax - tilt
        fy = sy
        # Draw polygon:
        canvas.create_polygon(
            sx,sy,
            sx+2*tilt, sy+slot_height,
            fx+2*tilt, sy+slot_height,
            fx,fy,
            tags=(self.uidtag(),self.name+"_transition",self.name+"_waveform",),
        )
        
        self.last_x = fx + tilt
        return       

    def _draw_low_close(self, canvas: tk.Canvas,  top: int, edge : str):
        slot_height = int(self.amplitude)
        # Default is waveform close ...
        (ulx, uly, brx, bry) = (self.wfends_x,top,self.wfends_x,top)
        (dlymax, dlymin) = (0,0)
        if edge!="": # If not closing end of waveform...
            eitem = self._get_edge_item(canvas, edge)
            (ulx, uly, brx, bry) = canvas.bbox(eitem)
            (dlymax, dlymin) = self._get_output_delays(canvas, eitem)
        # mid points:
        tilt = self.settings.waveform["tilt"]
        sx = self.last_x - tilt
        sy = top 
        mx = ulx + (brx - ulx)/2
        fx = mx + canvas.scale_factor*dlymin
        fy = sy + (slot_height/2)
        # Draw polygon:
        canvas.create_line(
            sx,sy,
            sx+2*tilt,sy+slot_height,
            fx-tilt,sy+slot_height,
            fx,fy,
            tags=(self.uidtag(),self.name+"_lowvalid",self.name+"_waveform",),
        )
        
        if self.last_x == self.wfstarts_x:
            bgcolor = canvas.cget("background")
            canvas.create_line(sx,sy,
                               sx+2*tilt,sy+slot_height,
                               fill=bgcolor,
                               width=self.lwidth+2,
                               tags=(self.uidtag(),self.name+"_waveform",),
                               )
        if edge=="":
            bgcolor = canvas.cget("background")
            canvas.create_line(fx-tilt,sy+slot_height,
                               fx,fy,
                               fill=bgcolor,
                               width=self.lwidth+2,
                               tags=(self.uidtag(),self.name+"_waveform",),
                               )
        return        

    def _draw_unknown_open(self, canvas: tk.Canvas,  top: int, edge : str):
        self._draw_data_open(canvas,top,edge)
        return
        
    def _draw_unknown_close(self, canvas: tk.Canvas,  top: int, edge : str):
        self._draw_generic_close(canvas,top,edge,"_unknown")
        return
