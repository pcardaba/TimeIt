import tkinter as tk
from tkinter import ttk
from .settings import Settings

class TimingMarker:
    # Static data
    static_id = 0
    interp = tk.Tcl()
    def __init__(self, name="", from_uid=None, from_at="", to_uid=None, to_at=""):
        self.settings  = None
        self.name      = name
        self.type      = "tmarker"
        self.from_uid  = from_uid # From waveform element
        self.from_at   = from_at
        self.to_uid    = to_uid # To waveform element
        self.to_at     = to_at
        self.arrow     = "both"
        # inner: |<--->|  outer: ->|   |<- 
        self.style     = "inner_both"
        self.visible   = True
        self.x_from    = 0 # This is start point of the element
        self.y_from    = 0 # 
        self.y         = -100 # timing markers are horizontal: same y.
        self.x_to      = 0 # This is the end point of the element.
        self.y_to      = 0
        self.label_relx = 0 # Relative to center x
        self.label_rely = 0 # Relative to center y
        self.timing    = 0.0
        self._canvas    = None
        self._vcanvas   = None # Virtual canvas for true timing measures
        self._dragging  = False
        self._last_y    = 0
        self._last_x    = 0
        self._tag_pressed = ""
        self._label_item = None
        self.uid       = TimingMarker.static_id
        TimingMarker.static_id += 1

        
    def uidtag(self) -> str:
        uidtag = "uid_"+str(self.uid)
        return uidtag

    def write(self, fileref):
        fileref.write(f"\ncreate_timing_marker -name {{{self.name}}}  \\\n")
        fileref.write(f"   -from {self.from_at}:{self.from_uid}  \\\n")
        fileref.write(f"   -to {self.to_at}:{self.to_uid}  \\\n")
        fileref.write(f"   -at {self.y}  \\\n")
        fileref.write(f"   -style {self.style}  \\\n")
        fileref.write(f"   -label_x {self.label_relx}  \\\n")
        fileref.write(f"   -label_y {self.label_rely} \n")
        
    def _on_press_mark(self, event):
        self._tag_pressed = "tmarker_marklb_"+self.uidtag()
        self._on_press(event)

    def _on_press_label(self, event):
        self._tag_pressed = "tmarker_label_"+self.uidtag()
        self._on_press(event)
        
    def _on_press(self, event):
        self._dragging = True
        self._last_y = event.y
        self._last_x = event.x
        self._canvas.itemconfig(self._tag_pressed,
                                fill=self.settings.marker["drag_color"])

    def _on_drag(self, event):
        if not self._dragging:
            return
        dy = event.y - self._last_y
        dx = event.x - self._last_x
        if not self._tag_pressed.startswith("tmarker_label_"):
            dx = 0
        else:
            self.label_rely += dy
            self.label_relx += dx
        self._canvas.move(self._tag_pressed, dx, dy)   # x locked
        self._last_y = event.y
        self._last_x = event.x

    def _on_release(self, event):
        if not self._tag_pressed.startswith("tmarker_label_"):
            self.y = self._last_y
            self.redraw()
        else:
            self._canvas.itemconfig(self._tag_pressed,
                                    fill=self.settings.marker["color"])
        self._dragging = False
        
    def _bind_events(self):
        tag = "tmarker_mark_"+self.uidtag()
        self._canvas.tag_bind(tag, "<ButtonPress-1>", self._on_press_mark)
        self._canvas.tag_bind(tag, "<B1-Motion>", self._on_drag)
        self._canvas.tag_bind(tag, "<ButtonRelease-1>", self._on_release)
        tag = "tmarker_label_"+self.uidtag()
        self._canvas.tag_bind(tag, "<Double-Button-1>", self._label_edit)
        self._canvas.tag_bind(tag, "<ButtonPress-1>", self._on_press_label)
        self._canvas.tag_bind(tag, "<B1-Motion>", self._on_drag)
        self._canvas.tag_bind(tag, "<ButtonRelease-1>", self._on_release)

    def get_leg_coord(self,canvas, uid, at):
        (ulx, uly, brx, bry)= canvas.bbox(uid)
        if at == "start":
            x = ulx
            y = (bry - uly)//2 + uly
        elif at == "end":
            x = brx
            y = (bry - uly)//2 + uly
        else:
            x = (brx - ulx)//2 + ulx
            y = (bry - uly)//2 + uly
            
        return (x, y)
            
    def draw(self, canvas: tk.Canvas):
        self.settings = canvas.settings
 
        # Get initial coords
        (self.x_from, self.y_from) = self.get_leg_coord(canvas, self.from_uid, self.from_at)
        (self.x_to, self.y_to) = self.get_leg_coord(canvas, self.to_uid, self.to_at)
        
        if self.y<-99: # First entry need to compute first default Y.    
            self.y = abs(self.y_to - self.y_from)//2
            self.y += min(self.y_from, self.y_to)

        # Timing measures come from virtual canvas.
        (vx_from, _) = self.get_leg_coord(self._vcanvas, self.from_uid, self.from_at)
        (vx_to, _) = self.get_leg_coord(self._vcanvas, self.to_uid, self.to_at)
        self.timing = float(vx_to - vx_from)/self._vcanvas.scale_factor

        tail_size = self.settings.marker["leg_tail"]
        ## Legs:
        tail = tail_size if self.y > self.y_from else -tail_size
        canvas.create_line(self.x_from, self.y_from,
                           self.x_from, self.y+tail,
                           fill=self.settings.marker["color"],
                           width=self.settings.marker["lwidth"],
                           tags=("tmarker_"+self.uidtag(), "tmarker_lleg_"+self.uidtag(), 
                                 "tmarkers","tmarkers_legs",))
        tail = tail_size if self.y > self.y_to else -tail_size
        canvas.create_line(self.x_to, self.y_to,
                           self.x_to, self.y+tail,
                           fill=self.settings.marker["color"],
                           width=self.settings.marker["lwidth"],
                           tags=("tmarker_"+self.uidtag(), "tmarker_rleg_"+self.uidtag(), 
                                 "tmarkers","tmarkers_legs",))
        ## Mark
        mark_tags = ("tmarker_"+self.uidtag(),
                     "tmarker_mark_"+self.uidtag(),
                     "tmarker_marklb_"+self.uidtag(), # mark and label
                     "tmarkers","tmarkers_mark",)
        
        self.arrow = (
            "first" if self.style == "inner_left"
            else "last" if self.style == "inner_right"
            else "both"
        )
        
        if self.style.startswith("inner_"):
            canvas.create_line(self.x_from, self.y,
                               self.x_to, self.y,
                               fill=self.settings.marker["color"],
                               width=self.settings.marker["lwidth"],
                               arrow=self.arrow,
                               arrowshape=self.settings.marker["arrow_shape"],
                               tags=mark_tags)
        else:
            outlength = self.settings.marker["outer_length"]
            canvas.create_line(self.x_from-outlength, self.y,
                               self.x_from, self.y,
                               fill=self.settings.marker["color"],
                               width=self.settings.marker["lwidth"],
                               arrow="last",
                               arrowshape=self.settings.marker["arrow_shape"],
                               tags=mark_tags)
            canvas.create_line(self.x_to+outlength, self.y,
                               self.x_to, self.y,
                               fill=self.settings.marker["color"],
                               width=self.settings.marker["lwidth"],
                               arrow="last",
                               arrowshape=self.settings.marker["arrow_shape"],
                               tags=mark_tags)
            
            
        ## Label/name
        mark_label =  format(self.timing, self.settings.marker["float_format"])
        mark_label += self.settings.waveform["tunits"]
        if self.name != "":
            mark_label = self.name
        self._label_item = canvas.create_text(
            ((self.x_from + self.x_to)//2) + self.label_relx,
            (self.y - 2) + self.label_rely,
            text=mark_label,
            font=self.settings.get_font(self.settings.marker["font"]),
            anchor=tk.S,   # text bottom aligned to that y
            tags=("tmarker_"+self.uidtag(),
                  "tmarker_label_"+self.uidtag(),
                  "tmarker_marklb_"+self.uidtag(), # mark and label
                  "tmarkers","tmarkers_label",))

    def redraw(self):
        tag = "tmarker_"+self.uidtag()
        self._canvas.delete(tag)
        self.draw(self._canvas)

    def set_canvas(self, canvas):
        self._canvas = canvas
        self._bind_events()
        
    def set_vcanvas(self, vcanvas):
        self._vcanvas = vcanvas

    def get_uid(self):
        return str(self.uid)

    def _label_edit(self, event):
        self._editing_item = self._label_item
        item = self._label_item
        # Get current text
        current_text = self._canvas.itemcget(item, "text")

        # Where is the item on the canvas?
        x, y = self._canvas.coords(item)  # text anchor position

        self._editor = ttk.Entry(self._canvas)
        self._editor.bind("<Return>", self._commit_edit)
        self._editor.bind("<Escape>", self._cancel_edit)
        self._editor.bind("<FocusOut>", self._commit_edit)

        # Put text in entry
        self._editor.delete(0, tk.END)
        self._editor.insert(0, current_text)

        # Place the Entry over the text item
        # Use bbox to size/position more accurately
        bbox = self._canvas.bbox(item)  # (x1, y1, x2, y2)
        if bbox:
            x1, y1, x2, y2 = bbox
            width = max(40, x2 - x1 + 10)
            height = max(18, y2 - y1 + 6)
            self._editor.place(x=x1, y=y1, width=width, height=height)
        else:
            # Fallback if bbox is None for some reason
            self._editor.place(x=x, y=y)

        self._editor.focus_set()
        self._editor.selection_range(0, tk.END)

    def _commit_edit(self, event=None):
        if self._editor is None or self._editing_item is None:
            return

        new_text = self._editor.get()
        self._canvas.itemconfigure(self._editing_item, text=new_text)
        self.name = new_text
        self.update_timings_dict()
        self._editor.destroy()
        self.redraw()
        # self._editor.place_forget()
        # self._editing_item = None

    def _cancel_edit(self, event=None):
        self._editor.destroy()
        # if self._editor is None:
        #    return
        # self._editor.place_forget()
        # self._editing_item = None

    def update_timings_dict(self):
        if self.name != "":
            mark_label =  format(self.timing, self.settings.marker["float_format"])
            mark_label += self.settings.waveform["tunits"]
            self.settings.marker["timings"][self.name] = mark_label
        
