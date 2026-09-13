# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2024 Pablo Cardaba

"""Double-clicking a signal name opens its edit dialog, for every type."""

from __future__ import annotations

import tkinter as tk
import unittest

from TimeIt.classes.clocksignaldlg import ClockSignalDlg
from TimeIt.classes.inputsignaldlg import InputSignalDlg
from TimeIt.classes.logicsignaldlg import LogicSignalDlg
from TimeIt.classes.sampledsignaldlg import SampledSignalDlg
from TimeIt.classes.waveformannotationdlg import WaveformAnnotationDlg
from TimeIt.tests.test_derived_dialogs import DialogTestCase


class TestDoubleClick(DialogTestCase):

    DIALOGS = (ClockSignalDlg, InputSignalDlg, LogicSignalDlg, SampledSignalDlg,
               WaveformAnnotationDlg)

    def _double_click(self, tag):
        canvas = self.app.canvas
        item = canvas.find_withtag(tag)[0]
        x1, y1, x2, y2 = canvas.bbox(item)
        event = tk.Event()
        ## No scrolling in the test window: window and canvas coordinates
        ## coincide, so the item centre can be handed over directly.
        event.x = (x1 + x2) / 2
        event.y = (y1 + y2) / 2
        canvas._on_double_click(event)

    def test_name_opens_the_matching_dialog_for_every_type(self):
        opened = []

        def driver(dlg):
            opened.append(type(dlg).__name__)
            dlg.dismiss()

        for name in ("clk", "req", "busy", "busy_q"):
            self._run_dialog(lambda name=name: self._double_click(f"{name}_label"), driver)
        self.assertEqual(opened, ["ClockSignalDlg", "InputSignalDlg",
                                  "LogicSignalDlg", "SampledSignalDlg"])

    def test_waveform_element_still_opens_the_annotation_dialog(self):
        opened = []

        def driver(dlg):
            opened.append(type(dlg).__name__)
            dlg.destroy()

        self._run_dialog(lambda: self._double_click("busy_highvalid"), driver)
        self.assertEqual(opened, ["WaveformAnnotationDlg"])


if __name__ == "__main__":
    unittest.main()
