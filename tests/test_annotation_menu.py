# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2024 Pablo Cardaba

"""Context menu "Annotation": annotate the selected waveform element.

The entry replaces the double-click on a waveform element: it opens the
annotation dialog of the one element selected, with its annotation when
it has one, to create it otherwise.
"""

from __future__ import annotations

import tkinter as tk
import unittest

from TimeIt.classes.waveformannotationdlg import WaveformAnnotationDlg
from TimeIt.tests.test_derived_dialogs import DialogTestCase


class TestAnnotationMenu(DialogTestCase):

    DIALOGS = (WaveformAnnotationDlg,)

    def setUp(self):
        super().setUp()
        self.canvas = self.app.canvas

    def _item(self, tag):
        return self.canvas.find_withtag(tag)[0]

    def _uid(self, tag):
        return next(t for t in self.canvas.gettags(self._item(tag))
                    if t.startswith("uid_"))

    def _select(self, tag, additive=False):
        self.canvas._select_item(self._item(tag), additive=additive)

    def _menu_state(self):
        """State of "Annotation" after a right-click on an empty spot."""
        event = tk.Event()
        event.x = event.y = event.x_root = event.y_root = 0
        event.state = 0
        self.canvas._update_context_menu(event)
        return self.canvas._ctxmenu.entrycget("Annotation", "state")

    def test_entry_sits_below_select(self):
        menu = self.canvas._ctxmenu
        labels = [menu.entrycget(i, "label") if menu.type(i) != "separator"
                  else "---" for i in range(menu.index("end") + 1)]
        i = labels.index("Select")
        self.assertEqual(labels[i:i + 3], ["Select", "Annotation", "---"])

    def test_enabled_for_exactly_one_selected_element(self):
        self.assertEqual(self._menu_state(), "disabled")
        self._select("busy_highvalid")
        self.assertEqual(self._menu_state(), "normal")
        ## The same element in a second selection mode is still one element.
        self.canvas._sel_mode_tkvar.set("end")
        self._select("busy_highvalid", additive=True)
        self.assertEqual(len(self.canvas.selected), 2)
        self.assertEqual(self._menu_state(), "normal")
        ## Two different elements: which one is meant is not known.
        self._select("busy_q_highvalid", additive=True)
        self.assertEqual(self._menu_state(), "disabled")

    def test_signal_name_is_not_a_target(self):
        self._select("busy_label")
        self.assertEqual(self._menu_state(), "disabled")

    def test_creates_an_annotation_on_the_selected_element(self):
        uid = self._uid("busy_highvalid")
        self._select("busy_highvalid")

        def driver(dlg):
            self.assertIsNone(dlg._annotation)
            self.assertEqual(dlg.wf_uid, uid)
            dlg._text_tkvar.set("busy")
            dlg.ok()

        self._run_dialog(self.canvas._annotate_selected, driver)
        self.assertEqual(self.errors(), [])
        sig = self.app.signals.find("busy")
        self.assertEqual(sig.annotations[uid].text, "busy")
        self.assertRoundTrips()

    def test_edits_the_existing_annotation(self):
        uid = self._uid("busy_highvalid")
        self.tcl(f"create_waveform_annotation -on {uid} -text {{old}}")
        annotation = self.app.signals.find("busy").annotations[uid]
        self._select("busy_highvalid")

        def driver(dlg):
            self.assertIs(dlg._annotation, annotation)
            self.assertEqual(dlg._text_tkvar.get(), "old")
            dlg._text_tkvar.set("new")
            dlg.ok()

        self._run_dialog(self.canvas._annotate_selected, driver)
        self.assertEqual(self.errors(), [])
        self.assertEqual(
            self.app.signals.find("busy").annotations[uid].text, "new")

    def test_without_a_target_nothing_opens(self):
        self.canvas._annotate_selected()
        self.root.update()
        self.assertIsNone(self._find_dialog())


if __name__ == "__main__":
    unittest.main()
