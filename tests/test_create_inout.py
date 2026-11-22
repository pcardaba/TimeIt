# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2024 Pablo Cardaba

"""Integration tests of the create_inout command (bidirectional signals)."""

from __future__ import annotations

import math
import tempfile
import unittest
from pathlib import Path

from TimeIt.classes.inoutsignal import InOutSignal
from TimeIt.tests.apphelper import AppTestCase, REPO, SCRIPTS

INF = math.inf

## A 20 ns clock, a related divided clock and an unrelated one.
BASE = """
remove -all
set_app_var -name timings.tCLK -value {20}
create_clock -name clk -topology source -period {$tCLK} -rise_at {0} \\
   -fall_at {$tCLK/2} -show 10 -visible
create_clock -name clk2 -topology clockout -master clk -divide_by 2 -visible
create_clock -name other -topology source -period {30} -rise_at {0} \\
   -fall_at {15} -show 6 -visible
"""

## The device drives two words, releases the bus at 3P; after a turnaround
## cycle the other end drives three words and releases it at 7P; the device
## drives again at 8P. Internal delays: the output part runs forward from its
## launch edges (2..5, output enable 1..3), the input part is established 4
## before, and held 1 after, the rising edges capturing it.
BUS = """
create_inout -name dq -specify internal \\
   -in_launch_clock clk -rclk_inputdly_max {4} -rclk_inputdly_min {-1} \\
   -in_hiz_edges {0 7P} -in_data_edges {4P 5P 6P} \\
   -out_launch_clock clk -rclk_outputdly_max {5} -rclk_outputdly_min {2} \\
   -rclk_oedly_max {3} -rclk_oedly_min {1} \\
   -out_hiz_edges {0 3P} -out_data_edges {1P 2P 8P} -visible
"""


class InOutTestCase(AppTestCase):

    def setUp(self):
        super().setUp()
        self.tcl(BASE)
        self.clear_log()

    def warnings(self):
        return [text for tag, text in self.log if tag == "warning"]

    def items(self, canvas, tag):
        """(uid tag, x1, x2) of the items of `canvas` carrying `tag`."""
        out = []
        for item in canvas.find_withtag(tag):
            uid = next(t for t in canvas.gettags(item) if t.startswith("uid_"))
            xs = canvas.coords(item)[0::2]
            out.append((uid, min(xs), max(xs)))
        return out


