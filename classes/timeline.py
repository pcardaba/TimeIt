# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2024 Pablo Cardaba

"""Pure timeline algebra for derived (logic and sampled) signals.

A *timeline* is a sorted list of ``(start, end, value)`` tuples with values
in ``{"0", "1", "X", "D"}``. Segments are half-open ``[start, end)``. The
first segment starts at ``-inf`` and the last ends at ``+inf``. A *gap*
between two consecutive segments is a transition window: the value there is
not merely unknown, it is undergoing a transition, and the gap is preserved
so the renderer can draw it as such.

Nothing in this module imports Tk or touches a canvas or a signal object. It
is deliberately pure so it can be unit tested (tests/test_timeline.py).
"""

from __future__ import annotations

import math

ZERO = "0"
ONE = "1"
X = "X"
D = "D"

Segment = tuple[float, float, str]

## Operators accepted by combine(). "not" is unary, the others n-ary.
OPERATORS = ("and", "or", "xor", "nand", "nor", "not")
UNARY_OPERATORS = ("not",)


def coalesce(segments: list[Segment]) -> list[Segment]:
    """Drop empty segments and merge *contiguous* segments of equal value.

    Segments separated by a gap are never merged, even when their values are
    equal: the gap is a transition window and carries meaning.
    """
    out: list[Segment] = []
    for start, end, value in segments:
        if start >= end:
            continue
        if out and out[-1][2] == value and out[-1][1] == start:
            out[-1] = (out[-1][0], end, value)
        else:
            out.append((start, end, value))
    return out


_STATE_VALUES = {"low": ZERO, "high": ONE, "unknown": X, "data": D}


def _state_value(state: str, pulled_up: bool) -> str:
    """The timeline value a state_intervals() state maps to.

    A released open-drain net sits at logic 1 when it has a pull-up, and
    floats at no defined level without one.
    """
    if state == "hiz":
        return ONE if pulled_up else X
    return _STATE_VALUES.get(state, X)


def flatten(intervals, *, pulled_up: bool = False) -> list[Segment] | None:
    """Convert ``state_intervals()`` output into a value timeline.

    ``None`` in, ``None`` out: ``state_intervals()`` returns ``None`` when the
    signal cannot be resolved, and that has to propagate to the caller.
    """
    if intervals is None:
        return None

    out: list[Segment] = []
    previous_end = -math.inf
    for start, end, state in intervals:
        if start > previous_end:
            ## The transition window between two established states.
            out.append((previous_end, start, X))
        out.append((start, end, _state_value(state, pulled_up)))
        previous_end = end

    if previous_end < math.inf:
        out.append((previous_end, math.inf, X))
    return coalesce(out)


def value_at(segments: list[Segment], t: float) -> str | None:
    """Value of ``segments`` at time ``t``, or None when ``t`` falls in a gap.

    Segments are half-open, so a time landing exactly on a boundary takes the
    value of the segment that starts there.
    """
    for start, end, value in segments:
        if start <= t < end:
            return value
    return None


## Two-input tables. Unknown propagates except where a controlling value
## masks it: 0 AND x = 0, 1 OR x = 1. xor has no controlling value.
_BINARY_TABLES = {
    "and": {("0", "0"): ZERO, ("0", "1"): ZERO, ("0", "X"): ZERO,
            ("1", "0"): ZERO, ("1", "1"): ONE,  ("1", "X"): X,
            ("X", "0"): ZERO, ("X", "1"): X,    ("X", "X"): X},
    "or":  {("0", "0"): ZERO, ("0", "1"): ONE,  ("0", "X"): X,
            ("1", "0"): ONE,  ("1", "1"): ONE,  ("1", "X"): ONE,
            ("X", "0"): X,    ("X", "1"): ONE,  ("X", "X"): X},
    "xor": {("0", "0"): ZERO, ("0", "1"): ONE,  ("0", "X"): X,
            ("1", "0"): ONE,  ("1", "1"): ZERO, ("1", "X"): X,
            ("X", "0"): X,    ("X", "1"): X,    ("X", "X"): X},
}

_NOT_TABLE = {ZERO: ONE, ONE: ZERO, X: X}

## nand / nor are the inverted fold of and / or: the controlling value still
## masks the unknown (0 NAND x = 1, 1 NOR x = 0).
_INVERTED = {"nand": "and", "nor": "or"}


def _lookup_not(value: str | None) -> str:
    try:
        return _NOT_TABLE[value]
    except KeyError:
        raise ValueError("not cannot be applied to bus data") from None


def _fold(op: str, values: list[str | None]) -> str:
    """Apply the n-ary operator to the values of every operand at one time.

    A ``None`` value (the operand is inside a transition window) counts as
    unknown. and/or/xor are associative, so the fold is order independent.
    """
    base = _INVERTED.get(op, op)
    table = _BINARY_TABLES[base]
    acc = X if values[0] is None else values[0]
    if acc == D:
        raise ValueError(f"{op} cannot be applied to bus data")
    for value in values[1:]:
        value = X if value is None else value
        try:
            acc = table[(acc, value)]
        except KeyError:
            raise ValueError(f"{op} cannot be applied to bus data") from None
    return _NOT_TABLE[acc] if op in _INVERTED else acc


