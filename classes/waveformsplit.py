from __future__ import annotations

import math
import tkinter as tk
from typing import TextIO


class WaveformSplit:
    """
    Draggable waveform-break symbol drawn on a Tkinter Canvas.

    One individual split segment is rendered for every *visible* signal
    slot.  Each segment spans exactly one sinusoid period whose spatial
    length equals the signal's amplitude (slot height), with a small
    configurable overflow above and below the slot so adjacent segments
    do not visually touch.  The inter-slot gaps are left empty.

    Every segment is composed of three abutted vertical sinusoids:

        black | white | black

    The white centre curve (width = 2*gap) erases the waveform content
    underneath.  The two flanking black curves form the classic
    double-S silhouette.

    All segments share the same canvas tag and therefore move together
    when the object is dragged horizontally with the mouse.

    Usage
    -----
        split = WaveformSplit(canvas, x=300)
        split.move_to(500)   # programmatic reposition
        split.delete()       # remove from canvas

    Integration (WaveformsCanvas)
    ------------------------------
    Add ``self.splits: dict[int, WaveformSplit] = {}`` to
    ``WaveformsCanvas.__init__`` and, at the end of ``redraw()``:

        for split in self.splits.values():
            split.redraw()

    To place one (e.g. from a context-menu handler):

        split = WaveformSplit(canvas, x=event_x)
        canvas.splits[split.uid] = split
    """

    _id_counter: int = 0

    def __init__(
        self,
        canvas: tk.Canvas,
        t: float,
        *,
        amplitude: float = 6.0,
        gap: float = 5.0,
        overflow: float = 0.15,
        lwidth: int = 2,
        steps_per_slot: int = 80,
        uid: int | None = None,
    ) -> None:
        """
        Parameters
        ----------
        canvas          Parent WaveformsCanvas (must expose .settings and
                        .signals like WaveformsCanvas does).
        t               Time at (canvas time coords to be converted in x (pixel) coords).
        amplitude       Half-width of each sinusoid's x-oscillation (pixels).
                        Controls how "wide" the S-curves swing left/right.
        gap             Half-distance between the three curve centres (pixels).
                        The white stroke width = 2*gap, so the three curves
                        are exactly abutted with no overlap or gap.
        overflow        Fraction of slot height to extend above/below each
                        individual segment (e.g. 0.15 → 15 % overflow on
                        each side).  Prevents segments from looking truncated
                        at their tips while keeping the inter-slot gap clear.
        lwidth          Stroke width of the two black curves.
        steps_per_slot  Polyline segment count per signal slot (more → smoother
                        curves; 60-100 is usually sufficient).
        """
        self._canvas = canvas
        self.t = t
        self.x = canvas.time_to_x(t)
        self.amplitude = amplitude
        self.gap = gap
        self.overflow = overflow
        self.lwidth = lwidth
        self.steps_per_slot = steps_per_slot

        # A given uid (-use_uid) keeps the counter above it, so a split created
        # later never collides with it.
        self.uid = WaveformSplit._id_counter if uid is None else int(uid)
        if WaveformSplit._id_counter <= self.uid:
            WaveformSplit._id_counter = self.uid + 1

        self._drag_x: int = 0

        self.draw()
        self._bind_events()

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _tag(self) -> str:
        return f"wsplit_uid_{self.uid}"

    def _sine_segment_pts(
        self,
        cx: float,
        y_top: float,
        y_bot: float,
        period: float,
    ) -> list[float]:
        """
        Build a flat [x0,y0, x1,y1, …] point list for one vertical
        sinusoid segment running from y_top to y_bot.

        The spatial period of the sine equals ``period`` (= slot height),
        so exactly one full cycle fits in the slot, optionally extended by
        the overflow region.
        """
        pts: list[float] = []
        height = y_bot - y_top
        steps = max(4, self.steps_per_slot)
        for i in range(steps + 1):
            t = i / steps
            y = y_top + t * height
            # Phase offset so the curve starts and ends at x=cx (zero crossing)
            # when the slot boundaries align with full periods.
            x = cx + self.amplitude * math.sin(
                2.0 * math.pi * (y - y_top) / period
            )
            pts += [x, y]
        return pts

    def _iter_visible_slots(self):
        """
        Yield (top, slot_height) for every visible signal, in draw order.

        Replicates the y-layout logic of WaveformsCanvas.draw_signals():
          - hidden signals return incr=0 → take no vertical space
          - interslot gap is only added after visible slots
        """
        settings = self._canvas.settings
        top = settings.waveform["top_padding"]
        interslot = settings.waveform["interslot"]

        for sig in self._canvas.signals.values():
            if not sig.visible:
                # Hidden signal: no space consumed (matches draw() returning 0)
                continue
            slot_height = sig.amplitude
            top += sig.top_padding
            yield top, slot_height
            top += slot_height + interslot

    def _draw_triple(
        self,
        cx: float,
        y_top: float,
        y_bot: float,
        period: float,
        tag: str,
    ) -> None:
        """Draw the three abutted sinusoids for one slot segment."""
        white_width = max(1, round(self.gap * 2))

        # White centre — drawn first so black curves render on top of its edges
        self._canvas.create_line(
            self._sine_segment_pts(cx, y_top, y_bot, period),
            fill="white",
            width=white_width,
            smooth=True,
            tags=(tag, "waveform_splits"),
        )
        # Left black
        self._canvas.create_line(
            self._sine_segment_pts(cx - self.gap, y_top, y_bot, period),
            fill="black",
            width=self.lwidth,
            smooth=True,
            tags=(tag, "waveform_splits"),
        )
        # Right black
        self._canvas.create_line(
            self._sine_segment_pts(cx + self.gap, y_top, y_bot, period),
            fill="black",
            width=self.lwidth,
            smooth=True,
            tags=(tag, "waveform_splits"),
        )

    def _bind_events(self) -> None:
        tag = self._tag()
        self._canvas.tag_bind(tag, "<ButtonPress-1>",   self._on_press)
        self._canvas.tag_bind(tag, "<B1-Motion>",       self._on_drag)
        self._canvas.tag_bind(tag, "<ButtonRelease-1>", self._on_release)
        self._canvas.tag_bind(
            tag, "<Enter>",
            lambda _e: self._canvas.config(cursor="sb_h_double_arrow"),
        )
        self._canvas.tag_bind(
            tag, "<Leave>",
            lambda _e: self._canvas.config(cursor=""),
        )

    def _on_press(self, event: tk.Event) -> None:
        self._drag_x = int(event.x)
        self._undo_before = self._canvas.topapp.undo.begin()

    def _on_drag(self, event: tk.Event) -> None:
        dx = int(event.x) - self._drag_x
        self._canvas.move(self._tag(), dx, 0)
        self.x += dx
        self._drag_x = int(event.x)

    def _on_release(self, event: tk.Event) -> None:
        ## x was updated incrementally in _on_drag (to keep the move live); the
        ## command is what commits the final time to the model, and logs it.
        t = self._canvas.x_to_time(self.x)
        self._canvas.topapp.console.execute(
            f"create_waveform_split -use_uid {self.uid} -at {t}")
        self._canvas.topapp.undo.commit(self._undo_before)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def draw(self) -> None:
        """
        (Re)draw all per-signal split segments on the canvas.

        One triple-sinusoid segment is created for each visible signal.
        The sine period equals the signal slot height (amplitude), and
        the segment extends ``overflow * slot_height`` pixels above and
        below the slot boundaries.  The inter-slot gap is left empty.
        """
        tag = self._tag()
        self._canvas.delete(tag)

        cx = float(self.x)

        for top, slot_height in self._iter_visible_slots():
            ovf = self.overflow * slot_height
            y_top = top - ovf
            y_bot = top + slot_height + ovf
            # Period = slot height (one full cycle per waveform strip)
            self._draw_triple(cx, y_top, y_bot, float(slot_height), tag)

    def redraw(self) -> None:
        """Erase and redraw, then re-bind drag events.

        Call this after WaveformsCanvas.draw_signals() has re-laid out
        the signals (so y-positions are up to date).
        """
        # May require rescale.
        self.x = self._canvas.time_to_x(self.t)
        self.draw()
        self._bind_events()

    def move_to(self, x: int) -> None:
        """Translate the symbol to a new x position (canvas coordinates)."""
        dx = x - self.x
        self._canvas.move(self._tag(), dx, 0)
        self.x = x
        self.t = self._canvas.x_to_time(x)

    def delete(self) -> None:
        """Remove all canvas items belonging to this symbol."""
        self._canvas.delete(self._tag())

    def write(self, fileref: TextIO) -> None:
        """Serialise as a Tcl command (for script save/load)."""
        fileref.write(
            f"\ncreate_waveform_split"
            f"  -use_uid {self.uid}"
            f"  -at {self.t}"
            f"  -amplitude {self.amplitude}"
            f"  -gap {self.gap}"
            f"  -overflow {self.overflow}"
            f"  -lwidth {self.lwidth}\n"
        )
