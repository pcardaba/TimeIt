from __future__ import annotations

import math
import re
from pathlib import Path
from typing import TextIO

import tkinter as tk

from .signal import Signal


# ----------------------------------------------------------------------
# PWL file parsing
# ----------------------------------------------------------------------

## SPICE number suffixes, as powers of ten. The match is case-insensitive,
## as in SPICE: "M" is milli (not mega, which is "MEG") and "F" is femto
## (not Farad).
_SI_EXP = {
    "t": 12, "g": 9, "k": 3,
    "m": -3, "u": -6, "n": -9, "p": -12, "f": -15,
}

## Power of ten of each supported time unit, relative to the second.
_TUNITS_EXP = {"s": 0, "ms": -3, "us": -6, "ns": -9, "ps": -12, "fs": -15}

_NUMBER_RE = re.compile(
    r"^([+-]?(?:\d+\.?\d*|\.\d+)(?:[eE][+-]?\d+)?)\s*([A-Za-z]*)$")

## Column separators: ",", ";", a tab, or two or more spaces.
_SEP_RE = re.compile(r"\s*[,;]\s*|\t+|[ ]{2,}")


class PWLFileError(ValueError):
    """A PWL file can not be read or parsed."""


def _scale10(value: float, exp: int) -> float:
    """value * 10**exp, exact for the usual unit conversions (50ns -> 50)."""
    if exp >= 0:
        return value * (10 ** exp)
    return value / (10 ** (-exp))


def _parse_si_parts(token: str) -> tuple[float, int, str]:
    """(mantissa, power of ten of the SI prefix, unit letters)."""
    text = token.strip().replace("µ", "u")
    m = _NUMBER_RE.match(text)
    if m is None:
        raise ValueError(f"'{token}' is not a number")
    value = float(m.group(1))
    suffix = m.group(2)
    lowered = suffix.lower()

    if lowered.startswith("meg"):
        return value, 6, suffix[3:]
    ## A bare "s" (seconds) has no prefix; "ms"/"ns"... do. The lone
    ## letters "f", "m", "p"... are prefixes without unit (SPICE).
    if lowered and lowered != "s" and lowered[0] in _SI_EXP:
        return value, _SI_EXP[lowered[0]], suffix[1:]
    return value, 0, suffix


def parse_si_value(token: str) -> tuple[float, str]:
    """Parse "10mV", "400e-3", "1.4V", "5ns" into (value, unit).

    The SI prefix is applied to the value (SPICE semantics: "m" is milli,
    "meg" is mega, the match is case-insensitive). The unit letters that
    follow the prefix are returned untouched and not interpreted ("V", "A",
    "s", ...), an empty string when the number is dimensionless.
    """
    value, exp, unit = _parse_si_parts(token)
    return _scale10(value, exp), unit


def parse_time_token(token: str, tunits: str) -> float:
    """A time token converted into the diagram time units.

    A number without unit is already in `tunits`. A number followed by a
    time unit (s, ms, us, ns, ps, fs) is converted.
    """
    value, exp, unit = _parse_si_parts(token)
    if unit == "":
        return _scale10(value, exp)
    if unit.lower() != "s":
        raise ValueError(f"'{token}': unknown time unit '{unit}'")
    return _scale10(value, exp - _TUNITS_EXP.get(tunits, 0))


def split_columns(line: str) -> list[str]:
    """Split a data line into its columns."""
    cols = [c for c in _SEP_RE.split(line.strip()) if c.strip() != ""]
    if len(cols) != 2:
        ## Be lenient with a single space separator.
        cols = line.split()
    return [c.strip() for c in cols]


