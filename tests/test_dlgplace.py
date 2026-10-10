# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2024 Pablo Cardaba

"""Tests of where the dialogs open (``classes/dlgplace.py``).

The geometry is pure and tested without Tk. The integration tests park the
main window away from the centre of its monitor, where a window manager
left to itself would not put a dialog, open every dialog and check that it
comes up over the main window. The modal ones block in wait_window(), so
they are inspected from an ``after`` callback, as in ``test_timings_dlg``.
"""

from __future__ import annotations

import sys
import time
import tkinter as tk
import types
import unittest
from unittest import mock

from TimeIt.classes import dlgplace
from TimeIt.tests.apphelper import AppTestCase, REPO
from TimeIt.tests.test_create_logic import BASE

## Two monitors side by side, the second one being where TimeIt is.
LEFT = (0, 0, 1920, 1080)
RIGHT = (1920, 0, 2560, 1440)


# ----------------------------------------------------------------------
# Geometry
# ----------------------------------------------------------------------
class TestCentered(unittest.TestCase):

    def test_centred_over_the_owner(self):
        self.assertEqual(
            dlgplace.centered((400, 300), (2500, 400, 800, 500), RIGHT),
            (2700, 500))

    def test_a_dialog_larger_than_its_owner_is_centred_too(self):
        self.assertEqual(
            dlgplace.centered((1000, 700), (2500, 400, 800, 500), RIGHT),
            (2400, 300))

    def test_kept_inside_the_monitor_of_the_owner(self):
        ## The owner touches the left edge of the right monitor: the dialog
        ## does not spill over the left one.
        self.assertEqual(
            dlgplace.centered((1000, 300), (1920, 400, 800, 500), RIGHT),
            (1920, 500))
        ## ... nor past the bottom right corner.
        self.assertEqual(
            dlgplace.centered((1000, 700), (3900, 1100, 580, 340), RIGHT),
            (3480, 740))

    def test_monitor_at_negative_coordinates(self):
        ## Windows: a monitor on the left of the primary one.
        screen = (-1920, 0, 1920, 1080)
        self.assertEqual(
            dlgplace.centered((400, 300), (-1500, 200, 800, 500), screen),
            (-1300, 300))
        self.assertEqual(
            dlgplace.centered((1000, 300), (-1920, 200, 800, 500), screen),
            (-1920, 300))

    def test_a_dialog_larger_than_the_screen_keeps_its_title_bar(self):
        self.assertEqual(
            dlgplace.centered((3000, 2000), (2500, 400, 800, 500), RIGHT),
            (1920, 0))


class TestBeside(unittest.TestCase):

    OWNER = (2400, 300, 500, 600)

    def test_on_the_right_tops_level(self):
        self.assertEqual(dlgplace.beside((480, 280), self.OWNER, RIGHT, gap=8),
                         (2908, 300))

    def test_on_the_left_when_the_right_has_no_room(self):
        owner = (3900, 300, 500, 600)
        self.assertEqual(dlgplace.beside((480, 280), owner, RIGHT, gap=8),
                         (3412, 300))

    def test_a_room_that_only_misses_the_gap_is_no_room(self):
        ## 80 pixels left on the right of the owner, exactly the width.
        owner = (3900, 300, 500, 600)
        self.assertEqual(dlgplace.beside((80, 280), owner, RIGHT, gap=8),
                         (3812, 300))
        self.assertEqual(dlgplace.beside((80, 280), owner, RIGHT, gap=0),
                         (4400, 300))

    def test_no_room_on_either_side_takes_the_wider_one(self):
        screen = (0, 0, 1000, 800)
        ## 300 on the left, 200 on the right, 480 wanted.
        self.assertEqual(dlgplace.beside((480, 280), (300, 100, 500, 600), screen),
                         (0, 100))
        ## 200 on the left, 300 on the right.
        self.assertEqual(dlgplace.beside((480, 280), (200, 100, 500, 600), screen),
                         (520, 100))

    def test_kept_inside_the_screen_vertically(self):
        owner = (2400, 1300, 500, 140)
        self.assertEqual(dlgplace.beside((480, 280), owner, RIGHT, gap=8),
                         (2908, 1160))


