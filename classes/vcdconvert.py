# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2024 Pablo Cardaba

"""Conversion of an analyzed VCD min/max pair into TimeIt Tcl commands.

propose_choices() guesses a role for every common signal (clock topology,
input/output direction, best-fit launch clock); the characterization dialog
lets the user adjust them; VCDConverter then validates the final choices and
emits the create_clock / create_input / create_output commands that
reproduce the VCD waveforms.

Delay model: inputs are emitted with `-specify external` and outputs with
`-specify internal` -- the two specs whose delays run forward from the
launching clock edge, which is exactly what a VCD shows. Each transition's
min delay is measured on the min file against the min-file clock edge, and
the max delay on the max file against the max-file clock edge. TimeIt keeps
one delay value per signal and edge polarity, so when per-transition delays
differ the [min..max] envelope is used (with a warning).

All times are integer femtoseconds until formatting; commands are written
in ns.
"""

from __future__ import annotations

from bisect import bisect_right
from dataclasses import dataclass

from .vcdimport import ImportSignal, VCDPairAnalysis

SOURCE_TOPOLOGIES = ("clockin", "source")
GENERATED_TOPOLOGIES = ("clockout", "clockinout")
CLOCK_TOPOLOGIES = SOURCE_TOPOLOGIES + GENERATED_TOPOLOGIES

## Tolerance (fraction of the master period) when aligning generated clock
## edges on master clock edges.
_ALIGN_RTOL = 0.01
## Per-transition delay spread below this fraction of the launch clock
## period is not worth a warning.
_SPREAD_RTOL = 0.01


def _ns(t_fs: float) -> str:
    return f"{t_fs / 1e6:g}"


def _classify(value: str, width: int) -> str:
    """TimeIt edge-list class of a VCD value ('u' counts as unknown)."""
    if width == 1:
        if value == "1":
            return "high"
        if value == "0":
            return "low"
        if value == "z":
            return "hiz"
        return "unknown"
    if all(c == "z" for c in value):
        return "hiz"
    if any(c in "xu" for c in value):
        return "unknown"
    return "data"


def _clock_edges(changes: list[tuple[int, str]]) -> tuple[list[int], list[str]]:
    """(times, polarities) of the edges in an alternating 0/1 change list."""
    times: list[int] = []
    pols: list[str] = []
    for (t, v), (_pt, _pv) in zip(changes[1:], changes[:-1]):
        times.append(t)
        pols.append("P" if v == "1" else "N")
    return times, pols


@dataclass
class SignalChoice:
    """User-adjustable role of one imported signal.

    All signal references (master/launch/capture) are VCD full names.
    """
    kind: str                   # "clock" | "input" | "output"
    topology: str = "clockin"   # clocks only
    master: str | None = None   # clocks with a generated topology
    launch: str | None = None   # I/O only
    capture: str | None = None  # I/O only (None: same as launch)
    ## Proposal-side annotation (ignored by the converter): a slower clock
    ## whose BOTH edges explain this signal's transitions just as well as the
    ## proposed launch clock does with one polarity. The two readings draw
    ## identical waveforms, so the SDR one is proposed -- but the signal may
    ## really be DDR on this clock, and only the user can tell.
    ddr_hint: str | None = None


# ---------------------------------------------------------------------------
# Role proposals
# ---------------------------------------------------------------------------
def _launch_fit(sig: ImportSignal, times: list[int], pols: list[str],
                period_fs: int) -> tuple[float, int, int, int]:
    """How well a clock's edges explain this signal's transitions.

    Returns (score, spread_fs, n_polarity_buckets, unexplained). The score
    (lower is better) weighs the per-polarity delay spread and mean delay
    relative to the period, plus a penalty per extra polarity bucket and per
    change with no preceding edge.
    """
    buckets: dict[str, list[int]] = {}
    unexplained = 0
    total = 0
    for t, _v in sig.changes_min[1:]:
        i = bisect_right(times, t) - 1
        if i < 0:
            unexplained += 1
            continue
        buckets.setdefault(pols[i], []).append(t - times[i])
        total += 1
    if total == 0:
        return (10.0 * unexplained, 0, 0, unexplained)
    spread = sum(max(b) - min(b) for b in buckets.values())
    mean = sum(sum(b) for b in buckets.values()) / total
    score = ((spread + 0.1 * mean) / period_fs
             + 1.0 * (len(buckets) - 1) + 10.0 * unexplained)
    return (score, spread, len(buckets), unexplained)


