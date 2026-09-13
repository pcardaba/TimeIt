# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2024 Pablo Cardaba

"""Integration tests of the Logic and Sampled signal dialogs.

The dialogs are modal (their constructor blocks in wait_window), so each test
schedules a driver with `after` that fills the widgets and presses Ok or
Cancel once the dialog is up, exactly as a user would.
"""

from __future__ import annotations

import unittest

from TimeIt.classes.logicsignaldlg import LogicSignalDlg
from TimeIt.classes.sampledsignaldlg import SampledSignalDlg
from TimeIt.tests.apphelper import AppTestCase
from TimeIt.tests.test_create_logic import BASE


class DialogTestCase(AppTestCase):

    def setUp(self):
        super().setUp()
        self.tcl(BASE)
        self.tcl("create_logic -name busy -inputs {req ack} -tpd_max {$tPD} -visible")
        self.tcl("create_sampled -name busy_q -source busy -clock clk -setup {$tPD} -visible")
        self.clear_log()

    DIALOGS = (LogicSignalDlg, SampledSignalDlg)

    def _find_dialog(self):
        ## The dialogs are children of the application frame, not of the root.
        for widget in self.app.winfo_children():
            if isinstance(widget, self.DIALOGS):
                return widget
        return None

    def _run_dialog(self, open_dialog, driver):
        """Open a modal dialog and let `driver(dlg)` operate it.

        The dialog blocks in wait_window(), so the driver runs from an
        `after` callback. A failure inside the driver is kept and re-raised
        after the dialog is gone; a safety timer destroys a dialog nobody
        dismissed so a broken test can not hang the suite.
        """
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


class TestLogicSignalDlg(DialogTestCase):

    def test_create_with_preset_input(self):
        def driver(dlg):
            self.assertEqual(dlg.inputs, ["req"])
            dlg.name_tkvar.set("both")
            dlg.op_tkvar.set("nand")
            dlg.candidate_tkvar.set("ack")
            dlg._add_input()
            dlg.tpd_max_tkvar.set("$tPD")
            dlg.color_tkvar.set("blue")
            dlg.ok()

        self._run_dialog(lambda: LogicSignalDlg(self.app, preset="req"), driver)
        self.assertNoErrors()
        both = self.app.signals.find("both")
        self.assertEqual(both.op, "nand")
        self.assertEqual([s.name for s in both.inputs], ["req", "ack"])
        self.assertEqual((both.tpd_max, both.color), ("$tPD", "blue"))
        self.assertTrue(self.app.undo.can_undo())

    def test_candidates_exclude_clocks_buses_self_and_readers(self):
        def driver(dlg):
            ## data is a bus, clk a clock, busy_q reads busy (the edited one).
            self.assertEqual(dlg._candidate_inputs(), ("en",))
            dlg.cancel()

        self.tcl("create_input -name en -launch_clock clk -high_edges {2P} -low_edges {0}")
        busy = self.app.signals.find("busy")
        self._run_dialog(lambda: LogicSignalDlg(self.app, busy), driver)

    def test_typing_a_readers_name_drops_it_from_the_inputs(self):
        def driver(dlg):
            dlg.candidate_tkvar.set("busy_q")
            dlg._add_input()
            self.assertEqual(dlg.inputs, ["req", "busy_q"])
            ## Naming the new signal "busy" would make busy_q read itself.
            dlg.name_tkvar.set("busy")
            self.assertEqual(dlg.inputs, ["req"])
            self.assertNotIn("busy_q", dlg._candidate_inputs())
            dlg.cancel()

        self._run_dialog(lambda: LogicSignalDlg(self.app, preset="req"), driver)

    def test_edit_prefills_and_applies_in_place(self):
        before = self.app.signals.find("busy")

        def driver(dlg):
            self.assertEqual(dlg.name_tkvar.get(), "busy")
            self.assertEqual(dlg.op_tkvar.get(), "and")
            self.assertEqual(dlg.inputs, ["req", "ack"])
            self.assertEqual(dlg.tpd_max_tkvar.get(), "$tPD")
            dlg.op_tkvar.set("or")
            dlg.tpd_min_tkvar.set("$tPD/2")
            dlg.ok()

        self._run_dialog(lambda: LogicSignalDlg(self.app, before), driver)
        self.assertNoErrors()
        after = self.app.signals.find("busy")
        self.assertIs(after, before)
        self.assertEqual((after.op, after.tpd_min), ("or", "$tPD/2"))

    def test_not_keeps_a_single_input(self):
        def driver(dlg):
            dlg.op_tkvar.set("not")
            dlg._update_op()
            self.assertEqual(dlg.inputs, ["req"])
            dlg.candidate_tkvar.set("ack")
            dlg._add_input()          # replaces rather than appends
            self.assertEqual(dlg.inputs, ["ack"])
            dlg.name_tkvar.set("ack_n")
            dlg.ok()

        self._run_dialog(lambda: LogicSignalDlg(self.app, preset="req"), driver)
        self.assertNoErrors()
        self.assertEqual([s.name for s in self.app.signals.find("ack_n").inputs], ["ack"])

    def test_remove_input_and_cancel(self):
        def driver(dlg):
            dlg.lb_inputs.selection_set(0)
            dlg._remove_input()
            self.assertEqual(dlg.inputs, [])
            self.assertEqual(dlg._build_command(), "")   # no inputs: nothing to run
            dlg.name_tkvar.set("nothing")
            dlg.cancel()

        self._run_dialog(lambda: LogicSignalDlg(self.app, preset="req"), driver)
        self.assertNotIn("nothing", self.app.signals)
        self.assertFalse(self.app.undo.can_undo())


