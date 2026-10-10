# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2024 Pablo Cardaba

"""UI scale: the factor, the logical-pixel canvas and a scaled application.

The factor is process-wide, so every test that changes it restores 1.0: the
rest of the suite runs unscaled.
"""

from __future__ import annotations

import os
import tkinter as tk
import unittest
from unittest import mock

from TimeIt.classes import uiscale
from TimeIt.tests.apphelper import AppTestCase, SCRIPTS, has_display


class ScaleTestCase(unittest.TestCase):
    """Restores the unscaled factor after each test."""

    def setUp(self) -> None:
        self.addCleanup(uiscale.set_scale, 1.0)


class TestFactor(ScaleTestCase):

    def test_unscaled_is_a_pass_through(self):
        uiscale.set_scale(1.0)
        self.assertEqual(uiscale.px(7), 7)
        self.assertEqual(uiscale.unpx(7), 7)
        self.assertEqual(uiscale.font_size(11), 11)
        self.assertEqual(uiscale.logical_font_size(11), 11)
        self.assertEqual(uiscale.font("TkFixedFont", 9, "bold"),
                         ("TkFixedFont", 9, "bold"))

    def test_pixels(self):
        uiscale.set_scale(2.0)
        self.assertEqual(uiscale.px(10), 20)
        self.assertEqual(uiscale.unpx(20), 10)
        uiscale.set_scale(1.5)
        self.assertEqual(uiscale.px(5), 8)
        self.assertEqual(uiscale.px(0), 0)
        ## Never rounded down to nothing.
        uiscale.set_scale(1.25)
        self.assertEqual(uiscale.px(1), 1)

    def test_window_size_survives_a_round_trip(self):
        for factor in (1.25, 1.5, 1.75, 2.0, 3.0):
            uiscale.set_scale(factor)
            for size in (1, 333, 804, 1216):
                self.assertEqual(uiscale.unpx(uiscale.px(size)), size)

    def test_fonts_are_given_in_pixels(self):
        uiscale.set_scale(2.0)
        ## 11 pt = 14.67 px at the logical 96 dpi.
        self.assertEqual(uiscale.font_size(11), -29)
        self.assertEqual(uiscale.logical_font_size(11), -15)
        self.assertEqual(uiscale.font("TkFixedFont", 9), ("TkFixedFont", -24))

    def test_factor_is_clamped_and_snapped(self):
        uiscale.set_scale(0.5)
        self.assertEqual(uiscale.scale(), 1.0)
        uiscale.set_scale(1.04)             # a 100 dpi screen is not scaled
        self.assertEqual(uiscale.scale(), 1.0)
        uiscale.set_scale(99)
        self.assertEqual(uiscale.scale(), uiscale.MAX_SCALE)

    def test_layout_distances(self):
        uiscale.set_scale(2.0)
        self.assertEqual(uiscale._scale_distance(5), 10)
        self.assertEqual(uiscale._scale_distance((0, 5)), (0, 10))
        self.assertEqual(uiscale._scale_distance("5 10"), "10 20")
        self.assertEqual(uiscale._scale_distance("2m"), "2m")


@unittest.skipUnless(has_display(), "no display: needs Tk")
class TestDetection(ScaleTestCase):

    def setUp(self) -> None:
        super().setUp()
        self.root = tk.Tk()
        self.root.withdraw()
        self.addCleanup(self.root.destroy)

    def test_environment_variable_wins(self):
        with mock.patch.dict(os.environ, {uiscale.ENV_VAR: "1.5"}):
            self.assertEqual(uiscale.detect(self.root), 1.5)

    def test_bad_environment_variable_is_ignored(self):
        with mock.patch.dict(os.environ, {uiscale.ENV_VAR: "big"}):
            self.assertGreaterEqual(uiscale.detect(self.root), 1.0)

    def test_setup_scales_the_named_fonts(self):
        from tkinter import font as tkfont
        default = tkfont.nametofont("TkDefaultFont", root=self.root)
        before = default.metrics("linespace")
        uiscale.setup(self.root, 2.0)
        self.assertLess(int(default.cget("size")), 0)       # pixels
        self.assertAlmostEqual(default.metrics("linespace") / before, 2.0,
                               delta=0.25)

    def test_grid_paddings_are_logical(self):
        uiscale.setup(self.root, 2.0)
        label = tk.Label(self.root, text="x")
        label.grid(row=0, column=0, padx=5, pady=(0, 3))
        self.root.grid_columnconfigure(0, minsize=40)
        info = label.grid_info()
        self.assertEqual(int(info["padx"]), 10)
        self.assertEqual(tuple(int(p) for p in info["pady"]), (0, 6))
        self.assertEqual(self.root.grid_columnconfigure(0)["minsize"], 80)
        ## Back to unscaled: the wrappers pass through.
        uiscale.set_scale(1.0)
        label.grid(padx=5)
        self.assertEqual(int(label.grid_info()["padx"]), 5)