def _ddr_alternative(best: ImportSignal, fits: dict[str, tuple],
                     clocks: list[ImportSignal]) -> str | None:
    """A slower clock that reads this signal as DDR just as well.

    A signal whose changes all follow one polarity of a fast clock also
    follows both edge polarities of a related clock running at half the
    rate (the fast clock's edge grid contains both). When such a slower
    clock explains every change on both polarities with no worse spread,
    the waveforms are identical under both readings and the proposal is
    genuinely ambiguous -- worth telling the user about.
    """
    _score, best_spread, n_buckets, _unexp = fits[best.name]
    if n_buckets != 1:
        return None
    for clk in sorted(clocks, key=lambda c: c.clock.period_fs, reverse=True):
        if clk.clock.period_fs <= best.clock.period_fs:
            continue
        _s, spread, nb, unexplained = fits[clk.name]
        tol = int(clk.clock.period_fs * _SPREAD_RTOL)
        if nb == 2 and unexplained == 0 and spread <= best_spread + tol:
            return clk.name
    return None


def propose_choices(analysis: VCDPairAnalysis) -> dict[str, SignalChoice]:
    """Initial SignalChoice per common signal, keyed by VCD full name."""
    clocks = [s for s in analysis.signals if s.is_clock_candidate]
    timelines = {s.name: _clock_edges(s.changes_min) for s in clocks}

    choices: dict[str, SignalChoice] = {}
    for sig in analysis.signals:
        if sig.is_clock_candidate:
            derived = sig.clock.master is not None
            choices[sig.name] = SignalChoice(
                kind="clock",
                topology="clockout" if derived else "clockin",
                master=sig.clock.master)
            continue

        kind = "output" if sig.display.lower().rstrip("<[0123456789:]>") \
                              .endswith(("_o", "out")) else "input"
        best = None
        best_score = None
        fits: dict[str, tuple] = {}
        for clk in clocks:
            times, pols = timelines[clk.name]
            fit = _launch_fit(sig, times, pols, clk.clock.period_fs)
            fits[clk.name] = fit
            score = fit[0]
            ## Strictly better wins; a tie goes to the slower clock.
            if best_score is None or score < best_score - 1e-12:
                best, best_score = clk, score
            elif abs(score - best_score) <= 1e-12 \
                    and clk.clock.period_fs > best.clock.period_fs:
                best = clk
        choices[sig.name] = SignalChoice(
            kind=kind,
            launch=best.name if best else None,
            capture=best.name if best else None,
            ddr_hint=_ddr_alternative(best, fits, clocks) if best else None)
    return choices


