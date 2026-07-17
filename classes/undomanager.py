# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2024 Pablo Cardaba

"""GUI-only undo/redo built on temporary snapshot scripts.

Every mutable canvas action is bracketed by two snapshots written with the
application's normal save format (``write_script``): one *before* and one
*after* the mutation. Undo re-``source``s the *before* snapshot of the last
action; redo re-``source``s the *after* snapshot. Snapshots live in a
per-process temporary directory that is removed when the application closes.
"""

from __future__ import annotations

import atexit
import shutil
import tempfile
from contextlib import contextmanager
from pathlib import Path

import tkinter as tk


def meaningful_lines(text: str) -> list[str]:
    """Return script lines excluding comments/blank lines.

    ``write_script`` emits a ``# datetime:`` header that always differs between
    two snapshots, so comparing generated scripts must ignore comment lines.
    Also used by TimeItApp to detect unsaved changes.
    """
    out = []
    for line in text.splitlines():
        stripped = line.strip()
        if stripped and not stripped.startswith("#"):
            out.append(stripped)
    return out


def _meaningful_lines(path: str) -> list[str]:
    with open(path, encoding="utf-8") as f:
        return meaningful_lines(f.read())


class UndoManager:
    """Tracks undo/redo history as paired before/after snapshot files."""

    def __init__(self, topapp):
        self.topapp = topapp
        self._dir = Path(tempfile.mkdtemp(prefix="timeit_undo_"))
        self._counter = 0
        # History of (before_path, after_path); _pos = number of applied actions.
        self._history: list[tuple[str, str]] = []
        self._pos = 0
        # True while a snapshot is being sourced: suppresses recording so the
        # mutations triggered by restoration are not themselves captured.
        self._restoring = False
        # Nesting depth: only the outermost transaction records, so a mutation
        # that internally calls other wrapped mutations (e.g. recursive
        # _delete_signal) produces a single undo entry.
        self._depth = 0
        atexit.register(self.cleanup)

    # ------------------------------------------------------------------
    # Snapshot recording
    # ------------------------------------------------------------------
    def _snapshot(self) -> str:
        path = self._dir / f"snap_{self._counter:06d}.tcl"
        self._counter += 1
        with path.open("w", encoding="utf-8", newline="\n") as f:
            self.topapp.write_script(f)
        return str(path)

    def _record(self, before: str, after: str) -> None:
        # Skip no-op actions (cancelled dialogs, zero-distance drags).
        if _meaningful_lines(before) == _meaningful_lines(after):
            return
        # A new action after an undo invalidates the stale redo branch.
        del self._history[self._pos:]
        self._history.append((before, after))
        self._pos = len(self._history)

    @contextmanager
    def transaction(self):
        """Bracket a synchronous mutation with before/after snapshots.

        Re-entrant: nested transactions are absorbed into the outermost one.
        """
        if self._restoring:
            yield
            return
        outer = self._depth == 0
        self._depth += 1
        before = self._snapshot() if outer else None
        try:
            yield
        finally:
            self._depth -= 1
            if outer:
                after = self._snapshot()
                self._record(before, after)

    def begin(self) -> str | None:
        """Capture a before-snapshot (e.g. on drag press). See ``commit``."""
        if self._restoring:
            return None
        return self._snapshot()

    def commit(self, before: str | None) -> None:
        """Record the action started by ``begin`` (e.g. on drag release)."""
        if before is None or self._restoring:
            return
        after = self._snapshot()
        self._record(before, after)

    # ------------------------------------------------------------------
    # Undo / redo
    # ------------------------------------------------------------------
    def can_undo(self) -> bool:
        return self._pos > 0

    def can_redo(self) -> bool:
        return self._pos < len(self._history)

    def undo(self) -> None:
        if not self.can_undo():
            return
        self._pos -= 1
        self._source(self._history[self._pos][0])

    def redo(self) -> None:
        if not self.can_redo():
            return
        self._source(self._history[self._pos][1])
        self._pos += 1

    def _source(self, path: str) -> None:
        self._restoring = True
        try:
            self.topapp.console.interp.eval("source {" + path + "}")
        except tk.TclError as exc:
            self.topapp.console.append_log(f"Error: {exc}\n", "error")
        finally:
            self._restoring = False

    # ------------------------------------------------------------------
    # Cleanup
    # ------------------------------------------------------------------
    def cleanup(self) -> None:
        shutil.rmtree(self._dir, ignore_errors=True)
