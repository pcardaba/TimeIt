# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2024 Pablo Cardaba

"""Tests for the DerivedSignal base class: model half with fake operands,
renderer half with a recording fake canvas. No Tk needed."""

import math
import unittest

from TimeIt.classes.derivedsignal import DerivedSignal

INF = math.inf


class FakeOperand:
    """Minimal stand-in for a signal, exposing only what flattening needs."""

    def __init__(self, name, intervals, pulled_up=False):
        self.name = name
        self.type = "input"
        self.pulled_up = pulled_up
        self._intervals = intervals

    def state_intervals(self):
        return self._intervals


class FakeConsole:
    """Records error lines; evaluates timing expressions from a dict."""

    def __init__(self, values=None):
        self.errors = []
        self.values = values or {}
        self.interp = self

    def append_log(self, text, tag=None):
        if tag == "error":
            self.errors.append(text)

    def eval(self, expr):
        ## "expr {<name>}" -> the value registered under <name>.
        key = expr[len("expr {"):-1]
        if key not in self.values:
            import tkinter as tk
            raise tk.TclError(f'can\'t read "{key}": no such variable')
        return str(self.values[key])


class ConstantDerived(DerivedSignal):
    """A derived signal with a fixed timeline, for testing the base class."""

    def __init__(self, name, timeline):
        super().__init__(name)
        self._fixed = timeline

    def recompute(self):
        return self._fixed


class TestDerivedSignalModel(unittest.TestCase):

    def test_state_intervals_exposes_the_timeline(self):
        sig = ConstantDerived("q", [(-INF, 5.0, "0"), (5.0, INF, "1")])
        self.assertEqual(sig.state_intervals(),
                         [(-INF, 5.0, "low"), (5.0, INF, "high")])

    def test_state_intervals_maps_every_value_back_to_a_state(self):
        sig = ConstantDerived("q", [(-INF, 1.0, "0"), (1.0, 2.0, "1"),
                                    (2.0, 3.0, "X"), (3.0, INF, "D")])
        self.assertEqual([state for _, _, state in sig.state_intervals()],
                         ["low", "high", "unknown", "data"])

    def test_unresolvable_recompute_gives_none(self):
        sig = ConstantDerived("q", None)
        self.assertIsNone(sig.state_intervals())

    def test_operand_timeline_flattens_a_fake_operand(self):
        sig = ConstantDerived("q", [])
        operand = FakeOperand("a", [(-INF, 2.0, "low"), (4.0, INF, "high")])
        self.assertEqual(sig.operand_timeline(operand),
                         [(-INF, 2.0, "0"), (2.0, 4.0, "X"), (4.0, INF, "1")])

    def test_operand_timeline_honours_pulled_up(self):
        sig = ConstantDerived("q", [])
        operand = FakeOperand("a", [(-INF, INF, "hiz")], pulled_up=True)
        self.assertEqual(sig.operand_timeline(operand), [(-INF, INF, "1")])

    def test_missing_operand_gives_none(self):
        sig = ConstantDerived("q", [])
        self.assertIsNone(sig.operand_timeline(None))

    def test_operand_without_waveform_is_logged(self):
        sig = ConstantDerived("q", [])
        sig.console = FakeConsole()
        self.assertIsNone(sig.operand_timeline(object()))
        self.assertEqual(len(sig.console.errors), 1)

    def test_reentrancy_guard_breaks_a_cycle(self):
        ## A signal that reads itself must yield None rather than recurse
        ## until the stack blows up.
        class SelfReading(DerivedSignal):
            def recompute(inner):
                return inner.operand_timeline(inner)

        sig = SelfReading("loop")
        sig.console = FakeConsole()
        self.assertIsNone(sig.state_intervals())
        self.assertTrue(any("cycle" in e for e in sig.console.errors))

    def test_value_error_in_recompute_is_logged_not_raised(self):
        class Broken(DerivedSignal):
            def recompute(inner):
                raise ValueError("boom")

        sig = Broken("b")
        sig.console = FakeConsole()
        self.assertIsNone(sig.timeline())
        self.assertTrue(any("boom" in e for e in sig.console.errors))

    def test_eval_or_zero(self):
        sig = ConstantDerived("q", [])
        sig.console = FakeConsole({"$tpd": 1.5})
        self.assertEqual(sig._eval_or_zero(None), 0.0)
        self.assertEqual(sig._eval_or_zero("  "), 0.0)
        self.assertEqual(sig._eval_or_zero("$tpd"), 1.5)

    def test_related_clocks_are_the_clock_operands(self):
        clock = FakeOperand("clk", [])
        clock.type = "clock"
        data = FakeOperand("d", [])

        class TwoOperands(ConstantDerived):
            def operands(inner):
                return (data, clock)

        sig = TwoOperands("q", [])
        self.assertEqual(sig.related_clocks(), (clock,))


# ----------------------------------------------------------------------
# Renderer
# ----------------------------------------------------------------------

