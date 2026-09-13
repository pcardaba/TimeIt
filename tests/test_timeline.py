# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2024 Pablo Cardaba

"""Unit tests for the pure timeline algebra (no Tk, no canvas)."""

import math
import unittest

from TimeIt.classes import timeline as tl

INF = math.inf


def const(value):
    """A constant timeline."""
    return [(-INF, INF, value)]


class TestCoalesce(unittest.TestCase):

    def test_merges_adjacent_equal_segments(self):
        got = tl.coalesce([(-INF, 0.0, "0"), (0.0, 5.0, "0"), (5.0, INF, "1")])
        self.assertEqual(got, [(-INF, 5.0, "0"), (5.0, INF, "1")])

    def test_keeps_adjacent_different_segments(self):
        segs = [(-INF, 5.0, "0"), (5.0, INF, "1")]
        self.assertEqual(tl.coalesce(segs), segs)

    def test_drops_empty_segments(self):
        got = tl.coalesce([(-INF, 5.0, "0"), (5.0, 5.0, "1"), (5.0, INF, "0")])
        self.assertEqual(got, [(-INF, INF, "0")])

    def test_does_not_merge_across_a_gap(self):
        ## A gap between two equal-valued segments is a transition window and
        ## must survive: closing it would erase the uncertainty.
        segs = [(-INF, 5.0, "0"), (6.0, INF, "0")]
        self.assertEqual(tl.coalesce(segs), segs)


class TestFlatten(unittest.TestCase):

    def test_maps_each_state_to_its_value(self):
        got = tl.flatten([(-INF, 1.0, "low"),
                          (2.0, 3.0, "high"),
                          (4.0, 5.0, "unknown"),
                          (6.0, INF, "data")])
        self.assertEqual(got, [(-INF, 1.0, "0"),
                               (1.0, 2.0, "X"),
                               (2.0, 3.0, "1"),
                               (3.0, 6.0, "X"),
                               (6.0, INF, "D")])

    def test_gap_between_intervals_becomes_x(self):
        ## The gap is the min/max transition window computed by
        ## state_intervals(); it is where the timing realism lives.
        got = tl.flatten([(-INF, 1.0, "low"), (3.0, INF, "high")])
        self.assertEqual(got, [(-INF, 1.0, "0"),
                               (1.0, 3.0, "X"),
                               (3.0, INF, "1")])

    def test_hiz_is_one_when_pulled_up(self):
        got = tl.flatten([(-INF, INF, "hiz")], pulled_up=True)
        self.assertEqual(got, [(-INF, INF, "1")])

    def test_hiz_is_unknown_when_floating(self):
        got = tl.flatten([(-INF, INF, "hiz")], pulled_up=False)
        self.assertEqual(got, [(-INF, INF, "X")])

    def test_empty_input_is_all_unknown(self):
        self.assertEqual(tl.flatten([]), [(-INF, INF, "X")])

    def test_none_propagates(self):
        ## state_intervals() returns None when the signal cannot be resolved.
        self.assertIsNone(tl.flatten(None))


class TestValueAt(unittest.TestCase):

    SEGS = [(-INF, 1.0, "0"), (1.0, 3.0, "X"), (3.0, INF, "1")]

    def test_inside_a_segment(self):
        self.assertEqual(tl.value_at(self.SEGS, 2.0), "X")

    def test_at_minus_infinity(self):
        self.assertEqual(tl.value_at(self.SEGS, -INF), "0")

    def test_boundary_belongs_to_the_starting_segment(self):
        ## Segments are half-open [start, end), so t == 1.0 is the X segment,
        ## not the 0 segment that ends there.
        self.assertEqual(tl.value_at(self.SEGS, 1.0), "X")
        self.assertEqual(tl.value_at(self.SEGS, 3.0), "1")

    def test_inside_a_gap_is_none(self):
        self.assertIsNone(tl.value_at([(-INF, 1.0, "0"), (2.0, INF, "1")], 1.5))


