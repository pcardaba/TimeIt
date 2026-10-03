# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2024 Pablo Cardaba

"""Integration tests of the *User Timings* window and its use from the
modal signal dialogs.

A Tk grab only reaches the grab window and its descendants. The window is
therefore opened *under* a signal dialog (``TimeItApp.open_timings(dlg)``)
so that the user can create the timing variables a form needs while the
form is up. The dialogs block in wait_window(), so each test drives them
from an ``after`` callback, as ``test_derived_dialogs`` does.
"""

from __future__ import annotations

import tkinter as tk
import unittest
from unittest import mock

from TimeIt.classes import timingsdlg
from TimeIt.classes.clocksignaldlg import ClockSignalDlg
from TimeIt.classes.inputsignaldlg import InputSignalDlg
from TimeIt.classes.logicsignaldlg import LogicSignalDlg
from TimeIt.classes.outputsignaldlg import OutputSignalDlg
from TimeIt.classes.sampledsignaldlg import SampledSignalDlg
from TimeIt.classes.timingsdlg import TimingsDlg
from TimeIt.tests.apphelper import AppTestCase
from TimeIt.tests.test_create_logic import BASE

DIALOGS = (ClockSignalDlg, InputSignalDlg, OutputSignalDlg,
           LogicSignalDlg, SampledSignalDlg)


def expression_entries(widget):
    """Every entry under ``widget`` that carries the timing-variable menu."""
    found = []
    for child in widget.winfo_children():
        if hasattr(child, "timing_menu"):
            found.append(child)
        found.extend(expression_entries(child))
    return found


class TimingsDlgTestCase(AppTestCase):

    def setUp(self):
        super().setUp()
        self.tcl(BASE)
        self.clear_log()

    def _find_dialog(self):
        for widget in self.app.winfo_children():
            if isinstance(widget, DIALOGS):
                return widget
        return None

    def _run_dialog(self, open_dialog, driver):
        """Open a modal dialog and let ``driver(dlg)`` operate it."""
        seen = {}

        def drive():
            dlg = self._find_dialog()
            if dlg is None:
                seen["error"] = AssertionError("the dialog never opened")
                return
            seen["dlg"] = dlg
            try:
                driver(dlg)
            except Exception as exc:  # noqa: BLE001 - re-raised below
                seen["error"] = exc
            finally:
                if dlg.winfo_exists():
                    dlg.dismiss()

        def safety():
            dlg = self._find_dialog()
            if dlg is not None and dlg.winfo_exists():
                seen.setdefault("error", AssertionError("dialog left open"))
                dlg.dismiss()

        self.root.after(100, drive)
        self.root.after(5000, safety)
        open_dialog()
        self.root.update()
        if "error" in seen:
            raise seen["error"]
        return seen["dlg"]


