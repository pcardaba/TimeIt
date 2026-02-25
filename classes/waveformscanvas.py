import tkinter as tk

from .settings import Settings
from .timings import Timings
from .signal import Signal
from .clocksignaldlg import ClockSignalDlg
from .inputsignaldlg import InputSignalDlg
from .outputsignaldlg import OutputSignalDlg
from .timingmarker import TimingMarker
from .timingmarkerdlg import TimingMarkerDlg
import os

class WaveformsCanvas(tk.Canvas):
    """Canvas with Shift + MouseWheel horizontal zoom anchored at x = 0."""

    SHIFT_MASK = 0x0001
    CTRL_MASK = 0x0004 
    
    def __init__(self, master=None, *, topapp, zoom_step: float = 1.15, **kwargs):
        super().__init__(master, **kwargs)
        self.topapp = topapp
        self.settings = self.topapp.settings
        self.timings = self.topapp.timings
        self.signals = self.topapp.signals
        self.signal_related = {}
        self.hidden_signals = []
        self._current_tags = None
        self.zoom_step = float(zoom_step)
        ## The key is the uid_* item tag selected. Selection type.
        self.selected = {}
        # selection mode: "full" | "middle" | "start" | "end"
        self.selection_mode_tkvar = tk.StringVar(value="full")
        self.marker_style_tkvar = tk.StringVar(value="inner_both") 
        self.markers = {}
        if self.zoom_step <= 1.0:
            raise ValueError("zoom_step must be > 1.0")
        
        self.scale_factor: float = 1.0
        self.is_scaled = False
        self.is_virtual = False
        
        self.ctxmenu: tk.Menu | None = None        
        self._build_canvas_context_menu()
        
        # Windows / macOS
        self.bind("<MouseWheel>", self._on_mousewheel)
        # Linux / X11
        self.bind("<Button-4>", lambda e: self._on_linux_wheel(e, +1))
        self.bind("<Button-5>", lambda e: self._on_linux_wheel(e, -1))

        self.bind("<Button-1>", self._on_click)
        
        # self.bind("<Button-3>", self._show_canvas_context_menu)
        self.bind('<Button-3>', self._show_canvas_context_menu)
        
    def _on_click(self, event) -> None:
        # In the “nearby” hits (tolerance)
        x = self.canvasx(event.x)
        y = self.canvasy(event.y)
        r = self.settings.selection["click_tolerance"]
        items = self.find_overlapping(x-r, y-r, x+r, y+r)
        if not (event.state & self.CTRL_MASK):
            self.delete("selection_bbox")
            self.selected = {}
            self.dtag("selected", "selected")
            
        for item_id in items:
            tags = self.gettags(item_id)
            if "selection_bbox" in tags:
                continue # selection bbox are not clickable...
            uid = next((t for t in tags if t.startswith("uid_")), None)
            if uid is None:
                continue
            if "selected" in tags:
                self.dtag(item_id, "selected") # Tag item_id as selected
                self.delete(uid+"_bbox") # erase selection bbox
                self.selected.pop(uid)  # remove entry in selected dict 
            else:
                self.addtag_withtag("selected", item_id) # Tag new selected item
                self.selected[uid] = self.selection_mode_tkvar.get()
                self.draw_selection_bbox(uid) # Draw selected bbox only
                
            
    def _on_mousewheel(self, event):
        if event.state & self.SHIFT_MASK:
            direction = 1 if event.delta > 0 else -1
            return self._zoom_x(direction)
        return None # let Tk handle it

    def _on_linux_wheel(self, event, direction: int):
        if event.state & self.SHIFT_MASK:
            return self._zoom_x(direction)
        return None
    
    def _zoom_x(self, direction: int):
        factor = self.zoom_step if direction > 0 else 1.0 / self.zoom_step
        self.scale_factor *= factor

        # preserve current view (fraction of scrollregion)
        x0, _ = self.xview()

        self.redraw() # deletes all + recreates using scale_factor
        self.update_scrollregion()

        # restore view position
        self.xview_moveto(x0)
        
        return "break"

    def _create_new_signal(self, stype: str) -> None:
        if stype == "clock":
            ClockSignalDlg(self.topapp)
        elif stype == "input":
            InputSignalDlg(self.topapp)
        elif stype == "output":
            OutputSignalDlg(self.topapp)
        else:
            raise ValueError(f"Unknown signal type: {stype!r}")
            
    def _build_canvas_context_menu(self) -> None:
        self.ctxmenu = tk.Menu(self, tearoff=False)
        # New Signal submenu
        new_menu = tk.Menu(self.ctxmenu, tearoff=False)
        self.ctxmenu.add_cascade(label="New Signal", menu=new_menu)
        new_menu.add_command(label="Clock...", command=lambda: self._create_new_signal("clock"))
        new_menu.add_command(label="Input...", command=lambda: self._create_new_signal("input"))
        new_menu.add_command(label="Output...", command=lambda: self._create_new_signal("output"))
        # -- HERE !!!
        self.ctxmenu.add_command(label="Edit Signal", state="disabled",
                                 command=lambda: self._edit_signal())
        self.ctxmenu.add_command(label="Delete Signal", state="disabled",
                                 command=lambda: self._delete_signal())
        self._hidden_menu = tk.Menu(self.ctxmenu, tearoff=False)
        self.ctxmenu.add_cascade(label="Hidden Signals", state="disabled",
                                 menu=self._hidden_menu)
        
        self.ctxmenu.add_separator()
        # Selection mode
        sel_mode_menu = self._build_selection_mode_menu(self.ctxmenu)
        self.ctxmenu.add_cascade(label="Selection Mode", menu=sel_mode_menu)
        # Selection Time it
        self.ctxmenu.add_command(label="Time it", state="disabled",
                                 command=lambda: self.create_timing_marker())
        # Timing marker style
        mark_style_menu = self._build_marker_style_menu(self.ctxmenu)
        self.ctxmenu.add_cascade(label="Timing Marker", menu=mark_style_menu)
        mark_style_menu.add_separator()
        mark_style_menu.add_command(label="Delete", command=self._delete_marker)
        
    def _show_canvas_context_menu(self,event) -> None:
        if self.ctxmenu is None:
            return
        tags = self.gettags("current")
        self._current_tags = tags
        if "tmarkers" in tags:
            self.ctxmenu.entryconfig("Timing Marker", state="normal")
            for t in tags:
                if t.startswith("tmarker_uid_"):
                    self.markers["current"] = self.markers[t] 
                    self.marker_style_tkvar.set(self.markers[t].style)
                    break
        elif "wf_labels" in tags:
            self.ctxmenu.entryconfig("Edit Signal", state="normal")
            self.ctxmenu.entryconfig("Delete Signal", state="normal")
            self.ctxmenu.entryconfig("Timing Marker", state="disabled")
        else:
            self.ctxmenu.entryconfig("Timing Marker", state="disabled")
            self.ctxmenu.entryconfig("Edit Signal", state="disable")
            self.ctxmenu.entryconfig("Delete Signal", state="disable")
            
        if len(self.selected) >= 2:
            self.ctxmenu.entryconfig("Time it", state="normal")
        else:
            self.ctxmenu.entryconfig("Time it", state="disabled")
            
        self.ctxmenu.tk_popup(event.x_root, event.y_root)
     
    def update_scrollregion(self):
        self.update_idletasks()
        bbox = self.bbox("all")
        if not bbox:
            self.configure(scrollregion=(0, 0, 0, 0))
            return

        _, _, x2, y2 = bbox
        # Clamp to non-negative
        self.configure(scrollregion=(0, 0, max(0, x2), max(0, y2)))

    # ------------------------------------------------------------------
    # Context menus
    # ------------------------------------------------------------------
    def _build_selection_mode_menu(self, parent: tk.Menu) -> tk.Menu:
        mode_menu = tk.Menu(parent, tearoff=False)

        mode_menu.add_radiobutton(
            label="Full",
            variable=self.selection_mode_tkvar,
            value="full",
        )
        mode_menu.add_radiobutton(
            label="Start of",
            variable=self.selection_mode_tkvar,
            value="start",
        )
        mode_menu.add_radiobutton(
            label="Middle of",
            variable=self.selection_mode_tkvar,
            value="middle",
        )
        mode_menu.add_radiobutton(
            label="End of",
            variable=self.selection_mode_tkvar,
            value="end",
        )
        return mode_menu

    def _build_marker_style_menu(self, parent: tk.Menu) -> tk.Menu:
        style_menu = tk.Menu(parent, tearoff=False)

        src_dir = os.path.dirname(os.path.abspath(__file__))
        base_path = os.path.join(src_dir, "../data")
        
        inner_both_img = tk.PhotoImage(file=base_path+"/tmarker_inner_both.png"),
        style_menu.img1 = inner_both_img
        inner_right_img = tk.PhotoImage(file=base_path+"/tmarker_inner_right.png"),
        style_menu.img2 = inner_right_img
        inner_left_img = tk.PhotoImage(file=base_path+"/tmarker_inner_left.png"),
        style_menu.img3 = inner_left_img
        outer_img = tk.PhotoImage(file=base_path+"/tmarker_outer.png"),
        style_menu.img4 = outer_img
        
        style_menu.add_radiobutton(
            image=style_menu.img1,
            variable=self.marker_style_tkvar,
            value="inner_both",
            command=self._update_marker_style,
        )
        style_menu.add_radiobutton(
            image=style_menu.img2,
            variable=self.marker_style_tkvar,
            value="inner_right",
            command=self._update_marker_style,
        )
        style_menu.add_radiobutton(
            image=style_menu.img3,
            variable=self.marker_style_tkvar,
            value="inner_left",
            command=self._update_marker_style,
        )
        style_menu.add_radiobutton(
            image=style_menu.img4,
            variable=self.marker_style_tkvar,
            value="outer",
            command=self._update_marker_style,
        )

        return style_menu

    
    def _update_marker_style(self) -> None:
        self.markers["current"].style = self.marker_style_tkvar.get()
        self.markers["current"].redraw()
        
    def _set_signal_visible(self, signame):
        sig = self.signals.find(signame)
        sig.visible = True
        menu = self._hidden_menu
        for i in range(menu.index("end") + 1):
            if menu.entrycget(i, "label") == signame:
                menu.delete(i)
                self.hidden_signals.remove(signame)
                if len(self.hidden_signals) == 0:
                    self.ctxmenu.entryconfig("Hidden Signals", state="disabled")
            break
        self.redraw()
        
    def draw_signals(self) -> None:
        
        self.delete("all")
        top = self.settings.waveform["top_padding"]
        todelete = []
        for sig in self.signals.values():
            incr = sig.draw(self, top)
            if incr < 0:
                todelete.append(sig)
                continue
            top += incr
            if getattr(sig, "visible"):
                top += self.settings.waveform["interslot"]
            else:
                if sig.name not in self.hidden_signals:
                    self.hidden_signals.append(sig.name)
                    self._hidden_menu.add_command(label=sig.name,
                                                  command=lambda name=sig.name:
                                                  self._set_signal_visible(name),
                                                  )
                    self.ctxmenu.entryconfig("Hidden Signals", state="normal")
        for sig in todelete:
            self._delete_signal(sig)
              

    def draw_selection_bbox(self, uid="") -> None:
        # redraw deletes all. I need a way to recover
        # selections.
        if uid != "":
            mode = self.selected[uid]
            bbox = self.bbox(uid)
            if mode == "start":
                bbox = (bbox[0], bbox[1],
                        bbox[0]+2*self.settings.waveform["tilt"],bbox[3])
            elif mode == "end":
                bbox = (bbox[2]-2*self.settings.waveform["tilt"], bbox[1],
                        bbox[2],bbox[3])
            elif mode == "middle":
                midx = (bbox[2]-bbox[0])//2+bbox[0]
                bbox = (midx-self.settings.waveform["tilt"], bbox[1],
                        midx+self.settings.waveform["tilt"], bbox[3])

            color = self.settings.selection["to_color"]
            if list(self.selected).index(uid) == 0:
                color = self.settings.selection["from_color"]
            
            self.create_rectangle(
                bbox,
                outline=color,
                dash=self.settings.selection["dash"],
                width=self.settings.selection["lwidth"],
                tags=(uid+"_bbox","selection_bbox",mode,)
            )
            return
        ## ---
        self.delete("selection_bbox") # erase all bboxes
        for item_uid in self.selected:
            self.draw_selection_bbox(item_uid)
        
            
    def redraw(self) -> None:
        self.draw_signals()
        self.draw_selection_bbox()
        for uid, marker in self.markers.items():
            if uid != "current":
                # Ensure from/to signals are visible...
                from_signal = self.signals.find_by_uid(marker.from_uid.split("_")[1])
                to_signal = self.signals.find_by_uid(marker.to_uid.split("_")[1])
                if from_signal.visible and to_signal.visible:
                    self.markers[uid].draw(self)

    def add_timing_marker(self, marker):
        ## Add the marker to the from/to signal related objects.
        ## Remember signal uid tag is : uid_<signalid>_<elementid>
        for u in (marker.from_uid, marker.to_uid):
            self.signals.find_by_uid(u.split("_")[1]).add_related_obj(marker)
        marker.set_canvas(self)
        marker.set_vcanvas(self.topapp.vcanvas)
        marker.draw(self)
        self.markers["tmarker_uid_"+marker.get_uid()] = marker
        
    def create_timing_marker(self, marker=None):
        if marker is not None:
            self.add_timing_marker(marker)
            return
        first_uid = None
        first_mode = ""
        for uid, mode in self.selected.items():
            if first_uid is None:
                first_uid = uid
                first_mode = mode
                continue
            marker = TimingMarker(name="",
                                  from_uid=first_uid,
                                  from_at=first_mode,
                                  to_uid=uid,
                                  to_at=mode)
            
            self.add_timing_marker(marker)
            
    def _get_current_tags(self):
        # Linux and Windows behave in different way w.r.t. to 
        # dynamic tag "current" in Windows the item tagged
        # as "current" is only pressent on the event handler.
        # If you call a method in the handler the tag will be lost.
        # Therefore we keep the "current" tags in a variable
        return self._current_tags
    
    def _get_current_signal(self):
        # See _get_currnt_tags() comments
        tags = self._get_current_tags()
        signame = ""
        for t in tags:
            if t.endswith("_label"):
                signame = t.removesuffix("_label")
                break
            if t.endswith("_waveform"):
                signame = t.removesuffix("_waveform")
                break
        if signame != "": 
            signal = self.signals.find(signame)
            return signal

        return None        
    
    def _delete_marker(self):
        ## When deleting a marker, the marker shall also be removed
        ## from the concerned signal related objects. TODO. 
        tags = self._get_current_tags()
        for t in tags:
            if t.startswith("tmarker_uid_"):
                self.delete(t)
                self.markers.pop("current")
                ## Need to update signal related object.
                marker = self.markers[t]
                for u in (marker.from_uid, marker.to_uid):
                    self.signals.find_by_uid(u.split("_")[1]).remove_related_obj(marker)
                self.markers.pop(t)
                break
    
    def _edit_signal(self):
        signal = self._get_current_signal()
        ## Remove all selected.
        prefix = f"uid_{signal.uid}_"
        keys_to_remove = [k for k in self.selected if k.startswith(prefix)]
        for k in keys_to_remove:
            del self.selected[k]
        if signal.type == "clock":
            ClockSignalDlg(self.topapp, signal)
        elif signal.type == "input":
            InputSignalDlg(self.topapp, signal)
        elif signal.type == "output":
            OutputSignalDlg(self.topapp, signal)
        
    def _delete_signal(self, signal=None):
        ## When deleting a signal, all related objects must be
        ## also removed. TODO
        if signal is None:
            signal = self._get_current_signal()
        ## Remove any selected items from the signal to be removed.
        prefix = f"uid_{signal.uid}_"
        keys_to_remove = [k for k in self.selected if k.startswith(prefix)]
        for k in keys_to_remove:
            del self.selected[k]
        # Remove related objects...    
        relobjs = signal.get_related_objs()
        for obj in relobjs:
            if obj.type == "tmarker":
                self.markers.pop("tmarker_uid_"+obj.get_uid(), None)
            else:
                ## Other possible object is a signal.
                self._delete_signal(obj)

        if signal.name in self.hidden_signals:
            menu = self._hidden_menu
            for i in range(menu.index("end") + 1):
                if menu.entrycget(i, "label") == signal.name:
                    menu.delete(i)
                    self.hidden_signals.remove(signal.name)
                    if len(self.hidden_signals) == 0:
                        self.ctxmenu.entryconfig("Hidden Signals", state="disabled")
                    break
                
        self.signals.remove(signal.name)
        self.topapp.redraw()

    def write_script(self, fileref):
        self.settings.write(fileref)
        self.timings.write(fileref)
        for sig in self.signals.values():
            sig.write(fileref)
        for mkr in self.markers.values():
            mkr.write(fileref)
        fileref.write("\n\n# --- End of generated script. ---\n\n")
        return
