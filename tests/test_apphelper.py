# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2024 Pablo Cardaba

"""Smoke test of the integration harness itself.

Boots the application, loads one shipped example and checks the two things
every later integration test relies on: the log capture sees command errors,
and a saved diagram reloads into an identical diagram.
"""

from __future__ import annotations

import unittest

from TimeIt.tests.apphelper import AppTestCase, SCRIPTS, strip_comments


class TestAppHelper(AppTestCase):

    def test_example_loads_and_round_trips(self):
        self.source(SCRIPTS / "SPI_CPOL0_CPHA0.tcl")
        self.assertNoErrors()
        self.assertGreater(len(self.app.signals), 0)
        self.assertRoundTrips()

    def test_command_errors_are_captured(self):
        ## Command handlers report errors through the console log, not
        ## through exceptions: the harness has to see them there.
        self.tcl("create_input -name d -launch_clock nosuchclk")
        self.assertError("nosuchclk")
        self.assertSignals()

    def test_remove_all_empties_the_store(self):
        self.source(SCRIPTS / "SPI_CPOL0_CPHA0.tcl")
        self.tcl("remove -all")
        self.assertSignals()


class TestStripComments(unittest.TestCase):

    def test_drops_comment_lines_only(self):
        text = "# header\ncreate_clock -name c\n   # indented\nputs x"
        self.assertEqual(strip_comments(text), "create_clock -name c\nputs x")


if __name__ == "__main__":
    unittest.main()
