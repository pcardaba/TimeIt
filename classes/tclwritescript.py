# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2024 Pablo Cardaba

from __future__ import annotations

from .tclcommandbase import TclCommandBase, OptSpec


class TclWriteScript(TclCommandBase):
    """Implements the ``write_script`` Tcl command.

    Syntax
    ------
    write_script  [-file <path>] [-copy]

    Saves the diagram as a Tcl script, exactly what File->Write Script... and
    Ctrl+S write. With -file the file becomes the current file (title, later
    Ctrl+S), as the menu does, unless -copy asks for a copy that leaves the
    current file alone. Without -file the current file is rewritten (Ctrl+S).

    This is an action, not model state: it is never written back by
    TimeItApp.write_script and takes no undo snapshot.
    """

    command_name = "write_script"

    defaults = {"copy": False}

    spec = {
        "-file": OptSpec("file", True, str),
        "-copy": OptSpec("copy", False, lambda _v: True),
    }

    def validate(self, opts):
        if "file" not in opts:
            if opts["copy"]:
                raise ValueError("-copy needs -file: the current file is "
                                 "rewritten in place")
            if not self.topapp._file_path:
                raise ValueError("no current file: give -file (the diagram "
                                 "was never saved or loaded from a file)")

    def execute(self, opts):
        if "file" in opts:
            path = str(opts["file"])
            make_current = not opts["copy"]
        else:
            path = self.topapp._file_path
            make_current = True
        try:
            self.topapp.save_script(path, make_current=make_current)
        except OSError as exc:
            raise ValueError(f"{path}: {exc}") from exc
        self.console.append_log(f"Script written to {path}\n", "result")
        return ""
