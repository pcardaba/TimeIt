# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2024 Pablo Cardaba

"""PWL file names are portable: a diagram written on one system (or in one
directory) loads on another, and a saved diagram names its files relative to
itself with "/" separators (see classes/portpath.py)."""

from __future__ import annotations

import os
import re
import shutil
import tempfile
from pathlib import Path

from TimeIt.tests.apphelper import AppTestCase, SCRIPTS

HEADER = "set_app_var -name settings.waveform.tunits -value {ns}\n"


def files_option(script: str) -> list[str]:
    """The -files lists of a saved script, in order."""
    return re.findall(r"-files \{(.*)\}", script)


class TestPwlPaths(AppTestCase):

    def setUp(self) -> None:
        super().setUp()
        self.tmp = tempfile.TemporaryDirectory(prefix="timeit_pwlpath_")
        self.dir = Path(self.tmp.name)
        self.proj = self.dir / "proj"
        shutil.copytree(SCRIPTS / "pwl", self.proj / "pwl")

    def tearDown(self) -> None:
        self.tmp.cleanup()
        super().tearDown()

    def write(self, name: str, body: str) -> Path:
        path = self.proj / name
        path.write_text(HEADER + body, encoding="utf-8")
        return path

    def trace(self, name: str):
        for sig in self.app.signals.values():
            if sig.type == "pwl" and sig.find_trace(name) is not None:
                return sig.find_trace(name)
        self.fail(f"no trace {name}")

    # ------------------------------------------------------------------
    def test_windows_separators_load(self):
        script = self.write("win.tcl",
                            "create_pwl -names {VDD IDD} "
                            r"-files {pwl\vdd.pwl {pwl\\idd.pwl}} -visible" "\n")
        self.app._load_script(str(script))
        self.assertNoErrors()
        self.assertEqual(Path(self.trace("VDD").resolved),
                         self.proj / "pwl" / "vdd.pwl")
        self.assertEqual(Path(self.trace("IDD").resolved),
                         self.proj / "pwl" / "idd.pwl")

    def test_tcl_escapes_still_apply(self):
        (self.proj / "my files").mkdir()
        shutil.copy(self.proj / "pwl" / "vdd.pwl", self.proj / "my files")
        script = self.write("esc.tcl",
                            "create_pwl -names {VDD} "
                            r"-files {my\ files\vdd.pwl}" "\n")
        self.app._load_script(str(script))
        self.assertNoErrors()
        self.assertEqual(Path(self.trace("VDD").resolved),
                         self.proj / "my files" / "vdd.pwl")

    def test_foreign_absolute_names_are_relocated(self):
        script = self.write("abs.tcl",
                            "create_pwl -names {VDD} "
                            r"-files {{C:\Users\me\proj\pwl\vdd.pwl}}" "\n"
                            "create_pwl -names {TEMP} "
                            "-files {/home/someone/proj/pwl/temp.pwl}\n")
        self.app._load_script(str(script))
        self.assertNoErrors()
        self.assertEqual(Path(self.trace("VDD").resolved),
                         self.proj / "pwl" / "vdd.pwl")
        notes = [text for tag, text in self.log if tag == "comment"]
        self.assertTrue(any("not found as given" in t for t in notes), notes)
        ## Saved back portable.
        self.tcl("write_script")
        saved = (self.proj / "abs.tcl").read_text(encoding="utf-8")
        self.assertEqual(files_option(saved),
                         ["{pwl/vdd.pwl}", "{pwl/temp.pwl}"])

    def test_saved_relative_to_the_new_location(self):
        script = self.write("a.tcl", "create_pwl -names {VDD} "
                                     "-files {pwl/vdd.pwl} -visible\n")
        self.app._load_script(str(script))
        other = self.dir / "elsewhere" / "deep"
        other.mkdir(parents=True)
        out = other / "b.tcl"
        self.tcl("write_script -file {" + str(out) + "}")
        self.assertNoErrors()
        saved = out.read_text(encoding="utf-8")
        self.assertEqual(files_option(saved), ["{../../proj/pwl/vdd.pwl}"])
        self.assertNotIn("\\", files_option(saved)[0])
        ## And it reloads from there.
        self.tcl("remove -all")
        self.app._load_script(str(out))
        self.assertNoErrors()
        self.assertEqual(Path(self.trace("VDD").resolved),
                         self.proj / "pwl" / "vdd.pwl")

    def test_console_names_relative_to_the_current_file(self):
        """The dialog runs create_pwl through the console: a loaded diagram
        is edited with the names it holds, whatever the working directory."""
        script = self.write("a.tcl", "create_pwl -names {VDD} "
                                     "-files {pwl/vdd.pwl} -visible\n")
        self.app._load_script(str(script))
        cwd = os.getcwd()
        os.chdir(self.dir)
        try:
            self.app.console.execute(
                "create_pwl -names {VDD} -files {pwl/idd.pwl} -use_uid "
                f"{self.app.signals.find('VDD').uid} -visible")
            self.app.console.execute(
                "set_attribute -signal {VDD} -name file -value {pwl\\temp.pwl}")
        finally:
            os.chdir(cwd)
        self.assertNoErrors()
        self.assertEqual(Path(self.trace("VDD").resolved),
                         self.proj / "pwl" / "temp.pwl")

    def test_undo_keeps_files_and_saves_relative(self):
        script = self.write("a.tcl", "create_pwl -names {VDD} "
                                     "-files {pwl/vdd.pwl} -visible\n")
        self.app._load_script(str(script))
        uid = self.app.signals.find("VDD").uid
        with self.app.undo.transaction():
            self.app.console.execute(
                f"create_pwl -names {{VDD}} -files {{pwl/idd.pwl}} "
                f"-use_uid {uid} -visible")
        self.app.undo.undo()
        self.root.update()
        self.assertNoErrors()
        self.assertEqual(Path(self.trace("VDD").resolved),
                         self.proj / "pwl" / "vdd.pwl")
        self.tcl("write_script")
        saved = script.read_text(encoding="utf-8")
        self.assertEqual(files_option(saved), ["{pwl/vdd.pwl}"])

    def test_example_round_trips(self):
        self.app._load_script(str(SCRIPTS / "pwl_example.tcl"))
        self.assertNoErrors()
        self.assertRoundTrips()