@unittest.skipUnless(has_display(), "no display: needs Tk")
class TestScaledCanvas(ScaleTestCase):

    def setUp(self) -> None:
        super().setUp()
        from TimeIt.classes.scaledcanvas import ScaledCanvas
        self.root = tk.Tk()
        self.root.withdraw()
        self.addCleanup(self.root.destroy)
        uiscale.set_scale(2.0)
        self.canvas = ScaledCanvas(self.root)

    def device(self, method: str, *args):
        """The plain Tk answer, in device pixels."""
        return getattr(tk.Canvas, method)(self.canvas, *args)

    def test_coordinates_go_in_and_come_out_logical(self):
        item = self.canvas.create_line(10, 20, 30, 40, width=3)
        self.assertEqual(self.canvas.coords(item), [10.0, 20.0, 30.0, 40.0])
        self.assertEqual(self.device("coords", item), [20.0, 40.0, 60.0, 80.0])
        self.assertEqual(float(self.canvas.itemcget(item, "width")), 3.0)
        self.assertEqual(float(self.device("itemcget", item, "width")), 6.0)

        self.canvas.coords(item, 0, 0, 5, 5)
        self.assertEqual(self.device("coords", item), [0.0, 0.0, 10.0, 10.0])
        self.canvas.move(item, 4, 1)
        self.assertEqual(self.canvas.coords(item), [4.0, 1.0, 9.0, 6.0])

    def test_coordinate_lists_and_tuples(self):
        item = self.canvas.create_rectangle((1, 2, 3, 4))
        self.assertEqual(self.canvas.coords(item), [1.0, 2.0, 3.0, 4.0])
        item = self.canvas.create_line([1, 2, 3, 4, 5, 6])
        self.assertEqual(self.canvas.coords(item), [1.0, 2.0, 3.0, 4.0, 5.0, 6.0])

    def test_default_outline_is_one_logical_pixel(self):
        item = self.canvas.create_oval(0, 0, 10, 10)
        self.assertEqual(float(self.canvas.itemcget(item, "width")), 1.0)

    def test_bbox_is_whole_logical_pixels(self):
        item = self.canvas.create_rectangle(10, 10, 50, 30, width=1)
        box = self.canvas.bbox(item)
        self.assertTrue(all(isinstance(v, int) for v in box))
        self.assertLessEqual(box[0], 10)
        self.assertGreaterEqual(box[2], 50)
        self.assertLessEqual(box[2] - box[0], 44)
        self.assertIsNone(self.canvas.bbox("no_such_tag"))

    def test_dash_and_arrow_shape(self):
        item = self.canvas.create_line(0, 0, 50, 0, dash=(6, 3), arrow="last",
                                       arrowshape=(10, 12, 4), tags="g")
        ## Tk itself would report the scaled pattern truncated ("12 ").
        self.assertEqual(self.canvas.itemcget(item, "dash"), "6 3")
        self.assertEqual(self.canvas.itemcget(item, "arrowshape"), "10 12 4")
        self.canvas.itemconfigure("g", dash=(1, 2))
        self.assertEqual(self.canvas.itemcget(item, "dash"), "1 2")
        self.canvas.itemconfigure("g", dash="")
        self.assertEqual(self.canvas.itemcget(item, "dash"), "")

    def test_text_is_drawn_scaled_and_read_back_logical(self):
        from tkinter import font as tkfont
        item = self.canvas.create_text(0, 0, text="tSU", font=("Helvetica", 12, "bold"))
        logical = tkfont.nametofont(self.canvas.itemcget(item, "font"), root=self.root)
        device = tkfont.nametofont(self.device("itemcget", item, "font"), root=self.root)
        self.assertEqual(int(logical.cget("size")), -16)     # 12 pt at 96 dpi
        self.assertEqual(int(device.cget("size")), -32)
        self.assertEqual(logical.cget("weight"), "bold")
        ## One pair of fonts per description, however often it is drawn.
        again = self.canvas.create_text(0, 0, text="tH", font=("Helvetica", 12, "bold"))
        self.assertEqual(self.device("itemcget", again, "font"),
                         self.device("itemcget", item, "font"))

    def test_hit_testing_is_logical(self):
        item = self.canvas.create_rectangle(100, 100, 120, 120, fill="black")
        self.assertIn(item, self.canvas.find_overlapping(105, 105, 106, 106))
        self.assertNotIn(item, self.canvas.find_overlapping(205, 205, 206, 206))
        self.assertEqual(self.canvas.find_closest(110, 110), (item,))

    def test_to_device(self):
        self.assertEqual(self.canvas.to_device(21), 42)


