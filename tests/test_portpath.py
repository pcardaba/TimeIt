# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2024 Pablo Cardaba

"""portpath: file names in scripts that work on every system."""

from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path

from TimeIt.classes import portpath


class TestNormalize(unittest.TestCase):

    def test_backslashes_become_slashes(self):
        self.assertEqual(portpath.normalize(r"pwl\vdd.pwl"), "pwl/vdd.pwl")
        self.assertEqual(portpath.normalize(r"C:\work\pwl\vdd.pwl"),
                         "C:/work/pwl/vdd.pwl")

    def test_repeated_separators_folded_unc_kept(self):
        self.assertEqual(portpath.normalize("pwl//sub///a.pwl"), "pwl/sub/a.pwl")
        self.assertEqual(portpath.normalize(r"\\server\share\a.pwl"),
                         "//server/share/a.pwl")

    def test_blanks_stripped_relative_kept(self):
        self.assertEqual(portpath.normalize("  ../pwl/a.pwl "), "../pwl/a.pwl")

    def test_absolute_of_any_system(self):
        for name in ("/home/me/a.pwl", "~/a.pwl", "C:/a.pwl", r"c:\a.pwl",
                     r"\\server\share\a.pwl"):
            self.assertTrue(portpath.is_absolute(name), name)
        for name in ("a.pwl", "pwl/a.pwl", r"..\a.pwl", "C:a.pwl"):
            self.assertFalse(portpath.is_absolute(name), name)


class TestLocate(unittest.TestCase):

    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory(prefix="timeit_pp_")
        self.base = Path(self.tmp.name)
        (self.base / "pwl").mkdir()
        self.vdd = self.base / "pwl" / "vdd.pwl"
        self.vdd.write_text("0 0\n1 1\n", encoding="utf-8")

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def test_relative_to_base_any_separator(self):
        for name in ("pwl/vdd.pwl", r"pwl\vdd.pwl", "./pwl//vdd.pwl"):
            path, relocated = portpath.locate(name, self.base)
            self.assertEqual(path, self.vdd, name)
            self.assertFalse(relocated)

    def test_absolute_found_where_it_points(self):
        path, relocated = portpath.locate(str(self.vdd), "/nowhere")
        self.assertEqual(path, self.vdd)
        self.assertFalse(relocated)

    def test_foreign_absolute_found_by_its_tail(self):
        for name in (r"C:\Users\me\proj\pwl\vdd.pwl",
                     "/home/me/proj/pwl/vdd.pwl",
                     r"\\server\share\proj\pwl\vdd.pwl"):
            path, relocated = portpath.locate(name, self.base)
            self.assertEqual(path, self.vdd, name)
            self.assertTrue(relocated)

    def test_case_mismatch_found(self):
        path, relocated = portpath.locate("PWL/VDD.pwl", self.base)
        self.assertEqual(path.name.casefold(), "vdd.pwl")
        self.assertTrue(path.is_file())

    def test_missing_returns_the_literal_place(self):
        path, relocated = portpath.locate("pwl/none.pwl", self.base)
        self.assertEqual(path, self.base / "pwl" / "none.pwl")
        self.assertFalse(relocated)
        self.assertFalse(path.exists())

    def test_no_base_is_the_working_directory(self):
        path = portpath.resolve("x/y.pwl")
        self.assertEqual(path, Path(os.path.abspath("x/y.pwl")))


class TestForScript(unittest.TestCase):

    def test_relative_with_slashes(self):
        base = os.path.abspath(os.path.join("proj", "diagrams"))
        target = os.path.join(base, "pwl", "vdd.pwl")
        self.assertEqual(portpath.for_script(target, base), "pwl/vdd.pwl")
        up = os.path.join(os.path.dirname(base), "pwl", "vdd.pwl")
        self.assertEqual(portpath.for_script(up, base), "../pwl/vdd.pwl")

    def test_absolute_without_base(self):
        target = os.path.abspath(os.path.join("pwl", "vdd.pwl"))
        written = portpath.for_script(target, None)
        self.assertNotIn("\\", written)
        self.assertTrue(portpath.is_absolute(written))

    def test_round_trip_through_locate(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "sub dir" / "a.pwl"
            target.parent.mkdir()
            target.write_text("0 0\n", encoding="utf-8")
            base = Path(tmp) / "diagrams"
            name = portpath.for_script(target, base)
            self.assertEqual(name, "../sub dir/a.pwl")
            self.assertEqual(portpath.resolve(name, base), target)


if __name__ == "__main__":
    unittest.main()
