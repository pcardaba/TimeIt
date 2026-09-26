#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Start TimeIt with its socket console already open.

Equivalent to launching TimeIt and typing
"source scripts/timeit_socket.tcl" in its console, for the cases where the
program driving TimeIt has to start it too. Needs a display (TimeIt is a GUI)
and a copy of the TimeIt source tree. Standard library only.

    timeit_serve.py                          TimeIt found next to this skill, or $TIMEIT_DIR
    timeit_serve.py --timeit-dir ~/TimeIt    explicit source tree
    timeit_serve.py --port 9000 --bind 0.0.0.0

Prints "listening on <addr>:<port>" once the server is up (the port may differ
from the one asked for when it was busy), then runs the GUI until its window is
closed. Run it in the background and read that line to know where to connect.
"""

from __future__ import annotations

import argparse
import importlib.util
import os
import sys
from pathlib import Path


def find_timeit_dir(explicit: str | None) -> Path:
    candidates = []
    if explicit:
        candidates.append(Path(explicit))
    if os.environ.get("TIMEIT_DIR"):
        candidates.append(Path(os.environ["TIMEIT_DIR"]))
    here = Path(__file__).resolve()
    ## The skill ships inside the repo at ai-portable/timeit-interactive/scripts
    candidates.append(here.parents[3])
    candidates += [Path.home() / "TimeIt", Path.cwd() / "TimeIt", Path.cwd()]
    for c in candidates:
        c = c.expanduser()
        if (c / "main.py").is_file() and (c / "scripts" / "timeit_socket.tcl").is_file():
            return c.resolve()
    sys.exit("TimeIt source tree not found: pass --timeit-dir or set TIMEIT_DIR "
             "to the directory holding main.py and scripts/timeit_socket.tcl")


def import_timeit(repo: Path):
    """Import the source tree as the package "TimeIt" whatever its directory name."""
    spec = importlib.util.spec_from_file_location(
        "TimeIt", repo / "__init__.py", submodule_search_locations=[str(repo)])
    module = importlib.util.module_from_spec(spec)
    sys.modules["TimeIt"] = module
    spec.loader.exec_module(module)
    from TimeIt.classes.timeitapp import TimeItApp  # noqa: E402
    return TimeItApp


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--timeit-dir", help="TimeIt source tree (default: autodetect)")
    ap.add_argument("--port", type=int, default=7777, help="first port to try (default 7777)")
    ap.add_argument("--bind", default="127.0.0.1",
                    help="address to bind; 0.0.0.0 accepts other hosts (default 127.0.0.1)")
    args = ap.parse_args()

    repo = find_timeit_dir(args.timeit_dir)
    TimeItApp = import_timeit(repo)

    import tkinter as tk
    from tkinter import ttk

    root = tk.Tk()
    app = TimeItApp(root)
    try:
        ttk.Style(root).theme_use("clam")
    except tk.TclError:
        pass

    tcl = app.console.interp
    tcl.eval("namespace eval ::timeit_socket {"
             f"variable port_default {args.port}; variable bind_addr {args.bind}}}")
    app.console.execute("source {" + str(repo / "scripts" / "timeit_socket.tcl") + "}")
    port = tcl.eval("set ::timeit_socket::port")
    if not port:
        print("could not open the socket server; see the TimeIt console", file=sys.stderr)
        return 2
    addr = tcl.eval("set ::timeit_socket::addr")
    print(f"listening on {addr}:{port}", flush=True)
    root.mainloop()
    return 0


if __name__ == "__main__":
    sys.exit(main())
