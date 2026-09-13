# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2024 Pablo Cardaba

"""Unit tests for SampledSignal, using a fake clock and operand (no Tk)."""

import io
import math
import unittest

from TimeIt.classes.sampledsignal import SampledSignal
from TimeIt.tests.test_derivedsignal import FakeConsole, FakeOperand

INF = math.inf


class FakeClock:
    """A source clock with rise at 0, fall at half period, 3 cycles.

    `enabled` optionally lists which pulses a gating enable lets through;
    edge_time() then raises past the last enabled pulse, as ClockSignal does.
    """

    type = "clock"

    def __init__(self, name="clk", period=10.0, rise_at=0.0, fall_at=5.0,
                 cycles=3, enabled=None):
        self.name = name
        self.cycles = cycles
        self._period = period
        self._rise_at = rise_at
        self._fall_at = fall_at
        self._enabled = enabled

    def ensure_resolved(self):
        return True

    def _waveform(self):
        return (self._period, self._rise_at, self._fall_at)

    def edge_time(self, index):
        index = int(index)
        if self._enabled is not None:
            pulse, offset = divmod(index - 1, 2)
            visible = [n for n, on in enumerate(self._enabled) if on]
            if pulse >= len(visible):
                raise ValueError("beyond the last enabled pulse")
            index = 2 * visible[pulse] + 1 + offset
        first, second = ((self._rise_at, self._fall_at)
                         if self._rise_at < self._fall_at
                         else (self._fall_at, self._rise_at))
        cycle, position = divmod(index - 1, 2)
        return self._period * cycle + (first if position == 0 else second)


class TestSampledSignal(unittest.TestCase):

    def _signal(self, source, clock, edge="rising", values=None, **attrs):
        sig = SampledSignal("q")
        sig.source = source
        sig.clock = clock
        sig.edge = edge
        sig.console = FakeConsole(values)
        for key, value in attrs.items():
            setattr(sig, key, value)
        return sig

    def test_rising_edges_are_used(self):
        source = FakeOperand("d", [(-INF, 12.0, "low"), (12.0, INF, "high")])
        sig = self._signal(source, FakeClock())
        ## Rising edges at 0, 10, 20: samples 0, 0, 1.
        self.assertEqual(sig.recompute(),
                         [(-INF, 0.0, "X"), (0.0, 20.0, "0"), (20.0, INF, "1")])

    def test_falling_edges_are_used(self):
        source = FakeOperand("d", [(-INF, 12.0, "low"), (12.0, INF, "high")])
        sig = self._signal(source, FakeClock(), edge="falling")
        ## Falling edges at 5, 15, 25: samples 0, 1, 1.
        self.assertEqual(sig.recompute(),
                         [(-INF, 5.0, "X"), (5.0, 15.0, "0"), (15.0, INF, "1")])

    def test_sampling_edges_lists_the_right_times(self):
        sig = self._signal(FakeOperand("d", []), FakeClock())
        self.assertEqual(sig.sampling_edges(), [0.0, 10.0, 20.0])
        sig.edge = "falling"
        self.assertEqual(sig.sampling_edges(), [5.0, 15.0, 25.0])

    def test_inverted_clock_maps_polarity_from_the_waveform(self):
        ## rise_at > fall_at: the first edge of a cycle is the falling one.
        clock = FakeClock(rise_at=5.0, fall_at=0.0)
        sig = self._signal(FakeOperand("d", []), clock)
        self.assertEqual(sig.sampling_edges(), [5.0, 15.0, 25.0])

    def test_gated_clock_provides_only_the_enabled_edges(self):
        clock = FakeClock(enabled=[True, False, True])
        sig = self._signal(FakeOperand("d", []), clock)
        ## The drawn (visible) edges are the ones of pulses 0 and 2.
        self.assertEqual(sig.sampling_edges(), [0.0, 20.0])

    def test_setup_hold_aperture_captures_unknown(self):
        ## d settles at 19, the flop needs 2 of setup at t=20.
        source = FakeOperand("d", [(-INF, 18.0, "low"), (19.0, INF, "high")])
        sig = self._signal(source, FakeClock(), values={"$tSU": 2.0, "$tHO": 1.0},
                           setup="$tSU", hold="$tHO")
        self.assertEqual(sig.recompute(), [(-INF, 0.0, "X"), (0.0, 20.0, "0"),
                                           (20.0, INF, "X")])

    def test_tco_window_is_a_transition_gap(self):
        source = FakeOperand("d", [(-INF, 5.0, "low"), (5.0, INF, "high")])
        sig = self._signal(source, FakeClock(), values={"$max": 2.0, "$min": 1.0},
                           tco_max="$max", tco_min="$min")
        self.assertEqual(sig.recompute(), [(-INF, 1.0, "X"), (2.0, 11.0, "0"),
                                           (12.0, INF, "1")])

    def test_tco_min_above_max_is_logged_and_gives_none(self):
        sig = self._signal(FakeOperand("d", [(-INF, INF, "high")]), FakeClock(),
                           values={"$a": 1.0, "$b": 2.0}, tco_max="$a", tco_min="$b")
        self.assertIsNone(sig.timeline())
        self.assertTrue(any("tco_min" in e for e in sig.console.errors))

    def test_missing_clock_gives_none(self):
        sig = self._signal(FakeOperand("d", [(-INF, INF, "high")]), None)
        self.assertIsNone(sig.recompute())
        self.assertTrue(sig.console.errors)

    def test_unresolved_clock_gives_none(self):
        clock = FakeClock()
        clock.ensure_resolved = lambda: False
        sig = self._signal(FakeOperand("d", [(-INF, INF, "high")]), clock)
        self.assertIsNone(sig.recompute())

    def test_unresolvable_source_gives_none(self):
        self.assertIsNone(self._signal(FakeOperand("d", None), FakeClock()).recompute())

    def test_bus_source_is_held_as_a_bus(self):
        source = FakeOperand("d", [(-INF, 5.0, "unknown"), (5.0, INF, "data")])
        sig = self._signal(source, FakeClock())
        self.assertEqual(sig.recompute(), [(-INF, 10.0, "X"), (10.0, INF, "D")])

    def test_operands_include_source_and_clock(self):
        source = FakeOperand("d", [])
        clock = FakeClock()
        sig = self._signal(source, clock)
        self.assertEqual(sig.operands(), (source, clock))
        self.assertEqual(sig.related_clocks(), (clock,))

    def test_write_emits_a_recreating_command(self):
        sig = self._signal(FakeOperand("d", []), FakeClock(), edge="falling",
                           setup="$tSU", tco_max="1.2")
        sig.visible = True
        out = io.StringIO()
        sig.write(out)
        text = out.getvalue()
        self.assertIn("create_sampled -name q", text)
        self.assertIn("-source d", text)
        self.assertIn("-clock clk", text)
        self.assertIn("-edge falling", text)
        self.assertIn("-setup {$tSU}", text)
        self.assertIn("-tco_max {1.2}", text)
        self.assertNotIn("-hold", text)
        self.assertNotIn("-tco_min", text)
        self.assertIn(f"-use_uid {sig.uid}", text)
        self.assertIn("-visible", text)


if __name__ == "__main__":
    unittest.main()
