# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2024 Pablo Cardaba

"""Integration tests of the create_logic command on a live application."""

from __future__ import annotations

import math
import unittest

from TimeIt.tests.apphelper import AppTestCase

INF = math.inf

## A 10 ns clock and two inputs arriving 1 to 2 ns after their launch edge.
BASE = """
remove -all
set_app_var -name timings.tCLK -value {10}
set_app_var -name timings.tINmax -value {2}
set_app_var -name timings.tINmin -value {1}
set_app_var -name timings.tPD -value {1.5}
create_clock -name clk -topology source -period {$tCLK} -rise_at {0} \\
   -fall_at {$tCLK/2} -show 10 -visible
create_input -name req -specify external -launch_clock clk \\
   -rclk_inputdly_max {$tINmax} -rclk_inputdly_min {$tINmin} \\
   -high_edges {3P} -low_edges {0 8P} -visible
create_input -name ack -specify external -launch_clock clk \\
   -rclk_inputdly_max {$tINmax} -rclk_inputdly_min {$tINmin} \\
   -high_edges {5P} -low_edges {0 9P} -visible
create_input -name data -specify external -launch_clock clk \\
   -rclk_inputdly_max {$tINmax} -rclk_inputdly_min {$tINmin} \\
   -data_edges {2P 6P} -visible
"""


class TestCreateLogic(AppTestCase):

    def setUp(self):
        super().setUp()
        self.tcl(BASE)
        self.clear_log()

    # -- happy path -------------------------------------------------------

    def test_and_of_two_inputs(self):
        self.tcl("create_logic -name busy -op and -inputs {req ack} -visible")
        self.assertNoErrors()
        busy = self.app.signals.find("busy")
        self.assertEqual(busy.type, "logic")
        ## ack rises 41..42 while req is 1 (unknown lets through), req falls
        ## 71..72 while ack is 1. Everywhere else a 0 masks the other input.
        self.assertEqual(busy.state_intervals(),
                         [(-INF, 41.0, "low"), (41.0, 42.0, "unknown"),
                          (42.0, 71.0, "high"), (71.0, 72.0, "unknown"),
                          (72.0, INF, "low")])
        self.assertSignals("clk", "req", "ack", "data", "busy")

    def test_default_operator_is_and(self):
        self.tcl("create_logic -name busy -inputs {req ack}")
        self.assertNoErrors()
        self.assertEqual(self.app.signals.find("busy").op, "and")

    def test_not_and_chaining(self):
        self.tcl("create_logic -name busy -inputs {req ack}")
        self.tcl("create_logic -name busy_n -op not -inputs {busy} -visible")
        self.assertNoErrors()
        intervals = self.app.signals.find("busy_n").state_intervals()
        self.assertEqual(intervals[0], (-INF, 41.0, "high"))
        self.assertEqual(intervals[2], (42.0, 71.0, "low"))

    def test_hidden_signal_is_computed_and_readable(self):
        self.tcl("create_logic -name sel -op xor -inputs {req ack}")
        self.tcl("create_logic -name out -op and -inputs {sel req} -visible")
        self.assertNoErrors()
        self.assertFalse(self.app.signals.find("sel").visible)
        self.assertIsNotNone(self.app.signals.find("out").state_intervals())

    def test_tpd_delays_the_result(self):
        self.tcl("create_logic -name busy -inputs {req ack} -tpd_max {$tPD}")
        self.assertNoErrors()
        self.assertEqual(self.app.signals.find("busy").state_intervals()[2],
                         (43.5, 72.5, "high"))

    def test_changing_a_timing_variable_updates_the_signal(self):
        self.tcl("create_logic -name busy -inputs {req ack} -tpd_max {$tPD}")
        self.tcl("set_app_var -name timings.tPD -value {0.5}")
        self.assertEqual(self.app.signals.find("busy").state_intervals()[2],
                         (42.5, 71.5, "high"))

    def test_round_trip(self):
        self.tcl("create_logic -name busy -op nor -inputs {req ack} "
                 "-tpd_max {$tPD} -tpd_min {$tPD/2} -color blue -visible")
        self.tcl("create_logic -name busy_n -op not -inputs {busy}")
        self.assertRoundTrips()
        self.assertSignals("clk", "req", "ack", "data", "busy", "busy_n")
        busy = self.app.signals.find("busy")
        self.assertEqual(busy.op, "nor")
        self.assertEqual(busy.tpd_min, "$tPD/2")
        self.assertEqual(busy.color, "blue")

    def test_redefinition_keeps_position_and_clears_absent_delays(self):
        self.tcl("create_logic -name busy -inputs {req ack} -tpd_max {$tPD}")
        self.tcl("create_input -name later -launch_clock clk -high_edges {2P} -low_edges {0}")
        self.tcl("create_logic -name busy -op or -inputs {req ack}")
        self.assertNoErrors()
        busy = self.app.signals.find("busy")
        self.assertEqual(busy.op, "or")
        self.assertIsNone(busy.tpd_max)
        self.assertSignals("clk", "req", "ack", "data", "busy", "later")

    def test_help_and_registrations(self):
        self.tcl("create_logic -help")
        self.assertNoErrors()
        self.assertTrue(any("-inputs {list_signal_names}" in text
                            for _, text in self.log))
        self.assertIn("create_logic", self.app.console.commands)
        self.assertIn("create_logic", self.app.console.tcl_commands._registry)

    # -- refusals ---------------------------------------------------------

    def test_inputs_are_required(self):
        self.tcl("create_logic -name busy -op and")
        self.assertError("at least two inputs")
        self.assertNotIn("busy", self.app.signals)

    def test_not_takes_exactly_one_input(self):
        self.tcl("create_logic -name x -op not -inputs {req ack}")
        self.assertError("exactly one input")

    def test_binary_operator_needs_two_inputs(self):
        self.tcl("create_logic -name x -op xor -inputs {req}")
        self.assertError("at least two inputs")

    def test_unknown_operator_is_refused(self):
        self.tcl("create_logic -name x -op xnor -inputs {req ack}")
        self.assertError("not a valid value for -op")

    def test_unknown_signal_is_refused(self):
        self.tcl("create_logic -name x -inputs {req nosuch}")
        self.assertError("nosuch signal not found")

    def test_clock_operand_is_refused(self):
        self.tcl("create_logic -name x -inputs {req clk}")
        self.assertError("clk is a clock")

    def test_bus_operand_is_refused(self):
        self.tcl("create_logic -name x -inputs {req data}")
        self.assertError("carries bus data")

    def test_self_reference_is_refused(self):
        self.tcl("create_logic -name busy -inputs {req ack}")
        self.clear_log()
        self.tcl("create_logic -name busy -inputs {busy ack}")
        self.assertError("depend on itself")
        ## The existing definition is untouched.
        self.assertEqual([o.name for o in self.app.signals.find("busy").inputs],
                         ["req", "ack"])

    def test_indirect_cycle_is_refused(self):
        self.tcl("create_logic -name busy -inputs {req ack}")
        self.tcl("create_logic -name busy_n -op not -inputs {busy}")
        self.clear_log()
        self.tcl("create_logic -name busy -inputs {busy_n ack}")
        self.assertError("depend on itself through busy_n")

    def test_unresolvable_delay_removes_the_signal_with_a_reason(self):
        ## Codebase convention: a signal that can not be drawn is removed.
        self.tcl("create_logic -name busy -inputs {req ack} -tpd_max {$nosuchvar} -visible")
        self.assertError("nosuchvar")
        self.assertNotIn("busy", self.app.signals)


if __name__ == "__main__":
    unittest.main()