class TestCreateInout(InOutTestCase):

    # -- the command ------------------------------------------------------

    def test_creates_a_bidirectional_signal(self):
        self.tcl(BUS)
        self.assertNoErrors()
        self.assertEqual(self.warnings(), [])
        dq = self.app.signals.find("dq")
        self.assertIsInstance(dq, InOutSignal)
        self.assertEqual(dq.type, "inout")
        self.assertEqual(dq.specify, "internal")
        self.assertEqual(dq.in_data_edges, ["4P", "5P", "6P"])
        self.assertEqual(dq.out_hiz_edges, ["0", "3P"])
        self.assertEqual(dq.rclk_oedly_max, "3")
        ## A single clock of a part both launches and captures.
        clk = self.app.signals.find("clk")
        self.assertIs(dq.in_capture_clock, clk)
        self.assertIs(dq.out_capture_clock, clk)
        self.assertEqual(dq.related_clocks(), (clk,))
        self.assertSignals("clk", "clk2", "other", "dq")

    def test_is_a_registered_command_with_help(self):
        self.assertIn("create_inout", self.app.console.tcl_commands.command_names())
        self.assertIn("create_inout", self.app.console.commands)
        self.assertTrue((REPO / "data" / "create_inout.help.txt").is_file())
        self.tcl("create_inout -help")
        self.assertNoErrors()
        self.assertTrue(any("-in_launch_clock" in text for _tag, text in self.log))
        self.assertIsNone(self.app.signals.find("-help"))

    def test_the_parts_do_not_use_up_uids(self):
        self.tcl(BUS)
        self.tcl("create_input -name after -launch_clock clk -high_edges {2P} -low_edges {0}")
        dq = self.app.signals.find("dq")
        self.assertEqual(self.app.signals.find("after").uid, dq.uid + 1)
        self.assertEqual(dq.inpart.uid, dq.uid)

    def test_validation(self):
        cases = (
            ("create_inout -in_launch_clock clk -out_launch_clock clk",
             "-name is required"),
            ("create_inout -name x -out_launch_clock clk",
             "-in_launch_clock and/or -in_capture_clock is required"),
            ("create_inout -name x -in_launch_clock clk",
             "-out_launch_clock and/or -out_capture_clock is required"),
            ("create_inout -name x -in_launch_clock clk -in_capture_clock other "
             "-out_launch_clock clk", "are not related"),
            ("create_inout -name x -in_launch_clock clk -out_launch_clock other",
             "must all share the same source clock"),
            ("create_inout -name x -in_launch_clock nosuch -out_launch_clock clk",
             "nosuch clock not found"),
            ("create_inout -name x -specify both -in_launch_clock clk "
             "-out_launch_clock clk", "both is not a valid value for -specify"),
            ("create_inout -name x -in_launch_clock clk -out_launch_clock clk "
             "-data_edges {1P}", "Unknown -data_edges option"),
        )
        for command, fragment in cases:
            with self.subTest(command=command):
                self.clear_log()
                self.tcl(command)
                self.assertError(fragment)
                self.assertIsNone(self.app.signals.find("x"))

    def test_related_clocks_may_differ(self):
        self.tcl("create_inout -name x -in_launch_clock clk -in_capture_clock clk2 "
                 "-out_launch_clock clk2 -in_hiz_edges {0} -out_hiz_edges {0} -visible")
        self.assertNoErrors()
        x = self.app.signals.find("x")
        self.assertEqual([c.name for c in x.related_clocks()], ["clk", "clk2"])

    # -- save / load ------------------------------------------------------

    def test_round_trips(self):
        self.tcl(BUS)
        self.tcl("create_inout -name sda -specify external -pulled_up -hide_contention "
                 "-in_launch_clock clk -in_capture_clock clk2 "
                 "-fclk_inputdly_max {$tCLK/4} -fclk_inputdly_min {1} "
                 "-in_hiz_edges {0 5N} -in_low_edges {4N} -in_unknown_edges {6N} "
                 "-out_launch_clock clk2 -out_capture_clock clk "
                 "-fclk_outputdly_max {3} -fclk_outputdly_min {-1} "
                 "-out_hiz_edges {0 2N} -out_low_edges {1N} -out_high_edges {3N} "
                 "-color blue -amplitude 30 -lwidth 3")
        self.tcl("set_attribute -signal dq -name top_padding -value 12")
        self.assertNoErrors()
        script = self.write_script()
        self.assertIn("create_inout -name dq", script)
        self.assertIn("-in_capture_clock clk2", script)
        self.assertIn("-pulled_up", script)
        self.assertIn("-hide_contention", script)
        self.clear_log()
        self.assertRoundTrips()
        sda = self.app.signals.find("sda")
        self.assertTrue(sda.pulled_up)
        self.assertTrue(sda.hide_contention)
        self.assertFalse(sda.visible)
        self.assertEqual(sda.in_unknown_edges, ["6N"])
        self.assertEqual(self.app.signals.find("dq").top_padding, 12)

    def test_internal_only_options_round_trip(self):
        self.tcl("create_inout -name x -specify internal -in_launch_clock clk "
                 "-rclk_inputdly_max {4} -rclk_inputdly_min {1} "
                 "-in_rclk_latency_max {0.5} -in_rclk_latency_min {0.2} "
                 "-in_hiz_edges {0} -out_launch_clock clk "
                 "-out_fclk_latency_max {0.3} -out_fclk_latency_min {0.1} "
                 "-fclk_oedly_max {2} -fclk_oedly_min {1} -out_hiz_edges {0} -visible")
        self.assertNoErrors()
        x = self.app.signals.find("x")
        self.assertEqual(x.inpart.rclk_latency_max, "0.5")
        self.assertEqual(x.outpart.fclk_latency_min, "0.1")
        self.assertEqual(x.outpart.fclk_oedly_max, "2")
        self.assertRoundTrips()

    def test_the_example_script_loads_and_round_trips(self):
        self.source(SCRIPTS / "bidir_example.tcl")
        self.assertNoErrors()
        self.assertIsInstance(self.app.signals.find("SDIO"), InOutSignal)
        self.assertEqual(self.app.signals.find("SDIO").contention_zones(), [])
        self.assertTrue(self.app.signals.find("SDIO_bad").contention_zones())
        self.clear_log()
        self.assertRoundTrips()

    # -- redefinition -----------------------------------------------------

    def test_reissuing_the_command_redefines_the_signal(self):
        self.tcl(BUS)
        dq = self.app.signals.find("dq")
        self.tcl("create_inout -name dq -specify external -in_launch_clock clk2 "
                 "-in_hiz_edges {0} -out_launch_clock clk2 -out_hiz_edges {0 2P} "
                 "-out_low_edges {1P} -visible")
        self.assertNoErrors()
        self.assertIs(self.app.signals.find("dq"), dq)
        self.assertEqual(dq.specify, "external")
        self.assertEqual(dq.in_data_edges, [])
        self.assertIsNone(dq.rclk_inputdly_max)
        self.assertIsNone(dq.rclk_oedly_max)
        self.assertEqual(dq.out_low_edges, ["1P"])
        ## It no longer goes with the clock it left.
        clk, clk2 = (self.app.signals.find(n) for n in ("clk", "clk2"))
        self.assertNotIn(dq, clk.get_related_objs())
        self.assertIn(dq, clk2.get_related_objs())

    def test_replaces_a_signal_of_another_type(self):
        self.tcl("create_output -name dq -launch_clock clk -data_edges {1P} "
                 "-hiz_edges {0} -visible")
        old = self.app.signals.find("dq")
        self.tcl(BUS)
        self.assertNoErrors()
        self.assertIsInstance(self.app.signals.find("dq"), InOutSignal)
        self.assertIsNot(self.app.signals.find("dq"), old)

    def test_is_not_redefined_by_create_input_or_create_output(self):
        self.tcl(BUS)
        for command in ("create_input", "create_output"):
            self.clear_log()
            self.tcl(f"{command} -name dq -launch_clock clk -data_edges {{1P}}")
            self.assertError("dq is a bidirectional signal")
        self.assertEqual(self.app.signals.find("dq").in_data_edges,
                         ["4P", "5P", "6P"])

    def test_a_signal_read_by_a_logic_signal_is_not_replaced(self):
        self.tcl("create_input -name a -launch_clock clk -high_edges {2P} -low_edges {0}")
        self.tcl("create_input -name b -launch_clock clk -high_edges {3P} -low_edges {0}")
        self.tcl("create_logic -name y -inputs {a b}")
        self.clear_log()
        self.tcl("create_inout -name a -in_launch_clock clk -out_launch_clock clk")
        self.assertError("a is read by y")
        self.assertEqual(self.app.signals.find("a").type, "input")

    def test_set_attribute_reaches_the_parts(self):
        self.tcl(BUS)
        self.tcl("set_attribute -signal dq -name rclk_outputdly_max -value {7}")
        self.tcl("set_attribute -signal dq -name pulled_up -value true")
        self.tcl("set_attribute -signal dq -name hide_contention -value true")
        self.assertNoErrors()
        dq = self.app.signals.find("dq")
        self.assertEqual(dq.outpart.rclk_outputdly_max, "7")
        self.assertTrue(dq.pulled_up)
        self.assertTrue(dq.outpart.pulled_up)
        self.assertIn("-rclk_outputdly_max {7}", self.write_script())

    # -- relationships ----------------------------------------------------

    def test_goes_with_its_clocks(self):
        self.tcl("create_inout -name x -in_launch_clock clk -out_launch_clock clk2 "
                 "-in_hiz_edges {0} -out_hiz_edges {0} -visible")
        clk2 = self.app.signals.find("clk2")
        self.tcl(f"remove -signal {clk2.uid}")
        self.assertNoErrors()
        self.assertSignals("clk", "other")

    def test_stays_below_its_clocks(self):
        self.tcl("create_clock -name late -topology clockout -master clk -divide_by 4 -visible")
        self.tcl("create_inout -name x -in_launch_clock clk -out_launch_clock late "
                 "-in_hiz_edges {0} -out_hiz_edges {0} -visible")
        self.clear_log()
        self.tcl("move_signal -name x -direction up")
        self.assertError("can not be moved above a signal it refers to")
        self.assertSignals("clk", "clk2", "other", "late", "x")

    def test_can_not_gate_a_clock(self):
        self.tcl("create_inout -name en -in_launch_clock clk -out_launch_clock clk "
                 "-in_hiz_edges {0} -out_low_edges {0} -out_high_edges {2P}")
        self.clear_log()
        self.tcl("set_attribute -signal clk2 -name enabled_by -value en")
        self.assertError("is not an input/output signal")

    def test_feeds_a_logic_signal(self):
        self.tcl("create_input -name en -specify external -launch_clock clk "
                 "-high_edges {0}")
        ## The device holds the line low until 2P, the other end drives it
        ## high from 4P.
        self.tcl("create_inout -name io -specify external "
                 "-in_launch_clock clk -in_hiz_edges {0} -in_high_edges {4P} "
                 "-out_launch_clock clk -rclk_outputdly_max {18} "
                 "-rclk_outputdly_min {0} -out_low_edges {0} -out_hiz_edges {2P}")
        self.tcl("create_logic -name y -op and -inputs {io en} -visible")
        self.assertNoErrors()
        self.assertEqual(self.warnings(), [])
        io = self.app.signals.find("io")
        self.assertEqual(io.state_intervals(),
                         [(-INF, 20.0, "low"), (22.0, 60.0, "hiz"),
                          (60.0, INF, "high")])
        self.assertEqual(self.app.signals.find("y").state_intervals(),
                         [(-INF, 20.0, "low"), (20.0, 60.0, "unknown"),
                          (60.0, INF, "high")])

    def test_bus_data_can_not_feed_a_logic_signal(self):
        self.tcl(BUS)
        self.tcl("create_input -name en -launch_clock clk -high_edges {0}")
        self.clear_log()
        self.tcl("create_logic -name y -inputs {dq en}")
        self.assertError("dq carries bus data")


