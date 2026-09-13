# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2024 Pablo Cardaba

"""Integration tests of the dependency rules between derived signals and
the signals they read: ordering, removal and replacement."""

from __future__ import annotations

import unittest

from TimeIt.tests.apphelper import AppTestCase
from TimeIt.tests.test_create_logic import BASE


class TestDependencies(AppTestCase):

    def setUp(self):
        super().setUp()
        self.tcl(BASE)
        self.tcl("create_logic -name busy -inputs {req ack} -visible")
        self.tcl("create_logic -name busy_n -op not -inputs {busy} -visible")
        self.tcl("create_sampled -name busy_q -source busy -clock clk -visible")
        self.clear_log()
        ## Order: clk req ack data busy busy_n busy_q

    # -- ordering ---------------------------------------------------------

    def test_operand_cannot_be_moved_below_its_reader(self):
        self.tcl("move_signal -name data -direction down")   # data is not read: fine
        self.assertNoErrors()
        self.assertSignals("clk", "req", "ack", "busy", "data", "busy_n", "busy_q")
        self.tcl("move_signal -name ack -direction down")    # would go below busy
        self.assertError("can not be moved below a signal that refers to it")
        self.assertSignals("clk", "req", "ack", "busy", "data", "busy_n", "busy_q")

    def test_reader_cannot_be_moved_above_its_operand(self):
        self.tcl("move_signal -name busy_n -direction up")
        self.assertError("can not be moved above a signal it refers to")
        self.tcl("move_signal -name busy -direction up")
        self.assertError("can not be moved above a signal it refers to")

    def test_legacy_clock_rules_still_hold(self):
        self.tcl("move_signal -name req -direction up")
        self.assertError("can not be moved above")
        self.clear_log()
        self.tcl("move_signal -name clk -direction down")
        self.assertError("can not be moved below")

    def test_any_reachable_order_reloads_intact(self):
        ## Every move the rules allow keeps the script loadable: no signal is
        ## ever written before one it reads.
        self.tcl("move_signal -name data -direction down")
        self.tcl("move_signal -name data -direction down")
        self.tcl("move_signal -name busy_q -direction up")
        self.assertNoErrors()
        self.assertSignals("clk", "req", "ack", "busy", "busy_n", "busy_q", "data")
        self.assertRoundTrips()
        self.assertSignals("clk", "req", "ack", "busy", "busy_n", "busy_q", "data")

    # -- removal ----------------------------------------------------------

    def _uid(self, name):
        return self.app.signals.find(name).uid

    def test_removing_a_read_operand_is_refused(self):
        self.tcl(f"remove -signal {{{self._uid('req')}}}")
        self.assertError("req is read by busy: remove or edit those derived signals")
        self.assertIn("req", self.app.signals)

    def test_removing_the_sampling_clock_is_refused(self):
        self.tcl("create_clock -name clk2 -topology source -period {10} -rise_at {0} -fall_at {5}")
        self.tcl("create_sampled -name req_q2 -source req -clock clk2")
        self.clear_log()
        self.tcl(f"remove -signal {{{self._uid('clk2')}}}")
        self.assertError("clk2 is read by req_q2")
        self.assertIn("clk2", self.app.signals)

    def test_removing_a_clock_whose_cascade_is_read_is_refused(self):
        ## clk itself is read by busy_q, and its I/O signals by busy.
        self.tcl(f"remove -signal {{{self._uid('clk')}}}")
        self.assertError("clk is read by busy, busy_q")
        self.assertSignals("clk", "req", "ack", "data", "busy", "busy_n", "busy_q")

    def test_removing_readers_first_then_the_operand(self):
        self.tcl(f"remove -signal {{{self._uid('busy_n')} {self._uid('busy_q')}}}")
        self.tcl(f"remove -signal {{{self._uid('busy')}}}")
        self.tcl(f"remove -signal {{{self._uid('req')}}}")
        self.assertNoErrors()
        self.assertSignals("clk", "ack", "data")

    def test_editing_the_reader_frees_the_operand(self):
        self.tcl(f"remove -signal {{{self._uid('busy_n')} {self._uid('busy_q')}}}")
        self.tcl("create_input -name en -launch_clock clk -high_edges {2P} -low_edges {0}")
        self.tcl("create_logic -name busy -inputs {ack en}")
        self.clear_log()
        self.tcl(f"remove -signal {{{self._uid('req')}}}")
        self.assertNoErrors()
        self.assertNotIn("req", self.app.signals)

    def test_a_clock_still_cascades_its_unread_io_signals(self):
        ## Legacy behaviour, unchanged: no derived signal reads clk2 or its I/O.
        self.tcl("create_clock -name clk2 -topology source -period {10} -rise_at {0} -fall_at {5}")
        self.tcl("create_input -name d2 -launch_clock clk2 -high_edges {2P} -low_edges {0}")
        self.clear_log()
        self.tcl(f"remove -signal {{{self._uid('clk2')}}}")
        self.assertNoErrors()
        self.assertNotIn("clk2", self.app.signals)
        self.assertNotIn("d2", self.app.signals)

    def test_remove_all_ignores_the_rules(self):
        self.tcl("remove -all")
        self.assertNoErrors()
        self.assertSignals()

    # -- replacement ------------------------------------------------------

    def test_replacing_a_read_signal_by_another_class_is_refused(self):
        ## busy (logic) is read by busy_n and busy_q; a sampled "busy" would
        ## be a different object and leave them reading a ghost.
        self.tcl("create_sampled -name busy -source req -clock clk")
        self.assertError("busy is read by busy_n, busy_q")
        self.assertEqual(self.app.signals.find("busy").type, "logic")

    def test_redefining_with_the_same_class_keeps_the_object(self):
        before = self.app.signals.find("busy")
        self.tcl("create_logic -name busy -op or -inputs {req ack}")
        self.assertNoErrors()
        self.assertIs(self.app.signals.find("busy"), before)
        self.assertIs(self.app.signals.find("busy_n").inputs[0], before)

    def test_unread_signal_can_change_class(self):
        self.tcl("create_sampled -name busy_n -source req -clock clk")
        self.assertNoErrors()
        self.assertEqual(self.app.signals.find("busy_n").type, "sampled")


if __name__ == "__main__":
    unittest.main()
