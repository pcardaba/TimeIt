# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2024 Pablo Cardaba

"""Capture-side windows never start before the edge that launches the data.

Output external and input internal delays hang both ends of a transition
window on capture clock edges (setup before the capturing edge, hold after
the previous capturing edge). When the launch edge falls after that hold
bound -- a launch clock faster than the capture clock, or a launch edge of
the polarity that does not capture -- the hold bound alone started the
transition before its own launch edge: an effect ahead of its cause. The
bug case is scripts/extdelay_bug_case.tcl: data1_o and data2_o launch every
16 fastclk cycles against a divide-by-16 capture clock, data1_o at 1P (on
the capture edge), data2_o at 4P (30 later), and both drew the same window.
"""

from __future__ import annotations

import unittest

from TimeIt.tests.apphelper import AppTestCase, SCRIPTS

EXAMPLE = SCRIPTS / "extdelay_bug_case.tcl"

CLOCKS = """
create_clock -name fastclk -topology clockin -period {10} -rise_at {5} -fall_at {10} -show 50 -visible
create_clock -name slowclk -topology clockout -master fastclk -divide_by 16 -show 3 -visible
"""


class TestLaunchEdgeFloor(AppTestCase):

    def signal(self, name: str):
        sig = next(s for s in self.app.signals if s.name == name)
        self.assertTrue(sig.resolve_clock_params())
        self.assertTrue(sig._resolve_delay_params())
        return sig

    def warnings(self) -> list[str]:
        return [text for tag, text in self.log if tag == "warning"]

    # ------------------------------------------------------------------
    # The bug case
    # ------------------------------------------------------------------
    def test_example_loads_and_round_trips(self):
        self.source(EXAMPLE)
        self.assertNoErrors()
        self.assertEqual(self.warnings(), [])
        self.assertSignals("fastclk", "slowclk", "data1_o", "data2_o")
        self.assertRoundTrips()

    def test_launch_on_the_capture_edge_keeps_the_hold_bound(self):
        self.source(EXAMPLE)
        ## fastclk 1P at 5 is also slowclk 1P: captured at 165, previous
        ## capturing edge at 5. Setup 13 / hold 9: window from 14 to 152.
        data1 = self.signal("data1_o")
        self.assertEqual(data1._delays_at(1, "P"), (147.0, 9.0))
        self.assertEqual(data1.state_intervals()[:2],
                         [(-float("inf"), 14.0, "low"), (152.0, 174.0, "high")])

    def test_launch_after_the_hold_bound_starts_at_the_launch_edge(self):
        self.source(EXAMPLE)
        ## fastclk 4P at 35: the hold bound (slowclk 1P + 9 = 14) is before
        ## the launch edge, so the transition starts at the launch edge
        ## (hold met with margin) and runs to the same setup bound (152).
        data2 = self.signal("data2_o")
        self.assertEqual(data2._delays_at(7, "P"), (117.0, 0.0))
        self.assertEqual(data2.state_intervals()[:3],
                         [(-float("inf"), 35.0, "low"), (152.0, 195.0, "high"),
                          (312.0, 355.0, "low")])
        ## The two signals no longer draw the same waveform.
        self.assertNotEqual(data2.state_intervals(),
                            self.signal("data1_o").state_intervals())

    def test_the_drawn_transition_starts_at_the_launch_edge(self):
        self.source(EXAMPLE)
        canvas = self.app.canvas
        edge = canvas.bbox(canvas.find_withtag("fastclk_edge_4P"))
        edge_x = (edge[0] + edge[2]) / 2
        ## The first transition polygon of data2_o (the one opened at 4P).
        polygons = [item for item in canvas.find_withtag("data2_o_transition")
                    if canvas.type(item) == "polygon"]
        first = min(polygons, key=lambda item: canvas.coords(item)[0])
        tilt = self.app.settings.waveform["tilt"]
        ## _draw_high_open places the polygon tilt to the left of dlymin.
        self.assertAlmostEqual(canvas.coords(first)[0], edge_x - tilt, delta=1.0)

    # ------------------------------------------------------------------
    # The mirror case: an input with internal delays
    # ------------------------------------------------------------------
    def test_input_internal_launched_after_the_hold_bound(self):
        self.tcl(CLOCKS)
        self.tcl("""
            create_input -name din -specify internal -launch_clock fastclk -capture_clock slowclk \
                -rclk_inputdly_max {13} -rclk_inputdly_min {-9} -high_edges {4P} -low_edges {0 20P} -visible
            create_input -name din_ref -specify internal -launch_clock fastclk -capture_clock slowclk \
                -rclk_inputdly_max {13} -rclk_inputdly_min {-9} -high_edges {1P} -low_edges {0 17P} -visible
        """)
        self.assertNoErrors()
        self.assertEqual(self.signal("din_ref")._delays_at(1, "P"), (147.0, 9.0))
        self.assertEqual(self.signal("din")._delays_at(7, "P"), (117.0, 0.0))

    # ------------------------------------------------------------------
    # Where the floor sits
    # ------------------------------------------------------------------
    def test_single_clock_launch_on_the_non_capturing_polarity(self):
        ## Rising delays only: data launched at a falling edge is captured by
        ## the next rising edge and the previous capturing edge is the rising
        ## one half a period before. The hold bound (-5 + 2) is before the
        ## launch edge: the transition starts at the launch edge.
        self.tcl("""
            create_clock -name clk -topology source -period {10} -rise_at {5} -fall_at {10} -show 10 -visible
            create_output -name o -specify external -launch_clock clk \
                -rclk_outputdly_max {3} -rclk_outputdly_min {-2} -data_edges {1N 2N 3N} -visible
        """)
        self.assertNoErrors()
        self.assertEqual(self.signal("o")._delays_at(2, "N"), (2.0, 0.0))

    def test_output_floor_follows_the_launching_flip_flops(self):
        ## Our flip-flops see a clockout launch clock its output delay
        ## before the pin: the floor is -outdly, as for the internal delays.
        ## genclk comes out at 7, 17, ...: launch 4P at 37, captured at 165,
        ## previous capturing edge at 5 (the hold bound 5 + 9 is well before).
        self.tcl("""
            create_clock -name fastclk -topology source -period {10} -rise_at {5} -fall_at {10} -show 50 -visible
            create_clock -name genclk -topology clockout -master fastclk -divide_by 1 -output_dly {2} -show 50 -visible
            create_clock -name slowclk -topology clockout -master fastclk -divide_by 16 -show 3 -visible
            create_output -name o -specify external -launch_clock genclk -capture_clock slowclk \
                -rclk_outputdly_max {13} -rclk_outputdly_min {-9} -high_edges {4P} -low_edges {0 20P} -visible
        """)
        self.assertNoErrors()
        self.assertEqual(self.signal("o")._delays_at(7, "P"), (115.0, -2.0))

    def test_floor_brought_forward_by_the_launch_uncertainty(self):
        ## The earliest launch edge is unc/2 early. slowclk inherits no
        ## uncertainty, so the setup bound does not move.
        self.tcl("""
            create_clock -name fastclk -topology source -period {10} -rise_at {5} -fall_at {10} \
                -rise_uncertainty {1} -show 50 -visible
            create_clock -name slowclk -topology clockout -master fastclk -divide_by 16 -show 3 -visible
            create_output -name o -specify external -launch_clock fastclk -capture_clock slowclk \
                -rclk_outputdly_max {13} -rclk_outputdly_min {-9} -high_edges {4P} -low_edges {0 20P} -visible
            create_input -name i -specify internal -launch_clock fastclk -capture_clock slowclk \
                -rclk_inputdly_max {13} -rclk_inputdly_min {-9} -high_edges {4P} -low_edges {0 20P} -visible
        """)
        self.assertNoErrors()
        self.assertEqual(self.signal("o")._delays_at(7, "P"), (117.0, -0.5))
        self.assertEqual(self.signal("i")._delays_at(7, "P"), (117.0, -0.5))

    def test_input_floor_is_the_pin_edge(self):
        ## The driving device sees the launch clock at the pin: the output
        ## delay of a clockout launch clock does not bring the floor forward
        ## (compare with the output case above).
        self.tcl("""
            create_clock -name fastclk -topology source -period {10} -rise_at {5} -fall_at {10} -show 50 -visible
            create_clock -name genclk -topology clockout -master fastclk -divide_by 1 -output_dly {2} -show 50 -visible
            create_clock -name slowclk -topology clockout -master fastclk -divide_by 16 -show 3 -visible
            create_input -name i -specify internal -launch_clock genclk -capture_clock slowclk \
                -rclk_inputdly_max {13} -rclk_inputdly_min {-9} -high_edges {4P} -low_edges {0 20P} -visible
        """)
        self.assertNoErrors()
        self.assertEqual(self.signal("i")._delays_at(7, "P"), (115.0, 0.0))

    def test_floor_against_a_faster_capture_clock(self):
        ## The launch clock is the slow generated one: data launched at its
        ## falling edge, captured by the fast clock edge generating its next
        ## rising edge. The previous capturing edge is its own rising edge, so
        ## the hold bound is before the launch edge.
        self.tcl("""
            create_clock -name fastclk -topology source -period {10} -rise_at {5} -fall_at {10} -show 20 -visible
            create_clock -name slowclk -topology clockout -master fastclk -divide_by 4 -show 5 -visible
            create_output -name o -specify external -launch_clock slowclk -capture_clock fastclk \
                -rclk_outputdly_max {3} -rclk_outputdly_min {-2} -data_edges {1N 2N 3N} -visible
        """)
        self.assertNoErrors()
        self.assertEqual(self.signal("o")._delays_at(2, "N"), (17.0, 0.0))

    def test_internal_specs_are_left_alone(self):
        ## Launch-side specs say explicitly when the data changes: a negative
        ## minimum delay is the user's statement, not a derived bound.
        self.tcl(CLOCKS)
        self.tcl("""
            create_output -name o -specify internal -launch_clock fastclk -capture_clock slowclk \
                -rclk_outputdly_max {3} -rclk_outputdly_min {-2} -data_edges {4P} -visible
            create_input -name i -specify external -launch_clock fastclk -capture_clock slowclk \
                -rclk_inputdly_max {3} -rclk_inputdly_min {-2} -data_edges {4P} -visible
        """)
        self.assertNoErrors()
        self.assertEqual(self.signal("o")._delays_at(7, "P"), (3.0, -2.0))
        self.assertEqual(self.signal("i")._delays_at(7, "P"), (3.0, -2.0))

    # ------------------------------------------------------------------
    # No budget at all
    # ------------------------------------------------------------------
    def test_no_budget_collapses_the_window_and_warns_once(self):
        ## Launched at fastclk 15P (145), captured at slowclk 2P (165) with a
        ## setup of 25: the data would have to be established before it is
        ## launched. The window collapses on the launch edge and a warning
        ## names the edge; a redraw does not repeat it.
        self.tcl(CLOCKS)
        self.tcl("""
            create_output -name o -specify external -launch_clock fastclk -capture_clock slowclk \
                -rclk_outputdly_max {25} -rclk_outputdly_min {-9} -high_edges {15P} -low_edges {0 20P} -visible
        """)
        self.assertNoErrors()
        self.assertEqual(self.signal("o")._delays_at(29, "P"), (0.0, 0.0))
        ## 20P (195) is captured at 325: plenty of budget, not reported.
        self.assertEqual(self.signal("o")._delays_at(39, "P"), (105.0, 0.0))
        self.assertEqual(len(self.warnings()), 1)
        self.assertIn("fastclk 15P", self.warnings()[0])
        self.assertNotIn("20P", self.warnings()[0])
        self.app.redraw()
        self.root.update()
        self.assertEqual(len(self.warnings()), 1)
        ## Fixing the spec clears it silently; breaking it again warns again
        ## (set_attribute does not take delays: the model is edited directly,
        ## as the signal dialog does).
        self.clear_log()
        o = self.signal("o")
        o.rclk_outputdly_max = "13"
        self.app.redraw()
        self.root.update()
        self.assertEqual(self.warnings(), [])
        o.rclk_outputdly_max = "25"
        self.app.redraw()
        self.root.update()
        self.assertEqual(len(self.warnings()), 1)


if __name__ == "__main__":
    unittest.main()