class TestInoutDrawing(InOutTestCase):

    def test_one_slot_and_the_tags_of_an_io_signal(self):
        self.tcl(BUS)
        canvas = self.app.canvas
        dq = self.app.signals.find("dq")
        self.assertEqual(len(canvas.find_withtag("dq_label")), 1)
        self.assertEqual([sig.name for _top, _bottom, sig in canvas.slots][-1], "dq")
        ## Three words driven by each part, and every change (three words and
        ## a release each) is a transition the quick selection can reach.
        self.assertEqual(len(canvas.find_withtag("dq_valid")), 6)
        transitions = [item for item in canvas.find_withtag("transitions")
                       if any(t.startswith(f"uid_{dq.uid}_")
                              for t in canvas.gettags(item))]
        self.assertEqual(len(transitions), 8)
        ## No two elements share a uid tag.
        uids = [uid for uid, _x1, _x2 in self.items(canvas, "dq_waveform")]
        self.assertEqual(len(uids), len(set(uids)))

    def test_hiz_is_only_drawn_where_no_part_drives(self):
        self.tcl(BUS)
        canvas = self.app.canvas
        lines = self.items(canvas, "dq_hizvalid")
        ## Before the first word, the turnaround after 3P, the one after 7P.
        ## By themselves the parts would draw two lines each, running under
        ## the words of the other part.
        self.assertEqual(len(lines), 3)
        driven = self.items(canvas, "dq_valid") + self.items(canvas, "dq_transition")
        for _uid, x1, x2 in lines:
            for _other, d1, d2 in driven:
                self.assertFalse(x1 < d2 - 3 and d1 + 3 < x2,
                                 f"Hi-Z {x1}..{x2} runs under {d1}..{d2}")
        ## The turnaround: from the end of the release (3P + 3) to where the
        ## input may start changing (the hold bound after 4P: 4P + 1). Then
        ## from the input released (setup bound before 8P) to the device
        ## driving again (8P + 1).
        times = [(round(canvas.x_to_time(x1)), round(canvas.x_to_time(x2)))
                 for _uid, x1, x2 in lines]
        self.assertEqual(times, [(0, 1), (43, 61), (136, 141)])

    def test_both_canvases_draw_the_same_elements(self):
        self.tcl(BUS)
        self.tcl("create_inout -name bad -specify internal -in_launch_clock clk "
                 "-in_hiz_edges {0 4P} -in_data_edges {2P} -out_launch_clock clk "
                 "-rclk_outputdly_max {5} -rclk_outputdly_min {2} "
                 "-out_hiz_edges {0 3P} -out_data_edges {1P} -visible")
        for name in ("dq", "bad"):
            for kind in ("hizvalid", "valid", "transition", "contention"):
                visible = [uid for uid, _a, _b
                           in self.items(self.app.canvas, f"{name}_{kind}")]
                virtual = [uid for uid, _a, _b
                           in self.items(self.app.vcanvas, f"{name}_{kind}")]
                self.assertEqual(visible, virtual, f"{name}_{kind}")

    def test_a_timing_marker_measures_the_turnaround(self):
        self.tcl(BUS)
        uid = self.items(self.app.canvas, "dq_hizvalid")[1][0]
        self.tcl(f"create_timing_marker -name tTA -from start:{uid} -to end:{uid}")
        self.assertNoErrors()
        self.assertEqual(self.app.settings.marker["timings"]["tTA"], "18.0ns")

    def test_hidden_signal_takes_no_slot(self):
        self.tcl(BUS.replace("-visible", ""))
        self.assertNoErrors()
        canvas = self.app.canvas
        self.assertNotIn("dq", [sig.name for _t, _b, sig in canvas.slots])
        self.assertIn("dq", canvas.hidden_signals)
        for item in canvas.find_withtag("dq_waveform"):
            self.assertEqual(canvas.itemcget(item, "state"), "hidden")

    def test_pulled_up_release_is_drawn_once(self):
        self.tcl("set_app_var -name settings.waveform.line_pullup -value {10}")
        self.tcl("create_inout -name sda -specify internal -pulled_up "
                 "-in_launch_clock clk -in_hiz_edges {0 7P} -in_low_edges {6P} "
                 "-out_launch_clock clk -out_hiz_edges {0 3P} -out_low_edges {1P} "
                 "-visible")
        self.assertNoErrors()
        canvas = self.app.canvas
        ## Released from the start to 1P, from 3P to 6P, and after 7P.
        self.assertEqual(len(self.items(canvas, "sda_hizvalid")), 3)
        self.assertEqual(len(canvas.find_withtag("sda_pu_transition")), 2)

    ## An I2C acknowledge after a "0" bit: the master releases SDA at 4N
    ## while the slave pulls it low from 4N. SCL falls at whole microseconds
    ## (4N is at 4000 ns); a 2 kohm pull-up on 100 pF rises in 1000 ns.
    ACK = """
    set_app_var -name settings.waveform.line_pullup -value {2000.0}
    create_clock -name scl -topology source -period {1000} -rise_at {500} \\
       -fall_at {1000} -show 6 -visible
    create_inout -name sda -specify external -pulled_up \\
       -in_launch_clock scl -fclk_inputdly_max {200} -fclk_inputdly_min {100} \\
       -in_hiz_edges {0 5N} -in_low_edges {%s} \\
       -out_launch_clock scl -fclk_outputdly_max {250} -fclk_outputdly_min {-50} \\
       -out_hiz_edges {0 2N 4N} -out_low_edges {1N 3N} -visible
    """

    def rises(self, canvas):
        """(first time, last time, hidden) of every pull-up rise of sda."""
        out = []
        for item in canvas.find_withtag("sda_pu_transition"):
            xs = canvas.coords(item)[0::2]
            out.append((round(canvas.x_to_time(min(xs)), 3),
                        round(canvas.x_to_time(max(xs)), 3),
                        canvas.itemcget(item, "state") == "hidden"))
        return sorted(out)

    def test_pullup_rise_stops_where_the_other_part_takes_the_line(self):
        self.tcl(self.ACK % "4N")
        self.assertNoErrors()
        ## The master releases from 4000 + 50 (external delays: its hold of
        ## 50 after the edge): by itself the line would rise up to 5050. The
        ## slave surely holds it low from 4000 + 200. The other two rises
        ## (master at 2N, slave at 5N) have nobody taking the line.
        self.assertEqual(self.rises(self.app.vcanvas),
                         [(2050.0, 3050.0, False), (4050.0, 4200.0, False),
                          (5100.0, 6100.0, False)])
        visible = self.rises(self.app.canvas)
        self.assertEqual(len(visible), 3)
        self.assertAlmostEqual(visible[1][1], 4200.0, delta=10.0)

    def test_no_rise_when_the_line_is_already_held_low(self):
        ## The slave already holds the line low (from 3N) when the master
        ## releases it: the line never rises. The element is kept, hidden,
        ## so that both canvases number the same elements.
        self.tcl(self.ACK % "3N")
        self.assertNoErrors()
        rises = self.rises(self.app.vcanvas)
        self.assertEqual(rises[1][2], True)
        self.assertEqual(rises[1][0], rises[1][1])
        for canvas in (self.app.canvas, self.app.vcanvas):
            self.assertEqual(len(canvas.find_withtag("sda_pu_transition")), 3)
        ## A hidden rise can not be quick-selected.
        canvas = self.app.canvas
        hidden = [i for i in canvas.find_withtag("sda_pu_transition")
                  if canvas.itemcget(i, "state") == "hidden"]
        self.assertIsNone(canvas.bbox(hidden[0]))
        self.assertRoundTrips()