class TestCombineTables(unittest.TestCase):
    """The operator tables, checked value by value on constant timelines."""

    def _op(self, op, *values):
        return tl.combine(op, [const(v) for v in values])[0][2]

    def _check(self, op, expected):
        for (a, b), want in expected.items():
            with self.subTest(a=a, b=b):
                self.assertEqual(self._op(op, a, b), want)

    AND = {("0", "0"): "0", ("0", "1"): "0", ("0", "X"): "0",
           ("1", "0"): "0", ("1", "1"): "1", ("1", "X"): "X",
           ("X", "0"): "0", ("X", "1"): "X", ("X", "X"): "X"}
    OR = {("0", "0"): "0", ("0", "1"): "1", ("0", "X"): "X",
          ("1", "0"): "1", ("1", "1"): "1", ("1", "X"): "1",
          ("X", "0"): "X", ("X", "1"): "1", ("X", "X"): "X"}
    XOR = {("0", "0"): "0", ("0", "1"): "1", ("0", "X"): "X",
           ("1", "0"): "1", ("1", "1"): "0", ("1", "X"): "X",
           ("X", "0"): "X", ("X", "1"): "X", ("X", "X"): "X"}
    NOT = {"0": "1", "1": "0", "X": "X"}

    def test_and_table(self):
        self._check("and", self.AND)

    def test_or_table(self):
        self._check("or", self.OR)

    def test_xor_table(self):
        self._check("xor", self.XOR)

    def test_nand_is_the_inverted_and_table(self):
        ## The controlling value still masks the unknown: 0 NAND x = 1.
        self._check("nand", {k: self.NOT[v] for k, v in self.AND.items()})

    def test_nor_is_the_inverted_or_table(self):
        self._check("nor", {k: self.NOT[v] for k, v in self.OR.items()})

    def test_not_table(self):
        for a, want in self.NOT.items():
            with self.subTest(a=a):
                self.assertEqual(self._op("not", a), want)


class TestCombineArity(unittest.TestCase):

    def test_three_input_and_is_masked_by_any_zero(self):
        self.assertEqual(tl.combine("and", [const("1"), const("X"), const("0")]),
                         const("0"))

    def test_three_input_and_of_ones_is_one(self):
        self.assertEqual(tl.combine("and", [const("1")] * 3), const("1"))

    def test_three_input_or_is_masked_by_any_one(self):
        self.assertEqual(tl.combine("or", [const("X"), const("0"), const("1")]),
                         const("1"))

    def test_three_input_xor_is_parity(self):
        self.assertEqual(tl.combine("xor", [const("1")] * 3), const("1"))
        self.assertEqual(tl.combine("xor", [const("1"), const("1"), const("0")]),
                         const("0"))

    def test_three_input_nor_of_zeros_is_one(self):
        self.assertEqual(tl.combine("nor", [const("0")] * 3), const("1"))

    def test_single_operand_is_a_buffer(self):
        a = [(-INF, 2.0, "0"), (2.0, INF, "1")]
        self.assertEqual(tl.combine("and", [a]), a)
        self.assertEqual(tl.combine("or", [a]), a)

    def test_not_takes_exactly_one_operand(self):
        with self.assertRaises(ValueError):
            tl.combine("not", [const("1"), const("0")])

    def test_no_operand_is_rejected(self):
        with self.assertRaises(ValueError):
            tl.combine("and", [])

    def test_unknown_operator_is_rejected(self):
        with self.assertRaises(ValueError):
            tl.combine("xnor", [const("1"), const("1")])