class TestMonitors(unittest.TestCase):

    XRANDR = ("Monitors: 2\n"
              " 0: +*DP-0 1920/527x1080/296+0+0  DP-0\n"
              " 1: +HDMI-0 2560/597x1440/336+1920+0  HDMI-0\n")

    def test_parse_xrandr(self):
        self.assertEqual(dlgplace.parse_xrandr_monitors(self.XRANDR),
                         [LEFT, RIGHT])

    def test_parse_xrandr_real_output_of_one_monitor(self):
        text = ("Monitors: 1\n"
                " 0: +*DisplayPort-0 5120/597x2880/336+0+0  DisplayPort-0\n")
        self.assertEqual(dlgplace.parse_xrandr_monitors(text),
                         [(0, 0, 5120, 2880)])

    def test_parse_xrandr_nothing_to_read(self):
        self.assertEqual(dlgplace.parse_xrandr_monitors(""), [])
        self.assertEqual(dlgplace.parse_xrandr_monitors("Can't open display\n"), [])

    def test_monitor_of_the_window(self):
        monitors = [LEFT, RIGHT]
        self.assertEqual(dlgplace.monitor_of((100, 100, 800, 500), monitors), LEFT)
        self.assertEqual(dlgplace.monitor_of((2500, 100, 800, 500), monitors), RIGHT)

    def test_a_window_across_two_monitors_is_on_the_one_showing_more(self):
        monitors = [LEFT, RIGHT]
        self.assertEqual(dlgplace.monitor_of((1700, 100, 800, 500), monitors), RIGHT)
        self.assertEqual(dlgplace.monitor_of((1300, 100, 800, 500), monitors), LEFT)

    @unittest.skipIf(sys.platform == "win32", "the fallback of the other systems")
    def test_win32_lookup_is_harmless_elsewhere(self):
        self.assertIsNone(dlgplace._win32_work_area((100, 100, 800, 500)))

    def test_a_window_on_no_monitor(self):
        self.assertIsNone(dlgplace.monitor_of((9000, 100, 800, 500), [LEFT, RIGHT]))
        self.assertIsNone(dlgplace.monitor_of((100, 100, 800, 500), []))


# ----------------------------------------------------------------------
# The dialogs of the application
# ----------------------------------------------------------------------
def rect(window: tk.Misc) -> tuple[int, int, int, int]:
    """The content of a toplevel on the screen: (x, y, width, height)."""
    return (window.winfo_rootx(), window.winfo_rooty(),
            window.winfo_width(), window.winfo_height())


class PlacementTestCase(AppTestCase):

    def setUp(self):
        super().setUp()
        self.tcl(BASE)
        self.clear_log()
        self._park_main_window()

    # -- helpers ----------------------------------------------------------
    def _settle(self, seconds: float = 0.15) -> None:
        """Let the window manager answer."""
        end = time.monotonic() + seconds
        while time.monotonic() < end:
            self.root.update()
            time.sleep(0.01)

    def _wait_shown(self, window: tk.Misc, timeout: float = 3.0) -> None:
        end = time.monotonic() + timeout
        while not window.winfo_viewable() and time.monotonic() < end:
            self.root.update()
            time.sleep(0.01)
        self._settle()

    def _park_main_window(self) -> None:
        """Three quarters of the way across the monitor the main window is
        on: away from the centre and from the top left corner, where the
        window managers put a window that asks for nothing."""
        self.screen = dlgplace.screen_of(self.root, rect(self.root))
        sx, sy, swidth, sheight = self.screen
        x = sx + (swidth - self.root.winfo_width()) * 3 // 4
        y = sy + (sheight - self.root.winfo_height()) * 3 // 4
        self.root.geometry(f"+{x}+{y}")
        self._settle(0.3)

    def _toplevels(self, widget=None) -> list[tk.Toplevel]:
        found = []
        for child in (widget or self.root).winfo_children():
            if isinstance(child, tk.Toplevel):
                found.append(child)
            found.extend(self._toplevels(child))
        return found

    def _run_modal(self, open_dialog, driver=None) -> None:
        """Open a modal dialog, check it once shown, then close it."""
        seen = {}

        def drive():
            dialogs = self._toplevels()
            if not dialogs:
                seen["error"] = AssertionError("the dialog never opened")
                return
            dlg = dialogs[0]
            seen["dlg"] = dlg
            try:
                self._wait_shown(dlg)
                self.assertOverMainWindow(dlg)
                self.assertIs(dlg.grab_current(), dlg)
                if driver is not None:
                    driver(dlg)
            except Exception as exc:  # noqa: BLE001 - re-raised below
                seen["error"] = exc
            finally:
                if dlg.winfo_exists():
                    dlg.destroy()

        def safety():
            for dlg in self._toplevels():
                seen.setdefault("error", AssertionError("dialog left open"))
                dlg.destroy()

        self.root.after(100, drive)
        timer = self.root.after(10000, safety)
        open_dialog()
        self.root.after_cancel(timer)
        self.root.update()
        if "error" in seen:
            raise seen["error"]
        self.assertIn("dlg", seen)

    def assertOverMainWindow(self, dlg: tk.Misc) -> None:
        """Shown, with its centre inside the main window."""
        self.assertTrue(dlg.winfo_viewable(), "the dialog is not shown")
        x, y, width, height = rect(self.root)
        dx, dy, dwidth, dheight = rect(dlg)
        cx, cy = dx + dwidth // 2, dy + dheight // 2
        self.assertTrue(
            x <= cx <= x + width and y <= cy <= y + height,
            f"{type(dlg).__name__} at {rect(dlg)} is not over the main "
            f"window at {rect(self.root)}")


