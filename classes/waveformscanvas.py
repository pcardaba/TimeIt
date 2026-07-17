from __future__ import annotations

import tkinter as tk
from tkinter import messagebox

from pathlib import Path

from .clocksignaldlg import ClockSignalDlg
from .inputsignaldlg import InputSignalDlg
from .outputsignaldlg import OutputSignalDlg
from .timingmarker import TimingMarker
from .timingmarkerdlg import TimingMarkerDlg
from .gridsettingsdlg import GridSettingsDlg
from .grid import Grid
from .waveformsplit import WaveformSplit
from .waveformannotationdlg import WaveformAnnotationDlg

class WaveformsCanvas(tk.Canvas):
    """Waveform canvas with selection, context menu, and horizontal zoom.

    Notes:
    - Shift + MouseWheel performs horizontal zoom anchored at x=0.
    - Selection uses an item tag prefix "uid_..." to group signal elements.
    """

    SHIFT_MASK = 0x0001
    CTRL_MASK = 0x0004


    def __init__( self, master: tk.Frame = None, *,
                  topapp: TimeItApp, zoom_step: float = 1.15,
                  **kwargs,) -> None:
        super().__init__(master, **kwargs)

        if zoom_step <= 1.0:
            raise ValueError("zoom_step must be > 1.0")

        self.topapp = topapp

        self.hidden_signals: set[str] = set()
        self.zoom_step = float(zoom_step)

        # key: uid_* tag, value: selection mode ("full"|"start"|"middle"|"end")
        self.selected: list[str] = []

        self._sel_mode_tkvar = tk.StringVar(value="full")
        self._marker_style_tkvar = tk.StringVar(value="inner_both")
        self._marker_anchor_tkvar = tk.StringVar(value="none")

        # References into the Timing Marker submenu for dynamic label updates
        self._mark_menu: tk.Menu | None = None
        self._anchor_from_idx: int = 0
        self._anchor_to_idx: int = 0

        # key: "tmarker_uid_<uid>" (and transient key "current"),
        # value: TimingMarker
        self.markers: dict[str, TimingMarker] = {}
        # key: uid (int), value: WaveformSplit
        self.splits: dict[int, WaveformSplit] = {}
        self.wfgrid = Grid(self.settings, self.signals)
        self.scale_factor: float = 1.0
        self.is_scaled = False
        self.is_virtual = False

        self._ctxmenu: tk.Menu | None = None
        self._hidden_menu: tk.Menu | None = None
        self._current_tags: tuple[str, ...] | None = None
        self._marker_under_edition = None
        self._click_counter = 0
        self._rclick_x = 0
        
        self.configure(yscrollincrement=20)

        self._build_canvas_context_menu()

        # Windows / macOS
        self.bind("<MouseWheel>", self._on_mousewheel)
        # Linux / X11
        self.bind("<Button-4>", lambda e: self._on_linux_wheel(e, +1))
        self.bind("<Button-5>", lambda e: self._on_linux_wheel(e, -1))

        self.bind("<Button-1>", self._on_click)
        self.bind("<Button-3>", self._show_canvas_context_menu)
        self.bind("<Double-Button-1>", self._on_double_click)

        self.bind("<ButtonPress-1>", self._end_any_marker_edit, add="+")

    @property
    def settings(self): 
        return self.topapp.settings

    @property
    def timings(self):
        return self.topapp.timings

    @property
    def signals(self):
        return self.topapp.signals

    def time_to_x(self, t: float) -> float:
        """Convert a waveform time value to a canvas x coordinate."""
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

    # ------------------------------------------------------------------
    # Private methods
    # ------------------------------------------------------------------
    def _on_click(self, event: tk.Event) -> None:
        # Nearby hit-test using a tolerance radius
        self._click_counter += 1
        x = self.canvasx(event.x)
        y = self.canvasy(event.y)
        tol = self.settings.selection["click_tolerance"]

        items = self.find_overlapping(x - tol, y - tol, x + tol, y + tol)
        nitm = len(items)
        sitm = 0
        if nitm > 1:
            sitm = self._click_counter % nitm
        item_id = items[sitm] if nitm > 0 else None
        
        # Clear selection unless Ctrl is held
        if not (event.state & self.CTRL_MASK):
            self.delete("selection_bbox")
            self.selected.clear()
            self.dtag("selected", "selected")

        if item_id is None:
            return
        # for item_id in items:
        tags = self.gettags(item_id)

        if "selection_bbox" in tags:
            # selection bbox are not clickable
            return

        uid = next((t for t in tags if t.startswith("uid_")), None)
        if uid is None:
            # continue
            return

        mode = self._sel_mode_tkvar.get()
        uid_n_mode = ":".join([uid,mode])
        if "selected" in tags:
            if uid_n_mode in self.selected:
                self.selected.remove(uid_n_mode)
                self.dtag(item_id, "selected")
                self.delete(f"{uid}_{mode}_bbox")
                return
            
        self.addtag_withtag("selected", item_id)
        self.selected.append(":".join([uid,mode]))
        self._draw_selection_bbox(uid_n_mode)
    
    def _on_mousewheel(self, event: tk.Event) -> str:
        if event.state & self.SHIFT_MASK:
            direction = 1 if event.delta > 0 else -1
            return self._zoom_x(direction)
        # Plain wheel → vertical scroll (-delta: wheel-up scrolls content upward)
        self._yscroll_clamped(-1 if event.delta > 0 else 1)
        return "break"

    def _on_linux_wheel(self, event: tk.Event, direction: int) -> str:
        if event.state & self.SHIFT_MASK:
            return self._zoom_x(direction)
        # Plain wheel → vertical scroll (direction +1=up, -1=down)
        self._yscroll_clamped(-direction)
        return "break"

    def _yscroll_clamped(self, units: int) -> None:
        """Scroll vertically by ``units``, keeping the top y-coordinate >= 0.

        ``yscrollincrement`` defeats Tk's ``confine``, so ``yview_scroll`` would
        otherwise reveal negative y-coordinates above the scrollregion top.
        """
        self.yview_scroll(units, "units")
        if self.canvasy(0) < 0:
            self.yview_moveto(0.0)

    def _on_double_click(self, event: tk.Event) -> None:
        """Open the annotation dialog when double-clicking a waveform item."""
        x = self.canvasx(event.x)
        y = self.canvasy(event.y)
        tol = self.settings.selection["click_tolerance"]

        items = self.find_overlapping(x - tol, y - tol, x + tol, y + tol)

        for item_id in items:
            tags = self.gettags(item_id)

            # If it's an existing annotation text, open it for editing.
            annot_tag = next((t for t in tags if t.startswith("annot_uid_")), None)
            if annot_tag:
                wf_uid = annot_tag[len("annot_"):]      # "uid_<sig>_<el>"
                sig_uid = wf_uid.split("_")[1]
                sig = self.signals.find_by_uid(sig_uid)
                if sig and wf_uid in sig.annotations:
                    WaveformAnnotationDlg(self.topapp, wf_uid, sig.annotations[wf_uid])
                return

            # If it's a waveform element (not a label / marker / grid line),
            # open the annotation dialog for that element.
            uid_tag = next((t for t in tags if t.startswith("uid_")), None)
            if uid_tag and "wf_labels" not in tags and "tmarkers" not in tags:
                sig_uid = uid_tag.split("_")[1]
                sig = self.signals.find_by_uid(sig_uid)
                if sig:
                    existing = sig.annotations.get(uid_tag)
                    WaveformAnnotationDlg(self.topapp, uid_tag, existing)
                return

    def _zoom_x(self, direction: int) -> str:
        factor = self.zoom_step if direction > 0 else 1.0 / self.zoom_step
        self.scale_factor *= factor

        # Preserve current view (fraction of scrollregion)
        x0, _ = self.xview()

        # Re-render at the new scale
        self.redraw()
        self.update_scrollregion()

        # Restore view position
        self.xview_moveto(x0)
        return "break"
   
    def _create_new_signal(self, stype: str) -> None:
        """ Create Signal context menu dialogs """
        if stype == "clock":
            ClockSignalDlg(self.topapp)
        elif stype == "input":
            InputSignalDlg(self.topapp)
        elif stype == "output":
            OutputSignalDlg(self.topapp)
        else:
            raise ValueError(f"Unknown signal type: {stype}")

    def _grid_dialog(self) -> None:
        """ Launch Grid... dialog """
        GridSettingsDlg(self.topapp, self.settings, self.draw_grid)
        
    def _build_canvas_context_menu(self) -> None:
        self._ctxmenu = tk.Menu(self, tearoff=False)

        # New Signal submenu
        new_menu = tk.Menu(self._ctxmenu, tearoff=False)
        self._ctxmenu.add_cascade(label="New Signal", menu=new_menu)
        new_menu.add_command(label="Clock...", command=lambda: self._create_new_signal("clock"))
        new_menu.add_command(label="Input...", command=lambda: self._create_new_signal("input"))
        new_menu.add_command(label="Output...", command=lambda: self._create_new_signal("output"))

        self._ctxmenu.add_command(label="Edit Signal", state="disabled", command=self._edit_signal)
        self._ctxmenu.add_command(label="Delete Signal", state="disabled", command=self._delete_signal_action)

        self._hidden_menu = tk.Menu(self._ctxmenu, tearoff=False)
        self._ctxmenu.add_cascade(label="Hidden Signals", state="disabled", menu=self._hidden_menu)
        self._ctxmenu.add_command(label="Move Up", state="disabled", command=self._move_signal_up)
        self._ctxmenu.add_command(label="Move Down", state="disabled", command=self._move_signal_down)
        
        self._ctxmenu.add_separator()

        # Selection mode
        sel_mode_menu = self._build_selection_mode_menu(self._ctxmenu)
        self._ctxmenu.add_cascade(label="Selection Mode", menu=sel_mode_menu)

        # Timing selection
        self._ctxmenu.add_command(label="Time it", state="disabled", command=self.create_timing_marker)

        # Timing marker style
        mark_style_menu = self._build_marker_style_menu(self._ctxmenu)
        self._ctxmenu.add_cascade(label="Timing Marker", menu=mark_style_menu)
        mark_style_menu.add_separator()
        mark_style_menu.add_command(label="── Vertical anchor ──", state="disabled")
        mark_style_menu.add_radiobutton(
            label="None (fixed)",
            variable=self._marker_anchor_tkvar,
            value="none",
            command=self._update_marker_anchor,
        )
        # Indices for these two entries are updated dynamically with signal names.
        # They are appended right after the "None (fixed)" entry, so their
        # menu indices are fixed once built.
        mark_style_menu.add_radiobutton(
            label="From: ?",
            variable=self._marker_anchor_tkvar,
            value="from",
            command=self._update_marker_anchor,
        )
        mark_style_menu.add_radiobutton(
            label="To: ?",
            variable=self._marker_anchor_tkvar,
            value="to",
            command=self._update_marker_anchor,
        )
        self._mark_menu = mark_style_menu
        # Capture the indices of the From/To entries for later label updates.
        self._anchor_from_idx = mark_style_menu.index("end") - 1
        self._anchor_to_idx   = mark_style_menu.index("end")
        mark_style_menu.add_separator()
        mark_style_menu.add_command(label="Edit Label", command=self._edit_marker)
        mark_style_menu.add_command(label="Delete", command=self._delete_marker)
        self._ctxmenu.add_separator()
        self._ctxmenu.add_command(label="Add Split", state="disabled",
                                  command=self.create_split)
        self._ctxmenu.add_command(label="Delete Split", state="disabled",
                                  command=self.delete_split)
        self._ctxmenu.add_separator()
        self._ctxmenu.add_command(label="Grid...", state="normal", command=self._grid_dialog)
        

    def _show_canvas_context_menu(self, event: tk.Event) -> None:
        if self._ctxmenu is None:
            return

        self._rclick_x = self.canvasx(event.x)
        tags = self.gettags("current")
        # Beware! "current" tag is volatile. Windows OS removes it as soon as
        # you get out the envent handler. Linux keeps it longer.
        self._current_tags = tags

        # Defaults
        self._ctxmenu.entryconfig("Timing Marker", state="disabled")
        self._ctxmenu.entryconfig("Edit Signal", state="disabled")
        self._ctxmenu.entryconfig("Delete Signal", state="disabled")
        self._ctxmenu.entryconfig("Delete Split", state="disabled")

        if "tmarkers" in tags:
            # If it is a timing maker ...
            self._ctxmenu.entryconfig("Timing Marker", state="normal")
            for t in tags:
                if t.startswith("tmarker_uid_") and t in self.markers:
                    marker = self.markers[t]
                    self.markers["current"] = marker
                    self._marker_style_tkvar.set(marker.style)
                    self._marker_anchor_tkvar.set(marker.anchor)
                    # Update From/To labels with the actual signal names
                    if self._mark_menu is not None:
                        from_sig = self.signals.find_by_uid(
                            marker.from_uid.split("_")[1])
                        to_sig = self.signals.find_by_uid(
                            marker.to_uid.split("_")[1])
                        from_name = from_sig.name if from_sig else "?"
                        to_name   = to_sig.name   if to_sig   else "?"
                        self._mark_menu.entryconfig(
                            self._anchor_from_idx, label=f"From: {from_name}")
                        self._mark_menu.entryconfig(
                            self._anchor_to_idx,   label=f"To: {to_name}")
                    break
        elif "wf_labels" in tags:
            # If it is a waveform label ....
            self._ctxmenu.entryconfig("Edit Signal", state="normal")
            self._ctxmenu.entryconfig("Delete Signal", state="normal")
            self._ctxmenu.entryconfig("Move Up", state="normal")
            self._ctxmenu.entryconfig("Move Down", state="normal")

        # Enable "Time it" only when selecting >= 2 items
        self._ctxmenu.entryconfig("Time it",
                                  state="normal" if len(self.selected) >= 2 else "disabled")
        if any(sig.visible for sig in self.signals.values()):
               self._ctxmenu.entryconfig("Add Split", state="normal")
        # "Delete Split" only makes sense when right-clicking on a split.
        if self._split_under_cursor() is not None:
            self._ctxmenu.entryconfig("Delete Split", state="normal")
        # Show the context menu now ...
        self._ctxmenu.tk_popup(event.x_root, event.y_root)

        
    def _build_selection_mode_menu(self, parent: tk.Menu) -> tk.Menu:
        mode_menu = tk.Menu(parent, tearoff=False)

        mode_menu.add_radiobutton(label="Full", variable=self._sel_mode_tkvar,
                                  value="full")
        mode_menu.add_radiobutton(label="Start of", variable=self._sel_mode_tkvar,
                                  value="start")
        mode_menu.add_radiobutton(label="Middle of", variable=self._sel_mode_tkvar,
                                  value="middle")
        mode_menu.add_radiobutton(label="End of", variable=self._sel_mode_tkvar,
                                  value="end")

        return mode_menu

    def _build_marker_style_menu(self, parent: tk.Menu) -> tk.Menu:
        style_menu = tk.Menu(parent, tearoff=False)
        base_path = (Path(__file__).resolve().parent / ".." / "data").resolve()

        # Keep strong references on the menu object to avoid image GC.
        style_menu.img_inner_both = tk.PhotoImage(file=str(base_path / "tmarker_inner_both.png"))
        style_menu.img_inner_right = tk.PhotoImage(file=str(base_path / "tmarker_inner_right.png"))
        style_menu.img_inner_left = tk.PhotoImage(file=str(base_path / "tmarker_inner_left.png"))
        style_menu.img_outer = tk.PhotoImage(file=str(base_path / "tmarker_outer.png"))

        style_menu.add_radiobutton(
            image=style_menu.img_inner_both,
            variable=self._marker_style_tkvar,
            value="inner_both",
            command=self._update_marker_style,
        )
        style_menu.add_radiobutton(
            image=style_menu.img_inner_right,
            variable=self._marker_style_tkvar,
            value="inner_right",
            command=self._update_marker_style,
        )
        style_menu.add_radiobutton(
            image=style_menu.img_inner_left,
            variable=self._marker_style_tkvar,
            value="inner_left",
            command=self._update_marker_style,
        )
        style_menu.add_radiobutton(
            image=style_menu.img_outer,
            variable=self._marker_style_tkvar,
            value="outer",
            command=self._update_marker_style,
        )

        return style_menu

    def _update_marker_style(self) -> None:
        marker = self.markers.get("current")
        if marker is None:
            return
        with self.topapp.undo.transaction():
            self.topapp.console.execute(
                f"create_timing_marker -use_uid {marker.get_uid()} "
                f"-style {self._marker_style_tkvar.get()}")

    def _update_marker_anchor(self) -> None:
        marker = self.markers.get("current")
        if marker is None:
            return

        new_anchor = self._marker_anchor_tkvar.get()
        old_anchor = marker.anchor
        if new_anchor == old_anchor:
            return

        # Convert the stored y between absolute and anchor-relative
        # representations so the marker does not visually jump when the anchor
        # mode changes. The command sets the two raw values it is given, so the
        # conversion is done here, where the canvas geometry is known.
        y = marker.y
        if y is not None:
            abs_y = y + marker._get_anchor_y(self) if old_anchor != "none" else y

            saved, marker.anchor = marker.anchor, new_anchor  # for _get_anchor_y
            y = abs_y - marker._get_anchor_y(self) if new_anchor != "none" else abs_y
            marker.anchor = saved

        with self.topapp.undo.transaction():
            cmd = (f"create_timing_marker -use_uid {marker.get_uid()} "
                   f"-anchor {new_anchor}")
            if y is not None:
                cmd += f" -at {y}"
            self.topapp.console.execute(cmd)

    def _set_signal_visible(self, signame: str) -> None:
        with self.topapp.undo.transaction():
            self.topapp.console.execute(
                f"set_attribute -signal {{{signame}}} -name visible -value true")

            ## The rest is menu bookkeeping: GUI-only state the command knows
            ## nothing about.
            if self._hidden_menu is not None:
                end = self._hidden_menu.index("end")
                if end is not None:
                    for i in range(end + 1):
                        if self._hidden_menu.entrycget(i, "label") == signame:
                            self._hidden_menu.delete(i)
                            break

            if signame in self.hidden_signals:
                self.hidden_signals.discard(signame)
                if not self.hidden_signals and self._ctxmenu is not None:
                    self._ctxmenu.entryconfig("Hidden Signals", state="disabled")

            self.redraw()

    def _draw_selection_bbox(self, uid_n_mode: str = "") -> None:
        # If uid given, draw only that bbox; otherwise redraw all.
        if uid_n_mode:
            uid, mode = uid_n_mode.split(":")
            bbox = self.bbox(uid)
            if bbox is None:
                return

            tilt = self.settings.waveform["tilt"]
            if mode == "start":
                bbox = (bbox[0], bbox[1], bbox[0] + 2 * tilt, bbox[3])
            elif mode == "end":
                bbox = (bbox[2] - 2 * tilt, bbox[1], bbox[2], bbox[3])
            elif mode == "middle":
                midx = (bbox[2] - bbox[0]) // 2 + bbox[0]
                bbox = (midx - tilt, bbox[1], midx + tilt, bbox[3])

            color = self.settings.selection["to_color"]
            if self.selected.index(uid_n_mode) == 0:
                color = self.settings.selection["from_color"]

            self.create_rectangle(
                bbox,
                outline=color,
                dash=self.settings.selection["dash"],
                width=self.settings.selection["lwidth"],
                tags=(f"{uid}_{mode}_bbox", "selection_bbox", mode),
            )
            return

        # Full redraw
        self.delete("selection_bbox")
        for item_uid in self.selected:
            self._draw_selection_bbox(item_uid)

    def _get_current_tags(self) -> tuple[str, ...]:
        # Linux and Windows behave differently w.r.t. dynamic tag "current".
        # The tag can be lost when calling into other methods; store it.
        return self._current_tags

    def _get_current_signal(self) -> Signal | None:
        tags = self._get_current_tags() or ()
        signame = ""
        for t in tags:
            if t.endswith("_label"):
                signame = t[: -len("_label")]
                break
            if t.endswith("_waveform"):
                signame = t[: -len("_waveform")]
                break

        return self.signals.find(signame) if signame else None

    def _edit_marker(self) -> None:
        tags = self._get_current_tags() or ()
        for t in tags:
            if t.startswith("tmarker_uid_") and t in self.markers:
                self.markers[t].label_edit()
                break
                                    
    def remove_marker(self, marker: TimingMarker) -> None:
        """Erase a timing marker and detach it from the signals it measures.

        No undo snapshot is taken here: this is also the path the Tcl `remove`
        command goes through, and Tcl command handlers must not record any.
        """
        tag = f"tmarker_uid_{marker.get_uid()}"
        self.delete(tag)

        for u in (marker.from_uid, marker.to_uid):
            signal = self.signals.find_by_uid(u.split("_")[1])
            if signal is not None:
                signal.remove_related_obj(marker)
        if marker.name: # Remove tmarker label from timings settings vars.
            self.settings.marker["timings"].pop(marker.name, None)
        self.markers.pop("current", None)
        self.markers.pop(tag, None)

    def _delete_marker(self) -> None:
        tags = self._get_current_tags() or ()
        for t in tags:
            if t.startswith("tmarker_uid_") and t in self.markers:
                uid = self.markers[t].get_uid()
                with self.topapp.undo.transaction():
                    self.topapp.console.execute(f"remove -tmarker {{{uid}}}")
                break

    def _edit_signal(self) -> None:
        signal = self._get_current_signal()
        if signal is None:
            return

        # Remove all selected entries belonging to this signal
        prefix = f"uid_{signal.uid}_"
        for k in self.selected:
            if k.startswith(prefix):
                self.selected.remove(k)

        if signal.type == "clock":
            ClockSignalDlg(self.topapp, signal)
        elif signal.type == "input":
            InputSignalDlg(self.topapp, signal)
        elif signal.type == "output":
            OutputSignalDlg(self.topapp, signal)

            
    def _delete_signal(self, signal: Signal = None) -> None:
        # When deleting a signal, all related objects must also be removed.
        if signal is None:
            signal = self._get_current_signal()
        if signal is None:
            return

        # Remove any selected items from the signal to be removed.
        prefix = f"uid_{signal.uid}_"
        for k in self.selected:
            if k.startswith(prefix):
                self.selected.remove(k)

        # Remove related objects
        for obj in list(signal.get_related_objs()):
            if getattr(obj, "type", None) == "tmarker":
                self.markers.pop(f"tmarker_uid_{obj.get_uid()}", None)
            else:
                # Other possible related object is a signal
                self._delete_signal(obj)

        # Remove from hidden menu if present
        if signal.name in self.hidden_signals:
            if self._hidden_menu is not None:
                end = self._hidden_menu.index("end")
                if end is not None:
                    for i in range(end + 1):
                        if self._hidden_menu.entrycget(i, "label") == signal.name:
                            self._hidden_menu.delete(i)
                            break

            self.hidden_signals.discard(signal.name)
            if not self.hidden_signals and self._ctxmenu is not None:
                self._ctxmenu.entryconfig("Hidden Signals", state="disabled")

        self.signals.remove(signal.name)

        ## A clock gated by the removed signal reverts to free running
        ## (deliberately not a cascade delete).
        for sig in self.signals.values():
            if getattr(sig, "enabled_by", None) is signal:
                sig.enabled_by = None

        self.topapp.redraw()

    def _delete_signal_action(self) -> None:
        """User-initiated 'Delete Signal' — records one undo entry.

        ``_delete_signal`` itself is also called by the renderer
        (``draw_signals``) for un-drawable signals, so the snapshot is taken
        here rather than inside it.
        """
        signal = self._get_current_signal()
        if signal is None:
            return
        with self.topapp.undo.transaction():
            self.topapp.console.execute(f"remove -signal {{{signal.uid}}}")

    def _end_any_marker_edit(self, event):
        if self._marker_under_edition is not None:
            self._marker_under_edition.end_edit()
            self._marker_under_edition = None
            
    def _move_signal(self, direction: str) -> None:
        signal = self._get_current_signal()
        if signal is None:
            return

        ## The ordering rules live in the store, so this dialog and the
        ## move_signal command reject exactly the same moves.
        error = self.signals.move_error(signal.name, direction)
        if error is not None:
            messagebox.showerror(
                f"Move {direction.capitalize()} not possible", error, parent=self)
            return

        index = self.signals.index(signal.name)
        at_end = index == 0 if direction == "up" else index == len(self.signals) - 1
        if at_end:
            return

        with self.topapp.undo.transaction():
            self.topapp.console.execute(
                f"move_signal -name {{{signal.name}}} -direction {direction}")

    def _move_signal_up(self) -> None:
        self._move_signal("up")

    def _move_signal_down(self) -> None:
        self._move_signal("down")


    # ------------------------------------------------------------------
    # Public methods
    # ------------------------------------------------------------------
    def update_scrollregion(self) -> None:
        self.update_idletasks()
        bbox = self.bbox("all")
        if not bbox:
            self.configure(scrollregion=(0, 0, 0, 0))
            return

        _, _, x2, y2 = bbox
        self.configure(scrollregion=(0, 0, max(0, x2), max(0, y2)))

        
    def draw_signals(self) -> None:
        self.delete("all")

        top = self.settings.waveform["top_padding"]
        to_delete: list[Signal] = []

        for sig in self.signals.values():
            incr = sig.draw(self, top)
            if incr < 0:
                # Signals unable to be drawn return a negative value.
                # ... schedule is a list to be removed later.
                to_delete.append(sig)
                continue

            top += incr
            if getattr(sig, "visible"):
                top += self.settings.waveform["interslot"]
            else:
                if sig.name not in self.hidden_signals:
                    self.hidden_signals.add(sig.name)
                    if self._hidden_menu is not None:
                        self._hidden_menu.add_command(
                            label=sig.name,
                            command=lambda name=sig.name: self._set_signal_visible(name),
                        )
                    if self._ctxmenu is not None:
                        self._ctxmenu.entryconfig("Hidden Signals", state="normal")

        for sig in to_delete:
            self._delete_signal(sig)

    def draw_grid(self) -> None:
        self.wfgrid.draw(self)
        
    def redraw(self) -> None:
        self.draw_signals()
        self._draw_selection_bbox()

        # Redraw waveform annotations (after signals so items exist)
        for sig in self.signals.values():
            for annot in sig.annotations.values():
                annot.redraw(self)

        # Re-draw markers that are still valid/visible
        for key, marker in list(self.markers.items()):
            if key == "current":
                continue
            from_signal = self.signals.find_by_uid(marker.from_uid.split("_")[1])
            to_signal = self.signals.find_by_uid(marker.to_uid.split("_")[1])
            if from_signal.visible and to_signal.visible:
                marker.draw(self)

        self.wfgrid.draw(self)

        for split in self.splits.values():
            split.redraw()

        self.update_scrollregion()

    def add_timing_marker(self, marker: TimingMarker) -> None:
        # Remember signal uid tag is : uid_<signalid>_<elementid>
        for u in (marker.from_uid, marker.to_uid):
            self.signals.find_by_uid(u.split("_")[1]).add_related_obj(marker)

        marker.set_canvas(self)
        marker.set_vcanvas(self.topapp.vcanvas)
        marker.draw(self)
        self.markers[f"tmarker_uid_{marker.get_uid()}"] = marker

        
    def create_timing_marker(self, marker: TimingMarker = None) -> None:
        if marker is not None:
            # Load/source path (Tcl create_timing_marker): not a user action.
            self.add_timing_marker(marker)
            return

        with self.topapp.undo.transaction():
            first_uid: str = None
            first_mode = ""

            for uid_n_mode in self.selected:
                uid , mode = uid_n_mode.split(":")
                if first_uid is None:
                    first_uid = uid
                    first_mode = mode
                    continue

                self.topapp.console.execute(
                    f"create_timing_marker -from {first_mode}:{first_uid} "
                    f"-to {mode}:{uid}"
                )

    def set_scale(self, scale: float) -> None:
        self.scale_factor = float(scale)
        self.is_scaled = True
          
    def write_script(self, fileref: Any) -> None:
        scalestr = format(self.scale_factor, ".1f")
        fileref.write(f"set_canvas_scale {scalestr}\n\n")

        ## Before settings/timings/signals: any of their values may be an
        ## expression referencing a user variable, which must therefore
        ## already exist when the script is sourced back.
        self.topapp.console.write_user_vars(fileref)

        self.settings.write(fileref)
        self.timings.write(fileref)

        for sig in self.signals.values():
            sig.write(fileref)

        ## Clock gating is emitted after every create_* line: the enable
        ## signal may well be created after the clock it gates.
        for sig in self.signals.values():
            if getattr(sig, "enabled_by", None) is not None:
                fileref.write(f"\nset_attribute -signal {{{sig.name}}} "
                              f"-name enabled_by -value {{{sig.enabled_by.name}}}\n")
                fileref.write(f"set_attribute -signal {{{sig.name}}} "
                              f"-name enable_active -value {sig.enable_active}\n")

        fileref.write("\n")

        for key, mkr in self.markers.items():
            if key == "current":
                continue
            mkr.write(fileref)

        for split in self.splits.values():
            split.write(fileref)

        for sig in self.signals.values():
            for annot in sig.annotations.values():
                annot.write(fileref)

        fileref.write("\n\n# --- End of generated script. ---\n\n")

    def set_marker_under_edition(self, marker: TimingMarker = None):
        self._marker_under_edition = marker
    
    def remove_all(self):
        # Delete all items in canvas
        self.delete("all")
        self._current_tags = None
        # Clear the selected dict.
        self.selected.clear()
        self.markers.clear()
        # The measured value of every named marker goes with the markers: it is
        # a cache fed by TimingMarker.update_timings_dict(), and entries left
        # behind would show up under the settings of the next diagram.
        self.settings.marker["timings"].clear()
        self.splits.clear()
        self.hidden_signals.clear()
        # Clear the dynamically-built "Hidden Signals" cascade entries too;
        # clearing only the set above would let draw_signals re-add every
        # hidden signal on the next load, duplicating stale menu commands.
        if self._hidden_menu is not None:
            self._hidden_menu.delete(0, "end")
        if self._ctxmenu is not None:
            self._ctxmenu.entryconfig("Hidden Signals", state="disabled")
        self.signals.clear()
        
    def create_split(self) -> None:
        t = self.x_to_time(self._rclick_x)
        with self.topapp.undo.transaction():
            self.topapp.console.execute(f"create_waveform_split -at {t}")

    def _split_under_cursor(self) -> WaveformSplit | None:
        """The split the context menu was called on, None when not on one."""
        for tag in self._get_current_tags() or ():
            if tag.startswith("wsplit_uid_"):
                uid = tag[len("wsplit_uid_"):]
                if uid.isdigit():
                    return self.splits.get(int(uid))
        return None

    def remove_split(self, split: WaveformSplit) -> None:
        """Erase a waveform split. No undo snapshot, see remove_marker()."""
        split.delete()
        self.splits.pop(split.uid, None)

    def remove_signal(self, signal: Signal) -> None:
        """Erase a signal and everything related to it. No undo snapshot."""
        self._delete_signal(signal)

    def delete_split(self) -> None:
        split = self._split_under_cursor()
        if split is None:
            return

        with self.topapp.undo.transaction():
            self.topapp.console.execute(f"remove -split {{{split.uid}}}")