def parse_pwl_text(text: str, tunits: str,
                   source: str = "<pwl>") -> tuple[list[tuple[float, float]], str]:
    """Parse the content of a PWL file.

    Returns the (time, value) points, time in `tunits`, and the unit letters
    found in the value column ("" when dimensionless). Blank lines and lines
    starting with "#" are ignored.
    """
    points: list[tuple[float, float]] = []
    units = ""
    for lineno, raw in enumerate(text.splitlines(), start=1):
        line = raw.strip()
        if line == "" or line.startswith("#"):
            continue
        cols = split_columns(line)
        if len(cols) != 2:
            raise PWLFileError(
                f"{source}:{lineno}: expected 2 columns (time, value), "
                f"got {len(cols)}: '{line}'")
        try:
            t = parse_time_token(cols[0], tunits)
            value, unit = parse_si_value(cols[1])
        except ValueError as exc:
            raise PWLFileError(f"{source}:{lineno}: {exc}") from exc
        if points and t < points[-1][0]:
            raise PWLFileError(
                f"{source}:{lineno}: time {cols[0]} goes backwards "
                f"(previous point at {points[-1][0]:g} {tunits})")
        if unit and not units:
            units = unit
        points.append((t, value))

    if not points:
        raise PWLFileError(f"{source}: no data points found")
    return points, units


def parse_pwl_file(path: str | Path, tunits: str) -> tuple[list[tuple[float, float]], str]:
    path = Path(path)
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise PWLFileError(f"can not read '{path}': {exc}") from exc
    return parse_pwl_text(text, tunits, source=path.name)


def eng_format(value: float, units: str = "", digits: int = 3) -> str:
    """Engineering notation with an SI prefix: 0.4 -> "400m", 1.4e-6 -> "1.4u"."""
    if value == 0 or not math.isfinite(value):
        return f"{value:g}{units}"
    exp3 = int(math.floor(math.log10(abs(value)) / 3.0)) * 3
    exp3 = max(-15, min(12, exp3))
    mant = value / (10.0 ** exp3)
    prefix = {12: "T", 9: "G", 6: "M", 3: "k", 0: "",
              -3: "m", -6: "u", -9: "n", -12: "p", -15: "f"}[exp3]
    text = f"{mant:.{digits}g}"
    if "e" in text:   # rounding pushed the mantissa to 1000
        return eng_format(float(text) * (10.0 ** exp3), units, digits)
    return f"{text}{prefix}{units}"


# ----------------------------------------------------------------------
# Traces and slot signal
# ----------------------------------------------------------------------

class PWLTrace:
    """One PWL waveform drawn in a PWL slot."""

    LINE_STYLES = {
        "solid": None,
        "dash": (6, 3),
        "dot": (1, 2),
        "dashdot": (6, 3, 1, 3),
    }
    DEFAULTS = {"color": "black", "lstyle": "solid", "lwidth": 2,
                "scale": 1.0, "offset": 0.0, "visible": True}

    def __init__(self, name: str, file: str) -> None:
        self.name: str = name
        self.file: str = file        # as given by the user (written back as is)
        self.color: str = "black"
        self.lstyle: str = "solid"
        self.lwidth: int = 2
        self.scale: float = 1.0
        self.offset: float = 0.0
        self.visible: bool = True

        self.resolved: str = file  # absolute path actually read
        self.points: list[tuple[float, float]] = []
        self.units: str = ""
        self.vmin: float = 0.0
        self.vmax: float = 0.0

    def load(self, tunits: str, base_dir: str | Path | None = None) -> None:
        """Read the PWL file. Raises PWLFileError."""
        path = Path(self.file).expanduser()
        if not path.is_absolute() and base_dir is not None:
            path = Path(base_dir) / path
        self.points, self.units = parse_pwl_file(path, tunits)
        self.resolved = str(path.resolve())
        values = [v for _, v in self.points]
        self.vmin, self.vmax = min(values), max(values)

    def copy_style_from(self, other: PWLTrace) -> None:
        for attr in self.DEFAULTS:
            setattr(self, attr, getattr(other, attr))

    @property
    def t_start(self) -> float:
        return self.points[0][0] if self.points else 0.0

    @property
    def t_end(self) -> float:
        return self.points[-1][0] if self.points else 0.0

    def value_at(self, t: float) -> float | None:
        """Linear interpolation of the waveform at time `t` (None outside)."""
        pts = self.points
        if not pts or t < pts[0][0] or t > pts[-1][0]:
            return None
        for i in range(1, len(pts)):
            t0, v0 = pts[i - 1]
            t1, v1 = pts[i]
            if t <= t1:
                if t1 == t0:
                    return v1
                return v0 + (v1 - v0) * (t - t0) / (t1 - t0)
        return pts[-1][1]

    def normalized(self, value: float) -> float:
        """Value mapped to [0, 1]: the file minimum is 0, the maximum is 1."""
        if self.vmax == self.vmin:
            return 0.5
        return (value - self.vmin) / (self.vmax - self.vmin)

    def slot_fraction(self, value: float) -> float:
        """Vertical position from the slot top, as a fraction of its height.

        0 is the top of the slot, 1 its bottom. Scale zooms around the slot
        centre and offset shifts the trace upwards (positive) or downwards,
        in slot-height fractions -- both before scaling, like the vertical
        knobs of an oscilloscope. Values may fall outside [0, 1]: the drawing
        clips them at the slot limits.
        """
        n = self.normalized(value)
        return 0.5 - self.scale * (n - 0.5 + self.offset)

    def write(self, fileref: TextIO) -> None:
        """Emit the set_attribute lines of the non-default attributes."""
        for attr, default in self.DEFAULTS.items():
            value = getattr(self, attr)
            if value != default:
                if isinstance(value, bool):
                    value = "true" if value else "false"
                fileref.write(f"set_attribute -signal {{{self.name}}} "
                              f"-name {attr} -value {{{value}}}\n")