# ----------------------------------------------------------------------
# The window on its own (Edit -> Timings…)
# ----------------------------------------------------------------------
class TestTimingsWindow(TimingsDlgTestCase):

    def test_lists_the_variables_of_the_model(self):
        dlg = self.app.open_timings()
        self.assertIsInstance(dlg, TimingsDlg)
        self.assertIs(dlg.master, self.app)
        self.assertEqual(dlg.names(), ["tCLK", "tINmax", "tINmin", "tPD"])
        ## Opening it again raises the same window.
        self.assertIs(self.app.open_timings(), dlg)
        self.assertIs(self.app.timings_dlg(), dlg)
        dlg._close()
        self.root.update()
        self.assertIsNone(self.app.timings_dlg())

    def test_set_variable_is_undoable_and_the_window_follows(self):
        dlg = self.app.open_timings()
        dlg.set_variable("tNEW", "$tCLK/4.0", "a quarter period")
        self.assertNoErrors()
        self.assertEqual(self.app.timings.tvars["tNEW"], "$tCLK/4.0")
        self.assertEqual(self.app.timings.tvars_desc["tNEW"], "a quarter period")
        self.assertEqual(self.tcl("set tNEW"), "2.5")
        self.assertIn("tNEW", dlg.names())
        self.assertTrue(self.app.undo.can_undo())

        self.app.undo.undo()
        self.root.update()
        self.assertNotIn("tNEW", self.app.timings.tvars)
        self.assertNotIn("tNEW", dlg.names())

        self.app.undo.redo()
        self.root.update()
        self.assertEqual(self.app.timings.tvars["tNEW"], "$tCLK/4.0")
        self.assertIn("tNEW", dlg.names())

    def test_remove_is_undoable(self):
        dlg = self.app.open_timings()
        item = dlg._rows()["tPD"]
        dlg.tree.selection_set(item)
        dlg.remove_node()
        self.assertNotIn("tPD", self.app.timings.tvars)
        self.assertNotIn("tPD", dlg.names())
        self.app.undo.undo()
        self.root.update()
        self.assertEqual(self.app.timings.tvars["tPD"], "1.5")
        self.assertIn("tPD", dlg.names())

    def test_a_variable_set_from_the_console_shows_up(self):
        dlg = self.app.open_timings()
        self.tcl("set_app_var -name timings.tX -value {3} -desc {from console}")
        self.assertIn("tX", dlg.names())
        self.assertEqual(tuple(dlg.tree.item(dlg._rows()["tX"], "values")),
                         ("3", "from console"))
        self.tcl("set_app_var -name timings.tX -value {4}")
        self.assertEqual(tuple(dlg.tree.item(dlg._rows()["tX"], "values")),
                         ("4", "from console"))
        self.tcl("remove -timing_var {tX}")
        self.assertNotIn("tX", dlg.names())

    def test_load_and_undo_refresh_the_window(self):
        dlg = self.app.open_timings()
        self.tcl("remove -all")
        self.assertEqual(dlg.names(), [])
        self.tcl(BASE)
        self.assertEqual(dlg.names(), ["tCLK", "tINmax", "tINmin", "tPD"])

    def test_pending_row_survives_a_refresh(self):
        dlg = self.app.open_timings()
        ## Add… without a prompt: the row exists, the variable does not yet.
        with mock.patch.object(timingsdlg.simpledialog, "askstring",
                               lambda *a, **k: "tPENDING"):
            dlg.add_node()
        self.assertIn("tPENDING", dlg.names())
        self.assertNotIn("tPENDING", self.app.timings.tvars)
        self.app.redraw()
        self.assertIn("tPENDING", dlg.names())
        ## Committing the value creates it; the row is not duplicated.
        dlg.set_variable("tPENDING", "7")
        self.assertEqual(dlg.names().count("tPENDING"), 1)
        self.assertEqual(self.app.timings.tvars["tPENDING"], "7")

    def test_round_trip_keeps_variables_created_from_the_window(self):
        dlg = self.app.open_timings()
        dlg.set_variable("tNEW", "$tCLK/4.0", "a quarter period")
        self.assertRoundTrips()
        self.assertIn("-desc {a quarter period}", self.write_script())