def combine(op: str, operands: list[list[Segment]]) -> list[Segment]:
    """Apply ``op`` pointwise over the merged breakpoints of all operands.

    ``operands`` is a list of timelines: exactly one for ``not``, one or more
    for the n-ary operators (a single operand is a buffer). Because the
    breakpoints are merged rather than snapped to a clock grid, operands
    driven by different -- or entirely unrelated -- clocks combine correctly:
    their transitions simply interleave.

    Raises ValueError on an unknown operator, a wrong operand count, or a
    bus (``D``) operand: a bus window carries no scalar value.
    """
    if op not in OPERATORS:
        raise ValueError(f"{op} is not a valid logic operator")
    if not operands:
        raise ValueError(f"the {op} operator needs at least one operand")

    if op in UNARY_OPERATORS:
        if len(operands) != 1:
            raise ValueError(f"the {op} operator takes exactly one operand")
        return coalesce([(start, end, _lookup_not(value))
                         for start, end, value in operands[0]])

    bounds = sorted({bound
                     for segments in operands
                     for start, end, _ in segments
                     for bound in (start, end)})

    out: list[Segment] = []
    for start, end in zip(bounds, bounds[1:]):
        values = [value_at(segments, start) for segments in operands]
        out.append((start, end, _fold(op, values)))
    return coalesce(out)


def shift(segments: list[Segment], delay_max: float,
          delay_min: float | None = None) -> list[Segment]:
    """Delay a timeline by a propagation delay given as a max/min pair.

    A value is only established once the slow path has propagated, so every
    segment *start* moves by ``delay_max``; it may begin changing as soon as
    the fast path does, so every segment *end* moves by ``delay_min``. The
    spread ``delay_max - delay_min`` therefore widens every transition window
    by that amount, exactly like the min/max delays of an I/O signal. A
    segment shorter than the spread is swallowed whole: a pulse narrower than
    the delay uncertainty is entirely uncertain.

    ``delay_min`` defaults to ``delay_max`` (a pure shift). Infinite
    boundaries are left alone.
    """
    if delay_min is None:
        delay_min = delay_max
    if delay_min > delay_max:
        raise ValueError("minimum delay can not exceed maximum delay")
    if not delay_max and not delay_min:
        return segments

    def moved(t: float, delay: float) -> float:
        return t if math.isinf(t) else t + delay

    return coalesce([(moved(start, delay_max), moved(end, delay_min), value)
                     for start, end, value in segments])


def _sampled_value(source: list[Segment], t: float,
                   setup: float, hold: float) -> str:
    """The value a flip-flop clocked at ``t`` captures from ``source``.

    The aperture is half-open ``[t - setup, t + hold)``, so the marginal cases
    meet their requirement as timing convention expects: a transition window
    ending exactly at ``t - setup`` has settled in time, and one starting
    exactly at ``t + hold`` has held long enough.

    Anything but a single stable value across the whole aperture -- two
    values, an X, or a gap -- captures as X.
    """
    low, high = t - setup, t + hold

    if high <= low:
        ## Degenerate aperture: a point lookup under the half-open rule.
        value = value_at(source, t)
        return value if value in (ZERO, ONE, D) else X

    seen = {value for start, end, value in source
            if start < high and end > low}

    ## A gap in the source is not covered by any segment, so the covered
    ## length has to be checked as well: a partially covered aperture is a
    ## transition window and captures as X.
    covered = sum(min(end, high) - max(start, low)
                  for start, end, _ in source
                  if start < high and end > low)

    if len(seen) == 1 and abs(covered - (high - low)) < 1e-12:
        value = seen.pop()
        return value if value in (ZERO, ONE, D) else X
    return X


def sample(source: list[Segment], edge_times, *,
           setup: float = 0.0, hold: float = 0.0,
           tco_max: float = 0.0, tco_min: float = 0.0) -> list[Segment]:
    """Resample ``source`` at each time in ``edge_times``, flip-flop style.

    The output holds each captured value until the next sampling edge, so a
    captured X persists to the next edge -- and beyond, when that edge
    captures X too. Consecutive edges capturing the same value produce one
    segment with no transition between them: a flip-flop whose output does
    not change does not glitch.

    The output is X before the first sampling edge: a flip-flop has no
    defined value before it is first clocked. The clock-to-output spread
    ``tco_max - tco_min`` is the transition window on each output change.
    """
    ## Seeding the runs with X at -inf both gives the undefined initial state
    ## and makes a first captured X merge into it rather than opening a
    ## spurious transition window.
    runs: list[tuple[float, str]] = [(-math.inf, X)]
    for t in sorted(edge_times):
        value = _sampled_value(source, t, setup, hold)
        if runs[-1][1] != value:
            runs.append((t, value))

    def moved(t: float, delay: float) -> float:
        return t if math.isinf(t) else t + delay

    out: list[Segment] = []
    for i, (t, value) in enumerate(runs):
        end = (moved(runs[i + 1][0], tco_min) if i + 1 < len(runs)
               else math.inf)
        out.append((moved(t, tco_max), end, value))
    return coalesce(out)