class TestInoutContention(InOutTestCase):

    ## No turnaround: the other end drives from 3P, where the device only
    ## starts releasing the bus (it may drive it until 3P + 3).
    CONTENTION = """
    create_inout -name dq -specify internal \\
       -in_launch_clock clk -rclk_inputdly_max {4} -rclk_inputdly_min {-1} \\
       -in_hiz_edges {0 5P} -in_data_edges {3P 4P} \\
       -out_launch_clock clk -rclk_outputdly_max {5} -rclk_outputdly_min {2} \\
       -rclk_oedly_max {3} -rclk_oedly_min {1} \\
       -out_hiz_edges {0 3P} -out_data_edges {1P 2P} -visible
    """

    def test_clean_definition_has_no_zone(self):
        self.tcl(BUS)
        dq = self.app.signals.find("dq")
        self.assertEqual(dq.contention_zones(), [])
        self.assertEqual(dq.definition_warnings(), [])
        self.assertEqual(self.app.canvas.find_withtag("dq_contention"), ())

    def test_overlap_is_a_zone_marked_and_warned(self):
        self.tcl(self.CONTENTION)
        self.assertNoErrors()
        dq = self.app.signals.find("dq")
        ## The input may change as soon as 1 after 3P (its hold bound), and
        ## the device may drive until 3 after 3P.
        self.assertEqual(dq.contention_zones(), [(41.0, 43.0)])
        zones = self.items(self.app.canvas, "dq_contention")
        self.assertEqual(len(zones), 1)
        _uid, x1, x2 = zones[0]
        self.assertAlmostEqual(self.app.canvas.x_to_time(x1), 41.0, places=6)
        self.assertAlmostEqual(self.app.canvas.x_to_time(x2), 43.0, places=6)
        warnings = self.warnings()
        self.assertEqual(len(warnings), 1)
        self.assertIn("dq: possible port contention", warnings[0])
        self.assertIn("from 41 to 43 ns", warnings[0])

    def test_the_warning_is_not_repeated_on_a_redraw(self):
        self.tcl(self.CONTENTION)
        self.clear_log()
        self.tcl("redraw")
        self.tcl("set_canvas_scale 3.0")
        self.assertEqual(self.warnings(), [])
        ## A change of the zones is told.
        self.tcl("set_attribute -signal dq -name rclk_oedly_max -value {6}")
        self.assertEqual(len(self.warnings()), 1)
        self.assertIn("from 41 to 46 ns", self.warnings()[0])

    def test_hide_contention_keeps_the_warning_only(self):
        self.tcl(self.CONTENTION.replace("-visible", "-visible -hide_contention"))
        self.assertEqual(self.app.canvas.find_withtag("dq_contention"), ())
        self.assertEqual(len(self.warnings()), 1)

    def test_handover_on_the_same_instant_is_not_a_contention(self):
        ## Both sides switch exactly 5 after 3P: a zero-length overlap.
        self.tcl("create_inout -name dq -specify external "
                 "-in_launch_clock clk -rclk_inputdly_max {5} -rclk_inputdly_min {5} "
                 "-in_hiz_edges {0} -in_data_edges {3P} "
                 "-out_launch_clock clk -rclk_outputdly_max {15} "
                 "-rclk_outputdly_min {-5} "
                 "-out_hiz_edges {3P} -out_data_edges {0} -visible")
        self.assertNoErrors()
        self.assertEqual(self.app.signals.find("dq").contention_zones(), [])

    def test_open_drain_low_against_low_is_not_a_contention(self):
        definition = ("create_inout -name sda -specify internal {pull} "
                      "-in_launch_clock clk -in_hiz_edges {{0 6P}} -in_low_edges {{2P}} "
                      "-out_launch_clock clk -out_hiz_edges {{0 4P}} "
                      "-out_low_edges {{1P}} -visible")
        self.tcl(definition.format(pull="-pulled_up"))
        self.assertEqual(self.app.signals.find("sda").contention_zones(), [])
        self.tcl(definition.format(pull=""))
        self.assertTrue(self.app.signals.find("sda").contention_zones())

    def test_a_part_without_edges_is_warned(self):
        self.tcl("create_inout -name dq -in_launch_clock clk -out_launch_clock clk "
                 "-out_hiz_edges {0} -out_data_edges {1P} -visible")
        self.assertNoErrors()
        warnings = self.app.signals.find("dq").definition_warnings()
        self.assertEqual(len(warnings), 1)
        self.assertIn("the input part has no launch edge", warnings[0])
        self.assertEqual(len(self.warnings()), 1)

    def test_the_port_is_unknown_where_both_drive(self):
        ## The other end drives low from 2P to 4P, right through the high
        ## level the device holds from 1P to 3P.
        self.tcl("create_inout -name io -specify external "
                 "-in_launch_clock clk -in_hiz_edges {0 4P} -in_low_edges {2P} "
                 "-out_launch_clock clk -rclk_outputdly_max {18} "
                 "-rclk_outputdly_min {0} -out_hiz_edges {0 3P} "
                 "-out_high_edges {1P} -visible")
        io = self.app.signals.find("io")
        self.assertEqual(io.state_intervals(),
                         [(-INF, 0.0, "hiz"), (2.0, 20.0, "high"),
                          (20.0, 40.0, "unknown"), (42.0, 60.0, "low"),
                          (60.0, INF, "hiz")])
        self.assertEqual(io.contention_zones(), [(20.0, 42.0)])