# ----------------------------------------------------------------------
# The window under a modal signal dialog
# ----------------------------------------------------------------------
class TestTimingsUnderSignalDialog(TimingsDlgTestCase):

    def test_every_dialog_offers_the_button_and_the_menus(self):
        for cls in DIALOGS:
            def driver(dlg):
                self.assertTrue(dlg.b_timings.winfo_exists(), cls.__name__)
                self.assertTrue(expression_entries(dlg), cls.__name__)
                dlg.b_timings.invoke()
                tdlg = self.app.timings_dlg()
                self.assertIsNotNone(tdlg, cls.__name__)
                self.assertIs(tdlg.master, dlg, cls.__name__)
                dlg.dismiss()
                self.root.update()
                ## It goes away with the dialog that owns it.
                self.assertIsNone(self.app.timings_dlg(), cls.__name__)

            self._run_dialog(lambda: cls(self.app), driver)

    def test_window_under_the_dialog_takes_input_while_the_dialog_is_modal(self):
        hits = {}

        def driver(dlg):
            self.assertIs(self.root.grab_current(), dlg)
            tdlg = self.app.open_timings(dlg)
            self.root.update()
            ## Still the dialog's grab, and the window is in its subtree.
            self.assertIs(self.root.grab_current(), dlg)
            self.assertTrue(str(tdlg).startswith(str(dlg) + "."))
            ## A real pointer press reaches a widget of the window...
            probe = tk.Entry(tdlg)
            probe.grid(row=2, column=0)
            self.root.update()
            probe.bind("<ButtonPress-1>", lambda e: hits.setdefault("child", True))
            probe.event_generate("<ButtonPress-1>", x=3, y=3, warp=True)
            probe.event_generate("<ButtonRelease-1>", x=3, y=3, warp=True)
            self.root.update()
            ## ...and not one of the main window (frozen by the grab).
            console = self.app.console.entry
            console.bind("<ButtonPress-1>", lambda e: hits.setdefault("main", True), add=True)
            console.event_generate("<ButtonPress-1>", x=3, y=3, warp=True)
            console.event_generate("<ButtonRelease-1>", x=3, y=3, warp=True)
            self.root.update()

        self._run_dialog(lambda: LogicSignalDlg(self.app, preset="req"), driver)
        self.assertEqual(hits, {"child": True})

    def test_create_a_variable_then_use_it_in_the_form(self):
        def driver(dlg):
            tdlg = self.app.open_timings(dlg)
            tdlg.set_variable("tHALF", "$tCLK/2", "half period")
            self.assertIs(self.root.grab_current(), dlg)
            dlg.clkname_tkvar.set("clk2")
            dlg.topology_tkvar.set("source")
            dlg.clkperiod_tkvar.set("$tCLK")
            dlg.clkrise_tkvar.set("0")
            dlg.clkfall_tkvar.set("$tHALF")
            dlg.ok()

        self._run_dialog(lambda: ClockSignalDlg(self.app), driver)
        self.assertNoErrors()
        clk2 = self.app.signals.find("clk2")
        self.assertEqual((clk2.period, clk2.fall_at), ("$tCLK", "$tHALF"))
        ## Two undo entries: the variable, then the clock. Undoing the clock
        ## keeps the variable it uses.
        self.app.undo.undo()
        self.root.update()
        self.assertIsNone(self.app.signals.find("clk2"))
        self.assertEqual(self.app.timings.tvars["tHALF"], "$tCLK/2")
        self.app.undo.undo()
        self.root.update()
        self.assertNotIn("tHALF", self.app.timings.tvars)

    def test_a_prompt_gives_the_grab_back_to_the_dialog(self):
        def fake_prompt(*args, **kwargs):
            ## What simpledialog.askstring does to the grab: takes it, and
            ## leaves none at all once destroyed.
            top = tk.Toplevel(kwargs["parent"])
            self.root.update()
            top.grab_set()
            top.destroy()
            self.root.update()
            return "tASKED"

        def driver(dlg):
            tdlg = self.app.open_timings(dlg)
            with mock.patch.object(timingsdlg.simpledialog, "askstring", fake_prompt):
                tdlg.add_node()
            self.assertIn("tASKED", tdlg.names())
            self.assertIs(self.root.grab_current(), dlg)
            ## A duplicate name is refused through a (grab-taking) error box.
            with mock.patch.object(timingsdlg.simpledialog, "askstring", fake_prompt), \
                 mock.patch.object(timingsdlg.messagebox, "showerror", fake_prompt):
                tdlg.add_node()
            self.assertEqual(tdlg.names().count("tASKED"), 1)
            self.assertIs(self.root.grab_current(), dlg)

        self._run_dialog(lambda: SampledSignalDlg(self.app, preset="req"), driver)

    def test_window_open_from_the_menu_is_replaced_under_the_dialog(self):
        main_dlg = self.app.open_timings()

        def driver(dlg):
            tdlg = self.app.open_timings(dlg)
            self.assertIsNot(tdlg, main_dlg)
            self.assertFalse(main_dlg.winfo_exists())
            self.assertIs(tdlg.master, dlg)
            ## And again from the button: the same instance.
            dlg.b_timings.invoke()
            self.assertIs(self.app.timings_dlg(), tdlg)

        self._run_dialog(lambda: LogicSignalDlg(self.app, preset="req"), driver)

    def test_right_click_menu_inserts_a_variable(self):
        def driver(dlg):
            entries = expression_entries(dlg)
            self.assertEqual(len(entries), 4)   # setup, hold, tco max, tco min
            entry = entries[0]
            menu = entry.timing_menu.build()
            labels = [menu.entrycget(i, "label")
                      for i in range(menu.index("end") + 1)
                      if menu.type(i) == "command"]
            self.assertEqual(labels[:4], ["tCLK  =  10", "tINmax  =  2",
                                          "tINmin  =  1", "tPD  =  1.5"])
            self.assertEqual(labels[-1], "Timings…")
            ## Inserted at the cursor, in place of a selection.
            entry.insert(0, "2*")
            entry.icursor("end")
            entry.timing_menu.insert("tPD")
            self.assertEqual(entry.get(), "2*$tPD")
            entry.select_range(0, "end")
            entry.timing_menu.insert("tCLK")
            self.assertEqual(entry.get(), "$tCLK")
            ## The last item opens the window under the dialog.
            menu.invoke(menu.index("end"))
            self.assertIs(self.app.timings_dlg().master, dlg)
            self.assertIs(self.root.grab_current(), dlg)

        self._run_dialog(lambda: SampledSignalDlg(self.app, preset="req"), driver)

    def test_menu_with_no_variables(self):
        self.tcl("remove -all")

        def driver(dlg):
            menu = expression_entries(dlg)[0].timing_menu.build()
            self.assertEqual(menu.entrycget(0, "label"), "(no timing variables)")
            self.assertEqual(str(menu.entrycget(0, "state")), "disabled")

        self._run_dialog(lambda: ClockSignalDlg(self.app), driver)


if __name__ == "__main__":
    unittest.main()
