# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2024 Pablo Cardaba

"""Quick selection: context menu Select > Next / Prev. Transition.

The transition next to the pointer, in the slot under it, is selected the
way a click would select it (selection mode, Ctrl for an additive
selection), so that "Time it" works unchanged on the result.
"""

from __future__ import annotations

import tkinter as tk
import unittest

from TimeIt.classes.signal import TRANSITIONS_TAG
from TimeIt.tests.apphelper import AppTestCase
from TimeIt.tests.test_create_logic import BASE


class QuickSelectionTestCase(AppTestCase):

    def setUp(self):
        super().setUp()
        self.tcl(BASE)
        self.tcl("create_logic -name busy -inputs {req ack} -tpd_max {$tPD} -visible")
        self.clear_log()
        self.canvas = self.app.canvas

    # -- geometry helpers ------------------------------------------------
    def _slot_y(self, name):
        """Canvas y in the middle of the slot of signal ``name``."""
        for y_top, y_bottom, sig in self.canvas.slots:
            if sig.name == name:
                return (y_top + y_bottom) / 2
        raise AssertionError(f"{name} has no slot")

    def _x(self, t):
        return self.canvas.time_to_x(t)

    def _mid_time(self, item):
        """The time at the centre of ``item`` (what a "full" leg measures)."""
        x1, _, x2, _ = self.canvas.bbox(item)
        return self.canvas.x_to_time((x1 + x2) / 2)

    def _event(self, x, y, ctrl=False):
        """A right-click at canvas (x, y); no scrolling, so window == canvas."""
        event = tk.Event()
        event.x, event.y = x, y
        event.x_root, event.y_root = x, y
        event.state = self.canvas.CTRL_MASK if ctrl else 0
        return event

    def _transitions_of(self, name):
        sig = self.app.signals.find(name)
        prefix = f"uid_{sig.uid}_"
        return [i for i in self.canvas.find_withtag(TRANSITIONS_TAG)
                if any(t.startswith(prefix) for t in self.canvas.gettags(i))]

    def _quick_select(self, t, name, direction, ctrl=False):
        """Right-click at time ``t`` over ``name`` and pick a Select entry."""
        self.canvas._update_context_menu(
            self._event(self._x(t), self._slot_y(name), ctrl))
        self.canvas._select_transition(direction)
        self.root.update()


class TestTransitionTagging(QuickSelectionTestCase):

    def test_every_drawn_change_carries_the_transitions_tag(self):
        ## Clock: two edges per cycle. I/O: one polygon per listed edge
        ## (the "0" edge opens the waveform, it is not a change). Derived:
        ## one polygon between consecutive drawn segments.
        self.assertEqual(len(self._transitions_of("clk")), 20)
        self.assertEqual(len(self._transitions_of("req")), 2)
        self.assertEqual(len(self._transitions_of("data")), 2)
        busy = self.app.signals.find("busy")
        self.assertEqual(len(self._transitions_of("busy")),
                         len(busy.state_intervals()) - 1)

    def test_transition_items_are_selectable_elements(self):
        for item in self._transitions_of("req") + self._transitions_of("clk"):
            tags = self.canvas.gettags(item)
            self.assertTrue(any(t.startswith("uid_") for t in tags), tags)

    def test_slots_follow_the_drawing_order(self):
        self.assertEqual([sig.name for _, _, sig in self.canvas.slots],
                         ["clk", "req", "ack", "data", "busy"])
        for (_, bottom, _), (top, _, _) in zip(self.canvas.slots,
                                                self.canvas.slots[1:]):
            self.assertLess(bottom, top)

    def test_hidden_signal_has_no_slot(self):
        ## Hiding req packs the slots below it up: where req was, ack is.
        y = self._slot_y("req")
        self.tcl("set_attribute -signal req -name visible -value false")
        self.assertNotIn("req", [s.name for _, _, s in self.canvas.slots])
        self.assertEqual(self.canvas.signal_at_y(y).name, "ack")
        nxt = self.canvas.find_transition(self._x(5), y, "next")
        self.assertIn("ack_transition", self.canvas.gettags(nxt))


