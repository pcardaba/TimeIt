# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2024 Pablo Cardaba

"""Helpers for integration tests that need a live TimeItApp.

Unit tests of pure modules do not need this. Integration tests boot the real
application on a Tk root (a display is required, exactly as for the GUI) and
drive it through the same Tcl interpreter the console uses, because saved
diagrams *are* Tcl scripts and every GUI action funnels through a command.

Typical use::

    class TestSomething(AppTestCase):
        def test_load(self):
            self.source(REPO / "scripts" / "SPI_CPOL0_CPHA0.tcl")
            self.assertNoErrors()
            self.assertRoundTrips()

Run from the parent directory of the repository (the same place
``python3 -m TimeIt.main`` is launched from)::

    python3 -m unittest discover -s TimeIt/tests -t .
"""

from __future__ import annotations

import io
import os
import tkinter as tk
import unittest
from pathlib import Path

## <repo>/tests/apphelper.py -> <repo>
REPO = Path(__file__).resolve().parents[1]
SCRIPTS = REPO / "scripts"


def has_display() -> bool:
    """True when a Tk root can be created (needed by every integration test)."""
    if os.name != "nt" and not os.environ.get("DISPLAY"):
        return False
    try:
        root = tk.Tk()
    except tk.TclError:
        return False
    root.destroy()
    return True


def strip_comments(script: str) -> str:
    """A saved script without its ``#`` lines.

    The ``# datetime:`` header always differs between two writes, so scripts
    are compared without comments (the undo manager applies the same rule).
    """
    return "\n".join(line for line in script.splitlines()
                     if not line.lstrip().startswith("#"))


class AppTestCase(unittest.TestCase):
    """A TimeItApp on a fresh Tk root per test, with the console log captured.

    ``self.app`` is the application, ``self.root`` the Tk root and
    ``self.log`` the list of ``(tag, text)`` pairs appended to the console
    since the last ``clear_log()``.
    """

    @classmethod
    def setUpClass(cls) -> None:
        if not has_display():
            raise unittest.SkipTest("no display: integration tests need Tk")

    def setUp(self) -> None:
        ## Imported here so that collecting the tests never needs Tk.
        from TimeIt.classes.timeitapp import TimeItApp

        self.root = tk.Tk()
        self.app = TimeItApp(self.root)
        ## Lay the window out before anything is drawn, as in a real session:
        ## the first clock drawn computes the canvas scale from the widget
        ## width, and an unmapped canvas reports a width of 1 pixel.
        self.root.update()
        self.log: list[tuple[str | None, str]] = []

        original = self.app.console.append_log

        def spy(text: str, tag: str | None = None) -> None:
            self.log.append((tag, text))
            original(text, tag)

        self.app.console.append_log = spy

    def tearDown(self) -> None:
        ## Not TimeItApp._on_close(): it asks about unsaved changes through a
        ## modal messagebox. Only its side effect matters here, the removal
        ## of the per-process undo snapshot directory.
        try:
            self.app.undo.cleanup()
        except Exception:  # noqa: BLE001 - never mask the test outcome
            pass
        try:
            self.root.destroy()
        except tk.TclError:
            pass

    # ------------------------------------------------------------------
    # Driving the application
    # ------------------------------------------------------------------
    def tcl(self, command: str) -> str:
        """Run one Tcl command on the shared interpreter and redraw.

        Goes through ``interp.eval`` rather than ``console.execute`` so that
        a Tcl error propagates to the test instead of being swallowed into
        the log. Command handlers report their own errors through the log
        (see ``errors()``), not through exceptions.
        """
        result = self.app.console.interp.eval(command)
        self.root.update()
        return result

    def source(self, path: Path | str) -> None:
        """Source a script file, forcing a redraw so render errors surface."""
        self.tcl("source {" + str(path) + "}")

    def write_script(self) -> str:
        buffer = io.StringIO()
        self.app.write_script(buffer)
        return buffer.getvalue()

    def roundtrip(self) -> tuple[str, str]:
        """Write the diagram, reload it from that text, write it again.

        Returns both scripts, comments stripped. Equal strings mean the save
        format reconstructs the model exactly.
        """
        first = self.write_script()
        path = REPO / "tests" / "_roundtrip.tcl"
        path.write_text(first, encoding="utf-8")
        try:
            self.source(path)
        finally:
            path.unlink(missing_ok=True)
        second = self.write_script()
        return strip_comments(first), strip_comments(second)

    # ------------------------------------------------------------------
    # Log inspection
    # ------------------------------------------------------------------
    def clear_log(self) -> None:
        self.log.clear()

    def errors(self) -> list[str]:
        """Texts appended to the console with the ``error`` tag."""
        return [text for tag, text in self.log if tag == "error"]

    # ------------------------------------------------------------------
    # Assertions
    # ------------------------------------------------------------------
    def assertNoErrors(self) -> None:
        self.assertEqual(self.errors(), [])

    def assertError(self, fragment: str) -> None:
        """At least one error line containing ``fragment``."""
        self.assertTrue(any(fragment in text for text in self.errors()),
                        f"no error containing {fragment!r}; "
                        f"errors: {self.errors()}")

    def assertRoundTrips(self) -> None:
        first, second = self.roundtrip()
        self.assertEqual(first, second)
        self.assertNoErrors()

    def assertSignals(self, *names: str) -> None:
        """The store holds exactly ``names``, in that order."""
        self.assertEqual(self.app.signals.names(), list(names))
