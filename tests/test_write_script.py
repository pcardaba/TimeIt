# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2024 Pablo Cardaba

"""The write_script command: the save path exposed to the console/socket."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from TimeIt.tests.apphelper import AppTestCase, SCRIPTS, strip_comments


class TestWriteScript(AppTestCase):

    def setUp(self) -> None:
        super().setUp()
        self.tmp = tempfile.TemporaryDirectory(prefix="timeit_ws_")
        self.dir = Path(self.tmp.name)

    def tearDown(self) -> None:
        self.tmp.cleanup()
        super().tearDown()

    def test_writes_the_save_format_and_becomes_current(self):
        self.source(SCRIPTS / "SPI_CPOL0_CPHA0.tcl")
        out = self.dir / "saved.tcl"
        self.tcl("write_script -file {" + str(out) + "}")
        self.assertNoErrors()
        self.assertEqual(strip_comments(out.read_text(encoding="utf-8")),
                         strip_comments(self.write_script()))
        self.assertEqual(self.app._file_path, str(out))
        self.assertIn("saved.tcl", self.root.title())
        self.assertFalse(self.app._session_modified())
        ## The written file reloads into the same diagram.
        self.tcl("remove -all")
        self.source(out)
        self.assertRoundTrips()

    def test_bare_rewrites_the_current_file(self):
        out = self.dir / "cur.tcl"
        self.tcl("create_clock -name clk -topology source -period {10} -rise_at {0} -fall_at {5} -show 4 -visible")
        self.tcl("write_script -file {" + str(out) + "}")
        self.tcl("create_input -name d -launch_clock clk -high_edges {2P} -low_edges {0} -visible")
        self.assertTrue(self.app._session_modified())
        self.tcl("write_script")
        self.assertNoErrors()
        self.assertIn("create_input -name d", out.read_text(encoding="utf-8"))
        self.assertFalse(self.app._session_modified())

    def test_bare_without_current_file_is_an_error(self):
        self.tcl("write_script")
        self.assertError("no current file")

    def test_copy_leaves_the_current_file_alone(self):
        cur = self.dir / "cur.tcl"
        copy = self.dir / "copy.tcl"
        self.tcl("create_clock -name clk -topology source -period {10} -rise_at {0} -fall_at {5} -show 4 -visible")
        self.tcl("write_script -file {" + str(cur) + "}")
        self.tcl("create_input -name d -launch_clock clk -high_edges {2P} -low_edges {0} -visible")
        self.tcl("write_script -file {" + str(copy) + "} -copy")
        self.assertNoErrors()
        self.assertIn("create_input -name d", copy.read_text(encoding="utf-8"))
        self.assertEqual(self.app._file_path, str(cur))
        self.assertTrue(self.app._session_modified())   # still unsaved in cur
        self.tcl("write_script -copy")
        self.assertError("-copy needs -file")

    def test_unwritable_path_is_reported(self):
        self.tcl("write_script -file {" + str(self.dir / "nodir" / "x.tcl") + "}")
        self.assertError("Error: ")

    def test_command_is_not_written_back(self):
        out = self.dir / "s.tcl"
        self.tcl("write_script -file {" + str(out) + "}")
        self.assertNotIn("write_script", out.read_text(encoding="utf-8"))

    def test_help_and_listing(self):
        self.tcl("write_script -help")
        self.assertNoErrors()
        self.tcl("help")
        self.assertIn("  write_script\n", "".join(t for _, t in self.log))


if __name__ == "__main__":
    unittest.main()