class TestInoutSdc(InOutTestCase):

    def write_sdc(self) -> str:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "out.sdc"
            self.tcl(f"write_sdc -file {{{path.as_posix()}}}")
            return path.read_text(encoding="utf-8")

    def test_an_input_and_an_output_delay_on_the_port(self):
        self.tcl("create_inout -name {dq<7:0>} -specify external "
                 "-in_launch_clock clk -rclk_inputdly_max {6} -rclk_inputdly_min {2} "
                 "-in_hiz_edges {0 6P} -in_data_edges {4P 5P} "
                 "-out_launch_clock clk -rclk_outputdly_max {4} "
                 "-rclk_outputdly_min {-1} "
                 "-out_hiz_edges {0 3P} -out_data_edges {1P 2P} -visible")
        self.clear_log()
        sdc = self.write_sdc()
        self.assertNoErrors()
        self.assertIn("set_input_delay -clock {clk} -max 6 -min 2 "
                      "[get_ports {dq<7:0>}]", sdc)
        self.assertIn("set_output_delay -clock {clk} -max 4 -min -1 "
                      "[get_ports {dq<7:0>}]", sdc)
        self.assertIn("Inout dq<7:0> : bidirectional port", sdc)
        self.assertNotIn("possible contention", sdc)
        self.assertTrue(any("0 input(s), 0 output(s), 1 inout(s))" in text
                            for _tag, text in self.log))

    def test_internal_delays_get_an_offset_per_part(self):
        self.tcl(BUS)
        sdc = self.write_sdc()
        self.assertNoErrors()
        self.assertIn("set dq_in_offset_P 20", sdc)
        self.assertIn("set dq_out_offset_P 20", sdc)
        self.assertIn("set_input_delay -clock {clk} -max "
                      "[expr {$dq_in_offset_P - (4)}] -min [expr {-(-1)}] "
                      "[get_ports {dq}]", sdc)
        ## The port is tri-stated: worst of the output and enable delays.
        self.assertIn("set_output_delay -clock {clk} -max "
                      "[expr {$dq_out_offset_P - max((5), (3))}] -min "
                      "[expr {-min((2), (1))}] [get_ports {dq}]", sdc)

    def test_contention_and_skipped_part_are_told(self):
        self.tcl(TestInoutContention.CONTENTION)
        self.tcl("create_inout -name half -in_launch_clock clk -out_launch_clock clk "
                 "-out_hiz_edges {0} -out_data_edges {1P} -visible")
        self.clear_log()
        sdc = self.write_sdc()
        self.assertIn("possible contention on this port (from 41 to 43 ns)", sdc)
        self.assertIn("WARNING: inout input part half skipped", sdc)
        self.assertIn("[get_ports {half}]", sdc)
        self.assertError("half (inout input part) skipped")
        self.assertTrue(any("2 inout(s), 1 skipped)" in text
                            for _tag, text in self.log))

    def test_hidden_signal_is_left_out(self):
        self.tcl(BUS.replace("-visible", ""))
        sdc = self.write_sdc()
        self.assertNotIn("get_ports {dq}", sdc)


if __name__ == "__main__":
    unittest.main()
