# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2024 Pablo Cardaba

"""Unit tests for LogicSignal, using fake operands (no Tk)."""

import io
import math
import unittest

from TimeIt.classes.logicsignal import LogicSignal
from TimeIt.tests.test_derivedsignal import FakeConsole, FakeOperand

INF = math.inf


def const(name, value, **kw):
    state = {"0": "low", "1": "high", "X": "unknown"}[value]
    return FakeOperand(name, [(-INF, INF, state)], **kw)


class TestLogicSignal(unittest.TestCase):

    def _signal(self, op, *inputs, values=None, **attrs):
        sig = LogicSignal("q")
        sig.op = op
        sig.inputs = list(inputs)
        sig.console = FakeConsole(values)
        for key, value in attrs.items():
            setattr(sig, key, value)
        return sig

    def test_and_of_two_operands(self):
        a = FakeOperand("a", [(-INF, 2.0, "low"), (2.0, INF, "high")])
        b = const("b", "1")
        self.assertEqual(self._signal("and", a, b).timeline(),
                         [(-INF, 2.0, "0"), (2.0, INF, "1")])

    def test_three_input_or(self):
        a = FakeOperand("a", [(-INF, 2.0, "low"), (2.0, INF, "high")])
        self.assertEqual(self._signal("or", a, const("b", "0"), const("c", "0")).timeline(),
                         [(-INF, 2.0, "0"), (2.0, INF, "1")])

    def test_nand_and_nor(self):
        self.assertEqual(self._signal("nand", const("a", "1"), const("b", "X")).timeline(),
                         [(-INF, INF, "X")])
        self.assertEqual(self._signal("nand", const("a", "0"), const("b", "X")).timeline(),
                         [(-INF, INF, "1")])
        self.assertEqual(self._signal("nor", const("a", "1"), const("b", "X")).timeline(),
                         [(-INF, INF, "0")])

    def test_not_of_one_operand(self):
        self.assertEqual(self._signal("not", const("a", "1")).timeline(),
                         [(-INF, INF, "0")])

    def test_transition_window_of_an_operand_is_unknown_unless_masked(self):
        a = FakeOperand("a", [(-INF, 2.0, "low"), (4.0, INF, "high")])
        self.assertEqual(self._signal("and", a, const("b", "1")).timeline(),
                         [(-INF, 2.0, "0"), (2.0, 4.0, "X"), (4.0, INF, "1")])
        self.assertEqual(self._signal("and", a, const("b", "0")).timeline(),
                         [(-INF, INF, "0")])

    def test_single_tpd_shifts_the_result(self):
        a = FakeOperand("a", [(-INF, 2.0, "low"), (2.0, INF, "high")])
        sig = self._signal("not", a, values={"$tpd": 1.5}, tpd_max="$tpd")
        self.assertEqual(sig.timeline(), [(-INF, 3.5, "1"), (3.5, INF, "0")])

    def test_tpd_spread_opens_a_transition_window(self):
        a = FakeOperand("a", [(-INF, 2.0, "low"), (2.0, INF, "high")])
        sig = self._signal("not", a, values={"$tmax": 3.0, "$tmin": 1.0},
                           tpd_max="$tmax", tpd_min="$tmin")
        self.assertEqual(sig.timeline(), [(-INF, 3.0, "1"), (5.0, INF, "0")])

    def test_blank_tpd_min_means_pure_shift(self):
        a = FakeOperand("a", [(-INF, 2.0, "low"), (2.0, INF, "high")])
        sig = self._signal("not", a, values={"$t": 1.0}, tpd_max="$t", tpd_min=" ")
        self.assertEqual(sig.timeline(), [(-INF, 3.0, "1"), (3.0, INF, "0")])

    def test_min_above_max_is_logged_and_gives_none(self):
        sig = self._signal("not", const("a", "1"), values={"$a": 1.0, "$b": 2.0},
                           tpd_max="$a", tpd_min="$b")
        self.assertIsNone(sig.timeline())
        self.assertTrue(any("minimum delay" in e for e in sig.console.errors))

    def test_unresolvable_expression_is_logged_and_gives_none(self):
        sig = self._signal("not", const("a", "1"), tpd_max="$nosuchvar")
        self.assertIsNone(sig.timeline())
        self.assertTrue(sig.console.errors)

    def test_hiz_operand_honours_pull_up(self):
        z = FakeOperand("z", [(-INF, INF, "hiz")], pulled_up=True)
        self.assertEqual(self._signal("and", z, const("b", "1")).timeline(),
                         [(-INF, INF, "1")])
        floating = FakeOperand("z", [(-INF, INF, "hiz")])
        self.assertEqual(self._signal("and", floating, const("b", "1")).timeline(),
                         [(-INF, INF, "X")])

    def test_unresolvable_operand_gives_none(self):
        self.assertIsNone(self._signal("and", FakeOperand("a", None),
                                       const("b", "1")).timeline())

    def test_operands_skip_missing_entries(self):
        sig = self._signal("and", const("a", "1"), None)
        self.assertEqual([o.name for o in sig.operands()], ["a"])

    def test_write_emits_the_create_logic_command(self):
        sig = self._signal("nor", const("req", "0"), const("ack", "0"),
                           tpd_max="$tmax", tpd_min="$tmin")
        sig.visible = True
        buffer = io.StringIO()
        sig.write(buffer)
        text = buffer.getvalue()
        self.assertIn("create_logic -name q", text)
        self.assertIn("-op nor", text)
        self.assertIn("-inputs {req ack}", text)
        self.assertIn("-tpd_max {$tmax}", text)
        self.assertIn("-tpd_min {$tmin}", text)
        self.assertIn(f"-use_uid {sig.uid}", text)
        self.assertIn("-visible", text)

    def test_write_omits_absent_delays(self):
        sig = self._signal("not", const("a", "1"))
        buffer = io.StringIO()
        sig.write(buffer)
        self.assertNotIn("-tpd", buffer.getvalue())


if __name__ == "__main__":
    unittest.main()
