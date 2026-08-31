# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2024 Pablo Cardaba

"""VCD (Value Change Dump, IEEE 1364) parsing and min/max pair analysis
for File -> Import VCDs.

parse_vcd_file() reads one dump into a VCDFileData. VCDPairAnalysis then
cross-checks the min/max pair (common signals, clock detection, delay
deltas, common time interval) and classifies each signal as a clock
candidate, derived-clock candidate or data — the input the upcoming
signal-characterization dialog will present to the user.

All times are integer femtoseconds so the two files can use different
$timescale units without float drift.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

_TIMESCALE_FS = {
    "s": 10**15, "ms": 10**12, "us": 10**9,
    "ns": 10**6, "ps": 10**3, "fs": 1,
}

## Relative tolerance when comparing periods (real dumps may carry jitter).
_PERIOD_RTOL = 0.01
## Absolute tolerance on duty-cycle fraction before min/max duty is
## considered different (and thus flagged as uncertainty).
_DUTY_ATOL = 0.01


class VCDParseError(Exception):
    """Malformed VCD content (message includes file and context)."""


# ---------------------------------------------------------------------------
# Single-file parsing
# ---------------------------------------------------------------------------
@dataclass
class VCDVar:
    id_code: str
    name: str          # full hierarchical name, dot-joined scopes
    basename: str      # leaf name without scope or bit range
    brange: str        # bit range as written, e.g. "[3:0]", or ""
    width: int
    var_type: str      # reg / wire / ...

    @property
    def display(self) -> str:
        return self.basename + self.brange


@dataclass
class VCDFileData:
    path: str
    timescale_fs: int = 1
    vars: dict[str, VCDVar] = field(default_factory=dict)          # by name
    changes: dict[str, list[tuple[int, str]]] = field(default_factory=dict)
    end_time_fs: int = 0
    warnings: list[str] = field(default_factory=list)

    def start_time_fs(self) -> int:
        firsts = [c[0][0] for c in self.changes.values() if c]
        return min(firsts) if firsts else 0


## VHDL-style extended values some simulators dump: weak high/low become
## plain 1/0, weak-unknown and don't-care become x. 'u' (uninitialized) is
## kept apart but is treated like x (unknown) downstream.
_VALUE_MAP = str.maketrans({"h": "1", "l": "0", "w": "x", "-": "x"})
_SCALAR_CHARS = "01xXzZuUwWhHlL-"


def _normalize_value(value: str, width: int) -> str:
    """Left-extend a VCD vector value to its declared width (IEEE rule:
    extend with the leading bit when it is x/z, with 0 otherwise)."""
    v = value.lower().translate(_VALUE_MAP)
    if len(v) < width:
        pad = v[0] if v[0] in "xzu" else "0"
        v = pad * (width - len(v)) + v
    elif len(v) > width:
        v = v[-width:]
    return v


def parse_vcd_file(path: str) -> VCDFileData:
    """Parse one VCD dump. Raises VCDParseError / OSError."""
    fname = Path(path).name
    text = Path(path).read_text(encoding="utf-8", errors="replace")
    tokens = text.split()
    data = VCDFileData(path=path)

    def err(msg: str) -> VCDParseError:
        return VCDParseError(f"{fname}: {msg}")

    def skip_to_end(i: int) -> int:
        while i < len(tokens) and tokens[i] != "$end":
            i += 1
        return i + 1

    # ---- header ----
    by_id: dict[str, VCDVar] = {}
    scope: list[str] = []
    i = 0
    while i < len(tokens):
        tok = tokens[i]
        if tok == "$enddefinitions":
            i = skip_to_end(i + 1)
            break
        if tok in ("$date", "$version", "$comment"):
            i = skip_to_end(i + 1)
        elif tok == "$timescale":
            j = i + 1
            spec = ""
            while j < len(tokens) and tokens[j] != "$end":
                spec += tokens[j]
                j += 1
            num = spec.rstrip("smunpf")
            unit = spec[len(num):]
            if unit not in _TIMESCALE_FS or num not in ("1", "10", "100"):
                raise err(f"unsupported $timescale '{spec}'")
            data.timescale_fs = int(num) * _TIMESCALE_FS[unit]
            i = j + 1
        elif tok == "$scope":
            if i + 2 >= len(tokens):
                raise err("truncated $scope")
            scope.append(tokens[i + 2])
            i = skip_to_end(i + 3)
        elif tok == "$upscope":
            if scope:
                scope.pop()
            i = skip_to_end(i + 1)
        elif tok == "$var":
            j = i + 1
            parts = []
            while j < len(tokens) and tokens[j] != "$end":
                parts.append(tokens[j])
                j += 1
            if len(parts) < 4:
                raise err(f"malformed $var: {' '.join(parts)}")
            var_type, size_s, id_code = parts[0], parts[1], parts[2]
            basename = parts[3]
            brange = parts[4] if len(parts) > 4 and parts[4].startswith("[") else ""
            try:
                width = int(size_s)
            except ValueError:
                raise err(f"bad $var size '{size_s}' for {basename}") from None
            full = ".".join(scope + [basename])
            if id_code in by_id:
                data.warnings.append(
                    f"{fname}: '{full}' is an alias of "
                    f"'{by_id[id_code].name}' (same id) — alias ignored.")
            else:
                var = VCDVar(id_code, full, basename, brange, width, var_type)
                by_id[id_code] = var
                if full in data.vars:
                    data.warnings.append(
                        f"{fname}: duplicate signal name '{full}' — "
                        "keeping the first one.")
                else:
                    data.vars[full] = var
                    data.changes[full] = []
            i = j + 1
        else:
            i += 1
    else:
        raise err("no $enddefinitions found")

    if not data.vars:
        raise err("no signals ($var) declared")

    # ---- value changes ----
    ts = data.timescale_fs
    cur_fs = 0
    real_warned = False

    def record(id_code: str, value: str) -> None:
        var = by_id.get(id_code)
        if var is None:
            raise err(f"value change for undeclared id '{id_code}'")
        lst = data.changes[var.name]
        norm = _normalize_value(value, var.width)
        if lst and lst[-1][0] == cur_fs:
            ## Several changes at the same timestamp: the last one wins.
            lst[-1] = (cur_fs, norm)
            if len(lst) >= 2 and lst[-2][1] == norm:
                lst.pop()
        elif not lst or lst[-1][1] != norm:
            lst.append((cur_fs, norm))

    while i < len(tokens):
        tok = tokens[i]
        c = tok[0]
        if c == "#":
            try:
                cur_fs = int(tok[1:]) * ts
            except ValueError:
                raise err(f"bad timestamp '{tok}'") from None
            data.end_time_fs = max(data.end_time_fs, cur_fs)
            i += 1
        elif c in _SCALAR_CHARS:
            record(tok[1:], tok[0])
            i += 1
        elif c in "bB":
            if i + 1 >= len(tokens):
                raise err(f"vector value '{tok}' without identifier")
            record(tokens[i + 1], tok[1:])
            i += 2
        elif c in "rR":
            if not real_warned:
                data.warnings.append(
                    f"{fname}: real-valued signals are not supported — "
                    "their changes are ignored.")
                real_warned = True
            i += 2
        elif tok == "$comment":
            i = skip_to_end(i + 1)
        elif tok == "$dumpoff":
            ## A $dumpoff block dumps every signal as x; recording it would
            ## fake changes. Skip the whole block.
            data.warnings.append(
                f"{fname}: $dumpoff block found — its content is ignored "
                "(signals are not really changing there).")
            i = skip_to_end(i + 1)
        elif c == "$":
            ## $dumpvars/$dumpall/$dumpon/$dumpoff open blocks whose body is
            ## plain value changes; $end closes them. Just skip the keywords.
            i += 1
        else:
            raise err(f"unexpected token '{tok}' in value-change section")

    return data


# ---------------------------------------------------------------------------
# Min/max pair analysis
# ---------------------------------------------------------------------------
@dataclass
class ClockInfo:
    period_fs: int
    duty_min: float
    duty_max: float
    first_rise_min_fs: int
    first_rise_max_fs: int
    first_fall_min_fs: int = 0
    first_fall_max_fs: int = 0
    master: str | None = None    # full name of the proposed source clock
    ratio: int = 1               # period(this) / period(master)

    @property
    def latency_fs(self) -> int:
        return self.first_rise_max_fs - self.first_rise_min_fs

    @property
    def duty_uncertain(self) -> bool:
        return abs(self.duty_max - self.duty_min) > _DUTY_ATOL


@dataclass
class ImportSignal:
    name: str                    # full hierarchical name
    display: str                 # leaf name + bit range
    width: int
    changes_min: list[tuple[int, str]]   # clipped to the common interval
    changes_max: list[tuple[int, str]]
    deltas_fs: list[int] = field(default_factory=list)  # per-change max-min
    clock: ClockInfo | None = None

    @property
    def is_clock_candidate(self) -> bool:
        return self.clock is not None


def _clock_profile(changes: list[tuple[int, str]]):
    """Return (period_fs, first_rise_fs, first_fall_fs, duty) when the change
    list looks like an undistorted clock (pure 0/1 alternation, constant
    period over at least three rising edges), else None."""
    if any(v not in ("0", "1") for _, v in changes):
        return None
    rises = [t for (t, v), (_, pv) in zip(changes[1:], changes[:-1])
             if v == "1" and pv == "0"]
    falls = [t for (t, v), (_, pv) in zip(changes[1:], changes[:-1])
             if v == "0" and pv == "1"]
    if len(rises) < 3 or not falls:
        return None
    periods = [b - a for a, b in zip(rises, rises[1:])]
    period = periods[0]
    if period <= 0 or any(abs(p - period) > period * _PERIOD_RTOL
                          for p in periods):
        return None
    ## High-time of each full pulse: rise -> next fall.
    highs = []
    fi = 0
    for r in rises:
        while fi < len(falls) and falls[fi] <= r:
            fi += 1
        if fi < len(falls):
            highs.append(falls[fi] - r)
    if not highs:
        return None
    duty = (sum(highs) / len(highs)) / period
    return period, rises[0], falls[0], duty


class VCDPairAnalysis:
    """Cross-check a (min, max) VCD pair and classify the common signals.

    After construction: `errors` (blocking), `warnings` (informative),
    `signals` (list of ImportSignal, min-file order), `t0_fs`/`t1_fs`
    (common interval). The import may proceed only when `ok` is True.
    """

    def __init__(self, vcd_min: VCDFileData, vcd_max: VCDFileData):
        self.vcd_min = vcd_min
        self.vcd_max = vcd_max
        self.errors: list[str] = []
        self.warnings: list[str] = list(vcd_min.warnings) + list(vcd_max.warnings)
        self.signals: list[ImportSignal] = []
        self.t0_fs = 0
        self.t1_fs = 0
        self.same_file = Path(vcd_min.path).resolve() == Path(vcd_max.path).resolve()
        self._run()

    @property
    def ok(self) -> bool:
        return not self.errors

    # -- helpers --
    @staticmethod
    def fs_to_ns(t_fs: float) -> float:
        return t_fs / 1e6

    def _fmt_ns(self, t_fs: float) -> str:
        return f"{self.fs_to_ns(t_fs):g} ns"

    # -- pipeline --
    def _run(self) -> None:
        vmin, vmax = self.vcd_min, self.vcd_max

        if vmin.timescale_fs != vmax.timescale_fs:
            self.warnings.append(
                "The two files use different $timescale units; "
                "times were normalized before comparing.")

        # 1. Common signal set; discard (with a warning) the rest.
        common = [n for n in vmin.vars if n in vmax.vars]
        only_min = [n for n in vmin.vars if n not in vmax.vars]
        only_max = [n for n in vmax.vars if n not in vmin.vars]
        for n in only_min:
            self.warnings.append(f"'{n}' only in the min file — discarded.")
        for n in only_max:
            self.warnings.append(f"'{n}' only in the max file — discarded.")
        if not common:
            self.errors.append("The two files have no signal in common.")
            return

        # 2. Common time interval: the shortest one.
        self.t0_fs = max(vmin.start_time_fs(), vmax.start_time_fs())
        self.t1_fs = min(vmin.end_time_fs, vmax.end_time_fs)
        if vmin.end_time_fs != vmax.end_time_fs:
            self.warnings.append(
                f"Time intervals differ (min ends at "
                f"{self._fmt_ns(vmin.end_time_fs)}, max at "
                f"{self._fmt_ns(vmax.end_time_fs)}) — "
                f"clipping to the shortest.")
        if self.t1_fs <= self.t0_fs:
            self.errors.append("The common time interval is empty.")
            return

        # 3. Per-signal checks and classification.
        for name in common:
            var_min, var_max = vmin.vars[name], vmax.vars[name]
            if var_min.width != var_max.width:
                self.errors.append(
                    f"'{name}': width differs between files "
                    f"({var_min.width} vs {var_max.width}).")
                continue
            ch_min = vmin.changes[name]
            ch_max = vmax.changes[name]
            if not ch_min or not ch_max:
                self.warnings.append(
                    f"'{name}' has no value changes in one of the files — "
                    "discarded.")
                continue

            sig = ImportSignal(
                name=name,
                display=var_min.display,
                width=var_min.width,
                changes_min=self._clip(ch_min),
                changes_max=self._clip(ch_max),
            )

            prof_min = _clock_profile(ch_min) if var_min.width == 1 else None
            prof_max = _clock_profile(ch_max) if var_min.width == 1 else None
            if prof_min and prof_max:
                self._check_clock(sig, prof_min, prof_max)
            elif bool(prof_min) != bool(prof_max):
                self.errors.append(
                    f"'{name}': looks like a clock in one file but not in "
                    "the other (clock distorted between min and max).")
                continue
            else:
                if not self._check_data(sig, ch_min, ch_max):
                    continue
            self.signals.append(sig)

        # 4. At least one clock must be present.
        clocks = [s for s in self.signals if s.is_clock_candidate]
        if not clocks:
            self.errors.append(
                "No clock signal detected: at least one periodic "
                "(undistorted) clock is required.")
            return

        # 5. Derived-clock proposals: a slower clock whose period is an
        #    integer multiple of a faster clock's period. A derived clock
        #    can never be faster than its primary.
        clocks.sort(key=lambda s: (s.clock.period_fs, s.clock.first_rise_min_fs))
        for s in clocks[1:]:
            for master in clocks:
                if master is s:
                    continue
                ratio = s.clock.period_fs / master.clock.period_fs
                if ratio >= 2 and abs(ratio - round(ratio)) <= _PERIOD_RTOL * ratio:
                    s.clock.master = master.name
                    s.clock.ratio = round(ratio)
                    break

    def _clip(self, changes: list[tuple[int, str]]) -> list[tuple[int, str]]:
        """Restrict a change list to [t0, t1]: value entering the interval
        becomes the value at t0; later changes beyond t1 are dropped."""
        out: list[tuple[int, str]] = []
        for t, v in changes:
            if t <= self.t0_fs:
                if out and out[0][0] == self.t0_fs:
                    out[0] = (self.t0_fs, v)
                else:
                    out.insert(0, (self.t0_fs, v))
            elif t <= self.t1_fs:
                out.append((t, v))
        return out

    def _check_clock(self, sig: ImportSignal, prof_min, prof_max) -> None:
        p_min, rise_min, fall_min, duty_min = prof_min
        p_max, rise_max, fall_max, duty_max = prof_max
        if abs(p_max - p_min) > p_min * _PERIOD_RTOL:
            self.errors.append(
                f"'{sig.name}': clock period differs between files "
                f"({self._fmt_ns(p_min)} vs {self._fmt_ns(p_max)}) — "
                "clocks must not be distorted.")
            return
        if rise_max < rise_min:
            self.errors.append(
                f"'{sig.name}': first clock edge is earlier in the max file "
                f"({self._fmt_ns(rise_max)} < {self._fmt_ns(rise_min)}) — "
                "max must be right-shifted (or equal).")
            return
        sig.clock = ClockInfo(
            period_fs=p_min,
            duty_min=duty_min, duty_max=duty_max,
            first_rise_min_fs=rise_min, first_rise_max_fs=rise_max,
            first_fall_min_fs=fall_min, first_fall_max_fs=fall_max,
        )
        if sig.clock.duty_uncertain:
            self.warnings.append(
                f"'{sig.name}': duty cycle differs between min and max "
                f"({duty_min * 100:.1f}% vs {duty_max * 100:.1f}%) — will be "
                "represented as uncertainty.")

    def _check_data(self, sig: ImportSignal,
                    ch_min: list[tuple[int, str]],
                    ch_max: list[tuple[int, str]]) -> bool:
        """Same value sequence in both files, every max delay >= min delay.
        Compared on the unclipped lists so a max change pushed just past the
        interval end is still matched with its min counterpart."""
        vals_min = [v for _, v in ch_min]
        vals_max = [v for _, v in ch_max]
        if vals_min != vals_max:
            self.errors.append(
                f"'{sig.name}': value sequences differ between min and max "
                f"files ({len(vals_min)} vs {len(vals_max)} changes) — "
                "the two dumps do not come from the same stimulus.")
            return False
        deltas = [tmax - tmin
                  for (tmin, _), (tmax, _) in zip(ch_min, ch_max)]
        bad = [i for i, d in enumerate(deltas) if d < 0]
        if bad:
            i = bad[0]
            self.errors.append(
                f"'{sig.name}': change to '{ch_min[i][1]}' happens earlier "
                f"in the max file ({self._fmt_ns(ch_max[i][0])} < "
                f"{self._fmt_ns(ch_min[i][0])}) — all max delays must be >= "
                "min delays.")
            return False
        sig.deltas_fs = deltas
        return True

    # -- console report --
    def report_lines(self) -> list[str]:
        """Human-readable classification summary, one line per signal."""
        lines = [f"Common interval: {self._fmt_ns(self.t0_fs)} .. "
                 f"{self._fmt_ns(self.t1_fs)}."]
        pad = max((len(s.display) for s in self.signals), default=0)
        for s in self.signals:
            if s.clock is not None:
                ck = s.clock
                desc = (f"clock candidate, period {self._fmt_ns(ck.period_fs)}, "
                        f"duty {ck.duty_min * 100:.0f}%")
                if ck.duty_uncertain:
                    desc += f"/{ck.duty_max * 100:.0f}% (uncertain)"
                if ck.latency_fs:
                    desc += f", latency +{self._fmt_ns(ck.latency_fs)}"
                if ck.master is not None:
                    base = self.vcd_min.vars[ck.master].basename
                    desc += f" — derived candidate of '{base}' (/{ck.ratio})"
            else:
                nz = [d for d in s.deltas_fs if d]
                desc = (f"data, {s.width} bit{'s' if s.width > 1 else ''}, "
                        f"{len(s.changes_min)} changes")
                if nz:
                    desc += (f", max-min delay {self._fmt_ns(min(nz))} .. "
                             f"{self._fmt_ns(max(nz))}")
            lines.append(f"  {s.display.ljust(pad)} : {desc}")
        return lines
