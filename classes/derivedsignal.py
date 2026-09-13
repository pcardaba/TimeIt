# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2024 Pablo Cardaba

"""Signals whose waveform is computed from other signals.

A derived signal keeps references to its operands and recomputes its waveform
on every draw, so editing an operand or changing a timing variable propagates
automatically: that is the whole live-update mechanism, and it needs no
observer wiring.

Because ``state_intervals()`` is both what a derived signal consumes and what
it produces, derived signals compose: one can be measured by a timing marker,
be annotated, or feed another derived signal, with no special casing anywhere.

Subclasses (LogicSignal, SampledSignal) implement ``operands()``,
``recompute()`` and ``write()``; this base class handles operand flattening,
cycle guarding, error logging, ``state_intervals()`` and all the drawing.
"""

from __future__ import annotations

import math
import tkinter as tk

from . import timeline as tline
from .signal import Signal


class DerivedSignal(Signal):
    """Base class for computed signals. Subclasses implement recompute()."""

    ## Timeline value -> the state name the rest of the application speaks.
    _VALUE_STATES = {tline.ZERO: "low", tline.ONE: "high",
                     tline.X: "unknown", tline.D: "data"}

    def __init__(self, name: str, sig_type: str = "derived") -> None:
        super().__init__(name, sig_type=sig_type)
        self._timeline: list[tuple[float, float, str]] | None = None
        ## Guards against a dependency cycle, mirroring _gating_busy in
        ## ClockSignal: a cycle must yield None, not recurse forever.
        self._busy: bool = False

    # ------------------------------------------------------------------
    # Subclass contract
    # ------------------------------------------------------------------
    def recompute(self) -> list[tuple[float, float, str]] | None:
        """The computed timeline, or None when it cannot be resolved."""
        raise NotImplementedError

    def operands(self) -> tuple:
        """The signals this one is computed from. Overridden by subclasses."""
        return ()

    # ------------------------------------------------------------------
    # Reading operands
    # ------------------------------------------------------------------
    def operand_timeline(self, operand) -> list | None:
        """Flatten ``operand`` into a value timeline, or None if unresolvable."""
        if operand is None:
            return None

        getter = getattr(operand, "state_intervals", None)
        if getter is None:
            self._log(f"{getattr(operand, 'name', operand)} has no waveform")
            return None

        return tline.flatten(getter(),
                             pulled_up=bool(getattr(operand, "pulled_up", False)))

    def _log(self, message: str) -> None:
        if self.console is not None:
            self.console.append_log(
                f"[{self.__class__.__name__}] {self.name}: {message}\n", "error")

    def _eval_or_zero(self, expr: str | None) -> float:
        """A timing expression resolved at draw time; empty means 0."""
        if expr is None or str(expr).strip() == "":
            return 0.0
        return self._tcl_eval_float(expr, context=self.__class__.__name__)

    # ------------------------------------------------------------------
    # Timeline access
    # ------------------------------------------------------------------
    def timeline(self) -> list | None:
        """The computed timeline, guarded against dependency cycles."""
        if self._busy:
            self._log("dependency cycle detected; not drawn")
            return None

        self._busy = True
        try:
            self._timeline = self.recompute()
        except (ValueError, tk.TclError) as exc:
            self._log(str(exc))
            self._timeline = None
        finally:
            self._busy = False
        return self._timeline

    def state_intervals(self):
        """The timeline in the vocabulary the rest of the application uses.

        This is what makes a derived signal indistinguishable from a basic one
        to timing markers and to other derived signals.
        """
        computed = self.timeline()
        if computed is None:
            return None
        return [(start, end, self._VALUE_STATES[value])
                for start, end, value in computed]

    # ------------------------------------------------------------------
    # Relationships
    # ------------------------------------------------------------------
    def related_clocks(self) -> tuple:
        """Clocks this signal depends on, for the store's ordering rules."""
        return tuple(op for op in self.operands()
                     if getattr(op, "type", None) == "clock")

    # ------------------------------------------------------------------
    # Drawing
    # ------------------------------------------------------------------
    def _x_bounds(self, canvas: tk.Canvas) -> tuple[float, float]:
        """Left and right x limits the waveform is clipped to.

        The timeline runs from -inf to +inf; the drawing has to stop where the
        diagram does. The right edge is derived from the longest clock's time
        span rather than from the widget width, exactly as I/O signals compute
        wfends_x. On the visible canvas the two agree, because the clock sets
        scale_factor to make them agree. On the hidden VirtualCanvas they do
        not: it is never laid out, so winfo_width() reports 1 and every
        segment would clip to zero width, leaving timing markers nothing to
        measure.
        """
        start_x = (self.settings.waveform["left_padding"]
                   + self.settings.waveform["nmargin"])

        span = 0.0
        for sig in canvas.signals.values():
            if getattr(sig, "type", None) != "clock":
                continue
            if not sig.ensure_resolved():
                continue
            try:
                period = sig._waveform()[0]
            except (ValueError, tk.TclError):
                continue
            span = max(span, period * float(sig.cycles))

        if span > 0.0:
            return start_x, canvas.time_to_x(span)

        ## No clock resolves: fall back to the widget so something is drawn.
        width = max(canvas.winfo_width(), 1)
        return start_x, width - self.settings.waveform["right_padding"]

    @staticmethod
    def _clip(canvas: tk.Canvas, left: float, right: float,
              start: float, end: float) -> tuple[float, float]:
        """Canvas x range of a time range, clipped to the margins."""
        x1 = left if math.isinf(start) else canvas.time_to_x(start)
        x2 = right if math.isinf(end) else canvas.time_to_x(end)
        return max(x1, left), min(x2, right)

    def _tags(self, kind: str) -> tuple[str, ...]:
        return (self.uidtag(), f"{self.name}_{kind}", f"{self.name}_waveform")

    def _level_y(self, top: int, value: str) -> float:
        """The y a value sits at: top for 1, bottom for 0, mid for X and D."""
        slot_height = int(self.amplitude)
        if value == tline.ONE:
            return top
        if value == tline.ZERO:
            return top + slot_height
        return top + slot_height / 2

    def _draw_level(self, canvas: tk.Canvas, top: int, x1: float, x2: float,
                    value: str, clipped_left: bool, clipped_right: bool) -> None:
        """Draw one timeline segment at its logic level.

        1 and 0 are lines; X and D are the same closed hexagons an I/O signal
        draws for an unknown or a data window, with the pointed ends squared
        off where the segment is cut by the diagram margin.
        """
        slot_height = int(self.amplitude)
        tilt = self.settings.waveform["tilt"]
        mid = top + slot_height / 2

        if value in (tline.ONE, tline.ZERO):
            y = self._level_y(top, value)
            kind = "highvalid" if value == tline.ONE else "lowvalid"
            canvas.create_line(x1, y, x2, y, tags=self._tags(kind))
            return

        bottom = top + slot_height
        lx = x1 if clipped_left else x1 + tilt
        rx = x2 if clipped_right else x2 - tilt
        ## Clockwise from the top-left corner: top edge, right point (unless
        ## squared off), bottom edge, left point (unless squared off).
        points = [lx, top, rx, top]
        if not clipped_right:
            points += [x2, mid]
        points += [rx, bottom, lx, bottom]
        if not clipped_left:
            points += [x1, mid]
        kind = "unknown" if value == tline.X else "valid"
        canvas.create_polygon(*points, tags=self._tags(kind))

    def _draw_transition(self, canvas: tk.Canvas, top: int,
                         x1: float, x2: float, before: str, after: str) -> None:
        """Draw the gap between two segments: the transition uncertainty.

        The polygon is the one an I/O signal draws: its left edge slants from
        the level of the previous value, its right edge to the level of the
        next one, each crossing mid-height at the exact boundary time. A
        zero-width gap degenerates into the single slanted edge an I/O signal
        draws when its min and max delays are equal.
        """
        slot_height = int(self.amplitude)
        tilt = self.settings.waveform["tilt"]
        bottom = top + slot_height
        mid = top + slot_height / 2

        ## Left edge, bottom to top.
        if before == tline.ZERO:
            left = [x1 - tilt, bottom, x1 + tilt, top]
        elif before == tline.ONE:
            left = [x1 + tilt, bottom, x1 - tilt, top]
        else:
            left = [x1 + tilt, bottom, x1, mid, x1 + tilt, top]

        ## Right edge, top to bottom.
        if after == tline.ONE:
            right = [x2 + tilt, top, x2 - tilt, bottom]
        elif after == tline.ZERO:
            right = [x2 - tilt, top, x2 + tilt, bottom]
        else:
            right = [x2 - tilt, top, x2, mid, x2 - tilt, bottom]

        canvas.create_polygon(*left, *right, tags=self._tags("transition"))

    def _draw_post_style(self, canvas: tk.Canvas) -> None:
        """Same styling as IOBaseSignal, for the tags a derived signal uses."""
        canvas.itemconfigure(f"{self.name}_transition",
                             fill="light grey", outline=self.color, width="1")
        canvas.itemconfigure(f"{self.name}_valid",
                             fill="white", outline=self.color, width=self.lwidth)
        canvas.itemconfigure(f"{self.name}_unknown",
                             stipple="gray50", outline=self.color,
                             width=self.lwidth)
        for kind in ("highvalid", "lowvalid"):
            canvas.itemconfigure(f"{self.name}_{kind}",
                                 fill=self.color, width=self.lwidth)

    def draw(self, canvas: tk.Canvas, top: int) -> int:
        """Render the computed timeline.

        Returns the vertical space consumed, or a negative value when the
        signal cannot be drawn. Note the convention: WaveformsCanvas
        .draw_signals() *removes* any signal whose draw() returns negative.
        """
        super().draw(canvas, top)
        top += self.top_padding

        computed = self.timeline()
        if computed is None:
            return -999

        self._draw_label(canvas, top)

        left, right = self._x_bounds(canvas)

        ## Levels first, transitions on top of them: a transition polygon
        ## overlaps the ends of its neighbouring level lines by `tilt`.
        visible: list[tuple[float, float, str]] = []
        for start, end, value in computed:
            x1, x2 = self._clip(canvas, left, right, start, end)
            if x2 <= x1:
                continue
            self._draw_level(canvas, top, x1, x2, value,
                             clipped_left=x1 <= left, clipped_right=x2 >= right)
            visible.append((x1, x2, value))

        for (_, x_end, before), (x_start, _, after) in zip(visible, visible[1:]):
            self._draw_transition(canvas, top, x_end, x_start, before, after)

        self._draw_post_style(canvas)

        if self._apply_hidden_state(canvas):
            return 0
        return self.top_padding + int(self.amplitude)