class TestSampledSignalDlg(DialogTestCase):

    def test_create_with_preset_source(self):
        def driver(dlg):
            self.assertEqual(dlg.source_tkvar.get(), "req")
            self.assertEqual(dlg.clock_tkvar.get(), "clk")
            dlg.name_tkvar.set("req_q")
            dlg.edge_tkvar.set("falling")
            dlg.setup_tkvar.set("$tPD")
            dlg.tco_max_tkvar.set("2")
            dlg.ok()

        self._run_dialog(lambda: SampledSignalDlg(self.app, preset="req"), driver)
        self.assertNoErrors()
        req_q = self.app.signals.find("req_q")
        self.assertEqual((req_q.edge, req_q.setup, req_q.tco_max), ("falling", "$tPD", "2"))
        self.assertIs(req_q.clock, self.app.signals.find("clk"))
        self.assertTrue(self.app.undo.can_undo())

    def test_preset_clock_fills_the_clock(self):
        def driver(dlg):
            self.assertEqual(dlg.clock_tkvar.get(), "clk")
            self.assertEqual(dlg.source_tkvar.get(), "")
            dlg.cancel()

        self._run_dialog(lambda: SampledSignalDlg(self.app, preset="clk"), driver)

    def test_candidates_exclude_clocks_self_and_readers(self):
        self.tcl("create_logic -name fb -op not -inputs {busy_q}")

        def driver(dlg):
            self.assertEqual(dlg._candidate_sources(), ("req", "ack", "data", "busy"))
            dlg.cancel()

        self._run_dialog(lambda: SampledSignalDlg(self.app, self.app.signals.find("busy_q")),
                         driver)

    def test_edit_prefills_and_applies_in_place(self):
        before = self.app.signals.find("busy_q")

        def driver(dlg):
            self.assertEqual(dlg.name_tkvar.get(), "busy_q")
            self.assertEqual(dlg.source_tkvar.get(), "busy")
            self.assertEqual(dlg.setup_tkvar.get(), "$tPD")
            dlg.source_tkvar.set("req")
            dlg.hold_tkvar.set("1")
            dlg.ok()

        self._run_dialog(lambda: SampledSignalDlg(self.app, before), driver)
        self.assertNoErrors()
        after = self.app.signals.find("busy_q")
        self.assertIs(after, before)
        self.assertIs(after.source, self.app.signals.find("req"))
        self.assertEqual(after.hold, "1")

    def test_cancel_creates_nothing(self):
        def driver(dlg):
            dlg.name_tkvar.set("nothing")
            dlg.cancel()

        self._run_dialog(lambda: SampledSignalDlg(self.app, preset="req"), driver)
        self.assertNotIn("nothing", self.app.signals)


class TestCanvasWiring(DialogTestCase):

    def test_new_signal_menu_opens_the_dialogs_with_the_current_signal(self):
        canvas = self.app.canvas
        canvas._current_tags = ("req_label",)

        def driver(dlg):
            self.assertEqual(dlg.inputs, ["req"])
            dlg.cancel()

        self._run_dialog(lambda: canvas._create_new_signal("logic"), driver)

        def driver2(dlg):
            self.assertEqual(dlg.source_tkvar.get(), "req")
            dlg.cancel()

        self._run_dialog(lambda: canvas._create_new_signal("sampled"), driver2)

    def test_edit_signal_routes_by_type(self):
        canvas = self.app.canvas
        opened = []

        def driver(dlg):
            opened.append(type(dlg).__name__)
            dlg.cancel()

        canvas._current_tags = ("busy_label",)
        self._run_dialog(canvas._edit_signal, driver)
        canvas._current_tags = ("busy_q_waveform",)
        self._run_dialog(canvas._edit_signal, driver)
        self.assertEqual(opened, ["LogicSignalDlg", "SampledSignalDlg"])


if __name__ == "__main__":
    unittest.main()
