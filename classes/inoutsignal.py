# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2024 Pablo Cardaba

"""Bidirectional (inout) signal: an input and an output sharing one port.

Seen from the device port, a bidirectional signal is driven from outside at
some times (its *input part*) and by the device at others (its *output
part*). ``InOutSignal`` is therefore a composite: it owns an input part and
an output part, each a full I/O signal with its own launch/capture clocks,
delays and edge lists, and draws both in the same slot. What belongs to the
port is held once, by the composite: the name, the style, the delay
specification (internal or external, the same for both parts) and the
pull-up.

Two things make it more than two waveforms on top of each other:

- **Hi-Z is the port being released.** A part that is Hi-Z does not drive,
  so its Hi-Z line is only drawn where the other part does not drive either.
  Without that every reception would be struck through by the Hi-Z line of
  the output part.
- **Contention.** Where both parts may drive the port at the same time the
  zone is marked and a warning is logged. It is only a warning: showing a
  contention may be the very purpose of the diagram.

Both are decided from the analytic (canvas-free) timelines of the parts, so
that the visible and the virtual canvas always draw the same elements under
the same uid tags, whatever the zoom.
"""

from __future__ import annotations

import math
from typing import TextIO

import tkinter as tk

from .signal import Signal, TRANSITIONS_TAG
from .inputsignal import InputSignal
from .outputsignal import OutputSignal

STATES = ("data", "hiz", "high", "low", "unknown")
_CLOCK_EDGES = ("rclk", "fclk")
_BOUNDS = ("max", "min")


class _InOutPart:
    """What the two parts of a bidirectional signal have in common.

    A part is never in the signals store: it is reached through its owner,
    draws under the owner's name and uid, and leaves its Hi-Z lines to it.
    """

    def _init_part(self, owner: "InOutSignal") -> None:
        self.owner = owner
        ## The Hi-Z lines and the pull-up rises of the last draw, as the
        ## polylines the part would have drawn by itself. The owner draws
        ## what remains of them.
        self.hiz_lines: list[list[float]] = []
        self.pullup_lines: list[list[float]] = []

    def uidtag(self) -> str:
        """Element tags are numbered across both parts, by the owner."""
        return self.owner.uidtag()

    def sync(self) -> None:
        """Take over what belongs to the port from the owner."""
        owner = self.owner
        self.name = owner.name
        self.uid = owner.uid
        self.style = owner.style
        self.visible = owner.visible
        self.specify = owner.specify
        self.pulled_up = owner.pulled_up
        self.console = owner.console
        self.settings = owner.settings

    def prepare(self, canvas: tk.Canvas) -> bool:
        """Resolve the clocks and the delays. False when they can not be."""
        if not self.resolve_clock_params():
            return False
        self._set_waveform_span(canvas)
        return self._resolve_delay_params()

    def draw_part(self, canvas: tk.Canvas, top: int) -> None:
        self.hiz_lines = []
        self.pullup_lines = []
        ## Nothing is closed yet: what the previous draw closed last must not
        ## decide how the first state of this one opens (the timelines the
        ## owner works from know no state before the first one either).
        self.last_closed = None
        self.last_x = None
        self._draw_states(canvas, top)

    def _draw_hiz_line(self, canvas: tk.Canvas, points: list[float]) -> None:
        self.hiz_lines.append(points)

    def _draw_pullup_line(self, canvas: tk.Canvas, points: list[float]) -> None:
        self.pullup_lines.append(points)

    def span_end(self) -> float:
        """Time the waveform of this part ends at (its launch clock span)."""
        return self.launchclk.cycles * self.lclk["period"]


class InOutInputPart(_InOutPart, InputSignal):
    """The port driven from outside and captured by the device."""

    ## How write_sdc calls the part in its comments and messages.
    sdc_kind = "inout input part"

    def __init__(self, owner: "InOutSignal") -> None:
        ## A part is not a signal of its own: it must not use up a uid.
        next_uid = Signal.static_id
        InputSignal.__init__(self, owner.name)
        Signal.static_id = next_uid
        self._init_part(owner)


