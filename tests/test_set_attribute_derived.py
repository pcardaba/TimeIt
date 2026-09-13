# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2024 Pablo Cardaba

"""Integration tests of set_attribute on logic and sampled signals."""

from __future__ import annotations

import math
import unittest

from TimeIt.tests.apphelper import AppTestCase
from TimeIt.tests.test_create_logic import BASE

INF = math.inf


class TestSetAttributeDerived(AppTestCase):

    def setUp(self):
        super().setUp()
        self.tcl(BASE)
        self.tcl("create_clock -name clk2 -topology source -period {10} -rise_at {0} -fall_at {5}")
        self.tcl("create_input -name en -launch_clock clk -high_edges {2P} -low_edges {0 4P}")
        self.tcl("create_logic -name busy -inputs {req ack} -tpd_max {$tPD} -visible")
        self.tcl("create_sampled -name busy_q -source busy -clock clk -setup {$tPD} -visible")
        self.clear_log()

    def _busy(self):
        return self.app.signals.find("busy")

    def _busy_q(self):
        return self.app.signals.find("busy_q")

    # -- logic ------------------------------------------------------------

    def test_op(self):
        self.tcl("set_attribute -signal busy -name op -value nor")
        self.assertNoErrors()
        self.assertEqual(self._busy().op, "nor")
        self.assertEqual(self._busy().state_intervals()[0][2], "high")

    def test_bad_op_is_refused(self):
        self.tcl("set_attribute -signal busy -name op -value xnor")
        self.assertError("not a valid value for op")
        self.assertEqual(self._busy().op, "and")
        self.assertIn("busy", self.app.signals)

    def test_op_must_fit_the_current_inputs(self):
        self.tcl("set_attribute -signal busy -name op -value not")
        self.assertError("takes exactly one input")
        self.assertEqual(self._busy().op, "and")

    def test_inputs(self):
        self.tcl("set_attribute -signal busy -name inputs -value {req ack en}")
        self.assertNoErrors()
        self.assertEqual([s.name for s in self._busy().inputs], ["req", "ack", "en"])
        self.assertRoundTrips()

    def test_inputs_must_fit_the_operator(self):
        self.tcl("set_attribute -signal busy -name inputs -value {req}")
        self.assertError("at least two inputs")
        self.assertEqual([s.name for s in self._busy().inputs], ["req", "ack"])

    def test_inputs_refuse_a_clock_a_bus_and_an_unknown_name(self):
        for value, fragment in (("{req clk}", "clk is a clock"),
                                ("{req data}", "carries bus data"),
                                ("{req nosuch}", "nosuch signal not found")):
            self.clear_log()
            self.tcl(f"set_attribute -signal busy -name inputs -value {value}")
            self.assertError(fragment)
        self.assertEqual([s.name for s in self._busy().inputs], ["req", "ack"])

    def test_inputs_refuse_a_cycle(self):
        self.tcl("set_attribute -signal busy -name inputs -value {req busy_q}")
        self.assertError("busy would depend on itself through busy_q")
        self.assertEqual([s.name for s in self._busy().inputs], ["req", "ack"])

    def test_tpd_expressions(self):
        self.tcl("set_attribute -signal busy -name tpd_max -value {$tPD*2}")
        self.tcl("set_attribute -signal busy -name tpd_min -value {$tPD}")
        self.assertNoErrors()
        self.assertEqual(self._busy().tpd_max, "$tPD*2")
        self.assertEqual(self._busy().tpd_min, "$tPD")
        ## Established at +3.0, released at +1.5: the 1 ns unknown windows are
        ## swallowed by the 1.5 ns spread, leaving pure transition gaps.
        self.assertEqual(self._busy().state_intervals(),
                         [(-INF, 42.5, "low"), (45.0, 72.5, "high"), (75.0, INF, "low")])

    def test_blank_tpd_clears_it(self):
        self.tcl("set_attribute -signal busy -name tpd_max -value {}")
        self.assertNoErrors()
        self.assertIsNone(self._busy().tpd_max)
        self.assertEqual(self._busy().state_intervals()[2], (42.0, 71.0, "high"))

    def test_generic_attributes_still_work(self):
        self.tcl("set_attribute -signal busy -name color -value red")
        self.tcl("set_attribute -signal busy -name visible -value false")
        self.assertNoErrors()
        self.assertEqual(self._busy().color, "red")
        self.assertFalse(self._busy().visible)

    # -- sampled ----------------------------------------------------------

    def test_source(self):
        self.tcl("set_attribute -signal busy_q -name source -value req")
        self.assertNoErrors()
        self.assertIs(self._busy_q().source, self.app.signals.find("req"))
        self.assertRoundTrips()

    def test_source_refuses_a_clock_and_a_cycle(self):
        self.tcl("set_attribute -signal busy_q -name source -value clk")
        self.assertError("clk is a clock and cannot be sampled")
        self.tcl("create_logic -name fb -op not -inputs {busy_q}")
        self.clear_log()
        self.tcl("set_attribute -signal busy_q -name source -value fb")
        self.assertError("busy_q would depend on itself through fb")
        self.assertIs(self._busy_q().source, self._busy())

    def test_clock(self):
        self.tcl("set_attribute -signal busy_q -name clock -value clk2")
        self.assertNoErrors()
        self.assertIs(self._busy_q().clock, self.app.signals.find("clk2"))
        self.tcl("set_attribute -signal busy_q -name clock -value req")
        self.assertError("req is not a clock")
        self.assertIs(self._busy_q().clock, self.app.signals.find("clk2"))

    def test_edge(self):
        self.tcl("set_attribute -signal busy_q -name edge -value falling")
        self.assertNoErrors()
        self.assertEqual(self._busy_q().edge, "falling")
        self.tcl("set_attribute -signal busy_q -name edge -value both")
        self.assertError("not a valid value for edge")
        self.assertEqual(self._busy_q().edge, "falling")

    def test_timings(self):
        self.tcl("set_attribute -signal busy_q -name hold -value {$tPD/3}")
        self.tcl("set_attribute -signal busy_q -name tco_max -value {2}")
        self.tcl("set_attribute -signal busy_q -name setup -value {}")
        self.assertNoErrors()
        q = self._busy_q()
        self.assertEqual((q.setup, q.hold, q.tco_max), (None, "$tPD/3", "2"))
        self.assertRoundTrips()

    def test_by_uid(self):
        self.tcl(f"set_attribute -signal uid_{self._busy().uid} -name op -value or")
        self.assertNoErrors()
        self.assertEqual(self._busy().op, "or")


if __name__ == "__main__":
    unittest.main()
