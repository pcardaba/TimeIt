from __future__ import annotations

from dataclasses import dataclass
from typing import TextIO

import tkinter as tk
from tkinter import ttk


@dataclass(slots=True)
class _DragState:
    dragging: bool = False
    last_x: int = 0
    last_y: int = 0
    tag_pressed: str = ""


class TimingMarker:
    """Interactive timing marker drawn on a Tkinter Canvas.
    A TimingMarker connects two waveform elements
    (identified by canvas item/tag ids) and displays the
    measured time difference based on a *virtual* canvas scale.
    """
    
    _id_counter: int = 0

    def __init__(
            self,
            name: str = "",
            from_uid: str | None = None,
            from_at: str = "",
            to_uid: str | None = None,
            to_at: str = "",
    ) -> None:
        self.name = name
        self.type = "tmarker"

        # From / to waveform element references (canvas tags or item ids)
        self.from_uid = from_uid
        self.from_at = from_at
        self.to_uid = to_uid
        self.to_at = to_at

        # Style: inner_both / inner_left / inner_right / outer
        self.style = "inner_both"
        self.arrow = "both"
        self.visible = True

        # Vertical anchor: "none" | "from" | "to"
        # When != "none", self.y is stored as an offset from the top of the
        # anchored signal's waveform slot, so the marker tracks the slot as
        # the layout changes (e.g. top_padding adjustments).
        self.anchor: str = "none"

        # Geometry
        self.x_from = 0
        self.y_from = 0
        self.x_to = 0
        self.y_to = 0
        self.y: int | None = None  # marker is horizontal at constant y
        self.label_relx = 0
        self.label_rely = 0

        # Measured timing
        self.timing: float = 0.0

        # Canvas references (set via set_canvas / set_vcanvas)
        self._canvas: tk.Canvas | None = None
        self._vcanvas: tk.Canvas | None = None  

        # Inline label editing
        self._label_item: int | None = None
        self._editor: ttk.Entry | None = None
        self._editing_item: int | None = None

        # Drag state
        self._drag = _DragState()

        # Unique id
        self.uid = TimingMarker._id_counter
        TimingMarker._id_counter += 1

        # Settings are taken from the real canvas at draw() 
        self.settings = None
        
    # ------------------------------------------------------------------
    # Private methods
    # ------------------------------------------------------------------

    def _get_anchor_y(self, canvas: tk.Canvas) -> int:
        """Return the canvas y-coordinate of the top of the anchored signal's
        waveform slot.  Returns 0 if the anchor cannot be resolved."""
        uid_ref = self.from_uid if self.anchor == "from" else self.to_uid
        if uid_ref is None:
            return 0
        signals = getattr(canvas, "signals", None)
        if signals is None:
            return 0
        sig = signals.find_by_uid(uid_ref.split("_")[1])
        if sig is None:
            return 0
        bbox = canvas.bbox(f"{sig.name}_waveform")
        return int(bbox[1]) if bbox else 0

    def _ensure_ready(self) -> tuple[tk.Canvas, object]:
        if self._canvas is None:
            raise RuntimeError("TimingMarker canvas is not set (call set_canvas).")
        if self._vcanvas is None:
            raise RuntimeError("TimingMarker virtual canvas is not set (call set_vcanvas).")
        return self._canvas, self._vcanvas

    def _format_timing_value(self) -> str:
        txt = format(self.timing, self.settings.marker["float_format"])
        return f"{txt}{self.settings.waveform['tunits']}"

    def _on_press_mark(self, event: tk.Event) -> None:
        self._drag.tag_pressed = f"tmarker_marklb_{self.uidtag()}"
        self._on_press(event)

    def _on_press_label(self, event: tk.Event) -> None:
        self._drag.tag_pressed = f"tmarker_label_{self.uidtag()}"
        self._on_press(event)

    def _on_press(self, event: tk.Event) -> str:
        canvas, _ = self._ensure_ready()
        if self.settings is None:
            self.settings = getattr(canvas, "settings", None)

        self._drag.dragging = True
        self._drag.last_y = int(event.y)
        self._drag.last_x = int(event.x)

        canvas.itemconfig(self._drag.tag_pressed, fill=self.settings.marker["drag_color"])
        return "break"
        
    def _on_drag(self, event: tk.Event) -> None:
        if not self._drag.dragging:
            return
        canvas, _ = self._ensure_ready()

        dy = int(event.y) - self._drag.last_y
        dx = int(event.x) - self._drag.last_x

        # Only labels can move in X; marker line is locked horizontally
        if not self._drag.tag_pressed.startswith("tmarker_label_"):
            dx = 0
        else:
            self.label_rely += dy
            self.label_relx += dx

        canvas.move(self._drag.tag_pressed, dx, dy)
        self._drag.last_y = int(event.y)
        self._drag.last_x = int(event.x)

    def _on_release(self, event: tk.Event) -> None:
        canvas, _ = self._ensure_ready()

        if not self._drag.tag_pressed.startswith("tmarker_label_"):
            abs_y = self._drag.last_y
            if self.anchor != "none":
                self.y = abs_y - self._get_anchor_y(canvas)
            else:
                self.y = abs_y
            self.redraw()
        else:
            canvas.itemconfig(self._drag.tag_pressed, fill=self.settings.marker["color"])

        self._drag.dragging = False

    def _bind_events(self) -> None:
        canvas, _ = self._ensure_ready()

        tag = f"tmarker_mark_{self.uidtag()}"
        canvas.tag_bind(tag, "<ButtonPress-1>", self._on_press_mark)
        canvas.tag_bind(tag, "<B1-Motion>", self._on_drag)
        canvas.tag_bind(tag, "<ButtonRelease-1>", self._on_release)
        canvas.tag_bind(tag, "<Enter>", lambda _e: canvas.config(cursor="fleur"))
        canvas.tag_bind(tag, "<Leave>", lambda _e: canvas.config(cursor=""))

        tag = f"tmarker_label_{self.uidtag()}"
        # canvas.tag_bind(tag, "<Double-Button-1>", self.label_edit)
        canvas.tag_bind(tag, "<ButtonPress-1>", self._on_press_label)
        canvas.tag_bind(tag, "<B1-Motion>", self._on_drag)
        canvas.tag_bind(tag, "<ButtonRelease-1>", self._on_release)
        canvas.tag_bind(tag, "<Enter>", lambda _e: canvas.config(cursor="fleur"))
        canvas.tag_bind(tag, "<Leave>", lambda _e: canvas.config(cursor=""))

        
    def _commit_edit(self, event: tk.Event = None) -> None:
        if self._editor is None or self._editing_item is None:
            return
        canvas, _ = self._ensure_ready()

        new_text = self._editor.get().strip()
        canvas.itemconfigure(self._editing_item, text=new_text)
        self.name = new_text
        self.update_timings_dict()
        
        canvas.set_marker_under_edition(None)
        
        self._editor.destroy()
        self._editor = None
        self._editing_item = None

        self.redraw()

    def _cancel_edit(self, event: Optional[tk.Event] = None) -> None:
        if self._editor is None:
            return
        self._editor.destroy()
        self._editor = None
        self._editing_item = None
      
    # ------------------------------------------------------------------
    # Public methods
    # ------------------------------------------------------------------   
    def uidtag(self) -> str:
        return f"uid_{self.uid}"

    def get_uid(self) -> str:
        return str(self.uid)

    def write(self, fileref: TextIO) -> None:
        """Serialize the marker as a Tcl command."""
        fileref.write(f"\ncreate_timing_marker -name {{{self.name}}}  \\\n")
        fileref.write(f"   -from {self.from_at}:{self.from_uid}  \\\n")
        fileref.write(f"   -to {self.to_at}:{self.to_uid}  \\\n")
        fileref.write(f"   -at {self.y if self.y is not None else -1}  \\\n")
        fileref.write(f"   -style {self.style}  \\\n")
        fileref.write(f"   -anchor {self.anchor}  \\\n")
        fileref.write(f"   -label_x {self.label_relx}  \\\n")
        fileref.write(f"   -label_y {self.label_rely} \n")


    def set_canvas(self, canvas: tk.Canvas) -> None:
        self._canvas = canvas
        if self._vcanvas is not None:
            self._bind_events()

    def set_vcanvas(self, vcanvas) -> None:
        """Set the virtual canvas used for timing measures.
        The virtual canvas is expected to provide:
          - bbox(uid) -> (x1, y1, x2, y2) like Tk canvas
          - scale_factor attribute (float)
        """
        self._vcanvas = vcanvas
        if self._canvas is not None:
            self._bind_events()

    def get_leg_coord(self, canvas, uid: str, at: str) -> tuple[int, int]:
        """Return (x, y) coordinate on a waveform element bbox."""
        bbox = canvas.bbox(uid)
        if not bbox:
            return (0, 0)

        x1, y1, x2, y2 = bbox
        y = (y2 - y1) // 2 + y1
        if at == "start":
            return (x1, y)
        if at == "end":
            return (x2, y)
        return ((x2 - x1) // 2 + x1, y)

    def draw(self, canvas: tk.Canvas) -> None:
        """Draw the marker onto the given canvas."""
        self.settings = getattr(canvas, "settings", None)
        if self.settings is None:
            raise RuntimeError("Canvas has no .settings;" +
                               "TimingMarker needs settings.marker/settings.waveform.")

        if self.from_uid is None or self.to_uid is None:
            raise ValueError("TimingMarker requires from_uid and to_uid to draw.")

        _, vcanvas = self._ensure_ready()

        # Real canvas coords
        self.x_from, self.y_from = self.get_leg_coord(canvas, self.from_uid, self.from_at)
        self.x_to, self.y_to = self.get_leg_coord(canvas, self.to_uid, self.to_at)

        # Default y on first draw.  When an anchor is active, self.y is stored
        # as an offset from the anchor signal's slot top; convert accordingly.
        if self.y is None:
            abs_y = abs(self.y_to - self.y_from) // 2 + min(self.y_from, self.y_to)
            if self.anchor != "none":
                self.y = abs_y - self._get_anchor_y(canvas)
            else:
                self.y = abs_y

        # Resolve the effective canvas y used for drawing.
        if self.anchor != "none":
            eff_y = self._get_anchor_y(canvas) + self.y
        else:
            eff_y = self.y

        # Timing from virtual canvas
        vx_from, _ = self.get_leg_coord(vcanvas, self.from_uid, self.from_at)
        vx_to, _ = self.get_leg_coord(vcanvas, self.to_uid, self.to_at)
        scale = getattr(vcanvas, "scale_factor", 1.0) or 1.0
        self.timing = float(vx_to - vx_from) / float(scale)

        tail_size = self.settings.marker["leg_tail"]
        color = self.settings.marker["color"]
        lwidth = self.settings.marker["lwidth"]

        # Legs
        tail = tail_size if eff_y > self.y_from else -tail_size
        canvas.create_line(
            self.x_from, self.y_from,
            self.x_from, eff_y + tail,
            fill=color,
            width=lwidth,
            tags=(f"tmarker_{self.uidtag()}",
                  f"tmarker_lleg_{self.uidtag()}",
                  "tmarkers", "tmarkers_legs"),
        )

        tail = tail_size if eff_y > self.y_to else -tail_size
        canvas.create_line(
            self.x_to, self.y_to,
            self.x_to, eff_y + tail,
            fill=color,
            width=lwidth,
            tags=(f"tmarker_{self.uidtag()}",
                  f"tmarker_rleg_{self.uidtag()}",
                  "tmarkers", "tmarkers_legs"),
        )

        # Mark (horizontal)
        mark_tags = (
            f"tmarker_{self.uidtag()}",
            f"tmarker_mark_{self.uidtag()}",
            f"tmarker_marklb_{self.uidtag()}",
            "tmarkers",
            "tmarkers_mark",
        )

        self.arrow = (
            "first" if self.style == "inner_left" \
                    else "last" if self.style == "inner_right" else "both"
        )

        if self.style.startswith("inner_"):
            canvas.create_line(
                self.x_from, eff_y,
                self.x_to, eff_y,
                fill=color,
                width=lwidth,
                arrow=self.arrow,
                arrowshape=self.settings.marker["arrow_shape"],
                tags=mark_tags,
            )
        else:
            outlength = self.settings.marker["outer_length"]
            canvas.create_line(
                self.x_from - outlength, eff_y,
                self.x_from, eff_y,
                fill=color,
                width=lwidth,
                arrow="last",
                arrowshape=self.settings.marker["arrow_shape"],
                tags=mark_tags,
            )
            canvas.create_line(
                self.x_to + outlength, eff_y,
                self.x_to, eff_y,
                fill=color,
                width=lwidth,
                arrow="last",
                arrowshape=self.settings.marker["arrow_shape"],
                tags=mark_tags,
            )

        # Label
        label_text = self.name if self.name else self._format_timing_value()
        self._label_item = canvas.create_text(
            ((self.x_from + self.x_to) // 2) + self.label_relx,
            (eff_y - 2) + self.label_rely,
            text=label_text,
            font=self.settings.get_font(self.settings.marker["font"]),
            anchor=tk.S,
            tags=(
                f"tmarker_{self.uidtag()}",
                f"tmarker_label_{self.uidtag()}",
                f"tmarker_marklb_{self.uidtag()}",
                "tmarkers",
                "tmarkers_label",
            ),
        )
        
    def redraw(self) -> None:
        canvas, _ = self._ensure_ready()
        canvas.delete(f"tmarker_{self.uidtag()}")
        self.draw(canvas)


    def update_timings_dict(self) -> None:
        """Update settings.marker['timings'] mapping when named."""
        if not self.name or self.settings is None:
            return
        self.settings.marker["timings"][self.name] = self._format_timing_value()

    def label_edit(self) -> None:
        canvas, _ = self._ensure_ready()
        if self._label_item is None:
            return

        self._editing_item = self._label_item
        current_text = canvas.itemcget(self._editing_item, "text")
  
        self._editor = ttk.Entry(canvas)
        self._editor.bind("<Return>", self._commit_edit)
        self._editor.bind("<Escape>", self._cancel_edit)
        self._editor.bind("<FocusOut>", self._commit_edit)

        self._editor.delete(0, tk.END)
        self._editor.insert(0, current_text)

        bbox = canvas.bbox(self._editing_item)
        if bbox:
            x1, y1, x2, y2 = bbox
            width = max(40, x2 - x1 + 10)
            height = max(18, y2 - y1 + 6)
            self._editor.place(x=x1, y=y1, width=width, height=height)
        else:
            x, y = canvas.coords(self._editing_item)
            self._editor.place(x=x, y=y)
             
        self._editor.focus_set()
        
        self._editor.selection_range(0, tk.END)
        canvas.set_marker_under_edition(self)


    def end_edit(self) -> None:
        if self._editor is not None:
            self._commit_edit()