class InOutOutputPart(_InOutPart, OutputSignal):
    """The port driven by the device and captured outside."""

    sdc_kind = "inout output part"

    def __init__(self, owner: "InOutSignal") -> None:
        next_uid = Signal.static_id
        OutputSignal.__init__(self, owner.name)
        Signal.static_id = next_uid
        self._init_part(owner)

    def _oe_delays_at(self, index: int, launch_pol: str) -> tuple[float, float]:
        """Analytic twin of _get_oe_delays()."""
        if self.specify == "internal":
            return self._internal_delays(self.oedly, launch_pol)
        return self._delays_at(index, launch_pol)

    def _transition_window(self, index: int, launch_pol: str, state: str,
                           previous: str | None) -> tuple[float, float]:
        """The window of a change, the output enable delays included.

        Follows what the drawing does: releasing the port takes the output
        enable delays (it may start as early as the fastest of the output
        and enable paths), and driving it again starts with the enable path
        and is established once both paths are.
        """
        dlymax, dlymin = self._delays_at(index, launch_pol)
        if state == "hiz":
            oemax, oemin = self._oe_delays_at(index, launch_pol)
            return (oemax, min(oemin, dlymin))
        if previous == "hiz":
            oemax, oemin = self._oe_delays_at(index, launch_pol)
            return (max(dlymax, oemax), oemin)
        return (dlymax, dlymin)


## Options of create_inout that belong to a part, in the order they are
## written: (attribute of the InOutSignal, attribute of the part, kind).
## The delay names tell the part by themselves; the names both parts share
## (clocks, latencies, edge lists) take an "in_" / "out_" prefix.
def _part_options(prefix: str, delay_groups: tuple[str, ...]) -> list[tuple[str, str, str]]:
    options = [(f"{prefix}_launch_clock", "launch_clock", "clock"),
               (f"{prefix}_capture_clock", "capture_clock", "clock")]
    for group in delay_groups:
        for edge in _CLOCK_EDGES:
            for bound in _BOUNDS:
                attr = f"{edge}_{group}_{bound}"
                options.append((attr, attr, "expr"))
    for edge in _CLOCK_EDGES:
        for bound in _BOUNDS:
            attr = f"{edge}_latency_{bound}"
            options.append((f"{prefix}_{attr}", attr, "expr"))
    for state in STATES:
        options.append((f"{prefix}_{state}_edges", f"{state}_edges", "edges"))
    return options


IN_OPTIONS = _part_options("in", ("inputdly",))
OUT_OPTIONS = _part_options("out", ("outputdly", "oedly"))