class TestFindTransition(QuickSelectionTestCase):

    def test_next_and_prev_edge_of_the_clock(self):
        y = self._slot_y("clk")
        nxt = self.canvas.find_transition(self._x(12), y, "next")
        prv = self.canvas.find_transition(self._x(12), y, "prev")
        self.assertIn("clk_edge_2N", self.canvas.gettags(nxt))
        self.assertIn("clk_edge_2P", self.canvas.gettags(prv))
        self.assertAlmostEqual(self._mid_time(nxt), 15.0, delta=0.2)
        self.assertAlmostEqual(self._mid_time(prv), 10.0, delta=0.2)

    def test_transition_under_the_pointer_is_both_next_and_prev(self):
        ## Within the click tolerance of the edge (the drawing rounds the
        ## edge to a whole pixel, so the pointer is never exactly on it).
        y = self._slot_y("clk")
        nxt = self.canvas.find_transition(self._x(10), y, "next")
        prv = self.canvas.find_transition(self._x(10), y, "prev")
        self.assertEqual(nxt, prv)
        self.assertIn("clk_edge_2P", self.canvas.gettags(nxt))

        ## Just beyond the tolerance it is the previous one only.
        tol = self.app.settings.selection["click_tolerance"]
        x = self._x(10) + tol + 1
        self.assertIn("clk_edge_2N",
                      self.canvas.gettags(self.canvas.find_transition(x, y, "next")))
        self.assertIn("clk_edge_2P",
                      self.canvas.gettags(self.canvas.find_transition(x, y, "prev")))

    def test_nothing_beyond_the_ends_of_the_waveform(self):
        y = self._slot_y("clk")
        self.assertIsNone(self.canvas.find_transition(self._x(-5), y, "prev"))
        self.assertIsNotNone(self.canvas.find_transition(self._x(-5), y, "next"))
        self.assertIsNone(self.canvas.find_transition(self._x(100), y, "next"))
        self.assertIsNotNone(self.canvas.find_transition(self._x(100), y, "prev"))

    def test_nothing_outside_a_slot(self):
        clk_top = self.canvas.slots[0][0]
        req_top = self.canvas.slots[1][0]
        clk_bottom = self.canvas.slots[0][1]
        self.assertIsNone(self.canvas.find_transition(self._x(12), clk_top - 5, "next"))
        gap = (clk_bottom + req_top) / 2
        self.assertIsNone(self.canvas.find_transition(self._x(12), gap, "next"))

    def test_a_signal_without_change_has_no_transition(self):
        self.tcl("create_input -name flat -specify external -launch_clock clk "
                 "-rclk_inputdly_max {$tINmax} -rclk_inputdly_min {$tINmin} "
                 "-low_edges {0} -visible")
        y = self._slot_y("flat")
        self.assertIsNone(self.canvas.find_transition(self._x(12), y, "next"))
        self.assertIsNone(self.canvas.find_transition(self._x(12), y, "prev"))

    def test_only_the_slot_signal_is_considered(self):
        ## The clock has an edge at 15; req's first change is at 3P (20..22).
        y = self._slot_y("req")
        nxt = self.canvas.find_transition(self._x(12), y, "next")
        self.assertIn("req_transition", self.canvas.gettags(nxt))
        self.assertIsNone(self.canvas.find_transition(self._x(12), y, "prev"))

    def test_the_selection_mode_locates_the_transition(self):
        ## req changes between 3P + tINmin and 3P + tINmax: 21 .. 22 (plus
        ## the tilt). A pointer inside that window sees it as the next
        ## transition in "end" mode (it ends right of the pointer) and as
        ## the previous one in "start" mode (it starts left of it).
        y = self._slot_y("req")
        x = self._x(21.5)
        first, second = sorted(self._transitions_of("req"),
                               key=lambda i: self.canvas.bbox(i)[0])
        self.assertEqual(self.canvas.find_transition(x, y, "next", "end"), first)
        self.assertIsNone(self.canvas.find_transition(x, y, "prev", "end"))
        self.assertEqual(self.canvas.find_transition(x, y, "prev", "start"), first)
        self.assertEqual(self.canvas.find_transition(x, y, "next", "start"), second)
        ## The current mode is the default.
        self.canvas._sel_mode_tkvar.set("end")
        self.assertEqual(self.canvas.find_transition(x, y, "next"), first)


