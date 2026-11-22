# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2024 Pablo Cardaba

"""Round caps on the lines that draw signal waveforms.

A waveform is drawn as separate line items meeting at its corners; "round"
caps (WAVEFORM_CAPSTYLE) fill the outer corner that "butt" leaves notched.
I/O levels at the edges of the diagram are drawn flat to the edge instead of
drawing a transition there and masking it with a background-coloured line:
the round cap of the level would stick out past the mask.
"""

from __future__ import annotations

import unittest

from TimeIt.classes.signal import WAVEFORM_CAPSTYLE
from TimeIt.tests.apphelper import AppTestCase, SCRIPTS
from TimeIt.tests.test_create_logic import BASE

EXTRA = """
create_input -name hi -specify external -launch_clock clk \\
   -rclk_inputdly_max {$tINmax} -rclk_inputdly_min {$tINmin} \\
   -high_edges {0 6P} -low_edges {2P} -lwidth 6 -visible
create_input -name lo -specify external -launch_clock clk \\
   -rclk_inputdly_max {$tINmax} -rclk_inputdly_min {$tINmin} \\
   -low_edges {0 6P} -high_edges {2P} -lwidth 6 -visible
create_input -name pu -specify external -launch_clock clk \\
   -rclk_inputdly_max {$tINmax} -rclk_inputdly_min {$tINmin} \\
   -hiz_edges {0 6P} -low_edges {2P} -pulled_up -visible
create_logic -name both -inputs {req ack} -visible
"""


class TestWaveformCapstyle(AppTestCase):

    def setUp(self):
        super().setUp()
        self.tcl(BASE + EXTRA)
        self.assertNoErrors()
        self.canvas = self.app.canvas

    def _lines(self, tag):
        return [i for i in self.canvas.find_withtag(tag)
                if self.canvas.type(i) == "line"]

    def assertRoundCaps(self, tag):
        items = self._lines(tag)
        self.assertTrue(items, f"no line tagged {tag}")
        for item in items:
            self.assertEqual(self.canvas.itemcget(item, "capstyle"),
                             WAVEFORM_CAPSTYLE, f"{tag} item {item}")

    def test_default_is_round(self):
        self.assertEqual(WAVEFORM_CAPSTYLE, "round")

    def test_clock_lines(self):
        self.assertRoundCaps("clk_waveform")

    def test_io_levels(self):
        for tag in ("hi_highvalid", "hi_lowvalid", "lo_highvalid",
                    "lo_lowvalid", "pu_lowvalid", "pu_hizvalid",
                    "pu_pu_transition"):
            with self.subTest(tag=tag):
                self.assertRoundCaps(tag)

    def test_derived_levels(self):
        for tag in ("both_highvalid", "both_lowvalid"):
            with self.subTest(tag=tag):
                self.assertRoundCaps(tag)

    def test_pwl_traces(self):
        self.source(SCRIPTS / "pwl_example.tcl")
        self.assertNoErrors()
        self.assertRoundCaps("pwl_traces")

    def test_io_levels_run_flat_to_the_diagram_edges(self):
        bg = self.canvas.cget("background")
        for name, first, last in (("hi", "highvalid", "highvalid"),
                                  ("lo", "lowvalid", "lowvalid")):
            sig = self.app.signals.find(name)
            with self.subTest(signal=name):
                ## No background-coloured mask over the level any more.
                for item in self._lines(f"{name}_waveform"):
                    self.assertNotEqual(self.canvas.itemcget(item, "fill"), bg)
                start = self.canvas.coords(self._lines(f"{name}_{first}")[0])
                self.assertEqual(start[0], sig.wfstarts_x)
                self.assertEqual(start[1], start[3], "level starts flat")
                end = self.canvas.coords(self._lines(f"{name}_{last}")[-1])
                self.assertAlmostEqual(end[-2], sig.wfends_x)
                self.assertEqual(end[-1], end[-3], "level ends flat")

    def test_pulled_up_line_ends_flat_at_the_diagram_edge(self):
        """A released pulled-up line bends down into the transition that
        follows; the last one has none, and runs flat to the edge."""
        sig = self.app.signals.find("pu")
        lines = self._lines("pu_hizvalid")
        first = self.canvas.coords(lines[0])
        self.assertNotEqual(first[-1], first[1], "bends into the low level")
        end = self.canvas.coords(lines[-1])
        self.assertAlmostEqual(end[-2], sig.wfends_x)
        self.assertEqual(len(end), 4)
        self.assertEqual(end[-1], end[1], "released line ends flat")


if __name__ == "__main__":
    unittest.main()