class TestModalDialogs(PlacementTestCase):

    def test_signal_dialogs(self):
        from TimeIt.classes.clocksignaldlg import ClockSignalDlg
        from TimeIt.classes.inputsignaldlg import InputSignalDlg
        from TimeIt.classes.logicsignaldlg import LogicSignalDlg
        from TimeIt.classes.outputsignaldlg import OutputSignalDlg
        from TimeIt.classes.pwlsignaldlg import PWLSignalDlg
        from TimeIt.classes.sampledsignaldlg import SampledSignalDlg

        for cls in (ClockSignalDlg, InputSignalDlg, OutputSignalDlg,
                    PWLSignalDlg, LogicSignalDlg, SampledSignalDlg):
            with self.subTest(dialog=cls.__name__):
                self._run_modal(lambda: cls(self.app))

    def test_editing_a_signal(self):
        from TimeIt.classes.clocksignaldlg import ClockSignalDlg

        clk = self.app.signals.find("clk")
        self._run_modal(lambda: ClockSignalDlg(self.app, clk))

    def test_timing_marker_dialog(self):
        from TimeIt.classes.timingmarkerdlg import TimingMarkerDlg

        marker = types.SimpleNamespace(name="tSU", timing=2.5,
                                       style="inner_both", anchor="start")
        self._run_modal(lambda: TimingMarkerDlg(self.app, marker))

    def test_annotation_dialog(self):
        from TimeIt.classes.waveformannotationdlg import WaveformAnnotationDlg

        self._run_modal(lambda: WaveformAnnotationDlg(self.app, "uid_2_11"))

    def test_about_dialog(self):
        from TimeIt.classes.aboutdlg import AboutDlg

        self._run_modal(lambda: AboutDlg(self.root))


class TestOtherDialogs(PlacementTestCase):
    """The dialogs whose constructor returns."""

    def _check(self, dlg, modal: bool) -> None:
        try:
            self._wait_shown(dlg)
            self.assertOverMainWindow(dlg)
            if modal:
                self.assertIs(dlg.grab_current(), dlg)
        finally:
            dlg.destroy()
            self.root.update()

    def test_settings(self):
        from TimeIt.classes.settingsdlg import SettingsDlg

        self._check(SettingsDlg(self.app, self.app.settings), modal=True)

    def test_grid_settings(self):
        from TimeIt.classes.gridsettingsdlg import GridSettingsDlg

        self._check(GridSettingsDlg(self.app, self.app.settings), modal=False)

    def test_import_vcds(self):
        from TimeIt.classes.importvcddlg import ImportVCDDlg

        self._check(ImportVCDDlg(self.root), modal=True)

    def test_import_vcds_characterization(self):
        from TimeIt.classes.importvcdchardlg import ImportVCDCharDlg
        from TimeIt.classes.vcdimport import VCDPairAnalysis, parse_vcd_file

        vcds = REPO / "data" / "VCDs"
        analysis = VCDPairAnalysis(parse_vcd_file(vcds / "import_vcd.min.vcd"),
                                   parse_vcd_file(vcds / "import_vcd.max.vcd"))
        self.assertTrue(analysis.ok)
        self._check(ImportVCDCharDlg(self.root, analysis), modal=True)

    def test_user_timings_from_the_edit_menu(self):
        self._check(self.app.open_timings(), modal=False)

    def test_dialog_follows_the_main_window(self):
        from TimeIt.classes.settingsdlg import SettingsDlg

        sx, sy, swidth, sheight = self.screen
        x = sx + (swidth - self.root.winfo_width()) // 4
        y = sy + (sheight - self.root.winfo_height()) // 4
        self.root.geometry(f"+{x}+{y}")
        self._settle(0.3)
        self._check(SettingsDlg(self.app, self.app.settings), modal=True)


