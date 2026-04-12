from __future__ import annotations

import tkinter as tk
from typing import TextIO, TYPE_CHECKING

if TYPE_CHECKING:
    from .signal import Signal


class WaveformAnnotation:
    """
    Annotation (text label and/or color override) attached to a specific
    waveform canvas item identified by its uidtag.

    Stored in the parent signal's ``annotations`` dict (keyed by wf_uid)
    so that deleting a signal automatically removes all its annotations.
    Annotations are redrawn after every canvas refresh.
    """

    def __init__(self, wf_uid: str, signal: Signal) -> None:
        self.wf_uid = wf_uid    # e.g. "uid_2_11"
        self.signal = signal     # parent signal

        # Text properties
        self.text: str = ""
        self.font_size: int | None = None   # None → use settings default
        self.font_slant: str = "normal"     # "normal" | "italic"
        self.font_weight: str = "normal"    # "normal" | "bold"
        self.font_color: str = "black"

        # Color overrides for the target canvas item
        self.fill: str | None = None    # polygon fill color
        self.line: str | None = None    # line / outline color

        # Text position relative to the bbox centre of wf_uid (pixels)
        self.rel_x: int = 0
        self.rel_y: int = 0

        # Runtime state (set during draw)
        self._canvas: tk.Canvas | None = None
        self._drag_start: tuple[int, int] = (0, 0)

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _annot_tag(self) -> str:
        return f"annot_{self.wf_uid}"

    def _make_font(self, settings) -> tuple:
        family = settings.waveform["font"]["family"]
        size = self.font_size if self.font_size else settings.waveform["font"]["size"]
        weight = self.font_weight
        slant = "italic" if self.font_slant == "italic" else "roman"
        return (family, size, weight, slant)

    def _apply_colors(self, canvas: tk.Canvas) -> None:
        """Apply fill/line color overrides to the target canvas item."""
        items = canvas.find_withtag(self.wf_uid)
        if not items:
            return
        item = items[0]
        item_type = canvas.type(item)

        if self.fill is not None and item_type == "polygon":
            try:
                canvas.itemconfigure(item, fill=self.fill)
            except tk.TclError:
                pass

        if self.line is not None:
            if item_type == "polygon":
                try:
                    canvas.itemconfigure(item, outline=self.line)
                except tk.TclError:
                    pass
            else:  # line, arc, etc.
                try:
                    canvas.itemconfigure(item, fill=self.line)
                except tk.TclError:
                    pass

    def _bind_drag(self, canvas: tk.Canvas) -> None:
        tag = self._annot_tag()
        canvas.tag_bind(tag, "<ButtonPress-1>", self._on_press)
        canvas.tag_bind(tag, "<B1-Motion>", self._on_drag)
        canvas.tag_bind(tag, "<ButtonRelease-1>", self._on_release)
        canvas.tag_bind(
            tag, "<Enter>",
            lambda _e: canvas.config(cursor="fleur"),
        )
        canvas.tag_bind(
            tag, "<Leave>",
            lambda _e: canvas.config(cursor=""),
        )
        canvas.tag_bind(tag, "<Double-Button-1>", self._on_double_click)

    def _on_press(self, event: tk.Event) -> None:
        self._drag_start = (event.x, event.y)

    def _on_drag(self, event: tk.Event) -> None:
        if self._canvas is None:
            return
        dx = event.x - self._drag_start[0]
        dy = event.y - self._drag_start[1]
        self._canvas.move(self._annot_tag(), dx, dy)
        self.rel_x += dx
        self.rel_y += dy
        self._drag_start = (event.x, event.y)

    def _on_release(self, event: tk.Event) -> None:
        pass  # rel_x / rel_y already updated incrementally in _on_drag

    def _on_double_click(self, event: tk.Event) -> None:
        """Open the annotation dialog when the user double-clicks the text."""
        from .waveformannotationdlg import WaveformAnnotationDlg
        if self._canvas is not None:
            topapp = getattr(self._canvas, "topapp", None)
            if topapp:
                WaveformAnnotationDlg(topapp, self.wf_uid, self)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def draw(self, canvas: tk.Canvas) -> None:
        """Draw the annotation on *canvas*.  Must be called after draw_signals()."""
        if getattr(canvas, "is_virtual", False):
            return

        self._canvas = canvas
        canvas.delete(self._annot_tag())

        self._apply_colors(canvas)

        if not self.text:
            return

        bbox = canvas.bbox(self.wf_uid)
        if bbox is None:
            return  # Target item does not exist (hidden signal, etc.)

        cx = (bbox[0] + bbox[2]) / 2.0 + self.rel_x
        cy = (bbox[1] + bbox[3]) / 2.0 + self.rel_y

        settings = canvas.settings
        font = self._make_font(settings)
        state = "normal" if self.signal.visible else "hidden"

        canvas.create_text(
            cx, cy,
            text=self.text,
            font=font,
            fill=self.font_color,
            state=state,
            tags=(self._annot_tag(), "wf_annotations"),
        )

        self._bind_drag(canvas)

    def redraw(self, canvas: tk.Canvas) -> None:
        """Erase and redraw.  Called from WaveformsCanvas.redraw()."""
        canvas.delete(self._annot_tag())
        self.draw(canvas)

    def write(self, fileref: TextIO) -> None:
        """Serialise to a ``create_waveform_annotation`` Tcl command."""
        cmd = f"\ncreate_waveform_annotation -on {self.wf_uid} "

        if self.text:
            cmd += f"\\\n  -text {{{self.text}}} "
            if self.font_size is not None:
                cmd += f"\\\n  -font_size {self.font_size} "
            if self.font_slant != "normal":
                cmd += f"\\\n  -font_slant {self.font_slant} "
            if self.font_weight != "normal":
                cmd += f"\\\n  -font_weight {self.font_weight} "
            if self.font_color != "black":
                cmd += f"\\\n  -font_color {self.font_color} "
            if self.rel_x != 0:
                cmd += f"\\\n  -rel_x {self.rel_x} "
            if self.rel_y != 0:
                cmd += f"\\\n  -rel_y {self.rel_y} "

        if self.fill is not None:
            cmd += f"\\\n  -fill {self.fill} "
        if self.line is not None:
            cmd += f"\\\n  -line {self.line} "

        fileref.write(cmd + "\n")