class InOutSignal(Signal):
    """A bidirectional port: an input part and an output part in one slot."""

    ## Zones listed by a warning before it says "and N more".
    MAX_ZONES_LISTED = 4

    def __init__(self, name: str) -> None:
        super().__init__(name, sig_type="inout")
        ## The delay specification is a property of the port: both parts are
        ## specified the same way.
        self.specify: str = "internal"
        self.pulled_up: bool = False
        ## The contention zones are marked unless told otherwise.
        self.hide_contention: bool = False

        self.inpart = InOutInputPart(self)
        self.outpart = InOutOutputPart(self)

        ## Warnings logged at the last draw, so that a redraw does not
        ## repeat them (same rule as the starved edges of an I/O signal).
        self._warnings_reported: tuple[str, ...] = ()

    @property
    def parts(self) -> tuple[_InOutPart, _InOutPart]:
        return (self.inpart, self.outpart)

    @property
    def data_edges(self) -> list[str]:
        """Bus data edges of either part: a derived signal can not combine them."""
        return list(self.inpart.data_edges) + list(self.outpart.data_edges)

    def _sync_parts(self) -> None:
        for part in self.parts:
            part.sync()

    def set_tcl_console(self, console) -> None:
        super().set_tcl_console(console)
        self._sync_parts()

    # ------------------------------------------------------------------
    # Relationships
    # ------------------------------------------------------------------
    def related_clocks(self) -> tuple:
        """The clocks of both parts, each once."""
        clocks = [clock for part in self.parts
                  for clock in part.related_clocks()]
        return tuple(dict.fromkeys(clocks))

    # ------------------------------------------------------------------
    # Serialization
    # ------------------------------------------------------------------
    def write(self, fileref: TextIO) -> None:
        fileref.write(f"\ncreate_inout -name {self.name}  \\\n")
        fileref.write(f"   -specify {self.specify}  \\\n")

        for options in (IN_OPTIONS, OUT_OPTIONS):
            for option, _attr, kind in options:
                value = getattr(self, option)
                if kind == "clock":
                    if value is not None:
                        fileref.write(f"   -{option} {value.name}  \\\n")
                elif kind == "expr":
                    if value is not None:
                        fileref.write(f"   -{option} {{{value}}}  \\\n")
                elif value:
                    fileref.write(f"   -{option} {{{' '.join(value)}}}  \\\n")

        if self.pulled_up:
            fileref.write("   -pulled_up  \\\n")
        if self.hide_contention:
            fileref.write("   -hide_contention  \\\n")
        self._write_common_args(fileref)
        super().write(fileref)

    # ------------------------------------------------------------------
    # Analytic timelines
    # ------------------------------------------------------------------
    def _part_events(self) -> tuple[list | None, list | None]:
        """state_events() of the input and of the output part."""
        self._sync_parts()
        for part in self.parts:
            if part.launchclk is None or part.captureclk is None:
                return (None, None)
        return (self.inpart.state_events(), self.outpart.state_events())

    @staticmethod
    def _stable_spans(events: list) -> list[tuple[float, float, str]]:
        """(established, begin of the next change, state) of every state."""
        return [(established,
                 events[i + 1][0] if i + 1 < len(events) else math.inf,
                 state)
                for i, (_begin, established, state) in enumerate(events)]

    @staticmethod
    def _possible_spans(events: list) -> list[tuple[float, float, str]]:
        """(begin, next state established, state): when a state may be on.

        Wider than the stable span by the transition windows at both ends:
        during a transition the port may still be, or may already be, in
        either of the two states.
        """
        return [(begin,
                 events[i + 1][1] if i + 1 < len(events) else math.inf,
                 state)
                for i, (begin, _established, state) in enumerate(events)]

    def _tolerance(self) -> float:
        """Time below which two instants are the same (a period fraction)."""
        periods = [abs(part.lclk["period"]) for part in self.parts]
        return max(periods + [0.0]) * 1e-9

    def contention_zones(self) -> list[tuple[float, float]] | None:
        """Time ranges where both parts may drive the port at once.

        A part drives in every state but Hi-Z, and may be driving all along
        the transition windows that lead to and from such a state: a release
        that may end after the other side may already drive is a contention,
        which is exactly what a bus turnaround time is there to avoid. With
        a pull-up the port is an open-drain line: both sides pulling it low
        is not a conflict.

        Sorted and merged; the first may start at -inf, the last end at
        +inf. None when the signal can not be resolved.
        """
        return self._contention_zones(*self._part_events())

    def _contention_zones(self, in_events: list | None,
                          out_events: list | None) -> list | None:
        if in_events is None or out_events is None:
            return None

        tol = self._tolerance()
        raw: list[tuple[float, float]] = []
        for in0, in1, in_state in self._possible_spans(in_events):
            if in_state == "hiz":
                continue
            for out0, out1, out_state in self._possible_spans(out_events):
                if out_state == "hiz":
                    continue
                if self.pulled_up and in_state == out_state == "low":
                    continue
                start, end = max(in0, out0), min(in1, out1)
                if end - start > tol:
                    raw.append((start, end))

        zones: list[tuple[float, float]] = []
        for start, end in sorted(raw):
            if zones and start <= zones[-1][1] + tol:
                zones[-1] = (zones[-1][0], max(zones[-1][1], end))
            else:
                zones.append((start, end))
        return zones

    def _zones_text(self, zones: list[tuple[float, float]]) -> str:
        tunits = ""
        if self.settings is not None:
            tunits = " " + str(self.settings.waveform["tunits"])

        def moment(t: float, infinite: str) -> str:
            return infinite if math.isinf(t) else f"{t:g}"

        texts = [f"from {moment(start, 'the start')} to "
                 f"{moment(end, 'the end')}{tunits}"
                 for start, end in zones[:self.MAX_ZONES_LISTED]]
        if len(zones) > self.MAX_ZONES_LISTED:
            texts.append(f"and {len(zones) - self.MAX_ZONES_LISTED} more")
        return ", ".join(texts)

    def definition_warnings(self) -> list[str]:
        """What looks wrong in the definition, as sentences. Empty when fine.

        Shared by the console (logged when the signal is drawn) and by the
        dialog (shown when the definition is applied). Nothing here prevents
        the signal from being created.
        """
        return self._definition_warnings(*self._part_events())

    def _definition_warnings(self, in_events: list | None,
                             out_events: list | None) -> list[str]:
        if in_events is None or out_events is None:
            return []

        warnings: list[str] = []
        if not in_events:
            warnings.append("the input part has no launch edge: the port "
                            "never receives (give its edge lists, or use an "
                            "output signal)")
        if not out_events:
            warnings.append("the output part has no launch edge: the port "
                            "never drives (give its edge lists, or use an "
                            "input signal)")

        zones = self._contention_zones(in_events, out_events)
        if zones:
            warnings.append(
                f"possible port contention, the input and the output part "
                f"may both drive the port {self._zones_text(zones)}: a part "
                f"must be Hi-Z while the other one drives")
        return warnings

    def state_intervals(self) -> list[tuple[float, float, str]] | None:
        """Analytic (start, end, state) timeline of the port.

        What a derived signal or a timing computation reads: the state of
        the part that drives, Hi-Z when none does, and unknown where both
        do (unless they agree on a level). A part with no state yet does
        not drive. Where a part is changing the port is changing: those
        ranges are left out, as the transition windows of any signal are.
        """
        in_events, out_events = self._part_events()
        if in_events is None or out_events is None:
            return None

        timelines = []
        for events in (in_events, out_events):
            defined_from = events[0][0] if events else math.inf
            timelines.append((defined_from, self._stable_spans(events)))

        def state_at(timeline, t: float) -> str | None:
            defined_from, spans = timeline
            if t < defined_from:
                return "hiz"
            for start, end, state in spans:
                if start <= t < end:
                    return state
            return None

        bounds = sorted({bound
                         for defined_from, spans in timelines
                         for start, end, _ in spans
                         for bound in (defined_from, start, end)}
                        | {-math.inf, math.inf})
        earliest = min(defined_from for defined_from, _ in timelines)

        intervals: list[tuple[float, float, str]] = []
        for start, end in zip(bounds, bounds[1:]):
            if start >= end or start < earliest:
                continue
            in_state = state_at(timelines[0], start)
            out_state = state_at(timelines[1], start)
            if in_state is None or out_state is None:
                continue
            if in_state == "hiz":
                state = out_state
            elif out_state == "hiz":
                state = in_state
            elif in_state == out_state and in_state in ("high", "low"):
                state = in_state
            else:
                state = "unknown"
            if intervals and intervals[-1][2] == state \
               and intervals[-1][1] == start:
                intervals[-1] = (intervals[-1][0], end, state)
            else:
                intervals.append((start, end, state))
        return intervals

    # ------------------------------------------------------------------
    # Drawing
    # ------------------------------------------------------------------
    def _released_ranges(self, part: _InOutPart, events: list,
                         canvas: tk.Canvas) -> list[tuple] | None:
        """Where `part` leaves the port alone: (t0, t1, x0, x1, line).

        Its Hi-Z states, each with the polyline the part would have drawn
        for it (`line`), and the ranges it has no state at all (before its
        first edge, after the span of its launch clock), with no line. In
        time order. None when the Hi-Z lines drawn do not match the Hi-Z
        states (an edge of the lists the launch clock does not have).
        """
        hiz = [(start, end) for start, end, state in self._stable_spans(events)
               if state == "hiz"]
        if len(hiz) != len(part.hiz_lines):
            return None

        ranges: list[tuple] = []
        first = events[0][0] if events else math.inf
        if first > -math.inf:
            x_first = math.inf if math.isinf(first) else canvas.time_to_x(first)
            ranges.append((-math.inf, first, -math.inf, x_first, None))
        ## The last state is drawn up to the end of the launch clock span.
        span_end = part.span_end()
        for (start, end), line in zip(hiz, part.hiz_lines):
            ranges.append((start, min(end, span_end), line[0], line[-2], line))
        if events:
            ranges.append((span_end, math.inf, part.wfends_x, math.inf, None))
        return ranges

    @staticmethod
    def _merge_ranges(ranges: list[tuple], tol: float) -> list[tuple]:
        """Join the released ranges that touch: (t0, t1, x0, x1)."""
        merged: list[tuple] = []
        for t0, t1, x0, x1, _line in ranges:
            if t1 <= t0:
                continue
            if merged and t0 <= merged[-1][1] + tol:
                merged[-1] = (merged[-1][0], max(merged[-1][1], t1),
                              merged[-1][2], max(merged[-1][3], x1))
            else:
                merged.append((t0, t1, x0, x1))
        return merged

    @staticmethod
    def _clip_polyline(points: list[float], x_from: float,
                       x_to: float) -> list[float]:
        """The part of a polyline running along x that is within [x_from, x_to].

        Always a line, be it a single point: whether a piece exists is
        decided in time, and must not depend on the canvas it is drawn on.
        """
        xs, ys = points[0::2], points[1::2]
        if any(b < a for a, b in zip(xs, xs[1:])):
            ## Folded back on itself (a Hi-Z shorter than its own
            ## transitions): nothing to cut, it is kept or dropped whole.
            return list(points)

        low = min(max(x_from, xs[0]), xs[-1])
        high = max(min(x_to, xs[-1]), low)

        def y_at(x: float) -> float:
            for i in range(len(xs) - 1):
                if xs[i] <= x <= xs[i + 1]:
                    if xs[i + 1] == xs[i]:
                        return ys[i + 1]
                    ratio = (x - xs[i]) / (xs[i + 1] - xs[i])
                    return ys[i] + ratio * (ys[i + 1] - ys[i])
            return ys[-1]

        clipped = [low, y_at(low)]
        for x, y in zip(xs, ys):
            if low < x < high:
                clipped += [x, y]
        clipped += [high, y_at(high)]
        return clipped

    def _hiz_pieces(self, canvas: tk.Canvas, in_events: list | None,
                    out_events: list | None) -> list[list[float]]:
        """The Hi-Z lines of the port, left to right.

        The port is Hi-Z where no part drives it. The output part draws its
        Hi-Z lines where the input part is Hi-Z too, or has no state; the
        input part only where the output part has no state, so that a range
        both release is drawn once.
        """
        released = None
        if in_events is not None and out_events is not None:
            released = (self._released_ranges(self.inpart, in_events, canvas),
                        self._released_ranges(self.outpart, out_events, canvas))
        if released is None or None in released:
            ## Not resolvable analytically: every line as its part drew it.
            return [line for part in (self.outpart, self.inpart)
                    for line in part.hiz_lines]

        tol = self._tolerance()
        in_released, out_released = released
        out_undefined = [r for r in out_released if r[4] is None]

        pieces: list[tuple[float, int, list[float]]] = []
        for order, (own, allowed) in enumerate((
                (out_released, self._merge_ranges(in_released, tol)),
                (in_released, self._merge_ranges(out_undefined, tol)))):
            for t0, t1, x0, x1, line in own:
                if line is None:
                    continue
                for a0, a1, ax0, ax1 in allowed:
                    start, end = max(t0, a0), min(t1, a1)
                    if end - start <= tol:
                        continue
                    ## The ends of a piece are where a line of either part
                    ## starts or ends on this canvas: the pieces then meet
                    ## the transitions they lead to exactly.
                    piece = self._clip_polyline(line,
                                                x0 if start == t0 else ax0,
                                                x1 if end == t1 else ax1)
                    pieces.append((start, order, piece))

        pieces.sort(key=lambda piece: piece[:2])
        return [piece for _start, _order, piece in pieces]

    def _draw_hiz_lines(self, canvas: tk.Canvas, in_events: list | None,
                        out_events: list | None) -> None:
        for piece in self._hiz_pieces(canvas, in_events, out_events):
            self._create_piece(canvas, piece, f"{self.name}_hizvalid")

    def _create_piece(self, canvas: tk.Canvas, piece: list[float],
                      *tags: str) -> None:
        """A line cut down by the other part, kept even when nothing is left.

        Both canvases must number the same elements: a piece cut down to
        nothing is still created, hidden (a single point would show as a dot
        of the line width).
        """
        item = canvas.create_line(
            *piece, tags=(self.uidtag(), *tags, f"{self.name}_waveform"))
        if piece[-2] <= piece[0]:
            canvas.itemconfigure(item, state="hidden")

    @staticmethod
    def _pullup_rises(events: list) -> list[float]:
        """Times the pull-up rises of a part start at, in drawing order.

        IOBaseSignal._draw_hiz_open() draws a rise on every release that
        does not come from an already high or released line, except at the
        "0" pseudo-edge: the release begins (edge time + min delay).
        """
        starts = []
        for i, (begin, _established, state) in enumerate(events):
            previous = events[i - 1][2] if i else None
            if state == "hiz" and begin > -math.inf \
               and previous not in ("hiz", "high"):
                starts.append(begin)
        return starts

    def _pullup_pieces(self, canvas: tk.Canvas, in_events: list | None,
                       out_events: list | None) -> list[list[float]]:
        """The pull-up rises of both parts, each stopped where the other takes the line.

        A released pulled-up line rises until something drives it. The rise
        of a part therefore stops where the other part is established in a
        driving state (the end of its transition window, the latest it takes
        the line): it would otherwise run on, up to the full level, across a
        line that is already driven.
        """
        pieces: list[list[float]] = []
        for part, own, other in ((self.inpart, in_events, out_events),
                                 (self.outpart, out_events, in_events)):
            starts = None if own is None else self._pullup_rises(own)
            if other is None or starts is None \
               or len(starts) != len(part.pullup_lines):
                ## Not resolvable analytically: the rises as the part drew them.
                pieces.extend(part.pullup_lines)
                continue

            driven = [(start, end) for start, end, state
                      in self._stable_spans(other) if state != "hiz"]
            for begin, line in zip(starts, part.pullup_lines):
                cut = next((max(begin, start) for start, end in driven
                            if end > begin), math.inf)
                if math.isinf(cut):
                    pieces.append(line)
                    continue
                x_cut = line[0] + (cut - begin) * canvas.scale_factor
                pieces.append(self._clip_polyline(line, line[0], x_cut))
        return pieces

    def _draw_pullup_lines(self, canvas: tk.Canvas, in_events: list | None,
                           out_events: list | None) -> None:
        for piece in self._pullup_pieces(canvas, in_events, out_events):
            self._create_piece(canvas, piece, TRANSITIONS_TAG,
                               f"{self.name}_pu_transition")

    def _draw_contention(self, canvas: tk.Canvas, top: int,
                         in_events: list | None,
                         out_events: list | None) -> None:
        """Mark the zones where both parts may drive the port."""
        if self.hide_contention:
            return
        zones = self._contention_zones(in_events, out_events)
        if not zones:
            return

        ## Cut to the diagram in time, not in pixels: both canvases must
        ## draw the same zones.
        span_end = max(part.span_end() for part in self.parts)
        bottom = top + int(self.amplitude)
        for start, end in zones:
            start, end = max(start, 0.0), min(end, span_end)
            if end <= start:
                continue
            x1, x2 = canvas.time_to_x(start), canvas.time_to_x(end)
            canvas.create_polygon(x1, top, x2, top, x2, bottom, x1, bottom,
                                  tags=(self.uidtag(),
                                        f"{self.name}_contention",
                                        f"{self.name}_waveform"))

    def _draw_post_style(self, canvas: tk.Canvas) -> None:
        self.inpart._draw_post_style(canvas)
        canvas.itemconfigure(f"{self.name}_contention",
                             fill="red", stipple="gray25",
                             outline="red", width="1")

    def _report_warnings(self, canvas: tk.Canvas, in_events: list | None,
                         out_events: list | None) -> None:
        """Log the definition warnings, once per change of them."""
        if canvas.is_virtual or self.console is None:
            return
        warnings = tuple(self._definition_warnings(in_events, out_events))
        if warnings == self._warnings_reported:
            return
        self._warnings_reported = warnings
        for warning in warnings:
            self.console.append_log(
                f"[{self.__class__.__name__}] {self.name}: {warning}\n",
                "warning")

    def draw(self, canvas: tk.Canvas, top: int) -> int:
        super().draw(canvas, top)
        self._sync_parts()

        for part in self.parts:
            if not part.prepare(canvas):
                return -999
        top += self.top_padding

        self._draw_label(canvas, top)

        in_events, out_events = self._part_events()
        ## The output part on top: where both drive, what the device itself
        ## puts on the port is what the diagram is usually about.
        for part in self.parts:
            part.draw_part(canvas, top)
        self._draw_pullup_lines(canvas, in_events, out_events)
        self._draw_hiz_lines(canvas, in_events, out_events)
        self._draw_contention(canvas, top, in_events, out_events)

        for part in self.parts:
            part._report_starved_edges(canvas)
        self._report_warnings(canvas, in_events, out_events)
        self._draw_post_style(canvas)

        if self._apply_hidden_state(canvas):
            return 0
        return self.top_padding + int(self.amplitude)


def _delegated(part_name: str, attr: str) -> property:
    """An attribute of the signal that lives on one of its parts."""
    def getter(self):
        return getattr(getattr(self, part_name), attr)

    def setter(self, value):
        setattr(getattr(self, part_name), attr, value)

    return property(getter, setter)


## Every create_inout option of a part is an attribute of the signal, named
## as the option: the command, the dialog, write() and set_attribute all
## address the parts through them.
for _option, _attr, _kind in IN_OPTIONS:
    setattr(InOutSignal, _option, _delegated("inpart", _attr))
for _option, _attr, _kind in OUT_OPTIONS:
    setattr(InOutSignal, _option, _delegated("outpart", _attr))
