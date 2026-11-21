# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2024 Pablo Cardaba

"""Clock waveform geometry (issue #15: period tail too long).

An edge is centred on its time, so it starts `tilt` px before it. The level
before it must stop exactly there: padding each period up to its boundary
left a `tilt` px tail past the foot of the next edge, plus a backward stub.
The drawn waveform must be one continuous path that never doubles back.
"""

from __future__ import annotations

import unittest

from TimeIt.tests.apphelper import AppTestCase
from TimeIt.tests.test_create_logic import BASE

CLOCKS = """
create_clock -name nclk -topology source -period {$tCLK} -rise_at {$tCLK/2} \\
   -fall_at {0} -show 10 -visible
create_clock -name sclk -topology source -period {$tCLK} -rise_at {2} \\
   -fall_at {7} -show 10 -visible
create_input -name en -specify external -launch_clock clk \\
   -rclk_inputdly_max {$tINmax} -rclk_inputdly_min {$tINmin} \\
   -high_edges {3P} -low_edges {0 6P} -visible
create_clock -name gclk -topology clockout -master clk -divide_by 1 \\
   -enabled_by en -enable_active high -visible
"""


class TestClockDrawing(AppTestCase):

    def setUp(self):
        super().setUp()
        self.tcl(BASE + CLOCKS)
        self.assertNoErrors()

    def _segments(self, canvas, name):
        """The (x0, y0, x1, y1) lines of the waveform of `name`, in order."""
        out = []
        for item in canvas.find_withtag(f"{name}_waveform"):
            if canvas.type(item) == "line":
                out.append(tuple(canvas.coords(item)))
        return out

    def _assert_continuous(self, canvas, name):
        segs = self._segments(canvas, name)
        self.assertTrue(segs, f"{name}: nothing drawn")
        for seg in segs:
            self.assertGreater(seg[2], seg[0],
                               f"{name}: segment not going forward {seg}")
        for prev, cur in zip(segs, segs[1:]):
            self.assertEqual(prev[2:], cur[:2],
                             f"{name}: {prev} does not join {cur}")

    def test_free_running_clocks_are_continuous(self):
        for canvas in (self.app.canvas, self.app.vcanvas):
            for name in ("clk", "nclk", "sclk"):
                with self.subTest(canvas=type(canvas).__name__, clock=name):
                    self._assert_continuous(canvas, name)

    def test_gated_clock_is_continuous(self):
        for canvas in (self.app.canvas, self.app.vcanvas):
            with self.subTest(canvas=type(canvas).__name__):
                self._assert_continuous(canvas, "gclk")

    def test_level_stops_at_the_foot_of_the_next_edge(self):
        canvas = self.app.canvas
        tilt = self.app.settings.waveform["tilt"]
        edges = [tuple(canvas.coords(i))
                 for i in canvas.find_withtag("clk_Pedges")]
        self.assertTrue(edges)
        for x0, _y0, x1, _y1 in edges:
            self.assertEqual(x1 - x0, 2 * tilt)
            ## No level line of the clock reaches past the foot of an edge
            ## on the side the edge leaves from.
            for seg in self._segments(canvas, "clk"):
                if seg[1] == seg[3] == _y0:
                    self.assertFalse(seg[0] < x0 < seg[2],
                                     f"level {seg} overshoots edge at {x0}")

    def test_waveform_spans_the_shown_periods(self):
        ## clk: period 10, 10 periods shown.
        canvas = self.app.canvas
        waveform = self.app.settings.waveform
        left = waveform["left_padding"] + waveform["nmargin"]
        end = round(10 * canvas.scale_factor * 10 + left)
        self.assertEqual(self._segments(canvas, "clk")[-1][2], end)


if __name__ == "__main__":
    unittest.main()