# ---------------------------------------------------------------------------
# Conversion
# ---------------------------------------------------------------------------
class VCDConverter:
    """Validate the choices and build the Tcl commands reproducing the VCDs.

    After run(): `errors` (blocking), `warnings`, `commands` (create_clock
    first -- sources before generated -- then create_input/create_output).
    """

    def __init__(self, analysis: VCDPairAnalysis,
                 choices: dict[str, SignalChoice]):
        self.analysis = analysis
        self.choices = choices
        self.sigs = {s.name: s for s in analysis.signals}
        self.errors: list[str] = []
        self.warnings: list[str] = []
        self.commands: list[str] = []

        self.tcl_names = self._tcl_names()
        self._timelines: dict[str, tuple] = {}
        ## Highest launch edge index the I/O signals reference, per clock.
        self._max_edge: dict[str, int] = {}

    # -- naming --
    def _tcl_names(self) -> dict[str, str]:
        """TimeIt signal name per VCD full name.

        Leaf name with the bit range as <msb:lsb> (TimeIt's own style; square
        brackets would break when the saved script re-sources: the name is
        written unquoted and [] is command substitution in Tcl). Signals whose
        leaf name collides keep their dotted hierarchical name.
        """
        leafs: dict[str, int] = {}
        for sig in self.sigs.values():
            leafs[sig.display] = leafs.get(sig.display, 0) + 1
        out = {}
        for name, sig in self.sigs.items():
            base = sig.display if leafs[sig.display] == 1 else name
            out[name] = base.replace("[", "<").replace("]", ">")
        return out

    # -- clock timeline (edges seen in the VCDs, clipped interval) --
    def _timeline(self, name: str) -> tuple[list[int], list[str], list[int]]:
        """(times_min, polarities, times_max) of clock `name` edges."""
        if name not in self._timelines:
            sig = self.sigs[name]
            times_min, pols = _clock_edges(sig.changes_min)
            times_max, _ = _clock_edges(sig.changes_max)
            self._timelines[name] = (times_min, pols, times_max)
        return self._timelines[name]

    # -- validation --
    def _validate(self) -> None:
        clocks = [n for n, c in self.choices.items() if c.kind == "clock"]
        if not clocks:
            self.errors.append("At least one signal must be kept as a clock.")

        def root_of(name: str) -> str | None:
            c = self.choices[name]
            if c.topology in GENERATED_TOPOLOGIES:
                return c.master
            return name

        for name, c in self.choices.items():
            sig = self.sigs.get(name)
            label = self.tcl_names.get(name, name)
            if sig is None:
                self.errors.append(f"'{label}': unknown signal.")
                continue
            if c.kind == "clock":
                if not sig.is_clock_candidate:
                    self.errors.append(
                        f"'{label}' is not periodic: it can not be imported "
                        "as a clock.")
                    continue
                if c.topology not in CLOCK_TOPOLOGIES:
                    self.errors.append(f"'{label}': bad topology '{c.topology}'.")
                elif c.topology in GENERATED_TOPOLOGIES:
                    m = c.master
                    if m is None or m not in self.choices:
                        self.errors.append(
                            f"'{label}': a generated clock needs a master "
                            "clock.")
                    elif self.choices[m].kind != "clock" \
                            or self.choices[m].topology not in SOURCE_TOPOLOGIES:
                        self.errors.append(
                            f"'{label}': master '{self.tcl_names.get(m, m)}' "
                            "must be a source clock.")
                    elif m == name:
                        self.errors.append(
                            f"'{label}' can not be its own master clock.")
            elif c.kind in ("input", "output"):
                launch = c.launch
                capture = c.capture or launch
                for role, clk in (("launch", launch), ("capture", capture)):
                    if clk is None or clk not in self.choices \
                            or self.choices[clk].kind != "clock":
                        self.errors.append(
                            f"'{label}': {role} clock is not one of the "
                            "imported clocks.")
                        break
                else:
                    if root_of(launch) != root_of(capture):
                        self.errors.append(
                            f"'{label}': launch and capture clocks are not "
                            "related (they do not share the same source "
                            "clock).")
            else:
                self.errors.append(f"'{label}': bad kind '{c.kind}'.")

    # -- pipeline --
    def run(self) -> bool:
        self._validate()
        if self.errors:
            return False

        io_cmds: list[str] = []
        for name, c in self.choices.items():
            if c.kind in ("input", "output"):
                cmd = self._convert_io(name, c)
                if cmd:
                    io_cmds.append(cmd)
        if self.errors:
            return False

        clock_cmds: list[str] = []
        ## Source clocks first: a generated clock needs its master to exist.
        ordered = [n for n, c in self.choices.items() if c.kind == "clock"
                   and c.topology in SOURCE_TOPOLOGIES]
        ordered += [n for n, c in self.choices.items() if c.kind == "clock"
                    and c.topology in GENERATED_TOPOLOGIES]
        for name in ordered:
            cmd = self._convert_clock(name, self.choices[name])
            if cmd:
                clock_cmds.append(cmd)
        if self.errors:
            return False

        self.commands = clock_cmds + io_cmds
        return True

    # -- clock conversion --
    def _cycles(self, name: str, period_fs: int) -> int:
        span = self.analysis.t1_fs - self.analysis.t0_fs
        base = -(-span // period_fs)  # ceil
        used = self._max_edge.get(name, 0)
        return max(int(base), (used + 2) // 2, 1)

    def _convert_clock(self, name: str, choice: SignalChoice) -> str | None:
        sig = self.sigs[name]
        label = self.tcl_names[name]
        ci = sig.clock
        t0 = self.analysis.t0_fs

        if choice.topology in GENERATED_TOPOLOGIES:
            spec = self._generated_spec(name, choice)
            if spec is None:
                return None
            if ci.latency_fs or ci.duty_uncertain:
                self.warnings.append(
                    f"'{label}': min/max clock differences (latency or duty) "
                    "can not be represented on a generated clock — ignored.")
            cmd = (f"create_clock -name {{{label}}} "
                   f"-topology {choice.topology} "
                   f"-master {{{self.tcl_names[choice.master]}}} {spec}")
        else:
            times, pols, _ = self._timeline(name)
            try:
                rise = times[pols.index("P")] - t0
                fall = times[pols.index("N")] - t0
            except ValueError:
                self.errors.append(f"'{label}': clock edges not found.")
                return None
            ## Keep the first drawn edge inside the first cycles.
            shift = (min(rise, fall) // ci.period_fs) * ci.period_fs
            rise -= shift
            fall -= shift
            cmd = (f"create_clock -name {{{label}}} "
                   f"-topology {choice.topology} "
                   f"-period {{{_ns(ci.period_fs)}}} "
                   f"-rise_at {{{_ns(rise)}}} -fall_at {{{_ns(fall)}}}")
            runc = ci.first_rise_max_fs - ci.first_rise_min_fs
            func = abs(ci.first_fall_max_fs - ci.first_fall_min_fs)
            if runc:
                cmd += f" -rise_uncertainty {{{_ns(runc)}}}"
            if func:
                cmd += f" -fall_uncertainty {{{_ns(func)}}}"

        cmd += f" -show {self._cycles(name, ci.period_fs)} -visible"
        return cmd

    def _generated_spec(self, name: str, choice: SignalChoice) -> str | None:
        """-divide_by/-edges (+-invert) of a generated clock, aligned on its
        master's VCD edges. None (with an error) when they do not align."""
        sig = self.sigs[name]
        label = self.tcl_names[name]
        master = self.sigs[choice.master]
        m_times, _pols, _ = self._timeline(choice.master)
        tol = int(master.clock.period_fs * _ALIGN_RTOL)

        times, pols, _ = self._timeline(name)
        try:
            rise0 = times[pols.index("P")]
            fall0 = times[pols.index("N")]
        except ValueError:
            self.errors.append(f"'{label}': clock edges not found.")
            return None

        ## An inverted clock is specified through its complement: the direct
        ## clock rises where this one falls.
        invert = fall0 < rise0
        r_t, f_t = (fall0, rise0) if invert else (rise0, fall0)
        e_t = r_t + sig.clock.period_fs

        def index_at(t: int) -> int | None:
            i = bisect_right(m_times, t + tol) - 1
            if i >= 0 and abs(m_times[i] - t) <= tol:
                return i + 1
            return None

        r, f, e = index_at(r_t), index_at(f_t), index_at(e_t)
        if None in (r, f, e) or not r < f < e:
            self.errors.append(
                f"'{label}': its edges do not align with master "
                f"'{self.tcl_names[choice.master]}' edges — import it as a "
                "source clock instead.")
            return None

        spec = f"-edges {{{r} {f} {e}}}"
        d = (e - 1) // 2
        if [r, f, e] == [1, d + 1, 2 * d + 1]:
            spec = f"-divide_by {d}"
        if invert:
            spec += " -invert"
        return spec

    # -- I/O conversion --
    def _convert_io(self, name: str, choice: SignalChoice) -> str | None:
        sig = self.sigs[name]
        label = self.tcl_names[name]
        launch = choice.launch
        capture = choice.capture or launch
        times_min, pols, times_max = self._timeline(launch)
        latency = self.sigs[launch].clock.latency_fs
        period = self.sigs[launch].clock.period_fs
        t0 = self.analysis.t0_fs

        edge_lists: dict[str, list[str]] = {
            "data": [], "hiz": [], "high": [], "low": [], "unknown": []}
        used_tokens: set[str] = set()
        ## (dmin, dmax) samples per delay group and polarity.
        delays: dict[tuple[str, str], list[tuple[int, int]]] = {}
        max_edge = 0
        prev_cls: str | None = None

        for i, (t, v) in enumerate(sig.changes_min):
            cls = _classify(v, sig.width)
            if i == 0 and t == t0:
                token = "0"
            else:
                idx = bisect_right(times_min, t) - 1
                if idx < 0:
                    self.warnings.append(
                        f"'{label}': change at {_ns(t - t0)} ns is before the "
                        f"first '{self.tcl_names[launch]}' edge — placed at "
                        "the waveform start.")
                    token = "0"
                else:
                    token = str(idx + 1)
                    max_edge = max(max_edge, idx + 1)
                    ## Delay of this transition: min file against the
                    ## min-file edge, max file against the max-file edge.
                    d_min = t - times_min[idx]
                    edge_max = (times_max[idx] if idx < len(times_max)
                                else times_min[idx] + latency)
                    if i < len(sig.changes_max) \
                            and sig.changes_max[i][1] == v:
                        d_max = sig.changes_max[i][0] - edge_max
                    else:
                        d_max = d_min
                    if choice.kind == "input":
                        group = "inputdly"
                    elif cls == "hiz" or prev_cls == "hiz":
                        group = "oedly"
                    else:
                        group = "outputdly"
                    key = "rclk" if pols[idx] == "P" else "fclk"
                    delays.setdefault((group, key), []).append((d_min, d_max))
            if token in used_tokens:
                self.warnings.append(
                    f"'{label}': two changes on launch edge {token} — only "
                    "the first one is kept.")
            else:
                used_tokens.add(token)
                edge_lists[cls].append(token)
            prev_cls = cls

        if max_edge:
            self._max_edge[launch] = max(self._max_edge.get(launch, 0),
                                         max_edge)

        create = "create_input" if choice.kind == "input" else "create_output"
        specify = "external" if choice.kind == "input" else "internal"
        cmd = (f"{create} -name {{{label}}} -specify {specify} "
               f"-launch_clock {{{self.tcl_names[launch]}}} "
               f"-capture_clock {{{self.tcl_names[capture]}}}")

        for (group, key), samples in sorted(delays.items()):
            dmins = [d for d, _ in samples]
            dmaxs = [d for _, d in samples]
            dmin, dmax = min(dmins), max(dmaxs)
            if dmax < dmin:
                self.warnings.append(
                    f"'{label}': {key} max delay resolves below the min one "
                    "(the clock shifts more than the data) — min used for "
                    "both.")
                dmax = dmin
            spread = max(max(dmins) - min(dmins), max(dmaxs) - min(dmaxs))
            if spread > period * _SPREAD_RTOL and len(samples) > 1:
                note = ""
                if self.analysis.same_file:
                    note = (" (same VCD given for min and max: this is "
                            "transition-to-transition variation, not corner "
                            "spread)")
                self.warnings.append(
                    f"'{label}': per-transition {key} delays differ by up to "
                    f"{_ns(spread)} ns — the [{_ns(dmin)}..{_ns(dmax)}] ns "
                    f"envelope is used{note}.")
            cmd += (f" -{key}_{group}_min {{{_ns(dmin)}}}"
                    f" -{key}_{group}_max {{{_ns(dmax)}}}")

        for cls in ("data", "hiz", "high", "low", "unknown"):
            if edge_lists[cls]:
                cmd += f" -{cls}_edges {{{' '.join(edge_lists[cls])}}}"

        cmd += " -visible"
        return cmd
