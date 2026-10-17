# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2024 Pablo Cardaba

"""Drag of a value marker label; Shift aligns it with the marked point.

With Shift held the label is put exactly beside the point (same y) or
exactly above or below it (same x), whichever is nearer to where the
pointer would put it; Shift can be pressed or released mid-drag.
"""

from __future__ import annotations

import tkinter as tk
import unittest

from TimeIt.tests.test_value_marker_pick import ValueMarkerPickTestCase


class TestLabelDrag(ValueMarkerPickTestCase):

    def setUp(self):
        super().setUp()
        self.tcl("create_value_marker -signal {VA} -use_uid 0 -at 25 "
                 "-label_x 10 -label_y -20")
        self.assertNoErrors()
        self.marker = self.slot.vmarkers[0]
        self.SHIFT = self.canvas.SHIFT_MASK

    def _event(self, x, y, state=0):
        event = tk.Event()
        event.x, event.y, event.state = x, y, state
        return event

    def _label_centre(self):
        x1, y1, x2, y2 = self.canvas.bbox(f"vmarker_label_{self.marker.uid}")
        return (x1 + x2) / 2, (y1 + y2) / 2

    def _drag(self, *moves):
        """Press at (100, 100), move by each (dx, dy, state), release."""
        self.marker._on_press(self._event(100, 100))
        for dx, dy, state in moves:
            self.marker._on_drag(self._event(100 + dx, 100 + dy, state))
        centre = self._label_centre()
        self.marker._on_release(self._event(100 + dx, 100 + dy, state))
        self.root.update()
        self.assertNoErrors()
        return centre

    def _offset(self):
        marker = self.app.signals.find("VA").vmarkers[0]
        return marker.label_relx, marker.label_rely

    def _assert_aligned(self, axis):
        """The label centre is level ("y") or plumb ("x") with the point."""
        px, py = self.marker._point
        lx, ly = self._label_centre()
        if axis == "y":
            self.assertAlmostEqual(ly, py, delta=1)
        else:
            self.assertAlmostEqual(lx, px, delta=1)

    def test_free_drag(self):
        self._drag((30, 12, 0))
        self.assertEqual(self._offset(), (40, -8))

    def test_shift_puts_the_label_beside_the_point(self):
        self._drag((30, 12, self.SHIFT))
        self.assertEqual(self._offset(), (40, 0))
        self._assert_aligned("y")

    def test_shift_puts_the_label_above_the_point(self):
        self._drag((5, -25, self.SHIFT))
        self.assertEqual(self._offset(), (0, -45))
        self._assert_aligned("x")

    def test_shift_puts_the_label_below_the_point(self):
        self._drag((-4, 40, self.SHIFT))
        self.assertEqual(self._offset(), (0, 20))
        self._assert_aligned("x")

    def test_shift_axis_follows_the_point_not_the_drag(self):
        ## A mostly vertical drag that leaves the label further beside the
        ## point than above it: the label is put beside it.
        self._drag((5, 15, self.SHIFT))
        self.assertEqual(self._offset(), (15, 0))

    def test_shift_released_mid_drag_frees_the_move(self):
        self._drag((30, 12, self.SHIFT), (30, 12, 0))
        self.assertEqual(self._offset(), (40, -8))

    def test_shift_pressed_mid_drag_snaps_to_the_point(self):
        self._drag((30, 12, 0), (30, 14, self.SHIFT))
        self.assertEqual(self._offset(), (40, 0))

    def test_within_click_tolerance_is_no_move(self):
        self._drag((1, 1, self.SHIFT))
        self.assertEqual(self._offset(), (10, -20))

    def test_drag_round_trips_and_undoes(self):
        self._drag((30, 12, self.SHIFT))
        self.assertRoundTrips()
        self.app.undo.undo()
        self.root.update()
        self.assertEqual(self._offset(), (10, -20))


if __name__ == "__main__":
    unittest.main()