class TestCombineTimelines(unittest.TestCase):

    def test_breakpoints_of_both_operands_are_merged(self):
        ## Operands driven by different clocks: their transitions interleave.
        a = [(-INF, 2.0, "0"), (2.0, INF, "1")]
        b = [(-INF, 3.0, "1"), (3.0, INF, "0")]
        self.assertEqual(tl.combine("and", [a, b]),
                         [(-INF, 2.0, "0"), (2.0, 3.0, "1"), (3.0, INF, "0")])

    def test_controlling_value_masks_an_unknown_window(self):
        ## b is transitioning between 2 and 4, but a holds 0 throughout, so
        ## the AND output never becomes unknown.
        a = const("0")
        b = [(-INF, 2.0, "1"), (2.0, 4.0, "X"), (4.0, INF, "0")]
        self.assertEqual(tl.combine("and", [a, b]), const("0"))

    def test_non_controlling_value_lets_the_unknown_through(self):
        a = const("1")
        b = [(-INF, 2.0, "1"), (2.0, 4.0, "X"), (4.0, INF, "0")]
        self.assertEqual(tl.combine("and", [a, b]),
                         [(-INF, 2.0, "1"), (2.0, 4.0, "X"), (4.0, INF, "0")])

    def test_a_gap_in_an_operand_counts_as_unknown(self):
        ## A gap is a transition window (value_at gives None there).
        a = const("1")
        b = [(-INF, 2.0, "1"), (4.0, INF, "0")]
        self.assertEqual(tl.combine("and", [a, b]),
                         [(-INF, 2.0, "1"), (2.0, 4.0, "X"), (4.0, INF, "0")])

    def test_result_is_coalesced(self):
        a = [(-INF, 2.0, "1"), (2.0, INF, "1")]
        b = [(-INF, 3.0, "1"), (3.0, INF, "1")]
        self.assertEqual(tl.combine("and", [a, b]), const("1"))

    def test_bus_operand_is_rejected(self):
        with self.assertRaises(ValueError):
            tl.combine("and", [const("D"), const("1")])
        with self.assertRaises(ValueError):
            tl.combine("not", [const("D")])


class TestShift(unittest.TestCase):

    SEGS = [(-INF, 2.0, "0"), (2.0, 5.0, "X"), (5.0, INF, "1")]

    def test_single_delay_shifts_finite_boundaries(self):
        got = tl.shift(self.SEGS, 1.5)
        self.assertEqual(got, [(-INF, 3.5, "0"), (3.5, 6.5, "X"), (6.5, INF, "1")])

    def test_leaves_infinite_boundaries_alone(self):
        self.assertEqual(tl.shift(const("1"), 3.0), const("1"))

    def test_zero_delay_is_identity(self):
        segs = [(-INF, 2.0, "0"), (2.0, INF, "1")]
        self.assertEqual(tl.shift(segs, 0.0), segs)
        self.assertEqual(tl.shift(segs, 0.0, 0.0), segs)

    def test_min_max_spread_opens_a_transition_window(self):
        ## A value ends when the fast path may change it (+min) and the next
        ## one is established when the slow path has settled (+max).
        segs = [(-INF, 2.0, "0"), (2.0, INF, "1")]
        self.assertEqual(tl.shift(segs, 3.0, 1.0),
                         [(-INF, 3.0, "0"), (5.0, INF, "1")])

    def test_spread_widens_an_existing_gap(self):
        segs = [(-INF, 2.0, "0"), (4.0, INF, "1")]
        self.assertEqual(tl.shift(segs, 3.0, 1.0),
                         [(-INF, 3.0, "0"), (7.0, INF, "1")])

    def test_pulse_narrower_than_the_spread_is_swallowed(self):
        segs = [(-INF, 2.0, "0"), (2.0, 3.0, "1"), (3.0, INF, "0")]
        self.assertEqual(tl.shift(segs, 3.0, 1.0),
                         [(-INF, 3.0, "0"), (6.0, INF, "0")])

    def test_min_above_max_is_rejected(self):
        with self.assertRaises(ValueError):
            tl.shift(self.SEGS, 1.0, 2.0)


