# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2024 Pablo Cardaba

"""Integration tests of the create_sampled command on a live application."""

from __future__ import annotations

import math
import unittest

from TimeIt.tests.apphelper import AppTestCase
from TimeIt.tests.test_create_logic import BASE

INF = math.inf

## On top of BASE (10 ns clk, req rises 21..22 and falls 71..72): an input
## settling 1 ns before the 3P and 6P sampling edges, and a gating enable.
EXTRA = """
set_app_var -name timings.tSU -value {2}
set_app_var -name timings.tHO -value {1}
set_app_var -name timings.tCOmax -value {2.5}
set_app_var -name timings.tCOmin -value {1}
create_input -name late -specify external -launch_clock clk \\
   -rclk_inputdly_max {$tCLK-1} -rclk_inputdly_min {$tCLK-2} \\
   -high_edges {2P} -low_edges {0 5P} -visible
create_input -name en -specify external -launch_clock clk \\
   -rclk_inputdly_max {$tINmax} -rclk_inputdly_min {$tINmin} \\
   -high_edges {3P} -low_edges {0 6P} -visible
create_clock -name gclk -topology clockout -master clk -divide_by 1 \\
   -enabled_by en -enable_active high -visible
"""


class TestCreateSampled(AppTestCase):

    def setUp(self):
        super().setUp()
        self.tcl(BASE + EXTRA)
        self.clear_log()

    # -- happy path -------------------------------------------------------

    def test_instantaneous_sampling_on_rising_edges(self):
        self.tcl("create_sampled -name req_q -source req -clock clk -visible")
        self.assertNoErrors()
        req_q = self.app.signals.find("req_q")
        self.assertEqual(req_q.type, "sampled")
        ## req is 0 at t=20 (settles at 22), 1 at 30..70, 0 again at 80.
        self.assertEqual(req_q.state_intervals(),
                         [(-INF, 0.0, "unknown"), (0.0, 30.0, "low"),
                          (30.0, 80.0, "high"), (80.0, INF, "low")])

    def test_falling_edges(self):
        self.tcl("create_sampled -name req_q -source req -clock clk -edge falling")
        self.assertNoErrors()
        ## Falling edges at 5, 15, 25...: req is 1 from t=25 on, 0 from t=75.
        self.assertEqual(self.app.signals.find("req_q").state_intervals(),
                         [(-INF, 5.0, "unknown"), (5.0, 25.0, "low"),
                          (25.0, 75.0, "high"), (75.0, INF, "low")])

    def test_setup_violation_captures_unknown(self):
        self.tcl("create_sampled -name late_q -source late -clock clk "
                 "-setup {$tSU} -hold {$tHO} -tco_max {$tCOmax} -tco_min {$tCOmin} -visible")
        self.assertNoErrors()
        ## late settles at 19 and 49: inside the [t-2, t+1) apertures of the
        ## 20 and 50 edges, captured as unknown and held to the next edge.
        self.assertEqual(self.app.signals.find("late_q").state_intervals(),
                         [(-INF, 1.0, "unknown"), (2.5, 21.0, "low"),
                          (22.5, 31.0, "unknown"), (32.5, 51.0, "high"),
                          (52.5, 61.0, "unknown"), (62.5, INF, "low")])

    def test_gated_clock_only_samples_on_enabled_pulses(self):
        self.tcl("create_sampled -name req_g -source req -clock gclk -visible")
        self.assertNoErrors()
        ## en is high from 22 to 51: pulses 30, 40, 50 are emitted.
        self.assertEqual(self.app.signals.find("req_g").sampling_edges(),
                         [30.0, 40.0, 50.0])

    def test_bus_source_is_allowed(self):
        self.tcl("create_sampled -name data_q -source data -clock clk -visible")
        self.assertNoErrors()
        states = {s for _, _, s in self.app.signals.find("data_q").state_intervals()}
        self.assertIn("data", states)

    def test_chaining_with_logic(self):
        self.tcl("create_logic -name busy -inputs {req ack}")
        self.tcl("create_sampled -name busy_q -source busy -clock clk")
        self.tcl("create_logic -name busy_q_n -op not -inputs {busy_q} -visible")
        self.assertNoErrors()
        self.assertIsNotNone(self.app.signals.find("busy_q_n").state_intervals())

    def test_changing_a_timing_variable_updates_the_signal(self):
        self.tcl("create_sampled -name late_q -source late -clock clk -setup {$tSU}")
        self.assertEqual(self.app.signals.find("late_q").state_intervals()[2][2],
                         "unknown")
        self.tcl("set_app_var -name timings.tSU -value {0.5}")
        ## With 0.5 of setup the 19 settling meets the 20 edge: no violation.
        self.assertEqual(self.app.signals.find("late_q").state_intervals(),
                         [(-INF, 0.0, "unknown"), (0.0, 20.0, "low"),
                          (20.0, 50.0, "high"), (50.0, INF, "low")])

    def test_round_trip(self):
        self.tcl("create_sampled -name late_q -source late -clock clk -edge falling "
                 "-setup {$tSU} -hold {$tHO} -tco_max {$tCOmax} -tco_min {$tCOmin} "
                 "-color red -visible")
        self.tcl("create_sampled -name req_g -source req -clock gclk")
        self.assertRoundTrips()
        late_q = self.app.signals.find("late_q")
        self.assertEqual(late_q.edge, "falling")
        self.assertEqual(late_q.hold, "$tHO")
        self.assertEqual(late_q.color, "red")
        self.assertIs(self.app.signals.find("req_g").clock, self.app.signals.find("gclk"))

    def test_redefinition_clears_absent_timings(self):
        self.tcl("create_sampled -name req_q -source req -clock clk -setup {$tSU}")
        self.tcl("create_sampled -name req_q -source ack -clock clk")
        self.assertNoErrors()
        req_q = self.app.signals.find("req_q")
        self.assertIsNone(req_q.setup)
        self.assertIs(req_q.source, self.app.signals.find("ack"))

    def test_help_and_registrations(self):
        self.tcl("create_sampled -help")
        self.assertNoErrors()
        self.assertTrue(any("-clock sampling_clk" in text for _, text in self.log))
        self.assertIn("create_sampled", self.app.console.commands)
        self.assertIn("create_sampled", self.app.console.tcl_commands._registry)

    # -- refusals ---------------------------------------------------------

    def test_source_and_clock_are_required(self):
        self.tcl("create_sampled -name q -clock clk")
        self.assertError("-source is required")
        self.clear_log()
        self.tcl("create_sampled -name q -source req")
        self.assertError("-clock is required")
        self.assertNotIn("q", self.app.signals)

    def test_clock_source_is_refused(self):
        self.tcl("create_sampled -name q -source clk -clock clk")
        self.assertError("clk is a clock and cannot be sampled")

    def test_non_clock_as_sampling_clock_is_refused(self):
        self.tcl("create_sampled -name q -source req -clock ack")
        self.assertError("ack is not a clock")

    def test_bad_edge_is_refused(self):
        self.tcl("create_sampled -name q -source req -clock clk -edge both")
        self.assertError("not a valid value for -edge")

    def test_cycle_is_refused(self):
        self.tcl("create_sampled -name req_q -source req -clock clk")
        self.tcl("create_logic -name fb -op not -inputs {req_q}")
        self.clear_log()
        self.tcl("create_sampled -name req_q -source fb -clock clk")
        self.assertError("req_q would depend on itself through fb")
        self.assertIs(self.app.signals.find("req_q").source, self.app.signals.find("req"))

    def test_unresolvable_timing_removes_the_signal_with_a_reason(self):
        self.tcl("create_sampled -name q -source req -clock clk -setup {$nosuchvar} -visible")
        self.assertError("nosuchvar")
        self.assertNotIn("q", self.app.signals)


if __name__ == "__main__":
    unittest.main()