@unittest.skipUnless(has_display(), "no display: needs Tk")
class TestScaledCanvasUnscaled(ScaleTestCase):

    def test_factor_one_is_plain_tk(self):
        from TimeIt.classes.scaledcanvas import ScaledCanvas
        root = tk.Tk()
        root.withdraw()
        self.addCleanup(root.destroy)
        uiscale.set_scale(1.0)
        canvas = ScaledCanvas(root)
        item = canvas.create_line(10, 20, 30, 40, dash=(6, 3))
        self.assertEqual(canvas.coords(item), [10.0, 20.0, 30.0, 40.0])
        self.assertEqual(canvas.bbox(item), tk.Canvas.bbox(canvas, item))
        self.assertEqual(canvas.itemcget(item, "dash"), "6 3")
        self.assertEqual(canvas.to_device(21), 21)


class TestScaledApp(AppTestCase):
    """The whole application at 200 %."""

    def setUp(self) -> None:
        uiscale.set_scale(2.0)
        self.addCleanup(uiscale.set_scale, 1.0)
        super().setUp()

    def test_example_loads_and_round_trips(self):
        self.source(SCRIPTS / "SPI_CPOL0_CPHA0.marked.tcl")
        self.assertNoErrors()
        self.assertRoundTrips()

    def test_window_size_is_saved_in_logical_pixels(self):
        self.tcl("set_window_size -width 500 -height 400")
        self.root.update()
        self.assertEqual(self.root.winfo_width(), 1000)
        self.assertIn("set_window_size -width 500 -height 400",
                      self.write_script())

    def test_drawing_is_twice_as_big_on_screen_only(self):
        self.tcl("set_canvas_scale 4.0")
        self.tcl("create_clock -name clk -topology source -period {10} "
                 "-rise_at {0} -fall_at {5} -show 4 -amplitude 40 -visible")
        self.assertNoErrors()
        canvas = self.app.canvas
        logical = canvas.bbox("clk_waveform")
        device = canvas.device_bbox("clk_waveform")
        ## 4 cycles of 10 at 4 px per unit, 40 px high, plus the edge tilt
        ## and the line width: logical pixels.
        self.assertAlmostEqual(logical[2] - logical[0], 160, delta=12)
        self.assertAlmostEqual(logical[3] - logical[1], 40, delta=6)
        self.assertAlmostEqual(device[2] - device[0],
                               2 * (logical[2] - logical[0]), delta=4)
        self.assertIn("set_canvas_scale 4.0", self.write_script())
        self.assertIn("-amplitude 40", self.write_script())


@unittest.skipUnless(has_display(), "no display: needs Tk")
class TestScaleIndependence(ScaleTestCase):
    """A diagram is the same document at every scale."""

    def _geometry(self, factor: float) -> list[tuple[str, list[float]]]:
        from TimeIt.classes.timeitapp import TimeItApp
        uiscale.set_scale(factor)
        root = tk.Tk()
        try:
            app = TimeItApp(root)
            root.update()
            app.console.interp.eval(
                "source {" + str(SCRIPTS / "SPI_CPOL0_CPHA0.marked.tcl") + "}")
            root.update()
            canvas = app.canvas
            items = [(canvas.type(i), canvas.coords(i)) for i in canvas.find_all()]
            app.undo.cleanup()
        finally:
            root.destroy()
        return items

    def test_logical_geometry_does_not_depend_on_the_scale(self):
        reference = self._geometry(1.0)
        for factor in (1.5, 2.0):
            scaled = self._geometry(factor)
            self.assertEqual([t for t, _ in scaled], [t for t, _ in reference])
            for (kind, got), (_, want) in zip(scaled, reference):
                self.assertEqual(len(got), len(want), kind)
                for a, b in zip(got, want):
                    ## Positions taken from a bounding box move by a pixel
                    ## at most (Tk pads the boxes in device pixels).
                    self.assertAlmostEqual(a, b, delta=1.5, msg=kind)


if __name__ == "__main__":
    unittest.main()
