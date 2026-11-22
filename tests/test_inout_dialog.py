# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2024 Pablo Cardaba

"""Integration tests of the bidirectional ("Bidir") signal dialog.

The dialog is modal (its constructor blocks in wait_window), so each test
drives it from an ``after`` callback, as ``test_derived_dialogs`` does. The
message boxes it raises are replaced by mocks: they are modal too.
"""

from __future__ import annotations

import tkinter as tk
import unittest
from unittest import mock

from TimeIt.classes import inoutsignaldlg
from TimeIt.classes.inoutsignal import InOutSignal
from TimeIt.classes.inoutsignaldlg import InOutSignalDlg
from TimeIt.tests.apphelper import AppTestCase
from TimeIt.tests.test_create_inout import BASE, BUS


class InOutDialogTestCase(AppTestCase):

    def setUp(self):
        super().setUp()
        self.tcl(BASE)
        self.clear_log()
        patcher = mock.patch.object(inoutsignaldlg, "messagebox")
        self.messagebox = patcher.start()
        self.addCleanup(patcher.stop)

    def _find_dialog(self):
        for widget in self.app.winfo_children():
            if isinstance(widget, InOutSignalDlg):
                return widget
        return None

    def _run_dialog(self, open_dialog, driver):
        """Open the modal dialog and let ``driver(dlg)`` operate it."""
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
        timer = self.root.after(5000, safety)
        open_dialog()
        self.root.after_cancel(timer)
        self.root.update()
        if "error" in seen:
            raise seen["error"]
        return seen["dlg"]

    @staticmethod
    def fill_bus(dlg):
        """A clean definition: the device sends, a turnaround, then receives."""
        dlg.name_tkvar.set("dq")
        dlg.in_form.launch_tkvar.set("clk")
        dlg.in_form.delay_tkvars[("inputdly", "rclk", "max")].set("4")
        dlg.in_form.delay_tkvars[("inputdly", "rclk", "min")].set("-1")
        dlg.in_form.edges_tkvars["hiz"].set("0 7P")
        dlg.in_form.edges_tkvars["data"].set("4P 5P 6P")
        dlg.out_form.launch_tkvar.set("clk")
        dlg.out_form.delay_tkvars[("outputdly", "rclk", "max")].set("5")
        dlg.out_form.delay_tkvars[("outputdly", "rclk", "min")].set("2")
        dlg.out_form.edges_tkvars["hiz"].set("0 3P")
        dlg.out_form.edges_tkvars["data"].set("1P 2P")


