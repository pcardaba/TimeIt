from __future__ import annotations

import tkinter as tk

from .clocksignal import ClockSignal


class GClockSignal(ClockSignal):
    """A generated clock: a divided version of a source clock.

    Topologies "clockout" and "clockinout". Its waveform is not given
    explicitly: it is derived from the master (source) clock waveform and the
    `edges` list, with the same semantics as the SDC
    `create_generated_clock -edges {r f e}` option:

      edges[0] : master edge that generates the rising edge of this clock.
      edges[1] : master edge that generates the falling edge of this clock.
      edges[2] : master edge that completes the cycle of this clock.

    Master edges are numbered from 1. `-edges {1 2 3}` is a copy of the master
    clock, `-edges {1 3 5}` a divide by 2, and so on.

    With `invert` the derived waveform is complemented (as the SDC
    `create_generated_clock -invert` option): the generating edges swap roles.
    """

    is_generated: bool = True

    def __init__(self, name):
        super().__init__(name)

        self.topology: str = "clockout"

        ## The source clock this clock derives from.
        self.master: ClockSignal | None = None
        self.edges: list[int] = [1, 2, 3]
        ## Set only when the clock was specified as a "divide by" (the edges
        ## list is then derived from it). None when edges were given directly.
        self.divide_by: int | None = None

        ## Inverted (complemented) clock: falls where the direct clock rises.
        self.invert: bool = False

        ## Expressions, resolved by Tcl.
        self.input_dly: str | None = None
        self.output_dly: str | None = None

    def source_root(self) -> ClockSignal:
        return self.master if self.master is not None else self

    # ------------------------------------------------------------------
    # Specification
    # ------------------------------------------------------------------
    @staticmethod
    def divide_by_edges(divisor: int) -> list[int]:
        """Master edges a clock divided by `divisor` is made of."""
        divisor = int(divisor)
        return [1, divisor + 1, 2 * divisor + 1]

    def set_divide_by(self, divisor: int) -> None:
        self.divide_by = int(divisor)
        self.edges = self.divide_by_edges(self.divide_by)

    def set_edges(self, edges) -> None:
        self.edges = [int(e) for e in edges]
        self.divide_by = None

    # ------------------------------------------------------------------
    # Derivation from the master clock
    # ------------------------------------------------------------------
    def _resolve_waveform(self) -> bool:
        """Derive period/rise_at/fall_at from master clock + edges + output delay.

        The generating edges come from the master clock waveform; the whole
        derived waveform is then right-shifted by the output delay (the delay
        the generated clock takes to come out of the interface).

        Returns False (and logs) when the clock can not be derived.
        """
        if self.master is None:
            if self.console is not None:
                self.console.append_log(
                    f"[GClockSignal] {self.name}: no master clock\n", "error")
            return False

        if len(self.edges) != 3:
            if self.console is not None:
                self.console.append_log(
                    f"[GClockSignal] {self.name}: -edges needs 3 values\n", "error")
            return False

        try:
            rise_at, fall_at, cycle_end = (self.master.edge_time(e) for e in self.edges)
            outdly = 0.0
            if self.output_dly is not None and not self.output_dly == "":
                outdly = self._tcl_eval_float(self.output_dly, context="GClockSignal")
        except (tk.TclError, ValueError) as exc:
            if self.console is not None:
                self.console.append_log(
                    f"[GClockSignal] {self.name}: can not derive from "
                    f"{self.master.name}\n{exc}\n", "error")
            return False

        period = cycle_end - rise_at
        if period <= 0.0:
            if self.console is not None:
                self.console.append_log(
                    f"[GClockSignal] {self.name}: -edges "
                    f"{{{' '.join(str(e) for e in self.edges)}}} gives a null "
                    f"or negative period\n", "error")
            return False

        ## An inverted clock swaps the roles of the generating edges: it
        ## falls where the direct clock would rise. The period is unchanged.
        if self.invert:
            rise_at, fall_at = fall_at, rise_at

        ## The generated clock comes out of the interface "outdly" later than
        ## the master clock edges that generate it.
        self.period = repr(period)
        self.rise_at = repr(rise_at + outdly)
        self.fall_at = repr(fall_at + outdly)

        ## A generated clock does not inherit the uncertainties of its master:
        ## they are not drawn on it.
        self.rise_uncertainty = None
        self.fall_uncertainty = None
        return True

    def ensure_resolved(self) -> bool:
        return self._resolve_waveform()

    # ------------------------------------------------------------------
    # Draw / write
    # ------------------------------------------------------------------
    def draw(self, canvas: tk.Canvas, top: int) -> int:
        if not self._resolve_waveform():
            return -999
        return super().draw(canvas, top)

    def _write_clock_args(self, fileref) -> None:
        if self.master is not None:
            fileref.write(f"   -master {self.master.name}  \\\n")

        if self.divide_by is not None:
            fileref.write(f"   -divide_by {self.divide_by}  \\\n")
        else:
            edges = " ".join(str(e) for e in self.edges)
            fileref.write(f"   -edges {{{edges}}}  \\\n")

        if self.invert:
            fileref.write("   -invert  \\\n")

        if self.topology == "clockinout" and self.input_dly is not None:
            fileref.write(f"   -input_dly {{{self.input_dly}}}  \\\n")
        if self.output_dly is not None:
            fileref.write(f"   -output_dly {{{self.output_dly}}}  \\\n")
