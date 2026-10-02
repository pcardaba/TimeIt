# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2024 Pablo Cardaba

"""DDR capture: which capture clock edge takes the data launched at an edge.

When both rising and falling delays are given (both edges capture), the
capturing edge is the first capture clock edge of either polarity after the
launch edge, and its polarity picks the delays. Against a divided-by-2
capture clock this makes every launch edge captured, alternately on a
rising and on a falling edge -- the bug case of scripts/ddr_case_example.tcl
had the data of every other launch edge captured a full capture period late.
"""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from TimeIt.tests.apphelper import AppTestCase, SCRIPTS

EXAMPLE = SCRIPTS / "ddr_case_example.tcl"
EXAMPLE2 = SCRIPTS / "ddr_case_example2.tcl"

CLOCKS = """
create_clock -name launch_clk -topology source -period {10} -rise_at {5} -fall_at {10} -show 20 -visible
create_clock -name capture_clk -topology clockout -master launch_clk -divide_by 2 -show 10 -visible
"""


class TestDdrCapture(AppTestCase):

    def signal(self, name: str):
        sig = next(s for s in self.app.signals if s.name == name)
        self.assertTrue(sig.resolve_clock_params())
        self.assertTrue(sig._resolve_delay_params())
        return sig

    def delays(self, name: str, indexes=(1, 3, 5, 7)) -> list[tuple[float, float]]:
        """(dlymax, dlymin) of the rising-edge launches at absolute edge `indexes`."""
        sig = self.signal(name)
        return [sig._delays_at(n, "P") for n in indexes]

    # ------------------------------------------------------------------
    # The example script
    # ------------------------------------------------------------------
    def test_example_loads_and_round_trips(self):
        self.source(EXAMPLE)
        self.assertNoErrors()
        self.assertSignals("launch_clk", "capture_clk", "data1", "data2", "data3",
                           "din_ref", "din", "data_sdr")
        self.assertRoundTrips()

    def test_ddr_output_against_divided_clock_matches_single_clock(self):
        self.source(EXAMPLE)
        ## Launch at t, captured 10 later: valid from t+7 to next t+2.
        self.assertEqual(self.delays("data1"), [(7.0, 2.0)] * 4)
        self.assertEqual(self.delays("data2"), self.delays("data1"))
        self.assertEqual(self.signal("data2").state_intervals(),
                         self.signal("data1").state_intervals())

    def test_ddr_output_same_clock_both_edges_matches_too(self):
        self.source(EXAMPLE)
        ## data3 launches on every capture_clk edge (absolute 1, 2, 3, ...).
        data3 = self.signal("data3")
        self.assertEqual([data3._delays_at(n, "PN"[(n + 1) % 2]) for n in (1, 2, 3, 4)],
                         [(7.0, 2.0)] * 4)
        self.assertEqual(data3.state_intervals(),
                         self.signal("data1").state_intervals())

    def test_ddr_input_internal_against_divided_clock(self):
        self.source(EXAMPLE)
        self.assertEqual(self.delays("din_ref"), [(7.0, 2.0)] * 4)
        self.assertEqual(self.delays("din"), self.delays("din_ref"))
        self.assertEqual(self.signal("din").state_intervals(),
                         self.signal("din_ref").state_intervals())

    def test_sdr_against_divided_clock_still_waits_for_the_rising_edge(self):
        self.source(EXAMPLE)
        ## Rising delays only: launch 1P at 5 is captured by the capture_clk
        ## rising edge at 25, not by its falling edge at 15.
        self.assertEqual(self.delays("data_sdr", (1, 5, 9)), [(17.0, 2.0)] * 3)

    # ------------------------------------------------------------------
    # The capture edge lookup itself
    # ------------------------------------------------------------------
    def test_capture_edge_alternates_against_a_slower_clock(self):
        self.source(EXAMPLE)
        data2 = self.signal("data2")
        both = (data2.rclk_outputdly_max, data2.fclk_outputdly_max)
        ## launch_clk rises at 5, 15, 25, ...; capture_clk rises at 5, 25,
        ## 45, ... and falls at 15, 35, ...
        self.assertEqual(data2._capture_edge(1, "P", *both), (10.0, "N", 0.0))
        self.assertEqual(data2._capture_edge(3, "P", *both), (10.0, "P", 0.0))
        self.assertEqual(data2._capture_edge(5, "P", *both), (10.0, "N", 0.0))
        ## A single capturing polarity keeps waiting for that polarity.
        self.assertEqual(data2._capture_edge(3, "P", "x", None), (10.0, "P", -10.0))
        self.assertEqual(data2._capture_edge(1, "P", "x", None), (20.0, "P", 0.0))
        self.assertEqual(data2._capture_edge(1, "P", None, "x"), (10.0, "N", -10.0))
        self.assertEqual(data2._capture_edge(3, "P", None, "x"), (20.0, "N", 0.0))
        ## Unknown launch edge: the same-clock rule, no offset.
        self.assertEqual(data2._capture_edge(None, "P", *both), (0.0, "N", 0.0))
        self.assertEqual(data2._capture_edge(None, "N", *both), (0.0, "P", 0.0))

    def test_capture_edge_same_clock_lands_on_the_opposite_polarity(self):
        self.source(EXAMPLE)
        data3 = self.signal("data3")
        both = (data3.rclk_outputdly_max, data3.fclk_outputdly_max)
        self.assertEqual(data3._capture_edge(1, "P", *both), (10.0, "N", 0.0))
        self.assertEqual(data3._capture_edge(2, "N", *both), (10.0, "P", 0.0))

    def test_capture_edge_with_a_faster_capture_clock(self):
        ## The launch clock is the slow one: the capturing edge is the fast
        ## clock edge generating the next launch clock edge, of either
        ## polarity when both capture.
        self.tcl("""
            create_clock -name fast -topology source -period {10} -rise_at {0} -fall_at {5} -show 20 -visible
            create_clock -name slow -topology clockout -master fast -divide_by 2 -show 10 -visible
            create_output -name o -specify external -launch_clock slow -capture_clock fast \\
                -rclk_outputdly_max {1} -rclk_outputdly_min {0} \\
                -fclk_outputdly_max {1} -fclk_outputdly_min {0} \\
                -data_edges {1P 1N 2P 2N} -visible
            create_output -name o_r -specify external -launch_clock slow -capture_clock fast \\
                -rclk_outputdly_max {1} -rclk_outputdly_min {0} -data_edges {1P 2P} -visible
        """)
        self.assertNoErrors()
        o = self.signal("o")
        both = (o.rclk_outputdly_max, o.fclk_outputdly_max)
        self.assertEqual(o._capture_edge(1, "P", *both), (10.0, "N", 0.0))
        self.assertEqual(o._capture_edge(2, "N", *both), (10.0, "P", 0.0))
        o_r = self.signal("o_r")
        self.assertEqual(o_r._capture_edge(1, "P", "x", None), (20.0, "P", 0.0))

    # ------------------------------------------------------------------
    # Inserted capture clock: the windows hang on the capture edges
    # ------------------------------------------------------------------
    def test_example2_loads_and_round_trips(self):
        self.source(EXAMPLE2)
        self.assertNoErrors()
        self.assertSignals("launch_clk", "capture_clk", "data3", "data2",
                           "din3", "din2")
        self.assertRoundTrips()

    def test_ddr_output_against_an_inserted_divided_clock(self):
        self.source(EXAMPLE2)
        ## capture_clk comes out 3 after launch_clk: launched at 5, 15, ...
        ## the data is captured at 18, 28, ... and the previous data was
        ## captured at 8, 18, ... Setup 3 / hold 2 around those edges give
        ## windows from 15 to 20, 25 to 30, ... for both descriptions.
        self.assertEqual(self.delays("data3"), [(7.0, 2.0)] * 4)
        self.assertEqual(self.delays("data2"), [(10.0, 5.0)] * 4)
        self.assertEqual(self.signal("data2").state_intervals(),
                         self.signal("data3").state_intervals())
        self.assertEqual(self.signal("data3").state_intervals()[:2],
                         [(15.0, 20.0, "data"), (25.0, 30.0, "data")])

    def test_ddr_input_internal_against_an_inserted_divided_clock(self):
        self.source(EXAMPLE2)
        ## Internal delays hang on the capture edges as the capturing
        ## flip-flops see them: 3 before the pin for a clockout clock (the
        ## capture clock trim), hence 3 less than the output case.
        self.assertEqual(self.delays("din3"), [(4.0, -1.0)] * 4)
        self.assertEqual(self.delays("din2"), [(7.0, 2.0)] * 4)
        self.assertEqual(self.signal("din2").state_intervals(),
                         self.signal("din3").state_intervals())

    def test_capture_edges_with_an_inserted_clock(self):
        self.source(EXAMPLE2)
        data2 = self.signal("data2")
        both = (data2.rclk_outputdly_max, data2.fclk_outputdly_max)
        ## Launch 1P at 5: captured by the falling edge at 18, the previous
        ## capturing edge is the rising one at 8.
        self.assertEqual(data2._capture_edge(1, "P", *both), (13.0, "N", 3.0))
        self.assertEqual(data2._capture_edge(3, "P", *both), (13.0, "P", 3.0))
        ## Rising edges only: captured at 28, previously sampled at 8.
        self.assertEqual(data2._capture_edge(1, "P", "x", None), (23.0, "P", 3.0))
        self.assertEqual(data2._capture_edge(3, "P", "x", None), (13.0, "P", -7.0))

    def test_capture_clock_uncertainty_widens_the_window_at_both_ends(self):
        ## A source capture clock with 2 of uncertainty: the data must be
        ## established 1 earlier (earliest edge) and held 1 longer (latest
        ## edge), for the external output as for the internal input.
        self.tcl("""
            create_clock -name clk -topology source -period {10} -rise_at {0} -fall_at {5} \
                -rise_uncertainty {2} -fall_uncertainty {2} -show 10 -visible
            create_output -name o -specify external -launch_clock clk -capture_clock clk \
                -rclk_outputdly_max {3} -rclk_outputdly_min {-2} -data_edges {1P 2P 3P} -visible
            create_input -name i -specify internal -launch_clock clk -capture_clock clk \
                -rclk_inputdly_max {3} -rclk_inputdly_min {-2} -data_edges {1P 2P 3P} -visible
        """)
        self.assertNoErrors()
        ## Without uncertainty: captured a period later, (10 - 3, 0 + 2).
        self.assertEqual(self.delays("o", (1, 3)), [(6.0, 3.0)] * 2)
        self.assertEqual(self.delays("i", (1, 3)), [(6.0, 3.0)] * 2)

    def test_prev_edge(self):
        self.tcl(CLOCKS)
        clk = next(s for s in self.app.signals if s.name == "capture_clk")
        self.assertTrue(clk.ensure_resolved())
        ## capture_clk rises at 5, 25, ... and falls at 15, 35, ...: an edge
        ## on the time itself counts.
        self.assertEqual(clk.prev_edge(15.0), (15.0, "N"))
        self.assertEqual(clk.prev_edge(14.0), (5.0, "P"))
        self.assertEqual(clk.prev_edge(24.0, "P"), (5.0, "P"))
        self.assertEqual(clk.prev_edge(25.0, "P"), (25.0, "P"))
        self.assertEqual(clk.prev_edge(30.0, "N"), (15.0, "N"))

    def test_next_edge_of_either_polarity(self):
        self.tcl(CLOCKS)
        clk = next(s for s in self.app.signals if s.name == "capture_clk")
        self.assertTrue(clk.ensure_resolved())
        self.assertEqual(clk.next_edge(5.0), (15.0, "N"))
        self.assertEqual(clk.next_edge(15.0), (25.0, "P"))
        self.assertEqual(clk.next_edge(15.0, "N"), (35.0, "N"))
        self.assertEqual(clk.next_edge(5.0, "P"), (25.0, "P"))
        self.assertEqual(clk.next_edge(5.0, "NP"), (15.0, "N"))

    def test_used_launch_edge_indexes(self):
        self.source(EXAMPLE)
        self.assertEqual(self.signal("data_sdr").used_launch_edge_indexes(),
                         [(1, "P"), (5, "P"), (9, "P"), (13, "P"), (17, "P")])
        self.assertEqual(self.signal("data3").used_launch_edge_indexes()[:4],
                         [(1, "P"), (2, "N"), (3, "P"), (4, "N")])
        self.assertEqual(self.signal("data3").used_launch_edges(), {"P": 1, "N": 2})

    # ------------------------------------------------------------------
    # write_sdc shares the lookup
    # ------------------------------------------------------------------
    def test_write_sdc_ddr_against_divided_clock(self):
        self.source(EXAMPLE)
        with tempfile.TemporaryDirectory(prefix="timeit_sdc_") as tmp:
            out = Path(tmp) / "ddr.sdc"
            self.tcl("write_sdc -file {" + str(out) + "}")
            self.assertNoErrors()
            sdc = out.read_text(encoding="utf-8")

        def section(name: str) -> str:
            start = sdc.index(f"---- Output {name} :") if name.startswith("data") \
                else sdc.index(f"---- Input {name} :")
            end = sdc.find("\n# ----", start + 1)
            return sdc[start:end if end > 0 else None]

        ## data2: one statement per capturing edge of capture_clk, both
        ## polarities, and a plain single cycle relationship (the data
        ## changes on every launch_clk period).
        data2 = section("data2")
        self.assertEqual(data2.count("set_output_delay"), 2)
        self.assertEqual(data2.count("-add_delay"), 1)
        self.assertRegex(data2, r"set_output_delay -clock \{capture_clk\} -max 3 "
                                r"-min -2( -add_delay)? \[get_ports \{data2\}\]")
        self.assertRegex(data2, r"set_output_delay -clock \{capture_clk\} -clock_fall "
                                r"-max 3 -min -2( -add_delay)? \[get_ports \{data2\}\]")
        self.assertIn("no multicycle path needed", data2)
        self.assertNotIn("WARNING", data2)

        ## data_sdr: captured two launch_clk periods later, held for two.
        data_sdr = section("data_sdr")
        self.assertNotIn("-clock_fall", data_sdr)
        self.assertIn("set_multicycle_path -setup 2 -start -to [get_ports {data_sdr}]",
                      data_sdr)
        self.assertIn("set_multicycle_path -hold 1 -start -to [get_ports {data_sdr}]",
                      data_sdr)

        ## din: set_input_delay is keyed by the launch edge, so the second
        ## capturing edge of the rising launches is reported, not written.
        din = section("din")
        self.assertEqual(din.count("set_input_delay"), 1)
        self.assertIn("set din_offset_P 10", din)
        self.assertIn("WARNING: the rising-edge launches are also captured at", din)
        self.assertIn("no multicycle path needed", din)


if __name__ == "__main__":
    unittest.main()
