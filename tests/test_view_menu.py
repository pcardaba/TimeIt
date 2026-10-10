# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2024 Pablo Cardaba

"""The View menu (time axis scale, grid) and the Left/Right scrolling keys."""

from __future__ import annotations

import tkinter as tk
import unittest

from TimeIt.classes.gridsettingsdlg import GridSettingsDlg
from TimeIt.tests.apphelper import AppTestCase
from TimeIt.tests.test_create_logic import BASE


class ViewTestCase(AppTestCase):

    def setUp(self):
        super().setUp()
        self.tcl(BASE)
        self.clear_log()
        self.canvas = self.app.canvas

    def _menu(self, label):
        """The cascade of the menubar called ``label``."""
        menubar = self.root.nametowidget(self.root.cget("menu"))
        return menubar.nametowidget(menubar.entrycget(label, "menu"))

    def _right_edge(self):
        return self.canvas.bbox("all")[2]

    def _zoom(self, steps):
        for _ in range(abs(steps)):
            if steps > 0:
                self.canvas.scale_up()
            else:
                self.canvas.scale_down()
        self.root.update()

    def _key(self, handler_direction, widget):
        event = tk.Event()
        event.widget = widget
        self.app._scroll_x(event, handler_direction)
        self.root.update()


class TestViewMenu(ViewTestCase):

    def test_view_sits_between_edit_and_help(self):
        menubar = self.root.nametowidget(self.root.cget("menu"))
        labels = [menubar.entrycget(i, "label")
                  for i in range(menubar.index("end") + 1)
                  if menubar.type(i) == "cascade"]
        self.assertEqual(labels, ["File", "Edit", "View", "Help"])

    def test_entries_and_shortcuts(self):
        view = self._menu("View")
        entries = []
        for i in range(view.index("end") + 1):
            if view.type(i) == "separator":
                entries.append("-")
            else:
                entries.append((view.entrycget(i, "label"),
                                view.entrycget(i, "accelerator")))
        self.assertEqual(entries, [("Scale Up", "Shift+Wheel Up"),
                                   ("Scale Down", "Shift+Wheel Down"),
                                   ("Scale Fit", "Ctrl+F"),
                                   "-",
                                   ("Grid…", "")])

    def test_scale_up_and_down_are_one_wheel_step(self):
        view = self._menu("View")
        scale = self.canvas.scale_factor
        step = self.canvas.zoom_step

        view.invoke("Scale Up")
        self.assertAlmostEqual(self.canvas.scale_factor, scale * step)
        view.invoke("Scale Down")
        view.invoke("Scale Down")
        self.assertAlmostEqual(self.canvas.scale_factor, scale / step)
        self.assertNoErrors()

    def test_grid_entry_opens_the_grid_dialog(self):
        self._menu("View").invoke("Grid…")
        self.root.update()
        dialogs = [w for w in self.app.winfo_children()
                   if isinstance(w, GridSettingsDlg)]
        self.assertEqual(len(dialogs), 1)
        dialogs[0].destroy()

    def test_view_commands_are_not_undoable(self):
        view = self._menu("View")
        for label in ("Scale Up", "Scale Down", "Scale Down", "Scale Fit"):
            view.invoke(label)
        self.assertFalse(self.app.undo.can_undo())


class TestScaleFit(ViewTestCase):

    def _assert_fits(self):
        width = self.canvas.winfo_width()
        padding = self.app.settings.waveform["right_padding"]
        right = self._right_edge()
        self.assertLessEqual(right, width - padding)
        self.assertGreaterEqual(right, width - padding - self.canvas.FIT_TOLERANCE)
        self.assertEqual(self.canvas.xview(), (0.0, 1.0))

    def test_fit_after_zooming_in(self):
        self._zoom(+10)
        self.assertGreater(self._right_edge(), self.canvas.winfo_width())
        self.canvas.xview_moveto(0.5)

        self._menu("View").invoke("Scale Fit")
        self.root.update()
        self._assert_fits()
        self.assertNoErrors()

    def test_fit_after_zooming_out(self):
        self._zoom(-10)
        self.assertLess(self._right_edge(), self.canvas.winfo_width() / 2)

        self.app._scale_fit()
        self.root.update()
        self._assert_fits()

    def test_fit_follows_the_window_width(self):
        self.tcl("set_window_size -width 1100 -height 500")
        self.app._scale_fit()
        self.root.update()
        self._assert_fits()

    def test_fit_is_stable(self):
        self.app._scale_fit()
        scale = self.canvas.scale_factor
        self.app._scale_fit()
        self.assertEqual(self.canvas.scale_factor, scale)

    def test_fit_on_an_empty_canvas_does_nothing(self):
        self.tcl("remove -all")
        scale = self.canvas.scale_factor
        self.app._scale_fit()
        self.assertEqual(self.canvas.scale_factor, scale)
        self.assertNoErrors()

    def test_fitted_scale_is_saved(self):
        self._zoom(+10)
        self.app._scale_fit()
        self.assertIn(f"set_canvas_scale {self.canvas.scale_factor:.1f}\n",
                      self.write_script())

    def test_shortcut_is_bound_on_the_window_and_on_the_command_line(self):
        self.assertTrue(self.root.bind("<Control-f>"))
        self.assertTrue(self.app.console.entry.bind("<Control-f>"))
        self.assertEqual(self.app._scale_fit(tk.Event()), "break")


class TestArrowKeys(ViewTestCase):

    def setUp(self):
        super().setUp()
        ## Wider than the window, so that there is something to scroll.
        self._zoom(+10)
        self.entry = self.app.console.entry

    def test_right_then_left_scroll_a_tenth_of_the_width(self):
        ## Tk's scrolling unit: a tenth of the width inside the widget border.
        step = self.canvas.winfo_width() / 10
        self._key(+1, self.canvas)
        self.assertAlmostEqual(self.canvas.canvasx(0), step, delta=3)
        self._key(+1, self.canvas)
        self.assertAlmostEqual(self.canvas.canvasx(0), 2 * step, delta=6)
        self._key(-1, self.canvas)
        self.assertAlmostEqual(self.canvas.canvasx(0), step, delta=3)

    def test_scrolling_stops_at_both_ends(self):
        self._key(-1, self.canvas)
        self.assertEqual(self.canvas.xview()[0], 0.0)

        for _ in range(200):
            self.app.canvas.scroll_x(+1)
        self.root.update()
        self.assertEqual(self.canvas.xview()[1], 1.0)

    def test_nothing_to_scroll_when_the_drawing_fits(self):
        self.app._scale_fit()
        self._key(+1, self.canvas)
        self.assertEqual(self.canvas.xview(), (0.0, 1.0))

    def test_empty_command_line_lets_the_keys_scroll(self):
        self.assertEqual(self.entry.get(), "")
        before = self.canvas.xview()
        self._key(+1, self.entry)
        self.assertGreater(self.canvas.xview()[0], before[0])

    def test_typed_command_line_keeps_the_keys(self):
        self.entry.insert(0, "create_clock")
        before = self.canvas.xview()
        self._key(+1, self.entry)
        self.assertEqual(self.canvas.xview(), before)

    def test_other_entries_keep_the_keys(self):
        ## As the in-place editor of a marker label: an entry on the canvas.
        editor = tk.Entry(self.canvas)
        before = self.canvas.xview()
        self._key(+1, editor)
        self.assertEqual(self.canvas.xview(), before)

    def test_keys_are_bound_on_the_window(self):
        self.assertTrue(self.root.bind("<Left>"))
        self.assertTrue(self.root.bind("<Right>"))


if __name__ == "__main__":
    unittest.main()
