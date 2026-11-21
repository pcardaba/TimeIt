# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2024 Pablo Cardaba

"""Integration tests of the *Settings Editor* dialog (Edit -> Settings...).

Issue #13: with the dialog left open, a value typed in the inline editor was
dropped on every other edit. The click that opens the editor also runs the
Treeview class binding, which focuses the tree, so the keys (Return
included) went to the tree, or the entry's <FocusOut> committed the
unchanged text at once. The tests click, type and press keys as a user does,
so that keyboard events go to whatever widget really has the focus.
"""

from __future__ import annotations

import time
import tkinter as tk
from unittest import mock

from TimeIt.classes import settingsdlg
from TimeIt.classes.settingsdlg import SettingsDlg
from TimeIt.tests.apphelper import AppTestCase


class SettingsDlgTestCase(AppTestCase):

    def setUp(self):
        super().setUp()
        self.dlg = SettingsDlg(self.app, self.app.settings)
        self.dlg.focus_force()
        self.pump()
        self.clear_log()

    def tearDown(self):
        if self.dlg.winfo_exists():
            self.dlg.destroy()
        super().tearDown()

    # ------------------------------------------------------------------
    def pump(self, seconds: float = 0.1) -> None:
        """Let Tk deliver the queued (focus, map) events."""
        end = time.monotonic() + seconds
        while time.monotonic() < end:
            self.dlg.update()
            time.sleep(0.005)

    def item(self, *path: str) -> str:
        tree = self.dlg.tree
        node = ""
        for name in path:
            node = next(c for c in tree.get_children(node)
                        if tree.item(c, "text") == name)
        return node

    def click_value(self, *path: str) -> str:
        tree = self.dlg.tree
        item = self.item(*path)
        tree.item(tree.parent(item), open=True)
        tree.see(item)
        self.pump()
        x, y, _w, h = tree.bbox(item, "#1")
        tree.event_generate("<Button-1>", x=x + 5, y=y + h // 2)
        tree.event_generate("<ButtonRelease-1>", x=x + 5, y=y + h // 2)
        self.pump()
        return item

    def type_text(self, text: str) -> None:
        """Replace the text of the widget that has the keyboard focus."""
        widget = self.dlg.focus_get()
        self.assertIs(widget, self.dlg._entry,
                      "the keyboard is not on the inline editor")
        widget.delete(0, tk.END)
        widget.insert(0, text)

    def press(self, key: str) -> None:
        ## Key events go to the focus window, wherever they are generated.
        self.dlg.focus_get().event_generate(f"<{key}>")
        self.pump()

    def commands(self) -> list[str]:
        return [h for h in self.app.console.history
                if h.startswith("set_app_var")]

    # ------------------------------------------------------------------
    def test_successive_edits_are_all_registered(self):
        waveform = self.app.settings.waveform
        for key, text, value in (("tilt", "3", 3), ("nmargin", "120", 120),
                                 ("interslot", "12", 12), ("tilt", "4", 4),
                                 ("top_padding", "25", 25)):
            item = self.click_value("waveform", key)
            self.type_text(text)
            self.press("Return")
            self.assertEqual(waveform[key], value, key)
            self.assertEqual(self.dlg.tree.set(item, "value"), text)
            self.assertFalse(self.dlg._entry.winfo_ismapped())
        self.assertNoErrors()

    def test_edits_in_nested_dictionary(self):
        font = self.app.settings.marker["font"]
        for text in ("12", "14", "9"):
            self.click_value("marker", "font", "size")
            self.type_text(text)
            self.press("Return")
            self.assertEqual(font["size"], int(text))
        self.assertNoErrors()

    def test_apply_commits_the_value_being_typed(self):
        self.click_value("waveform", "tilt")
        self.type_text("5")
        self.dlg.nametowidget(self._button("Apply")).invoke()
        self.assertEqual(self.app.settings.waveform["tilt"], 5)
        self.assertFalse(self.dlg._entry.winfo_ismapped())
        ## And again with the dialog still open.
        self.click_value("waveform", "tilt")
        self.type_text("6")
        self.dlg.nametowidget(self._button("Apply")).invoke()
        self.assertEqual(self.app.settings.waveform["tilt"], 6)

    def test_close_commits_the_value_being_typed(self):
        self.click_value("selection", "lwidth")
        self.type_text("4")
        self.dlg.nametowidget(self._button("Close")).invoke()
        self.assertEqual(self.app.settings.selection["lwidth"], 4)
        self.assertFalse(self.dlg.winfo_exists())

    def test_clicking_another_value_commits_the_first(self):
        self.click_value("waveform", "tilt")
        self.type_text("7")
        nmargin = self.click_value("waveform", "nmargin")
        self.assertEqual(self.app.settings.waveform["tilt"], 7)
        self.assertEqual(self.dlg._item_id, nmargin)
        self.assertIs(self.dlg.focus_get(), self.dlg._entry)

    def test_escape_discards_the_edit(self):
        self.click_value("waveform", "tilt")
        self.type_text("9")
        self.press("Escape")
        self.assertEqual(self.app.settings.waveform["tilt"], 2)
        self.assertEqual(self.commands(), [])

    def test_unchanged_value_issues_no_command(self):
        self.click_value("waveform", "tilt")
        self.press("Return")
        self.click_value("waveform", "nmargin")
        self.click_value("waveform", "interslot")
        self.assertEqual(self.commands(), [])

    def test_invalid_value_keeps_the_editor_open(self):
        with mock.patch.object(settingsdlg.messagebox, "showerror") as err:
            item = self.click_value("waveform", "tilt")
            self.type_text("abc")
            self.press("Return")
            err.assert_called_once()
            self.assertEqual(self.app.settings.waveform["tilt"], 2)
            self.assertEqual(self.dlg._item_id, item)
            self.assertTrue(self.dlg._entry.winfo_ismapped())
            ## A click elsewhere is refused while the value is invalid.
            self.click_value("waveform", "nmargin")
            self.assertEqual(self.dlg._item_id, item)
            self.assertEqual(err.call_count, 2)
        self.type_text("8")
        self.press("Return")
        self.assertEqual(self.app.settings.waveform["tilt"], 8)
        self.assertEqual(self.commands(),
                         ["set_app_var -name settings.waveform.tilt -value {8}"])

    def test_combobox_selection(self):
        self.click_value("waveform", "font", "weight")
        combo = self.dlg._entry
        self.assertIs(combo, self.dlg._combo_entry)
        combo.set("normal")
        combo.event_generate("<<ComboboxSelected>>")
        self.pump()
        self.assertEqual(self.app.settings.waveform["font"]["weight"], "normal")
        ## Then a plain value: the hidden combobox must not interfere.
        self.click_value("waveform", "tilt")
        self.type_text("3")
        self.press("Return")
        self.assertEqual(self.app.settings.waveform["tilt"], 3)
        self.assertEqual(self.app.settings.waveform["font"]["weight"], "normal")

    # ------------------------------------------------------------------
    def _button(self, text: str) -> str:
        def walk(widget):
            for child in widget.winfo_children():
                if child.winfo_class() == "TButton" and child.cget("text") == text:
                    return str(child)
                found = walk(child)
                if found:
                    return found
            return None
        found = walk(self.dlg)
        self.assertIsNotNone(found, f"no {text} button")
        return found
