# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2024 Pablo Cardaba

"""Context menu "Add Value Marker": a PWL trace is picked with a tolerance.

A right-click near a trace, not only exactly on its (thin) line, offers the
entry; the marker goes on the closest trace, at the time of its closest
point.
"""

from __future__ import annotations

import tempfile
import tkinter as tk
import unittest
from pathlib import Path

from TimeIt.tests.apphelper import AppTestCase

## VA ramps from 0 to 1 over the whole range; VB steps from 0 to 1 at t=50
## (a vertical edge). Both share the same min/max, so at t=25 VA is a quarter
## of the slot height above VB.
VA = "0, 0\n100, 1\n"
VB = "0, 0\n50, 0\n50, 1\n100, 1\n"


class ValueMarkerPickTestCase(AppTestCase):

    def setUp(self):
        super().setUp()
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        folder = Path(self.tmp.name)
        (folder / "va.pwl").write_text(VA)
        (folder / "vb.pwl").write_text(VB)
        self.tcl(f"create_pwl -names {{VA VB}} "
                 f"-files {{{folder / 'va.pwl'} {folder / 'vb.pwl'}}} "
                 f"-height 100 -visible")
        self.assertNoErrors()
        self.canvas = self.app.canvas
        self.slot = self.app.signals.find("VA")
        self.va, self.vb = self.slot.traces

    def _xy(self, trace, t):
        return self.slot.trace_xy(self.canvas, trace, t)

    def _rclick(self, x, y):
        """Pop the context menu up (not shown) for a right-click at (x, y)."""
        event = tk.Event()
        event.x, event.y = x, y
        event.x_root, event.y_root = x, y
        event.state = 0
        self.canvas._update_context_menu(event)
        return self.canvas._ctxmenu.entrycget("Add Value Marker", "state")

    def _add(self, x, y):
        self.assertEqual(self._rclick(x, y), "normal")
        self.canvas.add_value_marker()
        self.root.update()
        self.assertNoErrors()
        self.assertEqual(len(self.slot.vmarkers), 1)
        return next(iter(self.slot.vmarkers.values()))


class TestPick(ValueMarkerPickTestCase):

    def test_on_the_line(self):
        x, y = self._xy(self.va, 25)
        marker = self._add(x, y)
        self.assertIs(marker.trace(), self.va)
        ## canvasx() rounds the pointer to a whole pixel.
        self.assertAlmostEqual(marker.at, 25, delta=0.5)

    def test_near_the_line_off_the_item(self):
        x, y = self._xy(self.va, 25)
        ## 6 px above the ramp: off the drawn line, within the tolerance.
        self.assertNotIn("pwl_traces", self.canvas.gettags(
            self.canvas.find_overlapping(x, y - 6, x, y - 6) or 0))
        marker = self._add(x, y - 6)
        self.assertIs(marker.trace(), self.va)
        self.assertAlmostEqual(marker.at, 25, delta=2)

    def test_closest_trace_wins(self):
        x, y_va = self._xy(self.va, 25)
        _, y_vb = self._xy(self.vb, 25)
        ## Just above VB (well below VA): VB is picked.
        marker = self._add(x, y_vb - 4)
        self.assertIs(marker.trace(), self.vb)
        self.assertGreater(y_vb - y_va, 2 * self.canvas.VMARKER_PICK_TOLERANCE)

    def test_vertical_edge_is_picked_sideways(self):
        x_edge, _ = self._xy(self.vb, 50)
        top = self.slot.slot_top
        marker = self._add(x_edge + 5, top + 20)
        self.assertIs(marker.trace(), self.vb)
        self.assertAlmostEqual(marker.at, 50, places=6)

    def test_too_far_is_disabled(self):
        x, y_va = self._xy(self.va, 25)
        _, y_vb = self._xy(self.vb, 25)
        ## Half way between the two traces: beyond the tolerance of both.
        self.assertEqual(self._rclick(x, (y_va + y_vb) / 2), "disabled")

    def test_outside_the_time_range_is_clamped(self):
        x, y = self._xy(self.va, 0)
        marker = self._add(x - 5, y)
        self.assertAlmostEqual(marker.at, 0, places=6)

    def test_hidden_trace_is_not_picked(self):
        self.tcl("set_attribute -signal {VA} -name visible -value {false}")
        x, y = self._xy(self.va, 25)
        self.assertEqual(self._rclick(x, y), "disabled")

    def test_larger_click_tolerance_widens_the_pick(self):
        x, y_va = self._xy(self.va, 25)
        _, y_vb = self._xy(self.vb, 25)
        mid = (y_va + y_vb) / 2
        self.tcl("set_app_var -name settings.selection.click_tolerance "
                 "-value {20}")
        self.assertEqual(self._rclick(x, mid), "normal")

    def test_one_undo_entry_and_round_trip(self):
        x, y = self._xy(self.va, 25)
        self._add(x, y - 3)
        self.assertRoundTrips()
        self.app.undo.undo()
        self.root.update()
        self.assertEqual(len(self.app.signals.find("VA").vmarkers), 0)


if __name__ == "__main__":
    unittest.main()
