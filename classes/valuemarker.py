from __future__ import annotations

from dataclasses import dataclass
from typing import TextIO, TYPE_CHECKING

import tkinter as tk
from tkinter import ttk

from .pwlsignal import eng_format

if TYPE_CHECKING:
    from .pwlsignal import PWLSignal, PWLTrace


@dataclass(slots=True)
class _DragState:
    dragging: bool = False
    moved: bool = False
    last_x: int = 0
    last_y: int = 0


class ValueMarker:
    """A value read-out placed on a point of a PWL trace.

    The marker shows the (interpolated) value of the trace at a time. Its
    label can be dragged away from the point: a thin line then keeps the
    label attached to the marked point. Double-clicking the label edits its
    text (an empty text restores the computed value).
    """

    _id_counter: int = 0
    DOT_RADIUS = 3
    DEFAULT_LABEL_DY = -14

    def __init__(self, slot: PWLSignal, trace_name: str, at: float,
                 uid: int | None = None) -> None:
        self.type = "vmarker"
        self.slot = slot
        self.trace_name = trace_name
        self.at = float(at)          # time, in the diagram time units
        self.text: str = ""           # label override ("" = computed value)
        self.label_relx: int = 0
        self.label_rely: int = self.DEFAULT_LABEL_DY

        self.value: float | None = None

        self.uid = ValueMarker._id_counter if uid is None else int(uid)
        if ValueMarker._id_counter <= self.uid:
            ValueMarker._id_counter = self.uid + 1

        self._canvas: tk.Canvas | None = None
        self.settings = None
        self._drag = _DragState()
        self._undo_before = None

        # Inline label editing
        self._label_item: int | None = None
        self._editor: ttk.Entry | None = None

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def uidtag(self) -> str:
        return f"vmarker_uid_{self.uid}"

    def get_uid(self) -> str:
        return str(self.uid)

    def trace(self) -> PWLTrace | None:
        return self.slot.find_trace(self.trace_name)

    def label_text(self) -> str:
        if self.text:
            return self.text
        trace = self.trace()
        if trace is None or self.value is None:
            return "?"
        return eng_format(self.value, trace.units)

    # ------------------------------------------------------------------
    # Drawing
    # ------------------------------------------------------------------
    def draw(self, canvas: tk.Canvas) -> None:
        if getattr(canvas, "is_virtual", False):
            return
        self._canvas = canvas
        self.settings = getattr(canvas, "settings", None)
        canvas.delete(self.uidtag())

        trace = self.trace()
        if trace is None or not self.slot.visible:
            return
        self.value = trace.value_at(self.at)
        xy = self.slot.trace_xy(canvas, trace, self.at)
        if xy is None:
            return
        x, y = xy

        color = self.settings.marker["color"]
        lwidth = self.settings.marker["lwidth"]
        lx = x + self.label_relx
        ly = y + self.label_rely
        tags = (self.uidtag(), "vmarkers")

        ## Tether from the label to the marked point.
        canvas.create_line(x, y, lx, ly, fill=color, width=lwidth,
                           tags=tags + (f"vmarker_tether_{self.uid}",))
        r = self.DOT_RADIUS
        canvas.create_oval(x - r, y - r, x + r, y + r,
                           fill=trace.color, outline=color,
                           tags=tags + (f"vmarker_dot_{self.uid}",))
        self._label_item = canvas.create_text(
            lx, ly,
            text=self.label_text(),
            font=self.settings.get_font(self.settings.marker["font"]),
            fill=color,
            anchor="center",
            tags=tags + (f"vmarker_label_{self.uid}", "vmarkers_label"),
        )
        self._bind_events(canvas)

    def redraw(self) -> None:
        if self._canvas is not None:
            self.draw(self._canvas)

    # ------------------------------------------------------------------
    # Interaction: drag of the label
    # ------------------------------------------------------------------
    def _bind_events(self, canvas: tk.Canvas) -> None:
        tag = f"vmarker_label_{self.uid}"
        canvas.tag_bind(tag, "<ButtonPress-1>", self._on_press)
        canvas.tag_bind(tag, "<B1-Motion>", self._on_drag)
        canvas.tag_bind(tag, "<ButtonRelease-1>", self._on_release)
        canvas.tag_bind(tag, "<Double-Button-1>", self._on_double_click)
        canvas.tag_bind(tag, "<Enter>", lambda _e: canvas.config(cursor="fleur"))
        canvas.tag_bind(tag, "<Leave>", lambda _e: canvas.config(cursor=""))

    def _on_press(self, event: tk.Event) -> str:
        canvas = self._canvas
        self._drag.dragging = True
        self._drag.moved = False
        self._drag.last_x = int(event.x)
        self._drag.last_y = int(event.y)
        self._undo_before = canvas.topapp.undo.begin()
        canvas.itemconfig(f"vmarker_label_{self.uid}",
                          fill=self.settings.marker["drag_color"])
        return "break"

    def _on_drag(self, event: tk.Event) -> None:
        if not self._drag.dragging:
            return
        canvas = self._canvas
        dx = int(event.x) - self._drag.last_x
        dy = int(event.y) - self._drag.last_y
        if not self._drag.moved:
            tol = self.settings.selection["click_tolerance"]
            if abs(dx) <= tol and abs(dy) <= tol:
                return
            self._drag.moved = True
        self.label_relx += dx
        self.label_rely += dy
        canvas.move(f"vmarker_label_{self.uid}", dx, dy)
        ## Keep the tether attached to the moving label.
        x0, y0, _, _ = canvas.coords(f"vmarker_tether_{self.uid}")
        canvas.coords(f"vmarker_tether_{self.uid}",
                      x0, y0, x0 + self.label_relx, y0 + self.label_rely)
        self._drag.last_x = int(event.x)
        self._drag.last_y = int(event.y)

    def _on_release(self, event: tk.Event) -> None:
        if not self._drag.dragging:
            return
        canvas = self._canvas
        self._drag.dragging = False
        if not self._drag.moved:
            self.redraw()
            self._undo_before = None
            return
        canvas.topapp.console.execute(
            f"create_value_marker -use_uid {self.uid} "
            f"-label_x {self.label_relx} -label_y {self.label_rely}")
        canvas.topapp.undo.commit(self._undo_before)
        self._undo_before = None

    # ------------------------------------------------------------------
    # Interaction: inline label edition
    # ------------------------------------------------------------------
    def _on_double_click(self, event: tk.Event) -> str:
        self._drag.dragging = False
        self._undo_before = None
        self.label_edit()
        return "break"

    def label_edit(self) -> None:
        canvas = self._canvas
        if canvas is None or self._label_item is None:
            return
        if self._editor is not None:
            self._editor.focus_set()
            return

        self._editor = ttk.Entry(canvas)
        self._editor.bind("<Return>", self._commit_edit)
        self._editor.bind("<Escape>", self._cancel_edit)
        self._editor.bind("<FocusOut>", self._commit_edit)
        self._editor.insert(0, canvas.itemcget(self._label_item, "text"))

        vx, vy = canvas.canvasx(0), canvas.canvasy(0)
        bbox = canvas.bbox(self._label_item)
        if bbox:
            x1, y1, x2, y2 = bbox
            self._editor.place(x=x1 - vx, y=y1 - vy,
                               width=max(50, x2 - x1 + 10),
                               height=max(18, y2 - y1 + 6))
        self._editor.focus_set()
        self._editor.selection_range(0, tk.END)
        canvas.set_marker_under_edition(self)

    def _commit_edit(self, event: tk.Event = None) -> None:
        if self._editor is None:
            return
        canvas = self._canvas
        new_text = self._editor.get().strip()
        self._editor.destroy()
        self._editor = None
        canvas.set_marker_under_edition(None)

        ## Typing back the computed value clears the override.
        if new_text == eng_format(self.value or 0.0,
                                  getattr(self.trace(), "units", "")):
            new_text = ""
        if new_text == self.text:
            self.redraw()
            return
        with canvas.topapp.undo.transaction():
            canvas.topapp.console.execute(
                f"create_value_marker -use_uid {self.uid} -text {{{new_text}}}")

    def _cancel_edit(self, event: tk.Event = None) -> None:
        if self._editor is None:
            return
        self._editor.destroy()
        self._editor = None
        if self._canvas is not None:
            self._canvas.set_marker_under_edition(None)

    def end_edit(self) -> None:
        if self._editor is not None:
            self._commit_edit()

    # ------------------------------------------------------------------
    # Serialization
    # ------------------------------------------------------------------
    def write(self, fileref: TextIO) -> None:
        fileref.write(f"\ncreate_value_marker -signal {{{self.trace_name}}}  \\\n")
        fileref.write(f"   -use_uid {self.uid}  \\\n")
        fileref.write(f"   -at {self.at!r}  \\\n")
        if self.text:
            fileref.write(f"   -text {{{self.text}}}  \\\n")
        fileref.write(f"   -label_x {self.label_relx}  \\\n")
        fileref.write(f"   -label_y {self.label_rely} \n")
