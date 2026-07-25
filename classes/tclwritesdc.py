from __future__ import annotations

import re
from contextlib import contextmanager
from datetime import datetime
from typing import Any, Dict, TextIO

import tkinter as tk

from .tclcommandbase import TclCommandBase, OptSpec
from ._version import __version__


class TclWriteSdc(TclCommandBase):
    """Generate a partial SDC constraints file from the I/O signals.

    The SDC statements are derived analytically (canvas-free) from the same
    launch/capture model the drawing uses, but with the propagated-clock
    simplifications: clock latencies, clock interface delays and clock
    uncertainties are never folded into the emitted input/output delays.
    """

    command_name = "write_sdc"

    spec = {
        "-file": OptSpec("file", True, str),
    }

    def validate(self, opts: Dict[str, Any]) -> None:
        self.require(opts, "file")

    def execute(self, opts: Dict[str, Any]) -> str:
        path = str(opts["file"])
        try:
            with open(path, "w", encoding="utf-8", newline="\n") as f:
                self._write_header(f)
                self._write_timing_vars(f)
                self._write_clock_templates(f)
                n_in, n_out, n_skip = self._write_ports(f)
        except OSError as exc:
            raise ValueError(f"{path}: {exc}") from exc

        msg = f"SDC written to {path} ({n_in} input(s), {n_out} output(s)"
        if n_skip:
            msg += f", {n_skip} skipped"
        self.console.append_log(msg + ")\n", "result")
        return ""

    # ------------------------------------------------------------------
    # File sections
    # ------------------------------------------------------------------
    def _write_header(self, f: TextIO) -> None:
        ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        tunits = self.topapp.settings.waveform["tunits"]
        f.write(
            f"# TimeIt generated SDC constraints\n"
            f"# ================================\n"
            f"# version commit: ({__version__})\n"
            f"# datetime: {ts}\n"
            f"#\n"
            f"# DISCLAIMER: this file is NOT a complete, ready-to-use constraint\n"
            f"# deck. It is an aid meant to bootstrap the I/O constraining work:\n"
            f"# review every statement, complete the deck (clocks, uncertainties,\n"
            f"# exceptions, ...) and rework it to match the real design before\n"
            f"# using it.\n"
            f"#\n"
            f"# Assumptions:\n"
            f"# - Clock objects are NOT created here: proper create_clock /\n"
            f"#   create_generated_clock statements must exist BEFORE the\n"
            f"#   set_input_delay / set_output_delay statements below take effect\n"
            f"#   (commented-out templates are provided as a starting point).\n"
            f"# - Clocks are assumed PROPAGATED: clock latency and any other\n"
            f"#   clock network delay are NOT part of the I/O delays below.\n"
            f"# - Clock uncertainty is NOT included in the I/O delays: declare\n"
            f"#   it with set_clock_uncertainty on the clocks instead.\n"
            f"# - All time values are in the diagram time units ({tunits}).\n"
            f"# - Hidden (not visible) signals are left out.\n"
            f"# - Delay expressions reference the timing variables re-declared\n"
            f"#   below; expressions using other (plain) Tcl variables of the\n"
            f"#   diagram will not resolve.\n"
        )

    def _write_timing_vars(self, f: TextIO) -> None:
        tvars = self.topapp.timings.tvars
        if not tvars:
            return
        f.write("\n# ---- Timing variables ----\n")
        for name, expr in tvars.items():
            line = f"set {name} [expr {{{expr}}}]"
            desc = self.topapp.timings.tvars_desc.get(name)
            if desc:
                line += f"   ;# {desc}"
            f.write(line + "\n")

    def _write_clock_templates(self, f: TextIO) -> None:
        clocks = [s for s in self.topapp.signals if s.type == "clock"]
        if not clocks:
            return
        f.write(
            "\n# ---- Clock templates (uncomment and adapt) ----\n"
            "# The diagram clocks written as SDC statements. The -source of a\n"
            "# generated clock is a guess: point it to the actual pin of your\n"
            "# design. Declare your set_clock_uncertainty here too.\n"
        )
        for clk in clocks:
            self._write_clock_template(f, clk)

    def _write_clock_template(self, f: TextIO, clk) -> None:
        try:
            resolved = clk.ensure_resolved()
            if resolved:
                period, rise_at, fall_at = clk._waveform()
        except (tk.TclError, ValueError):
            resolved = False
        if not resolved:
            f.write(f"# {clk.name}: can not be resolved, no template\n")
            return

        if clk.is_generated:
            master = clk.master.name if clk.master is not None else "?"
            stmt = (f"create_generated_clock -name {clk.name} "
                    f"-source [get_ports {{{master}}}]")
            if clk.divide_by is not None:
                stmt += f" -divide_by {clk.divide_by}"
            else:
                stmt += f" -edges {{{' '.join(str(e) for e in clk.edges)}}}"
            if clk.invert:
                stmt += " -invert"
            stmt += f" [get_ports {{{clk.name}}}]"
        else:
            ## SDC -waveform wants the first rise then the following fall.
            fall = fall_at if fall_at > rise_at else fall_at + period
            stmt = (f"create_clock -name {clk.name} -period {period:g} "
                    f"-waveform {{{rise_at:g} {fall:g}}} "
                    f"[get_ports {{{clk.name}}}]")
        f.write(f"# {stmt}\n")

        if clk.rise_uncertainty or clk.fall_uncertainty:
            f.write(f"#   NOTE: {clk.name} diagram uncertainty: "
                    f"rise {{{clk.rise_uncertainty or 0}}} "
                    f"fall {{{clk.fall_uncertainty or 0}}} "
                    f"-- declare it via set_clock_uncertainty.\n")
        if clk.enabled_by is not None:
            f.write(f"#   NOTE: {clk.name} is gated by {clk.enabled_by.name} in "
                    f"the diagram. The SDC clock is defined\n"
                    f"#   free running: the gating enable path is a netlist "
                    f"clock-gating check, not a\n"
                    f"#   clock definition matter.\n")

    # ------------------------------------------------------------------
    # I/O ports
    # ------------------------------------------------------------------
    def _write_ports(self, f: TextIO) -> tuple[int, int, int]:
        n_in = n_out = n_skip = 0
        for sig in self.topapp.signals:
            if sig.type not in ("input", "output"):
                continue
            if not sig.visible:
                ## Hidden signals are deliberately left out.
                continue
            if not self._write_port(f, sig):
                n_skip += 1
            elif sig.type == "input":
                n_in += 1
            else:
                n_out += 1

        if n_in == 0 and n_out == 0:
            f.write("\n# No visible input/output signal in the diagram.\n")
        return n_in, n_out, n_skip

    def _write_port(self, f: TextIO, sig) -> bool:
        if not sig.resolve_clock_params():
            return self._warn_skip(f, sig,
                                   "launch/capture clocks can not be resolved")
        if not sig._resolve_delay_params():
            return self._warn_skip(f, sig,
                                   "delay expressions can not be resolved")
        pols = sig.used_launch_edges()
        if not pols:
            return self._warn_skip(f, sig, "no launch edge used (empty edge "
                                           "lists)")

        f.write(f"\n# ---- {sig.type.capitalize()} {sig.name} : "
                f"specify {sig.specify}, launch {sig.launchclk.name} -> "
                f"capture {sig.captureclk.name} ----\n")

        gated = [clk.name for clk in dict.fromkeys((sig.launchclk,
                                                    sig.captureclk))
                 if clk.enabled_by is not None]
        if gated:
            f.write(f"# NOTE: {' and '.join(gated)} is gated in the diagram. "
                    f"The constraints below are derived\n"
                    f"# from the free-running (ungated) waveform, as STA "
                    f"assumes: data transfers are\n"
                    f"# assumed while the clock is not gated (gating must not "
                    f"be used to create\n"
                    f"# multicycle data transfers).\n")

        ## One entry per launch polarity actually used by the edge lists.
        ## The offsets are computed on the nominal (ungated) waveforms: SDC
        ## clock definitions are free running, gating only removes pulses
        ## without moving them, and STA conservatively assumes all of them.
        entries = []  # (launch_pol, cap_pol, key, offset)
        with self._ungated(sig.launchclk, sig.captureclk):
            for launch_pol in ("P", "N"):
                if launch_pol not in pols:
                    continue
                cap_pol, key, assumed = self._delay_key(sig, launch_pol)
                offset = sig._capture_offset_at(pols[launch_pol], cap_pol)
                entries.append((launch_pol, cap_pol, key, offset, assumed))

        if sig.type == "input":
            self._write_input_delays(f, sig, entries)
        else:
            self._write_output_delays(f, sig, entries)

        self._write_multicycle(f, sig, entries)
        return True

    @staticmethod
    def _delay_key(sig, launch_pol: str) -> tuple[str, str, bool]:
        """(capture polarity, delay dict key, capture polarity assumed?).

        The delays of a capture-side spec (input internal, output external)
        are keyed by the capture polarity they themselves induce. A
        launch-side spec (input external, output internal) does not model
        the capture edge at all: it is assumed of the launch polarity.
        """
        if sig.type == "input":
            capture_side = sig.specify != "external"
            rdly, fdly = sig.rclk_inputdly_max, sig.fclk_inputdly_max
        else:
            capture_side = sig.specify == "external"
            rdly, fdly = sig.rclk_outputdly_max, sig.fclk_outputdly_max

        if capture_side:
            cap_pol = sig._capture_polarity(launch_pol, rdly, fdly)
            return cap_pol, ("rclk" if cap_pol == "P" else "fclk"), False
        return launch_pol, ("rclk" if launch_pol == "P" else "fclk"), True

    # ------------------------------------------------------------------
    # set_input_delay / set_output_delay
    # ------------------------------------------------------------------
    def _write_input_delays(self, f: TextIO, sig, entries) -> None:
        clock = sig.launchclk.name
        internal = sig.specify != "external"
        first = True
        for launch_pol, cap_pol, key, offset, _assumed in entries:
            raw_max = getattr(sig, f"{key}_inputdly_max")
            raw_min = getattr(sig, f"{key}_inputdly_min")

            if internal:
                ## Internal (capture flip-flop) delays converted into the
                ## equivalent external arrival window at the pin.
                var = self._offset_var(sig, launch_pol)
                f.write(f"# Internal delays converted to equivalent external "
                        f"input delays: capture at\n"
                        f"# {self._capture_desc(sig, cap_pol)}, {offset:g} "
                        f"after the {self._edge_word(launch_pol)} {clock} "
                        f"launch edge.\n")
                f.write(f"set {var} {offset:g}\n")
                vmax = f"[expr {{${var} - ({self._inner(raw_max)})}}]"
                vmin = f"[expr {{-({self._inner(raw_min)})}}]"
                num_max = offset - sig.indly[f"{key}max"]
                num_min = -sig.indly[f"{key}min"]
            else:
                vmax = self._format_expr(raw_max)
                vmin = self._format_expr(raw_min)
                num_max = sig.indly[f"{key}max"]
                num_min = sig.indly[f"{key}min"]

            stmt = f"set_input_delay -clock {{{clock}}}"
            if launch_pol == "N":
                stmt += " -clock_fall"
            stmt += f" -max {vmax} -min {vmin}"
            if not first:
                stmt += " -add_delay"
            stmt += f" [get_ports {{{sig.name}}}]"
            f.write(stmt + "\n")
            f.write(f"#   (resolves to -max {num_max + 0.0:g} -min {num_min + 0.0:g})\n")
            first = False

    def _write_output_delays(self, f: TextIO, sig, entries) -> None:
        clock = sig.captureclk.name
        internal = sig.specify != "external"
        merge_oe = internal and bool(sig.hiz_edges)
        first = True
        for launch_pol, cap_pol, key, offset, assumed in entries:
            raw_max = getattr(sig, f"{key}_outputdly_max")
            raw_min = getattr(sig, f"{key}_outputdly_min")

            if internal:
                ## Internal (launch path) delays converted into the equivalent
                ## external requirement seen from the capture edge.
                var = self._offset_var(sig, launch_pol)
                f.write(f"# Internal delays converted to equivalent external "
                        f"output delays: capture assumed at\n"
                        f"# {self._capture_desc(sig, cap_pol)}, {offset:g} "
                        f"after the {self._edge_word(launch_pol)} "
                        f"{sig.launchclk.name} launch edge\n"
                        f"# (the diagram does not model the capture edge of an "
                        f"internal-specify output: adjust\n"
                        f"# {var} if the receiving device uses another "
                        f"edge).\n")
                f.write(f"set {var} {offset:g}\n")
                if merge_oe:
                    oe_max = getattr(sig, f"{key}_oedly_max")
                    oe_min = getattr(sig, f"{key}_oedly_min")
                    f.write(f"# Tri-stated output: worst case of the output "
                            f"and output enable delays.\n")
                    vmax = (f"[expr {{${var} - max(({self._inner(raw_max)}), "
                            f"({self._inner(oe_max)}))}}]")
                    vmin = (f"[expr {{-min(({self._inner(raw_min)}), "
                            f"({self._inner(oe_min)}))}}]")
                    num_max = offset - max(sig.outdly[f"{key}max"],
                                           sig.oedly[f"{key}max"])
                    num_min = -min(sig.outdly[f"{key}min"],
                                   sig.oedly[f"{key}min"])
                else:
                    vmax = f"[expr {{${var} - ({self._inner(raw_max)})}}]"
                    vmin = f"[expr {{-({self._inner(raw_min)})}}]"
                    num_max = offset - sig.outdly[f"{key}max"]
                    num_min = -sig.outdly[f"{key}min"]
            else:
                vmax = self._format_expr(raw_max)
                vmin = self._format_expr(raw_min)
                num_max = sig.outdly[f"{key}max"]
                num_min = sig.outdly[f"{key}min"]

            stmt = f"set_output_delay -clock {{{clock}}}"
            if cap_pol == "N":
                stmt += " -clock_fall"
            stmt += f" -max {vmax} -min {vmin}"
            if not first:
                stmt += " -add_delay"
            stmt += f" [get_ports {{{sig.name}}}]"
            f.write(stmt + "\n")
            f.write(f"#   (resolves to -max {num_max + 0.0:g} -min {num_min + 0.0:g})\n")
            first = False

    # ------------------------------------------------------------------
    # set_multicycle_path
    # ------------------------------------------------------------------
    def _write_multicycle(self, f: TextIO, sig, entries) -> None:
        """Per-port multicycle relationship between the launch/capture clocks.

        The setup multiplier is the launch->capture offset counted in periods
        of the faster clock: -start when the launch clock is the faster one
        (the multiplier then counts launch edges), -end when the capture
        clock is. The hold multiplier is the period ratio minus one: the
        data changes once per slow clock period only.
        """
        if sig.launchclk is sig.captureclk:
            return
        lperiod = sig.lclk["period"]
        cperiod = sig.cclk["period"]
        fast = min(lperiod, cperiod)
        if fast <= 0.0:
            return

        launch_pol, cap_pol, _key, offset, _assumed = entries[0]
        ratio = max(lperiod, cperiod) / fast
        mult = offset / fast
        r_i = round(ratio)
        m_i = round(mult)

        if abs(ratio - r_i) > 1e-6 * ratio:
            f.write(f"# WARNING: {sig.launchclk.name}/{sig.captureclk.name} "
                    f"period ratio {ratio:g} is not an integer: review the "
                    f"multicycle statements.\n")
        if abs(mult - m_i) > 1e-6 * max(1.0, abs(mult)):
            f.write(f"# WARNING: launch->capture offset {offset:g} is not a "
                    f"whole number of {'launch' if lperiod < cperiod else 'capture'} "
                    f"clock periods ({mult:g}): review the multicycle "
                    f"statements.\n")
        for other in entries[1:]:
            if abs(other[3] - offset) > 1e-6 * max(1.0, abs(offset)):
                f.write(f"# WARNING: the {self._edge_word(other[0])}-edge "
                        f"launches have a different capture offset "
                        f"({other[3]:g}): the multicycle below only reflects "
                        f"the {self._edge_word(launch_pol)}-edge ones.\n")

        if m_i == 1 and r_i == 1:
            f.write("# (default single cycle launch->capture relationship: "
                    "no multicycle path needed)\n")
            return

        flag = "-start" if lperiod < cperiod else "-end"
        if sig.type == "input":
            anchor = f"-from [get_ports {{{sig.name}}}]"
        else:
            anchor = f"-to [get_ports {{{sig.name}}}]"
        f.write(f"set_multicycle_path -setup {m_i} {flag} {anchor}\n")
        f.write(f"set_multicycle_path -hold {r_i - 1} {flag} {anchor}\n")

    # ------------------------------------------------------------------
    # Small helpers
    # ------------------------------------------------------------------
    @staticmethod
    @contextmanager
    def _ungated(*clocks):
        """Temporarily disable clock gating on `clocks`.

        A gated clock numbers its edges on the emitted pulses only and its
        next-edge lookups skip the gated-off ones: the launch->capture
        offsets must instead be taken on the nominal free-running waveform
        (the one the SDC clock definitions describe).
        """
        saved = [(clk, clk.enabled_by) for clk in dict.fromkeys(clocks)]
        for clk, _ in saved:
            clk.enabled_by = None
        try:
            yield
        finally:
            for clk, enable in saved:
                clk.enabled_by = enable

    def _warn_skip(self, f: TextIO, sig, reason: str) -> bool:
        f.write(f"\n# WARNING: {sig.type} {sig.name} skipped: {reason}.\n")
        self.console.append_log(f"[write_sdc] {sig.name} skipped: {reason}\n",
                                "error")
        return False

    def _offset_var(self, sig, launch_pol: str) -> str:
        return f"{re.sub(r'[^0-9A-Za-z_]', '_', sig.name)}_offset_{launch_pol}"

    @staticmethod
    def _edge_word(pol: str) -> str:
        return "rising" if pol == "P" else "falling"

    def _capture_desc(self, sig, cap_pol: str) -> str:
        """Words for the capturing edge of `sig` (goes into a comment).

        When the capture clock is the faster one the polarity names a launch
        (generated) clock edge, not the physical capture clock edge that
        generates it (same convention as _capture_offset_at).
        """
        word = self._edge_word(cap_pol)
        if sig.cclk["period"] < sig.lclk["period"] * (1.0 - 1e-9):
            return (f"the {sig.captureclk.name} edge generating the next "
                    f"{word} {sig.launchclk.name} edge")
        return f"the next {word} {sig.captureclk.name} edge"

    @staticmethod
    def _inner(raw) -> str:
        """A delay expression as it goes inside a bigger [expr {...}]."""
        s = "" if raw is None else str(raw).strip()
        return s if s else "0"

    @classmethod
    def _format_expr(cls, raw) -> str:
        """A delay expression as a stand-alone SDC value."""
        s = cls._inner(raw)
        try:
            float(s)
            return s
        except ValueError:
            return f"[expr {{{s}}}]"