def clip_polyline(points: list[tuple[float, float]],
                  ymin: float, ymax: float) -> list[tuple[float, float]]:
    """Clamp a polyline to the [ymin, ymax] band, keeping the crossing points.

    Where a segment leaves the band the trace continues flat along the band
    limit (what an oscilloscope shows for an over-ranged signal).
    """
    out: list[tuple[float, float]] = []
    prev: tuple[float, float] | None = None
    for x, y in points:
        if prev is not None:
            px, py = prev
            crossings = []
            for yb in (ymin, ymax):
                if (py - yb) * (y - yb) < 0 and y != py:
                    t = (yb - py) / (y - py)
                    crossings.append((t, px + t * (x - px), yb))
            for _, cx, cy in sorted(crossings):
                out.append((cx, cy))
        out.append((x, min(max(y, ymin), ymax)))
        prev = (x, y)
    return out


class PWLSignal(Signal):
    """A waveform slot showing one or more PWL (analog) traces.

    The slot is registered in the signals store under the name of its first
    trace. Every trace name is unique diagram-wide (see TclCreatePwl), so a
    trace can be addressed by name with set_attribute.
    """

    DEFAULT_HEIGHT = 100   # 2.5 x the default clock/input/output amplitude
    DOT_RADIUS = 4

    def __init__(self, name: str) -> None:
        super().__init__(name, sig_type="pwl")
        self.style.amplitude = self.DEFAULT_HEIGHT
        self.traces: list[PWLTrace] = []
        # Value markers keyed by uid: they go away with the slot.
        self.vmarkers: dict[int, ValueMarker] = {}
        # Geometry of the last draw on the visible canvas (value markers).
        self.slot_top: int = 0

    # -- height is the slot amplitude (splits and layout use `amplitude`)
    @property
    def height(self) -> int:
        return self.style.amplitude

    @height.setter
    def height(self, value: int) -> None:
        self.style.amplitude = int(value)

    def find_trace(self, name: str) -> PWLTrace | None:
        for trace in self.traces:
            if trace.name == name:
                return trace
        return None

    def trace_names(self) -> list[str]:
        return [t.name for t in self.traces]

    def t_end(self) -> float:
        return max((t.t_end for t in self.traces if t.points), default=0.0)

    # ------------------------------------------------------------------
    # Geometry
    # ------------------------------------------------------------------
    def _x0(self) -> float:
        return (self.settings.waveform["left_padding"]
                + self.settings.waveform["nmargin"])

    def trace_xy(self, canvas: tk.Canvas, trace: PWLTrace, t: float,
                 top: int | None = None) -> tuple[float, float] | None:
        """Canvas coordinates of the trace point at time `t` (clipped)."""
        if self.settings is None:
            self.settings = getattr(canvas, "settings", None)
        value = trace.value_at(t)
        if value is None:
            return None
        if top is None:
            top = self.slot_top
        x = self._x0() + t * canvas.scale_factor
        frac = min(max(trace.slot_fraction(value), 0.0), 1.0)
        return x, top + frac * self.height

    # ------------------------------------------------------------------
    # Drawing
    # ------------------------------------------------------------------
    def _draw_label_stack(self, canvas: tk.Canvas, top: int) -> None:
        font = self.settings.get_font(self.settings.waveform["font"])
        linespace = font.metrics("linespace")
        n = len(self.traces)
        y = top + self.height / 2.0 - (n - 1) * linespace / 2.0
        x = self.settings.waveform["left_padding"]
        r = self.DOT_RADIUS
        tags = (self.uidtag(), "wf_labels", f"{self.name}_label")
        for trace in self.traces:
            ## A hidden trace keeps its name in the stack (hollow dot, grey
            ## name) so that the slot can still be edited from it.
            canvas.create_oval(x, y - r, x + 2 * r, y + r,
                               fill=trace.color if trace.visible else "",
                               outline=trace.color,
                               tags=tags)
            canvas.create_text(x + 2 * r + 4, y, text=trace.name, font=font,
                               fill="black" if trace.visible else "grey",
                               anchor="w", tags=tags)
            y += linespace

    def draw(self, canvas: tk.Canvas, top: int) -> int:
        super().draw(canvas, top)
        top += self.top_padding
        height = self.height

        if not canvas.is_virtual:
            self.slot_top = top

        if not getattr(canvas, "is_scaled", False):
            ## No clock fixed the time scale yet: fit the slot to the width.
            width = max(canvas.winfo_width(), 1)
            width -= (self.settings.waveform["left_padding"]
                      + self.settings.waveform["nmargin"]
                      + self.settings.waveform["right_padding"])
            span = self.t_end()
            if span > 0 and width > 0:
                canvas.scale_factor = float(width) / span
                canvas.is_scaled = True

        if not canvas.is_virtual:
            self._draw_label_stack(canvas, top)

        x0 = self._x0()
        scale = canvas.scale_factor
        for index, trace in enumerate(self.traces):
            if len(trace.points) < 1 or not trace.visible:
                continue
            pts = [(x0 + t * scale, top + trace.slot_fraction(v) * height)
                   for t, v in trace.points]
            if len(pts) == 1:
                pts = pts * 2
            pts = clip_polyline(pts, top, top + height)
            flat = [c for p in pts for c in p]
            canvas.create_line(
                *flat,
                fill=trace.color,
                width=trace.lwidth,
                dash=PWLTrace.LINE_STYLES.get(trace.lstyle),
                tags=(self.uidtag(), "waveforms", f"{self.name}_waveform",
                      "pwl_traces", f"pwltrace_{self.uid}_{index}"),
            )

        if self._apply_hidden_state(canvas):
            return 0
        return self.top_padding + height

    # ------------------------------------------------------------------
    # Serialization
    # ------------------------------------------------------------------
    def write(self, fileref: TextIO) -> None:
        ## An undo snapshot is sourced from the undo temp dir: it needs the
        ## resolved file paths. A saved diagram keeps the paths as given.
        snapshot = (self.console is not None
                    and getattr(self.console.topapp, "snapshot_mode", False))
        names = " ".join(f"{{{t.name}}}" for t in self.traces)
        files = " ".join(f"{{{t.resolved if snapshot else t.file}}}"
                         for t in self.traces)
        fileref.write(f"\ncreate_pwl -names {{{names}}}  \\\n")
        fileref.write(f"   -files {{{files}}}  \\\n")
        fileref.write(f"   -height {self.height}  \\\n")
        fileref.write(f"   -use_uid {self.uid}  ")
        if self.visible:
            fileref.write("   -visible ")
        fileref.write("\n")
        for trace in self.traces:
            trace.write(fileref)
        super().write(fileref)

    def write_vmarkers(self, fileref: TextIO) -> None:
        for marker in self.vmarkers.values():
            marker.write(fileref)