class FakeSettings:
    waveform = {"left_padding": 10, "nmargin": 100, "right_padding": 5,
                "tilt": 2, "font": None}

    def get_font(self, _):
        return None


class FakeClock:
    type = "clock"

    def __init__(self, period, cycles):
        self.period, self.cycles = period, cycles

    def ensure_resolved(self):
        return True

    def _waveform(self):
        return (self.period, 0.0, self.period / 2)


class FakeStore:
    def __init__(self, *signals):
        self._signals = signals

    def values(self):
        return iter(self._signals)


class FakeCanvas:
    """Records the items a draw() creates. x = x0 + t * scale_factor."""

    def __init__(self, clocks=(), scale_factor=10.0, is_virtual=False,
                 width=1):
        self.settings = FakeSettings()
        self.signals = FakeStore(*clocks)
        self.scale_factor = scale_factor
        self.is_virtual = is_virtual
        self._width = width
        self.items = []          # (kind, coords, tags)
        self.configured = []     # (tag, options)

    @property
    def x0(self):
        return (self.settings.waveform["left_padding"]
                + self.settings.waveform["nmargin"])

    def time_to_x(self, t):
        return self.x0 + t * self.scale_factor

    def winfo_width(self):
        return self._width

    def create_line(self, *coords, **kw):
        self.items.append(("line", list(coords), kw.get("tags", ())))

    def create_polygon(self, *coords, **kw):
        self.items.append(("polygon", list(coords), kw.get("tags", ())))

    def create_text(self, *coords, **kw):
        self.items.append(("text", list(coords), kw.get("tags", ())))

    def itemconfigure(self, tag, **options):
        self.configured.append((tag, options))

    # -- queries
    def of_kind(self, kind):
        return [(coords, tags) for k, coords, tags in self.items if k == kind]

    def tagged(self, suffix):
        return [(coords, tags) for _, coords, tags in self.items
                if any(t.endswith(suffix) for t in tags)]