class TestTimingsBesideADialog(PlacementTestCase):
    """Opened from a signal dialog, the User Timings window is used together
    with it: it comes up next to the dialog, not over it."""

    def test_next_to_the_dialog(self):
        from TimeIt.classes.inputsignaldlg import InputSignalDlg

        def driver(dlg):
            timings = self.app.open_timings(dlg)
            self._wait_shown(timings)
            self.assertTrue(timings.winfo_viewable())
            ## The dialog keeps the grab: the rest of the app stays blocked.
            self.assertIs(dlg.grab_current(), dlg)

            dx, dy, dwidth, _ = rect(dlg)
            tx, ty, twidth, _ = rect(timings)
            sx, _, swidth, _ = self.screen
            needed = twidth + 60  # the window, its frame and the gap
            if dx - sx < needed and sx + swidth - (dx + dwidth) < needed:
                self.skipTest("screen too narrow for two windows side by side")
            on_the_right = tx >= dx + dwidth
            on_the_left = tx + twidth <= dx
            self.assertTrue(on_the_right or on_the_left,
                            f"timings at {rect(timings)} overlaps the dialog "
                            f"at {rect(dlg)}")
            distance = tx - (dx + dwidth) if on_the_right else dx - (tx + twidth)
            self.assertLess(distance, 60)
            self.assertAlmostEqual(ty, dy, delta=10)

        self._run_modal(lambda: InputSignalDlg(self.app), driver)


class TestPlace(PlacementTestCase):

    def test_owner_not_on_screen_leaves_it_to_the_window_manager(self):
        owner = tk.Toplevel(self.root)
        owner.withdraw()
        window = tk.Toplevel(self.root)
        with mock.patch.object(window, "wm_geometry") as geometry:
            dlgplace.place(window, owner)
        geometry.assert_not_called()
        self._wait_shown(window)
        self.assertTrue(window.winfo_viewable())

    def test_asks_for_the_position_before_the_window_is_shown(self):
        window = tk.Toplevel(self.root)
        tk.Frame(window, width=300, height=200).pack()
        shown = []
        original = window.wm_geometry

        def spy(*args):
            if args:
                shown.append(window.winfo_viewable())
            return original(*args)

        with mock.patch.object(window, "wm_geometry", side_effect=spy):
            dlgplace.place(window, self.app)
        self.assertEqual(shown, [0])
        self._wait_shown(window)
        self.assertOverMainWindow(window)

    def test_monitors_unknown_falls_back_to_the_desktop(self):
        with mock.patch.object(dlgplace, "_x11_monitors", return_value=[]), \
                mock.patch.object(dlgplace, "_win32_work_area", return_value=None):
            screen = dlgplace.screen_of(self.root, rect(self.root))
        self.assertEqual(screen, (self.root.winfo_vrootx(), self.root.winfo_vrooty(),
                                  self.root.winfo_vrootwidth(),
                                  self.root.winfo_vrootheight()))

    def test_stays_on_the_monitor_of_the_main_window(self):
        """Two screens: the main window on the right half of the desktop,
        against the border between the two. A dialog wider than the main
        window does not reach the left screen."""
        sx, sy, swidth, sheight = self.screen
        half = swidth // 2
        right = (sx + half, sy, swidth - half, sheight)
        self.root.geometry(f"+{sx + half}+{sy + sheight // 4}")
        self._settle(0.3)

        window = tk.Toplevel(self.root)
        tk.Frame(window, width=self.root.winfo_width() + 300, height=200).pack()
        with mock.patch.object(dlgplace, "screen_of", return_value=right):
            dlgplace.place(window, self.app)
        self._wait_shown(window)
        self.assertGreaterEqual(window.winfo_rootx(), sx + half)


if __name__ == "__main__":
    unittest.main()