class TestSelectMenu(QuickSelectionTestCase):

    def _labels(self, menu):
        return [menu.entrycget(i, "label") if menu.type(i) != "separator"
                else "---" for i in range(menu.index("end") + 1)]

    def test_select_cascade_sits_below_selection_mode(self):
        labels = self._labels(self.canvas._ctxmenu)
        i = labels.index("Selection Mode")
        self.assertEqual(labels[i:i + 3], ["Selection Mode", "Select", "Time it"])
        self.assertEqual(self._labels(self.canvas._select_menu),
                         ["Next Transition", "Prev. Transition"])

    def test_entries_follow_what_is_around_the_pointer(self):
        ctx, sel = self.canvas._ctxmenu, self.canvas._select_menu
        y = self._slot_y("clk")

        self.canvas._update_context_menu(self._event(self._x(12), y))
        self.assertEqual(ctx.entrycget("Select", "state"), "normal")
        self.assertEqual(sel.entrycget("Next Transition", "state"), "normal")
        self.assertEqual(sel.entrycget("Prev. Transition", "state"), "normal")

        self.canvas._update_context_menu(self._event(self._x(-5), y))
        self.assertEqual(sel.entrycget("Next Transition", "state"), "normal")
        self.assertEqual(sel.entrycget("Prev. Transition", "state"), "disabled")

        self.canvas._update_context_menu(self._event(self._x(12), self.canvas.slots[0][0] - 5))
        self.assertEqual(ctx.entrycget("Select", "state"), "disabled")
        self.assertEqual(sel.entrycget("Next Transition", "state"), "disabled")
        self.assertEqual(sel.entrycget("Prev. Transition", "state"), "disabled")

    def test_selection_replaces_unless_ctrl_was_held(self):
        self._quick_select(12, "clk", "next")
        self.assertEqual(len(self.canvas.selected), 1)
        first = self.canvas.selected[0]
        uid, mode = first.split(":")
        self.assertEqual(mode, "full")
        self.assertIn("selected", self.canvas.gettags(uid))
        self.assertTrue(self.canvas.find_withtag(f"{uid}_full_bbox"))

        ## Ctrl at the right-click: added, the first selection stays "from".
        self._quick_select(12, "req", "next", ctrl=True)
        self.assertEqual(len(self.canvas.selected), 2)
        self.assertEqual(self.canvas.selected[0], first)
        self.assertEqual(len(self.canvas.find_withtag("selection_bbox")), 2)

        ## No Ctrl: replaced.
        self._quick_select(12, "clk", "prev")
        self.assertEqual(len(self.canvas.selected), 1)
        self.assertNotEqual(self.canvas.selected[0], first)
        self.assertEqual(len(self.canvas.find_withtag("selection_bbox")), 1)

    def test_ctrl_reselecting_the_same_point_deselects_it(self):
        self._quick_select(12, "clk", "next")
        self._quick_select(12, "clk", "next", ctrl=True)
        self.assertEqual(self.canvas.selected, [])
        self.assertEqual(self.canvas.find_withtag("selection_bbox"), ())

    def test_nothing_to_select_leaves_the_selection_alone(self):
        self._quick_select(12, "clk", "next")
        before = list(self.canvas.selected)
        self._quick_select(-5, "clk", "prev")
        self.assertEqual(self.canvas.selected, before)

    def test_the_selection_mode_applies(self):
        self.canvas._sel_mode_tkvar.set("start")
        self._quick_select(12, "req", "next")
        self.assertTrue(self.canvas.selected[0].endswith(":start"))
        self.assertTrue(self.canvas.find_withtag("start"))

    def test_time_it_on_quick_selections(self):
        ## From the 3P clock edge (20) to the middle of the req change it
        ## launches: tINmin .. tINmax = 1 .. 2 after it, i.e. 1.5.
        self._quick_select(18, "clk", "next")
        self._quick_select(18, "req", "next", ctrl=True)
        self.assertEqual(len(self.canvas.selected), 2)

        self.canvas.create_timing_marker()
        self.root.update()
        markers = [m for k, m in self.canvas.markers.items() if k != "current"]
        self.assertEqual(len(markers), 1)
        self.assertAlmostEqual(markers[0].timing, 1.5, delta=0.05)
        self.assertNoErrors()
        self.assertRoundTrips()


if __name__ == "__main__":
    unittest.main()