class TestDerivedSignalRenderer(unittest.TestCase):

    TOP = 20
    AMP = 40      # default amplitude
    TILT = 2

    def _canvas(self, **kw):
        kw.setdefault("clocks", (FakeClock(10.0, 10),))   # span 100 -> x 110..1110
        return FakeCanvas(**kw)

    def _draw(self, timeline, canvas=None, visible=True):
        canvas = canvas or self._canvas()
        sig = ConstantDerived("q", timeline)
        sig.visible = visible
        sig.console = FakeConsole()
        return sig.draw(canvas, self.TOP), canvas, sig

    def test_unresolvable_timeline_returns_negative_and_draws_nothing(self):
        height, canvas, _ = self._draw(None)
        self.assertLess(height, 0)
        self.assertEqual(canvas.items, [])

    def test_constant_high_is_one_line_across_the_diagram(self):
        height, canvas, _ = self._draw([(-INF, INF, "1")])
        self.assertEqual(height, self.AMP)
        lines = canvas.tagged("_highvalid")
        self.assertEqual(len(lines), 1)
        coords, _ = lines[0]
        self.assertEqual(coords, [canvas.x0, self.TOP, canvas.x0 + 1000, self.TOP])

    def test_low_level_sits_at_the_bottom_of_the_slot(self):
        _, canvas, _ = self._draw([(-INF, INF, "0")])
        coords, _ = canvas.tagged("_lowvalid")[0]
        self.assertEqual(coords[1], self.TOP + self.AMP)

    def test_label_is_drawn(self):
        _, canvas, _ = self._draw([(-INF, INF, "1")])
        self.assertEqual(len(canvas.tagged("_label")), 1)

    def test_transition_polygon_slants_like_an_io_signal(self):
        ## 0 until t=2, transition window, 1 from t=4: the polygon's left edge
        ## crosses mid-height at x(2) rising, its right edge at x(4).
        _, canvas, _ = self._draw([(-INF, 2.0, "0"), (4.0, INF, "1")])
        polys = canvas.tagged("_transition")
        self.assertEqual(len(polys), 1)
        coords, _ = polys[0]
        x1, x2 = canvas.time_to_x(2.0), canvas.time_to_x(4.0)
        top, bottom, tilt = self.TOP, self.TOP + self.AMP, self.TILT
        self.assertEqual(coords, [x1 - tilt, bottom, x1 + tilt, top,
                                  x2 + tilt, top, x2 - tilt, bottom])

    def test_falling_transition_mirrors_the_rising_one(self):
        _, canvas, _ = self._draw([(-INF, 2.0, "1"), (4.0, INF, "0")])
        coords, _ = canvas.tagged("_transition")[0]
        x1, x2 = canvas.time_to_x(2.0), canvas.time_to_x(4.0)
        top, bottom, tilt = self.TOP, self.TOP + self.AMP, self.TILT
        self.assertEqual(coords, [x1 + tilt, bottom, x1 - tilt, top,
                                  x2 - tilt, top, x2 + tilt, bottom])

    def test_contiguous_different_values_get_a_zero_width_transition(self):
        ## No gap between the segments: the polygon collapses to the single
        ## slanted edge an I/O signal draws when min and max delays agree.
        _, canvas, _ = self._draw([(-INF, 5.0, "0"), (5.0, INF, "1")])
        polys = canvas.tagged("_transition")
        self.assertEqual(len(polys), 1)
        coords, _ = polys[0]
        x = canvas.time_to_x(5.0)
        self.assertEqual(coords[0], x - self.TILT)
        self.assertEqual(coords[4], x + self.TILT)

    def test_unknown_segment_is_a_stippled_hexagon(self):
        _, canvas, _ = self._draw([(-INF, 2.0, "0"), (2.0, 4.0, "X"),
                                   (4.0, INF, "1")])
        unknown = canvas.tagged("_unknown")
        self.assertEqual(len(unknown), 1)
        coords, _ = unknown[0]
        x1, x2 = canvas.time_to_x(2.0), canvas.time_to_x(4.0)
        mid = self.TOP + self.AMP / 2
        ## Pointed at both ends (mid-height points at x1 and x2).
        self.assertIn([x2, mid], [coords[i:i + 2] for i in range(0, len(coords), 2)])
        self.assertIn([x1, mid], [coords[i:i + 2] for i in range(0, len(coords), 2)])
        ## Two transitions: into and out of the unknown window.
        self.assertEqual(len(canvas.tagged("_transition")), 2)
        ## Styled as I/O unknowns are.
        self.assertIn(("q_unknown", {"stipple": "gray50", "outline": "black",
                                     "width": 2}), canvas.configured)

    def test_bus_segment_uses_the_valid_tag(self):
        _, canvas, _ = self._draw([(-INF, INF, "D")])
        self.assertEqual(len(canvas.tagged("_valid")), 1)

    def test_segment_cut_by_the_left_margin_is_squared_off(self):
        _, canvas, _ = self._draw([(-INF, 3.0, "X"), (3.0, INF, "0")])
        coords, _ = canvas.tagged("_unknown")[0]
        ## Starts flat at x0 (no pointed end into the name margin).
        self.assertEqual(coords[0], canvas.x0)
        self.assertNotIn(canvas.x0 - self.TILT, coords)

    def test_segments_beyond_the_right_bound_are_dropped(self):
        ## The clock spans 100 time units; a change at t=500 is off-diagram.
        _, canvas, _ = self._draw([(-INF, 500.0, "1"), (500.0, INF, "0")])
        self.assertEqual(len(canvas.tagged("_highvalid")), 1)
        self.assertEqual(len(canvas.tagged("_lowvalid")), 0)
        self.assertEqual(len(canvas.tagged("_transition")), 0)

    def test_right_bound_comes_from_the_longest_clock_not_the_widget(self):
        ## A never laid out canvas reports width 1 (the virtual canvas case).
        canvas = self._canvas(clocks=(FakeClock(10.0, 4), FakeClock(5.0, 20)),
                              width=1, is_virtual=True)
        _, canvas, _ = self._draw([(-INF, INF, "1")], canvas)
        coords, _ = canvas.tagged("_highvalid")[0]
        self.assertEqual(coords[2], canvas.time_to_x(100.0))

    def test_without_any_clock_the_widget_width_is_used(self):
        canvas = self._canvas(clocks=(), width=800)
        _, canvas, _ = self._draw([(-INF, INF, "1")], canvas)
        coords, _ = canvas.tagged("_highvalid")[0]
        self.assertEqual(coords[2], 800 - FakeSettings.waveform["right_padding"])

    def test_hidden_signal_consumes_no_height_on_the_visible_canvas(self):
        height, canvas, _ = self._draw([(-INF, INF, "1")], visible=False)
        self.assertEqual(height, 0)
        self.assertIn(("q_waveform", {"state": "hidden"}), canvas.configured)

    def test_hidden_signal_is_still_drawn_on_the_virtual_canvas(self):
        canvas = self._canvas(is_virtual=True)
        height, canvas, _ = self._draw([(-INF, INF, "1")], canvas, visible=False)
        self.assertEqual(height, self.AMP)

    def test_top_padding_is_added(self):
        canvas = self._canvas()
        sig = ConstantDerived("q", [(-INF, INF, "1")])
        sig.visible = True
        sig.top_padding = 7
        self.assertEqual(sig.draw(canvas, self.TOP), self.AMP + 7)
        coords, _ = canvas.tagged("_highvalid")[0]
        self.assertEqual(coords[1], self.TOP + 7)

    def test_every_item_carries_a_selectable_uid_tag(self):
        _, canvas, sig = self._draw([(-INF, 2.0, "0"), (4.0, INF, "1")])
        for _, tags in canvas.of_kind("line") + canvas.of_kind("polygon"):
            self.assertTrue(any(t.startswith(f"uid_{sig.uid}_") for t in tags))


if __name__ == "__main__":
    unittest.main()