class TestSample(unittest.TestCase):

    def test_holds_the_sampled_value_until_the_next_edge(self):
        source = [(-INF, 5.0, "0"), (5.0, INF, "1")]
        got = tl.sample(source, [0.0, 10.0, 20.0])
        ## X before the first edge, 0 sampled at t=0, 1 sampled at t=10 and
        ## again at t=20 so the two runs merge.
        self.assertEqual(got, [(-INF, 0.0, "X"),
                               (0.0, 10.0, "0"),
                               (10.0, INF, "1")])

    def test_output_is_unknown_before_the_first_edge(self):
        got = tl.sample(const("1"), [10.0])
        self.assertEqual(got, [(-INF, 10.0, "X"), (10.0, INF, "1")])

    def test_no_edges_gives_an_all_unknown_output(self):
        self.assertEqual(tl.sample(const("1"), []), const("X"))

    def test_consecutive_equal_samples_draw_no_transition(self):
        ## Two edges sampling the same value must produce one segment with no
        ## clock-to-Q gap between them.
        got = tl.sample(const("1"), [0.0, 10.0], tco_max=2.0, tco_min=1.0)
        self.assertEqual(got, [(-INF, 1.0, "X"), (2.0, INF, "1")])

    def test_clock_to_q_leaves_a_transition_gap(self):
        source = [(-INF, 5.0, "0"), (5.0, INF, "1")]
        got = tl.sample(source, [0.0, 10.0], tco_max=2.0, tco_min=1.0)
        self.assertEqual(got, [(-INF, 1.0, "X"),
                               (2.0, 11.0, "0"),
                               (12.0, INF, "1")])

    def test_unknown_source_samples_unknown_and_holds(self):
        source = [(-INF, 4.0, "0"), (4.0, 6.0, "X"), (6.0, INF, "1")]
        got = tl.sample(source, [0.0, 5.0, 10.0])
        self.assertEqual(got, [(-INF, 0.0, "X"),
                               (0.0, 5.0, "0"),
                               (5.0, 10.0, "X"),
                               (10.0, INF, "1")])

    def test_transition_window_overlapping_the_aperture_gives_unknown(self):
        ## The captured X merges with the pre-first-edge X run, so the whole
        ## output is a single unknown segment.
        source = [(-INF, 9.5, "0"), (9.5, 10.5, "X"), (10.5, INF, "1")]
        got = tl.sample(source, [10.0], setup=2.0, hold=1.0)
        self.assertEqual(got, const("X"))

    def test_unknown_ending_exactly_at_setup_boundary_meets_setup(self):
        ## Half-open aperture: an X window that ends exactly at t - setup has
        ## settled in time and must not turn the sample unknown.
        source = [(-INF, 8.0, "X"), (8.0, INF, "1")]
        got = tl.sample(source, [10.0], setup=2.0, hold=1.0)
        self.assertEqual(got, [(-INF, 10.0, "X"), (10.0, INF, "1")])

    def test_unknown_starting_exactly_at_hold_boundary_meets_hold(self):
        source = [(-INF, 11.0, "1"), (11.0, INF, "X")]
        got = tl.sample(source, [10.0], setup=2.0, hold=1.0)
        self.assertEqual(got, [(-INF, 10.0, "X"), (10.0, INF, "1")])

    def test_degenerate_aperture_uses_the_segment_starting_at_the_edge(self):
        ## setup == hold == 0: half-open segment rule decides the boundary.
        source = [(-INF, 10.0, "0"), (10.0, INF, "1")]
        got = tl.sample(source, [10.0])
        self.assertEqual(got, [(-INF, 10.0, "X"), (10.0, INF, "1")])

    def test_a_bus_source_samples_as_a_bus(self):
        source = [(-INF, 5.0, "X"), (5.0, INF, "D")]
        got = tl.sample(source, [0.0, 10.0])
        self.assertEqual(got, [(-INF, 10.0, "X"), (10.0, INF, "D")])

    def test_a_gap_in_the_source_samples_unknown(self):
        ## A gap is a transition window; value_at returns None there.
        source = [(-INF, 9.0, "0"), (11.0, INF, "1")]
        got = tl.sample(source, [10.0])
        self.assertEqual(got, const("X"))


if __name__ == "__main__":
    unittest.main()
