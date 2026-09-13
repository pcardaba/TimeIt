# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2024 Pablo Cardaba

"""Unit tests of the SignalsStore dependency rules, with fake signals."""

from __future__ import annotations

import unittest

from TimeIt.classes.signalsstore import SignalsStore


class FakeSignal:
    ## SignalsStore.add() indexes by uid, so a stand-in signal needs one.
    _next_uid = 0

    def __init__(self, name, sig_type="input", operands=(), clocks=(),
                 master=None):
        self.name = name
        self.type = sig_type
        self._operands = operands
        self._clocks = clocks
        self.master = master
        self._related = set()
        self.uid = FakeSignal._next_uid
        FakeSignal._next_uid += 1

    def operands(self):
        return self._operands

    def related_clocks(self):
        return self._clocks

    def get_related_objs(self):
        return self._related


def build():
    """clk -> din, dout (I/O); g = din and dout; q = g sampled by clk."""
    store = SignalsStore()
    clk = FakeSignal("clk", "clock")
    din = FakeSignal("din", clocks=(clk,))
    dout = FakeSignal("dout", "output", clocks=(clk,))
    clk._related = {din, dout}          # cascade registration, as wire_io_clocks does
    g = FakeSignal("g", "logic", operands=(din, dout))
    q = FakeSignal("q", "sampled", operands=(g, clk))
    for sig in (clk, din, dout, g, q):
        store.add(sig.name, sig)
    return store, clk, din, dout, g, q


class TestReferences(unittest.TestCase):

    def test_io_signal_refers_to_its_clocks(self):
        store, clk, din, *_ = build()
        self.assertEqual(store._references(din), (clk,))

    def test_generated_clock_refers_to_its_master(self):
        store, clk, *_ = build()
        gclk = FakeSignal("gclk", "clock", master=clk)
        self.assertEqual(store._references(gclk), (clk,))

    def test_derived_signal_refers_to_its_operands(self):
        store, clk, din, dout, g, q = build()
        self.assertEqual(store._references(g), (din, dout))
        self.assertEqual(store._references(q), (g, clk))

    def test_none_has_no_references(self):
        self.assertEqual(SignalsStore._references(None), ())


class TestDependents(unittest.TestCase):

    def test_direct_readers(self):
        store, clk, din, dout, g, q = build()
        self.assertEqual(store.dependents_of("din"), ["g"])
        self.assertEqual(store.dependents_of("g"), ["q"])
        self.assertEqual(store.dependents_of("q"), [])

    def test_sampling_clock_is_read(self):
        store, *_ = build()
        ## q reads clk directly, and g through the cascaded din/dout.
        self.assertEqual(store.dependents_of("clk"), ["g", "q"])

    def test_readers_through_the_cascade(self):
        ## A clock referenced only by I/O signals is removable unless one of
        ## those I/O signals (removed with it) is read by a derived signal.
        store = SignalsStore()
        clk = FakeSignal("clk", "clock")
        din = FakeSignal("din", clocks=(clk,))
        clk._related = {din}
        store.add("clk", clk)
        store.add("din", din)
        self.assertEqual(store.dependents_of("clk"), [])
        g = FakeSignal("g", "logic", operands=(din, din))
        store.add("g", g)
        self.assertEqual(store.dependents_of("clk"), ["g"])

    def test_cascade_is_transitive(self):
        store = SignalsStore()
        clk = FakeSignal("clk", "clock")
        gclk = FakeSignal("gclk", "clock", master=clk)
        din = FakeSignal("din", clocks=(gclk,))
        clk._related = {gclk}
        gclk._related = {din}
        self.assertEqual({s.name for s in store.cascade_of(clk)}, {"gclk", "din"})

    def test_unknown_name_has_no_dependents(self):
        store, *_ = build()
        self.assertEqual(store.dependents_of("nosuch"), [])

    def test_remove_error_names_the_dependents(self):
        store, *_ = build()
        self.assertIsNone(store.remove_error("q"))
        error = store.remove_error("din")
        self.assertIn("din is read by g", error)
        self.assertIn("remove or edit", error)


class TestMoveRules(unittest.TestCase):

    def test_io_signal_cannot_move_above_its_clock(self):
        store, *_ = build()
        self.assertIsNotNone(store.move_error("din", "up"))

    def test_clock_cannot_move_below_a_signal_referring_to_it(self):
        store, *_ = build()
        self.assertIsNotNone(store.move_error("clk", "down"))

    def test_derived_signal_cannot_move_above_its_operand(self):
        store, *_ = build()
        ## g sits directly below dout, which it reads.
        self.assertIsNotNone(store.move_error("g", "up"))
        self.assertIsNotNone(store.move_error("q", "up"))

    def test_operand_cannot_move_below_its_reader(self):
        store, *_ = build()
        ## dout sits directly above g, which reads it.
        self.assertIsNotNone(store.move_error("dout", "down"))
        self.assertIsNotNone(store.move_error("g", "down"))

    def test_unrelated_moves_are_allowed(self):
        store, *_ = build()
        ## din and dout do not refer to each other.
        self.assertIsNone(store.move_error("din", "down"))
        self.assertIsNone(store.move_error("dout", "up"))

    def test_moves_at_the_ends_are_not_errors(self):
        store, *_ = build()
        self.assertIsNone(store.move_error("clk", "up"))
        self.assertIsNone(store.move_error("q", "down"))

    def test_unknown_signal_is_an_error(self):
        store, *_ = build()
        self.assertIn("not found", store.move_error("nosuch", "up"))


if __name__ == "__main__":
    unittest.main()
