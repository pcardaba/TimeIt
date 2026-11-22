# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2024 Pablo Cardaba

"""Layout of the input, output and bidir signal dialogs (classes/iodlgside).

They read in the order they are filled in: on the left the Signal frame over
the delay choice and its illustration, on the right the clocks, the delays
and the edge lists. The dialogs are modal, so each test drives them from an
``after`` callback.
"""

from __future__ import annotations

from tkinter import ttk

from TimeIt.classes.inoutsignaldlg import InOutSignalDlg
from TimeIt.classes.inputsignaldlg import InputSignalDlg
from TimeIt.classes.outputsignaldlg import OutputSignalDlg
from TimeIt.tests.apphelper import AppTestCase
from TimeIt.tests.test_create_inout import BASE

DIALOGS = (InputSignalDlg, OutputSignalDlg, InOutSignalDlg)


class IODialogLayoutTest(AppTestCase):

    def setUp(self):
        super().setUp()
        self.tcl(BASE)
        self.clear_log()

    def _run_dialog(self, cls, driver, signal=None):
        """Open the modal dialog `cls` (on `signal`) and let ``driver(dlg)``
        operate it."""
        seen = {}

        def drive():
            dlg = next((w for w in self.app.winfo_children()
                        if isinstance(w, cls)), None)
            if dlg is None:
                seen["error"] = AssertionError("the dialog never opened")
                return
            try:
                dlg.update_idletasks()
                driver(dlg)
            except Exception as exc:  # noqa: BLE001 - re-raised below
                seen["error"] = exc
            finally:
                if dlg.winfo_exists():
                    dlg.dismiss()

        self.root.after(100, drive)
        cls(self.app, signal)
        self.root.update()
        if "error" in seen:
            raise seen["error"]

    @staticmethod
    def _views(dlg):
        """Set the dialog to each of its illustrations in turn."""
        tabs = dlg.notebook.tabs() if isinstance(dlg, InOutSignalDlg) else [None]
        for tab in tabs:
            if tab is not None:
                dlg.notebook.select(tab)
            for topology in ("internal", "external"):
                dlg.topology_tkvar.set(topology)
                dlg._update_topology()
                dlg.update_idletasks()
                yield tab, topology

    def test_size_does_not_follow_the_illustration(self):
        for cls in DIALOGS:
            with self.subTest(dialog=cls.__name__):
                def driver(dlg):
                    sizes = {view: (dlg.winfo_reqwidth(), dlg.winfo_reqheight())
                             for view in self._views(dlg)}
                    self.assertEqual(len(set(sizes.values())), 1, sizes)
                self._run_dialog(cls, driver)

    def test_name_is_the_first_field(self):
        for cls in DIALOGS:
            with self.subTest(dialog=cls.__name__):
                def driver(dlg):
                    first = dlg.tk_focusNext()
                    self.assertIsInstance(first, ttk.Entry)
                    self.assertEqual(str(first.cget("textvariable")),
                                     str(dlg.name_tkvar))
                self._run_dialog(cls, driver)

    def test_signal_and_delay_choice_left_of_the_clocks(self):
        for cls in DIALOGS:
            with self.subTest(dialog=cls.__name__):
                def driver(dlg):
                    first = dlg.tk_focusNext()
                    if isinstance(dlg, InOutSignalDlg):
                        launch = dlg.in_form.cb_launch
                    else:
                        launch = dlg.cb_launch
                    image = dlg.lbimg_topo
                    ## Name above the illustration, both left of the clocks.
                    self.assertLess(first.winfo_rooty(), image.winfo_rooty())
                    self.assertLess(first.winfo_rootx() + first.winfo_width(),
                                    launch.winfo_rootx())
                    self.assertLess(image.winfo_rootx() + image.winfo_width(),
                                    launch.winfo_rootx())
                self._run_dialog(cls, driver)

    def test_editing_loads_the_signal_frame(self):
        self.tcl("create_input -name din -specify external -launch_clock clk"
                 " -capture_clock clk -color red -amplitude 30 -lwidth 3"
                 " -pulled_up -visible")

        def driver(dlg):
            self.assertEqual(dlg.name_tkvar.get(), "din")
            self.assertEqual((dlg.color_tkvar.get(), dlg.amplitude_tkvar.get(),
                              dlg.lwidth_tkvar.get()), ("red", 30, 3))
            self.assertTrue(dlg.pulled_up_tkvar.get())
            ## The illustration of the external delay is the one on show.
            self.assertEqual(str(dlg.lbimg_topo.cget("image")[0]),
                             str(dlg.images["external"]))

        self._run_dialog(InputSignalDlg, driver,
                         self.app.signals.find("din"))


if __name__ == "__main__":
    import unittest
    unittest.main()