class TestInOutSignalDlg(InOutDialogTestCase):

    def test_menu_entry_comes_right_after_output(self):
        ctx = self.app.canvas._ctxmenu
        new_menu = ctx.nametowidget(ctx.entrycget("New Signal", "menu"))
        labels = [new_menu.entrycget(i, "label")
                  for i in range(new_menu.index("end") + 1)]
        self.assertEqual(labels[labels.index("Output...") + 1], "Bidir...")

        opened = []
        self._run_dialog(lambda: new_menu.invoke(labels.index("Bidir...")),
                         lambda dlg: opened.append(dlg.title()))
        self.assertEqual(opened, ["Bidir Signal"])

    def test_one_tab_per_part(self):
        def driver(dlg):
            tabs = [dlg.notebook.tab(tab, "text") for tab in dlg.notebook.tabs()]
            self.assertEqual(tabs, ["Input part", "Output part"])

        self._run_dialog(lambda: InOutSignalDlg(self.app), driver)

    @staticmethod
    def _illustration(dlg):
        """The image the dialog shows, as Tk names it."""
        dlg.update()            # <<NotebookTabChanged>> is queued
        image = dlg.lbimg_topo.cget("image")
        if isinstance(image, tuple):
            image = image[0]
        return str(image)

    def test_illustration_follows_the_tab_and_the_delays(self):
        def driver(dlg):
            ## One illustration per part and delay specification.
            self.assertEqual(len({str(image) for image in dlg.images.values()}), 4)
            for image in dlg.images.values():
                self.assertGreater(image.width(), 1)

            shown = self._illustration
            self.assertEqual(shown(dlg), str(dlg.images[("in", "internal")]))
            dlg.notebook.select(dlg.out_form.frame)
            self.assertEqual(shown(dlg), str(dlg.images[("out", "internal")]))
            dlg.topology_tkvar.set("external")
            dlg._update_topology()
            self.assertEqual(shown(dlg), str(dlg.images[("out", "external")]))
            dlg.notebook.select(dlg.in_form.frame)
            self.assertEqual(shown(dlg), str(dlg.images[("in", "external")]))

        self._run_dialog(lambda: InOutSignalDlg(self.app), driver)

    def test_illustration_of_an_edited_signal(self):
        self.tcl("""
            create_inout -name dq -specify external \\
               -in_launch_clock clk -rclk_inputdly_max {4} -rclk_inputdly_min {1} \\
               -in_hiz_edges {0 7P} -in_data_edges {4P 5P 6P} \\
               -out_launch_clock clk -rclk_outputdly_max {5} -rclk_outputdly_min {2} \\
               -out_hiz_edges {0 3P} -out_data_edges {1P 2P} -visible
        """)
        self.assertNoErrors()
        signal = self.app.signals.find("dq")

        def driver(dlg):
            self.assertEqual(self._illustration(dlg),
                             str(dlg.images[("in", "external")]))

        self._run_dialog(lambda: InOutSignalDlg(self.app, signal), driver)

    def test_creates_the_signal(self):
        def driver(dlg):
            self.fill_bus(dlg)
            dlg.ok()
            self.assertFalse(dlg.winfo_exists())

        self._run_dialog(lambda: InOutSignalDlg(self.app), driver)
        self.assertNoErrors()
        dq = self.app.signals.find("dq")
        self.assertIsInstance(dq, InOutSignal)
        self.assertTrue(dq.visible)
        self.assertEqual(dq.specify, "internal")
        self.assertEqual(dq.in_data_edges, ["4P", "5P", "6P"])
        self.assertEqual(dq.out_hiz_edges, ["0", "3P"])
        self.assertEqual(dq.rclk_outputdly_max, "5")
        self.assertEqual(dq.in_launch_clock.name, "clk")
        self.messagebox.showwarning.assert_not_called()
        self.messagebox.showerror.assert_not_called()
        ## One undoable action.
        self.assertTrue(self.app.undo.can_undo())
        self.app.undo.undo()
        self.root.update()
        self.assertIsNone(self.app.signals.find("dq"))

    def test_edits_a_signal_and_leaves_it_as_it_is(self):
        self.tcl(BUS)
        self.tcl("create_inout -name sda -specify external -pulled_up -hide_contention "
                 "-in_launch_clock clk -in_capture_clock clk2 "
                 "-fclk_inputdly_max {3} -fclk_inputdly_min {1} "
                 "-in_hiz_edges {0} -out_launch_clock clk2 "
                 "-out_hiz_edges {0 2N} -out_low_edges {1N} -color blue")
        before = self.write_script()

        def edit(name):
            def driver(dlg):
                if name == "sda":
                    self.assertEqual(dlg.topology_tkvar.get(), "external")
                    self.assertTrue(dlg.pulled_up_tkvar.get())
                    self.assertFalse(dlg.contention_tkvar.get())
                    self.assertFalse(dlg.visible_tkvar.get())
                    self.assertEqual(dlg.in_form.capture_tkvar.get(), "clk2")
                    self.assertEqual(dlg.out_form.edges_tkvars["low"].get(), "1N")
                else:
                    self.assertEqual(
                        dlg.out_form.delay_tkvars[("oedly", "rclk", "max")].get(), "3")
                    self.assertEqual(dlg.in_form.edges_tkvars["hiz"].get(), "0 7P")
                dlg.ok()
            self._run_dialog(
                lambda: InOutSignalDlg(self.app, self.app.signals.find(name)), driver)

        edit("dq")
        edit("sda")
        self.assertNoErrors()
        self.assertEqual(self.write_script().split("remove -all")[1],
                         before.split("remove -all")[1])
        ## Nothing changed: nothing to undo.
        self.assertFalse(self.app.undo.can_undo())

    def test_double_click_on_the_name_opens_the_dialog(self):
        self.tcl(BUS)
        canvas = self.app.canvas
        x1, y1, x2, y2 = canvas.bbox(canvas.find_withtag("dq_label")[0])
        event = tk.Event()
        event.x, event.y = (x1 + x2) / 2, (y1 + y2) / 2
        names = []
        self._run_dialog(lambda: canvas._on_double_click(event),
                         lambda dlg: names.append(dlg.name_tkvar.get()))
        self.assertEqual(names, ["dq"])

    # -- one delay specification for the port -------------------------------

    def test_external_delays_have_no_latency_nor_enable_delay(self):
        def driver(dlg):
            self.fill_bus(dlg)
            dlg.in_form.delay_tkvars[("latency", "rclk", "max")].set("0.5")
            dlg.out_form.delay_tkvars[("oedly", "rclk", "max")].set("3")
            dlg.out_form.delay_tkvars[("latency", "fclk", "min")].set("0.2")
            dlg.topology_tkvar.set("external")
            dlg._update_topology()
            for form in dlg.forms:
                for widget in form.internal_widgets:
                    if widget.winfo_class() == "TEntry":
                        self.assertEqual(str(widget.cget("state")), "disabled")
                self.assertEqual(
                    form.delay_tkvars[("latency", "rclk", "max")].get(), "")
            self.assertEqual(
                dlg.out_form.delay_tkvars[("oedly", "rclk", "max")].get(), "")
            ## The delays themselves are kept.
            self.assertEqual(
                dlg.in_form.delay_tkvars[("inputdly", "rclk", "max")].get(), "4")
            command = dlg._build_command()
            self.assertIn("-specify external", command)
            self.assertNotIn("latency", command)
            self.assertNotIn("oedly", command)

            dlg.topology_tkvar.set("internal")
            dlg._update_topology()
            for form in dlg.forms:
                for widget in form.internal_widgets:
                    if widget.winfo_class() == "TEntry":
                        self.assertEqual(str(widget.cget("state")), "normal")

        self._run_dialog(lambda: InOutSignalDlg(self.app), driver)

    def test_a_lone_max_or_min_is_completed(self):
        def driver(dlg):
            self.fill_bus(dlg)
            dlg.in_form.delay_tkvars[("inputdly", "rclk", "min")].set("")
            dlg.out_form.delay_tkvars[("oedly", "fclk", "min")].set("2")
            command = dlg._build_command()
            self.assertIn("-rclk_inputdly_max {4} -rclk_inputdly_min {0}", command)
            self.assertIn("-fclk_oedly_max {2} -fclk_oedly_min {2}", command)
            self.assertIn("-in_launch_clock clk", command)
            self.assertNotIn("-in_capture_clock", command)

        self._run_dialog(lambda: InOutSignalDlg(self.app), driver)

    # -- clocks -------------------------------------------------------------

    def test_only_related_clocks_can_be_chosen(self):
        def choose(form_combo, tkvar, name):
            tkvar.set(name)
            event = tk.Event()
            event.widget = form_combo
            return event

        def driver(dlg):
            in_form, out_form = dlg.forms
            self.assertEqual(list(in_form.cb_launch["values"]),
                             ["clk", "clk2", "other"])
            dlg._update_clock_choices(
                choose(in_form.cb_launch, in_form.launch_tkvar, "clk"))
            ## The three other clocks are restricted, in both tabs.
            for combo in (in_form.cb_capture, out_form.cb_launch,
                          out_form.cb_capture):
                self.assertEqual(list(combo["values"]), ["clk", "clk2"])
            out_form.capture_tkvar.set("clk2")
            ## A clock of another domain prevails: the others are dropped.
            dlg._update_clock_choices(
                choose(out_form.cb_launch, out_form.launch_tkvar, "other"))
            self.assertEqual(in_form.launch_tkvar.get(), "")
            self.assertEqual(out_form.capture_tkvar.get(), "")
            self.assertEqual(list(in_form.cb_launch["values"]), ["other"])

        self._run_dialog(lambda: InOutSignalDlg(self.app), driver)

    def test_a_part_without_clock_is_refused(self):
        def driver(dlg):
            self.fill_bus(dlg)
            dlg.out_form.launch_tkvar.set("")
            dlg.notebook.select(dlg.in_form.frame)
            dlg.ok()
            ## The dialog stays, on the tab of the part to complete.
            self.assertTrue(dlg.winfo_exists())
            self.assertEqual(dlg.notebook.select(), str(dlg.out_form.frame))
            self.assertIs(dlg.grab_current(), dlg)

        self._run_dialog(lambda: InOutSignalDlg(self.app), driver)
        self.messagebox.showerror.assert_called_once()
        self.assertIn("output part", self.messagebox.showerror.call_args.args[1])
        self.assertIsNone(self.app.signals.find("dq"))

    def test_a_signal_needs_a_name(self):
        def driver(dlg):
            self.fill_bus(dlg)
            dlg.name_tkvar.set("  ")
            self.assertFalse(dlg.apply())

        self._run_dialog(lambda: InOutSignalDlg(self.app), driver)
        self.messagebox.showerror.assert_called_once()
        self.assertEqual(self.app.signals.names(), ["clk", "clk2", "other"])

    # -- warnings -----------------------------------------------------------

    def test_contention_is_warned_and_the_signal_created(self):
        def driver(dlg):
            self.fill_bus(dlg)
            ## The other end drives from 3P, where the device only starts
            ## releasing the port (it takes up to 3 to do so).
            dlg.in_form.edges_tkvars["data"].set("3P 4P 5P 6P")
            dlg.out_form.delay_tkvars[("oedly", "rclk", "max")].set("3")
            dlg.out_form.delay_tkvars[("oedly", "rclk", "min")].set("1")
            dlg.apply()
            self.assertTrue(dlg.winfo_exists())
            self.assertIs(dlg.grab_current(), dlg)

        self._run_dialog(lambda: InOutSignalDlg(self.app), driver)
        self.assertNoErrors()
        self.messagebox.showwarning.assert_called_once()
        text = self.messagebox.showwarning.call_args.args[1]
        self.assertIn("dq", text)
        self.assertIn("Possible port contention", text)
        self.assertIsInstance(self.app.signals.find("dq"), InOutSignal)
        self.assertEqual(len(self.app.canvas.find_withtag("dq_contention")), 1)

    def test_mark_contention_can_be_switched_off(self):
        def driver(dlg):
            self.fill_bus(dlg)
            dlg.in_form.edges_tkvars["data"].set("3P 4P 5P 6P")
            dlg.out_form.delay_tkvars[("oedly", "rclk", "max")].set("3")
            dlg.out_form.delay_tkvars[("oedly", "rclk", "min")].set("1")
            dlg.contention_tkvar.set(False)
            dlg.ok()

        self._run_dialog(lambda: InOutSignalDlg(self.app), driver)
        self.assertTrue(self.app.signals.find("dq").hide_contention)
        self.assertEqual(self.app.canvas.find_withtag("dq_contention"), ())
        ## Still warned.
        self.messagebox.showwarning.assert_called_once()

    def test_a_part_left_empty_is_warned(self):
        def driver(dlg):
            self.fill_bus(dlg)
            for tkvar in dlg.in_form.edges_tkvars.values():
                tkvar.set("")
            dlg.ok()

        self._run_dialog(lambda: InOutSignalDlg(self.app), driver)
        self.messagebox.showwarning.assert_called_once()
        self.assertIn("The input part has no launch edge",
                      self.messagebox.showwarning.call_args.args[1])


if __name__ == "__main__":
    unittest.main()
