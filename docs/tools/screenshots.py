# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2024 Pablo Cardaba

"""The screenshots of the user guide, one scene per picture.

Run through make_screenshots.sh (see there). Each scene is a generator
taking the Studio; it stages the application and ends with ``s.snap()``.
The numbers drawn are the steps of the procedure of the page that shows the
picture: keep them in step with the text.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
import tkinter as tk
from pathlib import Path
from tkinter import ttk

from .studio import REPO, Studio, centre, union

SCENES: dict[str, callable] = {}
OUT = Path(".")


def scene(func):
    SCENES[func.__name__] = func
    return func


# ----------------------------------------------------------------------
# Helpers shared by the scenes
# ----------------------------------------------------------------------
def find(widget, cls, text=None):
    """The first descendant of `widget` of class `cls` (with `text`)."""
    for child in widget.winfo_children():
        if isinstance(child, cls):
            try:
                if text is None or child.cget("text") == text:
                    return child
            except tk.TclError:
                pass
        found = find(child, cls, text)
        if found is not None:
            return found
    return None


def corner(rect, dx=-28, dy=22):
    """A point inside the top-right corner of `rect`, for a number."""
    return rect[2] + dx, rect[1] + dy


def transitions(s: Studio, name: str) -> list[int]:
    """Items drawing the changes of signal `name`, left to right."""
    c = s.canvas
    for top, bottom, sig in c.slots:
        if sig.name == name:
            items = [i for i in c.find_withtag("transitions")
                     if c.bbox(i) is not None
                     and top <= (c.bbox(i)[1] + c.bbox(i)[3]) / 2 <= bottom]
            return sorted(items, key=lambda i: c.bbox(i)[0])
    raise LookupError(name)


def marker_rect(s: Studio, part="mark") -> tuple:
    """Screen rectangle of the arrows ("mark") or of the label ("label") of
    the last timing marker."""
    c = s.canvas
    items = [i for i in c.find_all()
             if any(t.startswith(f"tmarker_{part}_") for t in c.gettags(i))]
    return union(*(s.item_rect(i) for i in items))


CLOCK = ("create_clock -name clk -topology source -period {10} -rise_at {0}"
         " -fall_at {5} -show 6 -visible")


def context_menu(s: Studio, x, y, *path, offset=None):
    """Right-click at x, y and open the cascades of `path`; the last label
    is highlighted. Returns (menus, rect of the last entry). `offset` posts
    the menu that far from the click, not to hide what was clicked."""
    s.rclick(x, y)
    menus = [s.canvas._ctxmenu]
    if offset:
        menus[0].unpost()
        menus[0].post(x + offset[0], y + offset[1])
    s.path_entries = []
    for label in path[:-1]:
        menus.append(s.cascade(menus[-1], label))
        s.path_entries.append(s.entry_rect(menus[-2], label))
    last = s.activate(menus[-1], path[-1])
    s.path_entries.append(last)
    return menus, last



def ctx_open(s: Studio, x, y, path, opener=None, *args, wait=1.0,
             offset=None):
    """Right-click at x, y, follow the menu `path`, grab the menus open,
    close them and run `opener` (what the entry does). Returns the grab,
    the rectangles of the menus and the one of the last entry."""
    menus, entry = context_menu(s, x, y, *path, offset=offset)
    yield 0.3
    image = s.grab()
    rects = [s.frame_rect(m) for m in menus]
    s.unpost(*menus)
    if opener is not None:
        s.later(opener, *args)
        yield wait
    return image, rects, entry


def bar_open(s: Studio, title, label, opener=None, *args, wait=1.0):
    """Drop a menu of the menu bar, highlight `label`, grab, close it and
    run `opener`. Returns the grab, the rectangles (menu, title) and the
    one of the entry."""
    menu, title_rect = s.menubar(title)
    entry = s.activate(menu, label)
    yield 0.3
    image = s.grab()
    rects = [s.frame_rect(menu), title_rect]
    s.close_menubar(menu)
    if opener is not None:
        s.later(opener, *args)
        yield wait
    return image, rects, entry


def beside(s: Studio, dlg, dx=-140, dy=20):
    """Move a dialog over the right side of the main window."""
    main = s.frame_rect(s.root)
    s.move(dlg, main[2] + dx, main[1] + dy)


def tree_item(tree, *path):
    """Open the Treeview nodes of `path` (texts) and return the last item."""
    item = ""
    for text in path:
        item = next(i for i in tree.get_children(item)
                    if tree.item(i, "text") == text)
        tree.item(item, open=True)
    return item


def row_rect(s: Studio, tree, item) -> tuple:
    tree.see(item)
    tree.update_idletasks()
    x, y, w, h = tree.bbox(item)
    rx, ry = tree.winfo_rootx(), tree.winfo_rooty()
    return (rx + x, ry + y, rx + tree.winfo_width(), ry + y + h)


STAGE = Path("/tmp/TimeIt")


def stage_dir() -> Path:
    """A neutral copy of the installation for the file dialogs to show:
    no path of the machine the pictures are made on, no untracked file."""
    import shutil
    if STAGE.exists():
        shutil.rmtree(STAGE)
    for sub in ("classes", "data", "docs", "tests"):
        (STAGE / sub).mkdir(parents=True)
    tracked = subprocess.run(["git", "ls-files", "scripts"], cwd=REPO,
                             capture_output=True, text=True).stdout.split()
    (STAGE / "scripts").mkdir()
    for name in tracked:
        (STAGE / name).parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(REPO / name, STAGE / name)
    return STAGE


FD = ".__tk_filedialog"


def fd_rect(s: Studio, part: str):
    return s.tk_rect(f"{FD}.contents.{part}")


# ----------------------------------------------------------------------
# 00 / README — example diagrams (canvas exports)
# ----------------------------------------------------------------------
def _export(s: Studio, script, out, dpi=150):
    s.load(script)
    yield 0.8
    s.export(OUT / out, dpi=dpi)


@scene
def QSPI_program_inst(s: Studio):
    yield from _export(s, "QSPI_program_inst.tcl", "QSPI_program_inst.png")


@scene
def I2C_frame(s: Studio):
    ## The open-drain view of the bus: released lines rise as pulled up.
    yield from _export(s, "I2C_Frame_pulledup.tcl", "I2C_frame.png")


@scene
def main_application_window(s: Studio):
    """The application at work: a diagram, and a signal being edited."""
    from ...classes.outputsignaldlg import OutputSignalDlg
    s.load("SPI_CPOL0_CPHA0.marked.tcl")
    ## Wide enough for the whole frame with its markers apart.
    s.window(1300, 760)
    yield 0.5
    s.canvas_height(480)
    s.app._scale_fit()
    yield 0.5
    s.later(OutputSignalDlg, s.app, s.app.signals.find("MOSI"))
    yield 1.0
    dlg = s.dialog()
    main = s.frame_rect(s.root)
    s.move(dlg, main[2] - 780, s.rect(s.canvas)[3] - 40)
    yield 0.5
    s.snap(OUT / "main_application_window.png",
           [s.frame_rect(s.root), s.frame_rect(dlg)], margin=12)


# ----------------------------------------------------------------------
# 02 — launch
# ----------------------------------------------------------------------
@scene
def timeit_at_launch(s: Studio):
    s.window(800, 480)
    yield 0.5
    canvas = s.rect(s.canvas)
    log = s.rect(s.app.console._output)
    entry = s.rect(s.app.console.entry)
    bar = s.frame_rect(s.root)
    s.snap(OUT / "timeit_at_launch.png", [bar],
           numbers=[(1, *centre(canvas)),
                    (2, centre(log)[0], centre(log)[1]),
                    (3, centre(entry)[0], centre(entry)[1]),
                    (4, bar[0] + 240, s.rect(s.canvas)[1] - 18)])


@scene
def load_script(s: Studio):
    import os
    s.window(800, 480)
    os.chdir(stage_dir() / "scripts")
    yield 0.3
    image, rects, entry = yield from bar_open(
        s, "File", "Load Script…", s.app._load_script_dialog)
    s.root.tk.call(f"{FD}.contents.f2.ent", "insert", 0,
                   "SPI_CPOL0_CPHA0.marked.tcl")
    s.root.tk.call(f"{FD}.contents.f2.ent", "xview", 0)
    s.move(FD, rects[0][2] + 40, s.frame_rect(s.root)[1] + 90)
    yield 0.5
    name, ok = fd_rect(s, "f2.ent"), fd_rect(s, "f2.ok")
    s.snap(OUT / "load_script.png",
           [s.frame_rect(s.root), s.frame_rect(FD), *rects],
           patches=[(image, r) for r in rects],
           pointers=[(entry[0] + 40, centre(entry)[1])],
           numbers=[(1, rects[1][0] - 22, centre(rects[1])[1]),
                    (2, entry[2] + 24, centre(entry)[1]),
                    (3, name[0] + 160, name[1] - 20),
                    (4, ok[2] + 26, centre(ok)[1])])


# ----------------------------------------------------------------------
# 03 — clocks
# ----------------------------------------------------------------------
@scene
def create_clocks(s: Studio):
    s.window(700, 440)
    s.tcl("create_clock -name refclk -topology source -period {10}"
          " -rise_at {0} -fall_at {5} -show 6 -visible")
    yield 0.5
    x, y = s.canvas_to_root(150, 120)
    image, rects, entry = yield from ctx_open(
        s, x, y, ("New Signal", "Clock..."),
        s.canvas._create_new_signal, "clock")
    dlg = s.dialog()
    dlg.clkname_tkvar.set("clk_out")
    dlg.topology_tkvar.set("clockout")
    dlg._update_topology()
    dlg.master_tkvar.set("refclk")
    dlg.genspec_tkvar.set("divide_by")
    dlg.divideby_tkvar.set(2)
    dlg._update_genspec()
    beside(s, dlg, dy=-20)
    yield 0.5
    spot = lambda text: s.title_spot(find(dlg, ttk.Labelframe, text))
    ok = s.rect(find(dlg, ttk.Button, "Ok"))
    visible = s.rect(find(dlg, ttk.Checkbutton, "Visible"))
    s.snap(OUT / "create_clocks.png",
           [s.frame_rect(s.root), s.frame_rect(dlg), *rects],
           patches=[(image, r) for r in rects],
           pointers=[(entry[0] + 30, centre(entry)[1])],
           numbers=[(1, entry[2] + 26, centre(entry)[1]),
                    (2, *spot("Topology")),
                    (3, visible[2] + 26, centre(visible)[1]),
                    (3, *spot("Generated clock")),
                    (4, *spot("Gating (enable signal)")),
                    (5, ok[2] + 26, centre(ok)[1])])


def _settings(s: Studio, *path, height=520):
    """Edit → Settings…, the node `path` opened and its last row selected."""
    from ...classes.settingsdlg import SettingsDlg
    image, rects, entry = yield from bar_open(
        s, "Edit", "Settings…",
        lambda: SettingsDlg(s.app, s.app.settings))
    dlg = s.dialog(SettingsDlg)
    dlg.geometry(f"860x{height}")
    item = tree_item(dlg.tree, *path) if path else None
    if item:
        dlg.tree.selection_set(item)
    beside(s, dlg, dx=-480, dy=50)
    yield 0.5
    row = row_rect(s, dlg.tree, item) if item else None
    return image, rects, entry, dlg, row


@scene
def waveform_settings(s: Studio):
    s.load("SPI_CPOL0_CPHA0.tcl")
    s.window(760, 420)
    yield 0.6
    image, rects, entry, dlg, row = yield from _settings(
        s, "waveform", "tunits")
    s.snap(OUT / "waveform_settings.png",
           [s.frame_rect(s.root), s.frame_rect(dlg), *rects],
           patches=[(image, r) for r in rects],
           pointers=[(entry[0] + 40, centre(entry)[1])],
           numbers=[(1, entry[2] + 24, centre(entry)[1]),
                    (2, row[0] + 260, centre(row)[1])])


@scene
def gen_clock_example(s: Studio):
    s.tcl("set_app_var -name settings.waveform.top_padding -value {40}")
    ## The source clock starts low: its edge 1 is then a whole edge.
    s.tcl("create_clock -name src_clock -topology source -period {10}"
          " -rise_at {5} -fall_at {10} -show 4 -visible")
    s.tcl("create_clock -name gen_clock -topology clockout -master src_clock"
          " -edges {1 3 5} -show 2 -visible")
    s.window(760, 300)
    yield 0.8
    edges = transitions(s, "src_clock")
    labels = []
    for n, item in enumerate(edges[:6], start=1):
        r = s.item_rect(item)
        colour = (0, 150, 0) if n in (1, 3, 5) else (0, 0, 0)
        labels.append((str(n), centre(r)[0], r[1] - 16, colour, 18, "mm"))
    keep = union(s.label_rect("src_clock"), s.label_rect("gen_clock"),
                 *(s.item_rect(i) for i in transitions(s, "gen_clock")),
                 *(s.item_rect(i) for i in edges[:6]))
    canvas = s.rect(s.canvas)
    keep = (canvas[0] + 2, keep[1] - 32, canvas[2] - 2, keep[3] + 8)
    s.snap(OUT / "gen_clock_example.png", [keep], labels=labels, margin=0)


## The gated clock of the page: SCK only toggles while CS_N is low.
GATED = ("""create_clock -name clkref -topology source -period {10} \\
   -rise_at {5} -fall_at {10} -show 16 -visible""",
         """create_input -name cs_n -specify external -launch_clock clkref \\
   -rclk_inputdly_max {2} -rclk_inputdly_min {1} \\
   -high_edges {0 14P} -low_edges {2P} -visible""",
         """create_clock -name sck -topology clockout -master clkref \\
   -divide_by 4 -enabled_by cs_n -enable_active low -show 4 -visible""")


@scene
def gated_clock_example(s: Studio):
    """The diagram of the gated clock example, clkref edges numbered."""
    s.tcl("set_canvas_scale 5")
    for setting, value in (("waveform.interslot", 25),
                           ("waveform.top_padding", 45),
                           ("grid.y_grid_enabled", True),
                           ("grid.y_line_style", "dash"),
                           ("grid.y_clock_name", "clkref"),
                           ("grid.y_show_edge_numbers", True)):
        s.tcl(f"set_app_var -name settings.{setting} -value {{{value}}}")
    for command in GATED:
        s.tcl(command)
    s.window(1000, 480)
    yield 0.8
    s.export(OUT / "gated_clock_example.png", dpi=100)


@scene
def create_gated_clock(s: Studio):
    """The dialog of the gated clock of the example, gating framed."""
    from ...classes.clocksignaldlg import ClockSignalDlg
    for command in GATED:
        s.tcl(command)
    s.window(600, 400, x=1100, y=600)
    yield 0.5
    s.later(ClockSignalDlg, s.app, s.app.signals.find("sck"))
    yield 1.0
    dlg = s.dialog(ClockSignalDlg)
    s.move(dlg, 60, 60)
    yield 0.5
    gen = s.rect(find(dlg, ttk.Labelframe, "Generated clock"))
    gate = s.rect(find(dlg, ttk.Labelframe, "Gating (enable signal)"))
    low = s.rect(find(dlg, ttk.Radiobutton, "Active low"))
    zone = (gen[0] - 8, gen[1] - 6, gen[2] + 8, gate[3] + 8)
    s.snap(OUT / "create_gated_clock.png", [s.frame_rect(dlg)],
           boxes=[(zone, (200, 30, 30))],
           arrows=[(low[2] + 70, centre(low)[1], low[2] + 6, centre(low)[1],
                    (200, 30, 30))])


@scene
def create_clocks_example(s: Studio):
    s.window(860, 440)
    s.tcl("""set Fclkout 100e6
set Tclkout [expr 1e9/$Fclkout]
create_clock -name clkout \\
             -topology source \\
             -period {$Tclkout} \\
             -rise_at 0 \\
             -fall_at {$Tclkout/2} \\
             -visible""")
    yield 0.5
    s.canvas_height(170)
    s.app._scale_fit()
    yield 0.8
    s.snap(OUT / "create_clocks_example.png", [s.frame_rect(s.root)],
           margin=8)

# ----------------------------------------------------------------------
# 04 — input / output signals
# ----------------------------------------------------------------------
def _io_dialog(s: Studio, label: str, out: str):
    s.window(700, 420)
    s.tcl(CLOCK)
    yield 0.5
    cx, cy = s.canvas_to_root(150, 160)
    menus, entry = context_menu(s, cx, cy, "New Signal", label)
    yield 0.3
    with_menus = s.grab()
    menu_rects = [s.frame_rect(m) for m in menus]
    s.unpost(*menus)
    s.later(s.canvas._create_new_signal, label[:-3].lower())
    yield 1.0
    dlg = s.dialog()
    main = s.frame_rect(s.root)
    s.move(dlg, main[2] - 140, main[1] + 20)
    yield 0.5
    spot = lambda text: s.title_spot(find(dlg, ttk.Labelframe, text))
    rising = find(dlg, ttk.Labelframe, "@ Clock Rising")
    falling = s.rect(find(dlg, ttk.Labelframe, "@ Clock Falling"))
    ok = s.rect(find(dlg, ttk.Button, "Ok"))
    s.snap(OUT / out,
           [main, s.frame_rect(dlg), *menu_rects],
           patches=[(with_menus, r) for r in menu_rects],
           pointers=[(entry[0] + 30, centre(entry)[1])],
           numbers=[(1, entry[2] + 26, centre(entry)[1]),
                    (2, *spot("Signal")),
                    (3, *spot(f"{label[:-3]} delay as")),
                    (4, *spot("Clocks")),
                    (5, (s.title_spot(rising)[0] + falling[0]) // 2,
                     s.title_spot(rising)[1]),
                    (6, *spot("Launch Clock Edges Lists")),
                    (7, ok[2] + 26, centre(ok)[1])])


@scene
def create_input(s: Studio):
    yield from _io_dialog(s, "Input...", "create_input.png")


@scene
def create_output(s: Studio):
    yield from _io_dialog(s, "Output...", "create_output.png")


def _example(s: Studio, out, *blocks, height=560, canvas=None):
    """A window showing the diagram and the commands that made it. `canvas`
    is the height given to the diagram, when the default does not show every
    signal."""
    s.window(960, height)
    for block in blocks:
        s.tcl(block)
    yield 0.5
    if canvas:
        s.canvas_height(canvas)
    s.app.redraw()
    s.app.console._output.see("end")
    yield 0.8
    s.snap(OUT / out, [s.frame_rect(s.root)], margin=8)


## The view of the examples of the page, as its first listing gives it: wide
## enough in time to tell a delay from a clock edge, the names clear of the
## waveforms, and the rising edges of clk numbered by the grid.
VIEW = """set_canvas_scale 18.3
set_app_var -name settings.waveform.nmargin -value {150}
set_app_var -name settings.waveform.interslot -value {30}
set_app_var -name settings.waveform.top_padding -value {50}
set_app_var -name settings.grid.y_grid_enabled -value {True}
set_app_var -name settings.grid.y_clock_name -value {clk}
set_app_var -name settings.grid.y_show_edge_numbers -value {True}"""

INPUT_EXAMPLE = """set in_delay 2.0
create_clock -name clk -topology source -period {10} \\
   -rise_at {0} -fall_at {5} -show 10 -visible
create_input -name addr_i<31:0> \\
   -specify external \\
   -launch_clock clk \\
   -rclk_inputdly_max {$in_delay} \\
   -rclk_inputdly_min {$in_delay} \\
   -data_edges {1P 2P 3P} \\
   -hiz_edges {0} \\
   -unknown_edges {4P} \\
   -visible"""

INPUT_EXAMPLE2 = """create_input -name data_i \\
   -specify internal \\
   -launch_clock clk \\
   -data_edges {1P 2P} \\
   -rclk_inputdly_max {3.5} \\
   -rclk_inputdly_min {1.0} \\
   -rclk_latency_max {0.5} \\
   -rclk_latency_min {0.1} \\
   -visible"""

INPUT_EXAMPLE3 = """create_clock -name clk_div2 \\
   -topology clockout \\
   -master clk \\
   -edges {1 3 5} \\
   -visible
create_input -name data2_i \\
   -specify internal \\
   -launch_clock clk \\
   -capture_clock clk_div2 \\
   -data_edges {1P 3P 5P} \\
   -rclk_inputdly_max {3.5} \\
   -rclk_inputdly_min {1.0} \\
   -visible"""

## One marker per example, on the delay it is about: from the edge the delay
## is counted from (2P of clk, then 2P of clk_div2) to the bound it sets.
INPUT_MARKER = """create_timing_marker -name {} \\
   -from full:uid_0_5 -to start:uid_1_4 \\
   -style outer -anchor to -at 57 -label_x 62 -label_y 13"""

INPUT_MARKER2 = """create_timing_marker -name {} \\
   -from end:uid_2_1 -to full:uid_0_5 \\
   -style outer -anchor from -at 57 -label_x 76 -label_y 13"""

INPUT_MARKER3 = """create_timing_marker -name {} \\
   -from end:uid_4_1 -to full:uid_3_5 \\
   -style outer -anchor from -at 57 -label_x 77 -label_y 13"""


@scene
def create_input_example(s: Studio):
    yield from _example(s, "create_input_example.png", VIEW, INPUT_EXAMPLE,
                        INPUT_MARKER, height=660, canvas=210)


@scene
def create_input_example2(s: Studio):
    yield from _example(s, "create_input_example2.png", VIEW, INPUT_EXAMPLE,
                        INPUT_MARKER, INPUT_EXAMPLE2, INPUT_MARKER2,
                        height=600, canvas=280)


@scene
def create_input_example3(s: Studio):
    yield from _example(s, "create_input_example3.png", VIEW, INPUT_EXAMPLE,
                        INPUT_MARKER, INPUT_EXAMPLE2, INPUT_MARKER2,
                        INPUT_EXAMPLE3, INPUT_MARKER3, height=800, canvas=420)


@scene
def create_output_example(s: Studio):
    s.load(REPO / "docs" / "screenshots" / "create_output_example.tcl")
    s.window(860, 600)
    yield 0.8
    s.snap(OUT / "create_output_example.png", [s.frame_rect(s.root)],
           margin=8)


# ----------------------------------------------------------------------
# 05 — timing markers
# ----------------------------------------------------------------------
## Zoom of the pictures of the page (canvas px per ns): the first bits of
## the SPI frame, wide enough for the markers and their labels to breathe.
MARKER_ZOOM = 4.0
## The pictures where a marker is created show still less of the frame, and
## more room between the waveforms: a marker goes between two of them.
CREATE_ZOOM = 6.0
ROOMY = "set_app_var -name settings.waveform.interslot -value {50}"


def zoom(s: Studio, scale=MARKER_ZOOM) -> None:
    """Set the time scale (set_scale() alone does not redraw)."""
    s.app.set_canvas_scale(scale)
    s.app.redraw()


def slot_of(s: Studio, name: str) -> tuple[float, float]:
    """Top and bottom (canvas y) of the slot of signal `name`."""
    return next((top, bottom) for top, bottom, sig in s.canvas.slots
                if sig.name == name)


@scene
def create_tmarker_basic(s: Studio):
    s.load("SPI_CPOL0_CPHA0.tcl")
    s.window(960, 640)
    s.tcl(ROOMY)
    s.canvas_height(390)
    zoom(s, CREATE_ZOOM)
    yield 0.6
    ## Rising edge to rising edge: one SCK period.
    edges = transitions(s, "SCK")
    first = s.select(edges[0])
    second = s.select(edges[2], additive=True)
    yield 0.3
    cx, cy = s.canvas_to_root(s.canvas.bbox(edges[2])[2] + 70, 150)
    menus, entry = context_menu(s, cx, cy, "Time it")
    yield 0.3
    with_menu = s.grab()
    menu_rect = s.frame_rect(menus[0])
    s.unpost(*menus)
    s.canvas.create_timing_marker()
    yield 0.3
    ## Step 4: dragged up, in the room between CS_N and SCK.
    s.tcl(f"create_timing_marker -use_uid 0 -at {slot_of(s, 'SCK')[0] - 13:.0f}")
    yield 0.5
    marker = marker_rect(s, "mark")
    gap = s.canvas_to_root(0, slot_of(s, "SCK")[0] - 25)[1]
    s.snap(OUT / "create_tmarker_basic.png", [s.frame_rect(s.root), menu_rect],
           patches=[(with_menu, menu_rect)],
           pointers=[(cx, cy), (entry[0] + 30, centre(entry)[1])],
           numbers=[(1, first[0] - 28, centre(first)[1]),
                    (2, second[0] - 28, centre(second)[1]),
                    (3, entry[0] - 30, centre(entry)[1]),
                    (4, marker[2] + 30, gap)])


def slot_items(s: Studio, name: str) -> list[int]:
    """Every drawn item of the slot of signal `name`, left to right."""
    c = s.canvas
    for top, bottom, sig in c.slots:
        if sig.name == name:
            items = [i for i in c.find_all() if c.bbox(i) is not None
                     and top <= (c.bbox(i)[1] + c.bbox(i)[3]) / 2 <= bottom
                     and c.type(i) == "polygon"]
            return sorted(items, key=lambda i: c.bbox(i)[0])
    raise LookupError(name)


@scene
def create_tmarker_selmode(s: Studio):
    s.load("SPI_CPOL0_CPHA0.tcl")
    s.window(960, 640)
    s.tcl(ROOMY)
    s.canvas_height(390)
    zoom(s, CREATE_ZOOM)
    yield 0.6
    ## From the SCK falling edge that launches a MOSI bit...
    falling = transitions(s, "SCK")[1]
    s.select(falling)
    yield 0.2
    c = s.canvas
    cx, cy = s.canvas_to_root(c.bbox(falling)[2] + 150,
                              slot_of(s, "MISO")[1] + 22)
    image, rects, entry = yield from ctx_open(
        s, cx, cy, ("Selection Mode", "Start of"))
    s.canvas._sel_mode_tkvar.set("start")
    ## ... to the start of the data window that follows it.
    data = next(i for i in slot_items(s, "MOSI")
                if c.bbox(i)[0] > c.bbox(falling)[2]
                and c.bbox(i)[2] - c.bbox(i)[0] > 60)
    target = s.select(data, additive=True)
    s.canvas.create_timing_marker()
    yield 0.3
    s.tcl(f"create_timing_marker -use_uid 0 -at {slot_of(s, 'MOSI')[0] - 12:.0f}")
    yield 0.5
    marker = marker_rect(s, "mark")
    s.snap(OUT / "create_tmarker_selmode.png", [s.frame_rect(s.root), *rects],
           patches=[(image, r) for r in rects],
           pointers=[(cx, cy), (entry[0] + 30, centre(entry)[1])],
           numbers=[(1, cx - 30, cy + 4),
                    (2, entry[2] + 26, centre(entry)[1]),
                    (3, target[0] + 40, centre(target)[1]),
                    (4, marker[0] - 30, marker[1] - 3)])


@scene
def create_tmarker_quicksel(s: Studio):
    s.load("SPI_CPOL0_CPHA0.tcl")
    s.window(960, 640)
    s.tcl(ROOMY)
    s.canvas_height(390)
    zoom(s, CREATE_ZOOM)
    yield 0.6
    ## The pointer in the MOSI strip, right of the transition wanted: the
    ## menu then opens clear of it.
    wanted = transitions(s, "MOSI")[1]
    x = s.item_rect(wanted)[2] + 90
    y = centre(s.label_rect("MOSI"))[1]
    image, rects, entry = yield from ctx_open(
        s, x, y, ("Select", "Prev. Transition"))
    s.canvas._select_transition("prev")
    yield 0.4
    chosen = s.item_rect(wanted)
    s.snap(OUT / "create_tmarker_quicksel.png",
           [s.frame_rect(s.root), *rects],
           patches=[(image, r) for r in rects],
           pointers=[(x, y), (entry[0] + 30, centre(entry)[1])],
           numbers=[(1, x - 4, y - 44),
                    (2, rects[0][0] - 24, centre(s.path_entries[0])[1]),
                    (3, entry[2] + 26, centre(entry)[1]),
                    (4, centre(chosen)[0], chosen[1] - 28)])


def _marker_menu(s: Studio, label, opener=None, *args):
    """Right-click the label tSCK of a marker, Timing Marker → `label`."""
    s.load("SPI_CPOL0_CPHA0.marked.tcl")
    s.window(1100, 600)
    s.canvas_height(480)
    zoom(s)
    yield 0.6
    tlabel = s.label_rect("tSCK")
    ## The pointer on the end of the label, which stays readable.
    x, y = tlabel[2] - 5, centre(tlabel)[1] + 3
    ## The menu goes right of the markers of the first bits, not over them.
    image, rects, entry = yield from ctx_open(
        s, x, y, ("Timing Marker", label), opener, *args, wait=0.6,
        offset=(210, 6))
    return image, rects, entry, (x, y)


def _marker_scene(s: Studio, out, label, extra=()):
    image, rects, entry, (x, y) = yield from _marker_menu(s, label)
    s.snap(OUT / out, [s.frame_rect(s.root), *rects],
           patches=[(image, r) for r in rects],
           pointers=[(x, y), (entry[0] + 30, centre(entry)[1])],
           numbers=[(1, x - 16, y - 34),
                    (2, rects[0][0] - 24, centre(s.path_entries[0])[1]),
                    (3, entry[2] + 26, centre(entry)[1]), *extra])


@scene
def create_tmarker_anchor(s: Studio):
    idx = s.canvas._anchor_from_idx
    yield from _marker_scene(s, "create_tmarker_anchor.png", idx)


@scene
def create_tmarker_style(s: Studio):
    yield from _marker_scene(s, "create_tmarker_style.png", 1)


@scene
def create_tmarker_delete(s: Studio):
    yield from _marker_scene(s, "create_tmarker_delete.png", "Delete")


@scene
def create_tmarker_label(s: Studio):
    image, rects, entry, (x, y) = yield from _marker_menu(
        s, "Edit Label", s.canvas._edit_marker)
    yield 0.3
    s.snap(OUT / "create_tmarker_label.png", [s.frame_rect(s.root), *rects],
           patches=[(image, r) for r in rects],
           pointers=[(entry[0] + 30, centre(entry)[1])],
           numbers=[(1, x - 16, y - 34),
                    (2, rects[0][0] - 24, centre(s.path_entries[0])[1]),
                    (3, entry[2] + 26, centre(entry)[1]),
                    (4, x + 36, y - 4)])


@scene
def create_tmarker_label_values(s: Studio):
    s.load("SPI_CPOL0_CPHA0.marked.tcl")
    s.window(900, 520)
    yield 0.6
    ## Tall enough for every marker of the example.
    image, rects, entry, dlg, row = yield from _settings(
        s, "marker", "timings", height=580)
    s.snap(OUT / "create_tmarker_label_values.png",
           [s.frame_rect(s.root), s.frame_rect(dlg), *rects],
           patches=[(image, r) for r in rects],
           pointers=[(entry[0] + 40, centre(entry)[1])],
           numbers=[(1, entry[2] + 24, centre(entry)[1]),
                    (2, row[0] + 125, centre(row)[1])])



@scene
def marker_styles(s: Studio):
    """The four arrow styles, each on a marker measuring one clock period
    and labelled with the name of its style."""
    s.tcl("set_canvas_scale 9")
    s.tcl("set_app_var -name settings.waveform.nmargin -value {60}")
    s.tcl("set_app_var -name settings.waveform.top_padding -value {20}")
    s.tcl("create_clock -name clk -topology source -period {20}"
          " -rise_at {10} -fall_at {20} -show 3 -visible")
    s.window(900, 520)
    yield 0.6
    c = s.canvas
    uid = lambda item: next(t for t in c.gettags(item) if t.startswith("uid_"))
    rising = [uid(i) for i in transitions(s, "clk")[0:3:2]]
    for row, style in enumerate(("inner_both", "inner_right", "inner_left",
                                 "outer")):
        s.tcl(f"create_timing_marker -name {{{style}}} -from full:{rising[0]}"
              f" -to full:{rising[1]} -style {style} -anchor from"
              f" -at {75 + 38 * row}")
    yield 0.6
    s.export(OUT / "marker_styles.png", dpi=110)


# ----------------------------------------------------------------------
# 06 — save / load
# ----------------------------------------------------------------------
@scene
def write_script(s: Studio):
    import os
    s.load("SPI_CPOL0_CPHA0.tcl")
    s.window(800, 480)
    os.chdir(stage_dir())
    yield 0.5
    image, rects, entry = yield from bar_open(
        s, "File", "Write Script…", s.app._write_script_dialog)
    ent = f"{FD}.contents.f2.ent"
    s.root.tk.call(ent, "delete", 0, "end")
    s.root.tk.call(ent, "insert", 0, "my_diagram.tcl")
    s.move(FD, rects[0][2] + 40, s.frame_rect(s.root)[1] + 90)
    yield 0.5
    name, ok = fd_rect(s, "f2.ent"), fd_rect(s, "f2.ok")
    s.snap(OUT / "write_script.png",
           [s.frame_rect(s.root), s.frame_rect(FD), *rects],
           patches=[(image, r) for r in rects],
           pointers=[(entry[0] + 40, centre(entry)[1])],
           numbers=[(1, rects[1][0] - 22, centre(rects[1])[1]),
                    (2, entry[2] + 24, centre(entry)[1]),
                    (3, name[0] + 160, name[1] - 20),
                    (4, ok[2] + 26, centre(ok)[1])])


@scene
def current_file(s: Studio):
    s.load("SPI_CPOL0_CPHA0.tcl")
    s.window(800, 300)
    yield 0.5
    frame = s.frame_rect(s.root)
    top = (frame[0], frame[1], frame[2], s.rect(s.canvas)[1] - 2)
    title = (centre(frame)[0] - 165, frame[1] + 3, centre(frame)[0] + 115,
             frame[1] + 24)
    s.snap(OUT / "current_file.png", [top], margin=0,
           boxes=[(title, (200, 30, 30))])


# ----------------------------------------------------------------------
# 07 — grid
# ----------------------------------------------------------------------
@scene
def grid(s: Studio):
    from ...classes.gridsettingsdlg import GridSettingsDlg
    s.load("SPI_CPOL0_CPHA0.tcl")
    ## The grid most diagrams use: on the rising edges of a clock, here
    ## the hidden reference clock every signal of the example is timed by.
    s.tcl("set_app_var -name settings.grid.y_clock_name -value {refclock}")
    s.tcl("set_app_var -name settings.grid.y_grid_enabled -value {True}")
    s.window(860, 460)
    yield 0.3
    s.app.redraw()
    yield 0.4
    cx, cy = s.canvas_to_root(150, 250)
    image, rects, entry = yield from ctx_open(
        s, cx, cy, ("Grid...",), s.canvas.grid_dialog)
    dlg = s.dialog(GridSettingsDlg)
    ## Below the diagram: the grid it sets stays in view.
    beside(s, dlg, dx=-420, dy=290)
    yield 0.5
    spot = lambda text: s.title_spot(find(dlg, ttk.Labelframe, text))
    apply = s.rect(dlg.btn_apply)
    s.snap(OUT / "grid.png", [s.frame_rect(s.root), s.frame_rect(dlg), *rects],
           patches=[(image, r) for r in rects],
           pointers=[(cx, cy), (entry[0] + 30, centre(entry)[1])],
           numbers=[(1, cx - 26, cy - 20),
                    (2, entry[2] + 26, centre(entry)[1]),
                    (3, *spot("X-Grid")),
                    (3, *spot("Y-Grid")),
                    (4, apply[2] + 26, centre(apply)[1])])


@scene
def grid_options(s: Studio):
    s.load("SPI_CPOL0_CPHA0.tcl")
    s.window(800, 460)
    yield 0.6
    image, rects, entry, dlg, row = yield from _settings(s, "grid")
    s.snap(OUT / "grid_options.png",
           [s.frame_rect(s.root), s.frame_rect(dlg), *rects],
           patches=[(image, r) for r in rects],
           pointers=[(entry[0] + 40, centre(entry)[1])],
           numbers=[(1, entry[2] + 24, centre(entry)[1]),
                    (2, row[0] + 120, centre(row)[1])])


# ----------------------------------------------------------------------
# 08 — export
# ----------------------------------------------------------------------
@scene
def export_canvas(s: Studio):
    import os
    s.load("SPI_CPOL0_CPHA0.tcl")
    s.window(800, 480)
    os.chdir(stage_dir())
    yield 0.5
    image, rects, entry = yield from bar_open(
        s, "File", "Export Canvas…", s.app._export_dialog)
    ent = f"{FD}.contents.f2.ent"
    s.root.tk.call(ent, "delete", 0, "end")
    s.root.tk.call(ent, "insert", 0, "my_diagram.svg")
    s.move(FD, rects[0][2] + 40, s.frame_rect(s.root)[1] + 90)
    yield 0.5
    name, ok = fd_rect(s, "f2.ent"), fd_rect(s, "f2.ok")
    kind = fd_rect(s, "f2.menu")
    ## The list of the formats, open under its button.
    types = f"{FD}.contents.f2.menu.m"
    s.root.tk.call(types, "post", kind[0], kind[3])
    s.root.tk.call(types, "activate", 2)
    yield 0.3
    types_rect = s.tk_rect(types)
    s.snap(OUT / "export_canvas.png",
           [s.frame_rect(s.root), s.frame_rect(FD), types_rect, *rects],
           patches=[(image, r) for r in rects],
           pointers=[(entry[0] + 40, centre(entry)[1])],
           numbers=[(1, rects[1][0] - 22, centre(rects[1])[1]),
                    (2, entry[2] + 24, centre(entry)[1]),
                    (3, name[0] + 160, name[1] - 20),
                    (4, types_rect[2] + 26, types_rect[1] + 20),
                    (5, ok[2] + 26, centre(ok)[1])])
    s.root.tk.call(types, "unpost")


# ----------------------------------------------------------------------
# 09 — annotations
# ----------------------------------------------------------------------
## A short frame: four words on a bus that is released before and after.
## Internal delays keep the transition windows narrow, so that the data
## windows (what gets annotated) are the wide ones.
ANNOTATED = """set_canvas_scale 11
set_app_var -name settings.waveform.interslot -value {30}
set_app_var -name settings.waveform.top_padding -value {30}
create_clock -name clk -topology source -period {10} \\
    -rise_at {5} -fall_at {10} -show 6 -visible
create_output -name data -specify internal -launch_clock clk \\
    -rclk_outputdly_max {2} -rclk_outputdly_min {1} \\
    -rclk_oedly_max {2} -rclk_oedly_min {1} \\
    -data_edges {1P 2P 3P 4P} -hiz_edges {0 5P} -visible"""


def _data_uids(s: Studio):
    """uid tags of the data windows of signal `data`, left to right."""
    c = s.canvas
    items = [i for i in slot_items(s, "data") if c.bbox(i)[2] - c.bbox(i)[0] > 60]
    uids = []
    for i in items:
        tag = next((t for t in c.gettags(i) if t.startswith("uid_")), None)
        if tag and tag not in uids:
            uids.append(tag)
    return uids


@scene
def waveform_annotations(s: Studio):
    s.window(860, 520)
    s.tcl(ANNOTATED)
    yield 0.3
    s.canvas_height(190)
    yield 0.3
    uids = _data_uids(s)
    ## A text and a fill colour, a text alone, a text and a line colour.
    s.tcl(f"create_waveform_annotation -on {uids[0]} -text {{CMD}}"
          " -font_weight bold -fill {#f7e463}")
    s.tcl(f"create_waveform_annotation -on {uids[1]} -text {{ADDR}}"
          " -font_weight bold -fill {#8fd3e8}")
    s.tcl(f"create_waveform_annotation -on {uids[2]} -text {{DATA}}")
    s.tcl(f"create_waveform_annotation -on {uids[3]} -text {{CRC}}"
          " -font_color red -line red")
    s.app.console._output.see("end")
    yield 0.5
    s.snap(OUT / "waveform_annotations.png", [s.frame_rect(s.root)], margin=8)


@scene
def waveform_annotations_dlg(s: Studio):
    from ...classes.waveformannotationdlg import WaveformAnnotationDlg
    s.window(800, 440)
    s.tcl(ANNOTATED)
    yield 0.5
    uid = _data_uids(s)[0]
    target = s.select(uid)
    yield 0.2
    cx, cy = s.canvas_to_root(380, 150)
    image, rects, entry = yield from ctx_open(
        s, cx, cy, ("Annotation",), s.canvas._annotate_selected)
    dlg = s.dialog(WaveformAnnotationDlg)
    dlg._text_tkvar.set("CMD")
    beside(s, dlg, dx=-160, dy=250)
    yield 0.5
    ok = s.rect(find(dlg, ttk.Button, "OK"))
    spot = lambda text: s.title_spot(find(dlg, ttk.Labelframe, text))
    s.snap(OUT / "waveform_annotations_dlg.png",
           [s.frame_rect(s.root), s.frame_rect(dlg), *rects],
           patches=[(image, r) for r in rects],
           pointers=[(centre(target)[0], centre(target)[1]),
                     (entry[0] + 30, centre(entry)[1])],
           numbers=[(1, centre(target)[0], target[3] + 28),
                    (2, entry[2] + 26, centre(entry)[1]),
                    (3, *spot("Text annotation")),
                    (3, *spot("Color overrides")),
                    (4, ok[2] + 26, centre(ok)[1])])


# ----------------------------------------------------------------------
# 10..13 — copy, move, delete, modify a signal
# ----------------------------------------------------------------------
def _on_label(s: Studio, name, path, opener=None, *args,
              script="SPI_CPOL0_CPHA0.tcl", size=(900, 520), wait=1.0):
    s.load(script)
    s.window(*size)
    yield 0.6
    x, y = centre(s.label_rect(name))
    image, rects, entry = yield from ctx_open(s, x, y, path, opener, *args,
                                              wait=wait, offset=(12, 22))
    return image, rects, entry, (x, y)


def left_of(s: Studio, name):
    """Where a number designates the name of a signal: on its left."""
    lab = s.label_rect(name)
    return lab[0] - 24, centre(lab)[1]


@scene
def waveform_copy(s: Studio):
    image, rects, entry, (x, y) = yield from _on_label(
        s, "MOSI", ("Edit Signal",), lambda: s.canvas._edit_signal())
    dlg = s.dialog()
    dlg.name_tkvar.set("MOSI_copy")
    beside(s, dlg, dx=-320, dy=40)
    yield 0.5
    name = s.rect(find(dlg, ttk.Entry))
    apply = s.rect(find(dlg, ttk.Button, "Apply"))
    s.snap(OUT / "waveform_copy.png",
           [s.frame_rect(s.root), s.frame_rect(dlg), *rects],
           patches=[(image, r) for r in rects],
           pointers=[(x, y), (entry[0] + 30, centre(entry)[1])],
           numbers=[(1, *left_of(s, "MOSI")),
                    (2, entry[2] + 26, centre(entry)[1]),
                    (3, name[2] + 26, centre(name)[1]),
                    (4, centre(apply)[0], apply[3] + 24)])


@scene
def waveform_copy2(s: Studio):
    s.load("SPI_CPOL0_CPHA0.tcl")
    s.window(900, 560)
    yield 0.6
    sda = s.app.signals.find("MOSI")
    from ...classes.outputsignaldlg import OutputSignalDlg

    def copy():
        dlg = s.dialog(OutputSignalDlg)
        dlg.name_tkvar.set("MOSI_copy")
        dlg.apply()
        dlg.dismiss()
    s.root.after(600, copy)
    s.later(OutputSignalDlg, s.app, sda)
    yield 1.5
    s.canvas_height(330)
    yield 0.4
    x, y = centre(s.label_rect("MOSI_copy"))
    image, rects, entry = yield from ctx_open(s, x, y, ("Edit Signal",),
                                              offset=(12, 22))
    s.snap(OUT / "waveform_copy2.png", [s.frame_rect(s.root), *rects],
           patches=[(image, r) for r in rects],
           pointers=[(x, y), (entry[0] + 30, centre(entry)[1])],
           numbers=[(5, *left_of(s, "MOSI_copy")),
                    (6, entry[2] + 26, centre(entry)[1])])


def _label_menu_scene(s: Studio, out, name, label, **kw):
    image, rects, entry, (x, y) = yield from _on_label(s, name, (label,), **kw)
    s.snap(OUT / out, [s.frame_rect(s.root), *rects],
           patches=[(image, r) for r in rects],
           pointers=[(x, y), (entry[0] + 30, centre(entry)[1])],
           numbers=[(1, *left_of(s, name)),
                    (2, entry[2] + 26, centre(entry)[1])])


@scene
def waveform_updown(s: Studio):
    yield from _label_menu_scene(s, "waveform_updown.png", "MISO",
                                 "Move Up")


@scene
def delete_signal(s: Studio):
    yield from _label_menu_scene(s, "delete_signal.png", "MISO",
                                 "Delete Signal")


@scene
def edit_signal(s: Studio):
    image, rects, entry, (x, y) = yield from _on_label(
        s, "MOSI", ("Edit Signal",), lambda: s.canvas._edit_signal())
    dlg = s.dialog()
    beside(s, dlg, dx=-320, dy=40)
    yield 0.5
    ok = s.rect(find(dlg, ttk.Button, "Ok"))
    spot = lambda text: s.title_spot(find(dlg, ttk.Labelframe, text))
    s.snap(OUT / "edit_signal.png",
           [s.frame_rect(s.root), s.frame_rect(dlg), *rects],
           patches=[(image, r) for r in rects],
           pointers=[(x, y), (entry[0] + 30, centre(entry)[1])],
           numbers=[(1, *left_of(s, "MOSI")),
                    (1, entry[2] + 26, centre(entry)[1]),
                    (2, *spot("Signal")),
                    (2, *spot("Clocks")),
                    (3, ok[2] + 26, centre(ok)[1])])


@scene
def hidden_signals(s: Studio):
    s.load("SPI_CPOL0_CPHA0.tcl")
    ## As unchecking Visible in its dialog does.
    s.app.signals.find("MISO").visible = False
    s.app.redraw()
    s.window(900, 520)
    yield 0.6
    cx, cy = s.canvas_to_root(300, 180)
    menus, entry = context_menu(s, cx, cy, "Hidden Signals", "MISO")
    yield 0.3
    rects = [s.frame_rect(m) for m in menus]
    s.snap(OUT / "hidden_signals.png", [s.frame_rect(s.root), *rects],
           pointers=[(cx, cy), (entry[0] + 30, centre(entry)[1])],
           numbers=[(1, cx - 26, cy - 22),
                    (2, rects[0][0] - 24, centre(s.path_entries[0])[1]),
                    (3, entry[2] + 26, centre(entry)[1])])
    s.unpost(*menus)



# ----------------------------------------------------------------------
# 14 — layout (waveform settings)
# ----------------------------------------------------------------------
def _double_arrow(x, y0, y1, colour=(52, 101, 164)):
    """Two arrows meeting nothing: a span from y0 to y1 at x."""
    return [(x, (y0 + y1) // 2, x, y0, colour), (x, (y0 + y1) // 2, x, y1, colour)]


@scene
def interslot_attribute(s: Studio):
    """The spacing between the waveform slots: the overall inter-slot and
    the top_padding of some signals (QSPI example)."""
    s.load("QSPI_program_inst.tcl")
    s.window(1000, 600)
    yield 0.5
    s.canvas_height(470)
    s.app._scale_fit()
    yield 0.6
    c = s.canvas
    slots = [(s.canvas_to_root(0, top)[1], s.canvas_to_root(0, bottom)[1], sig)
             for top, bottom, sig in c.slots]
    frame = s.frame_rect(s.root)
    x = s.rect(c)[2] - 10
    red, blue = (200, 30, 30), (52, 101, 164)
    arrows, labels = [], []
    marks = {red: [], blue: []}
    for (t0, b0, prev), (t1, b1, sig) in zip(slots, slots[1:]):
        if t1 - b0 < 6:
            continue
        colour = red if sig.top_padding > 0 else blue
        arrows += _double_arrow(x, b0, t1, colour)
        marks[colour].append((b0 + t1) // 2)
    lx = frame[2] + 30
    for colour, text in ((red, "signal specific inter-slot (top_padding)"),
                         (blue, "waveforms overall inter-slot")):
        if not marks[colour]:
            continue
        ys = marks[colour]
        ly = sum(ys) // len(ys) + (0 if colour == red else 30)
        labels.append((text, lx, ly, colour, 15))
        for y in ys:
            arrows.append((lx - 6, ly, x + 6, y, colour))
    keep = [frame, (lx, min(l[2] for l in labels) - 10, lx + 380,
                    max(l[2] for l in labels) + 10)]
    s.snap(OUT / "interslot_attribute.png", keep, arrows=arrows,
           labels=labels, margin=8)


@scene
def waveform_settings2(s: Studio):
    s.load("SPI_CPOL0_CPHA0.tcl")
    s.window(760, 420)
    yield 0.6
    image, rects, entry, dlg, row = yield from _settings(s, "waveform")
    s.snap(OUT / "waveform_settings2.png",
           [s.frame_rect(s.root), s.frame_rect(dlg), *rects],
           patches=[(image, r) for r in rects],
           pointers=[(entry[0] + 40, centre(entry)[1])],
           numbers=[(1, rects[1][0] - 22, centre(rects[1])[1]),
                    (2, entry[2] + 24, centre(entry)[1])])


def _settings_group(s: Studio, group, out, *more):
    from ...classes.settingsdlg import SettingsDlg
    s.load("SPI_CPOL0_CPHA0.marked.tcl")
    s.window(700, 400, x=1000, y=700)
    yield 0.5
    s.later(lambda: SettingsDlg(s.app, s.app.settings))
    yield 0.8
    dlg = s.dialog(SettingsDlg)
    dlg.geometry("860x520+60+60")
    item = tree_item(dlg.tree, group)
    for sub in more:
        tree_item(dlg.tree, group, sub)
    dlg.tree.selection_set(item)
    dlg.tree.see(item)
    yield 0.5
    s.snap(OUT / out, [s.frame_rect(dlg)], margin=8)


@scene
def waveform_group(s: Studio):
    yield from _settings_group(s, "waveform", "waveform_group.png", "font")


@scene
def selection_group(s: Studio):
    yield from _settings_group(s, "selection", "selection_group.png")


@scene
def marker_group(s: Studio):
    yield from _settings_group(s, "marker", "marker_group.png", "font")


@scene
def grid_group(s: Studio):
    yield from _settings_group(s, "grid", "grid_group.png")


# ----------------------------------------------------------------------
# 15 — command help
# ----------------------------------------------------------------------
@scene
def help(s: Studio):
    s.window(860, 640)
    yield 0.3
    s.canvas_height(120)
    s.tcl("create_clock -help")
    yield 0.5
    s.app.console._output.see("1.0")
    entry = s.rect(s.app.console.entry)
    log = s.rect(s.app.console._output)
    s.snap(OUT / "help.png", [s.frame_rect(s.root)], margin=8,
           numbers=[(1, entry[0] + 230, centre(entry)[1]),
                    (2, log[2] - 60, log[1] + 40)])


# ----------------------------------------------------------------------
# 17 — timing variables
# ----------------------------------------------------------------------
@scene
def timings_dialog(s: Studio):
    from ...classes.timingsdlg import TimingsDlg
    s.load("SPI_CPOL0_CPHA0.marked.tcl")
    s.window(800, 460)
    yield 0.6
    image, rects, entry = yield from bar_open(
        s, "Edit", "Timings…", s.app._open_timings)
    dlg = s.dialog(TimingsDlg)
    dlg.geometry("620x360")
    beside(s, dlg, dx=-380, dy=60)
    yield 0.5
    tree = dlg.tree
    first = tree.get_children("")[0]
    tree.selection_set(first)
    yield 0.2
    row = row_rect(s, tree, first)
    add = s.rect(find(dlg, ttk.Button, "Add…"))
    remove = s.rect(find(dlg, ttk.Button, "Remove"))
    close = s.rect(find(dlg, ttk.Button, "Close"))
    value_x = tree.winfo_rootx() + tree.column("#0", "width") + 40
    s.snap(OUT / "timings_dialog.png",
           [s.frame_rect(s.root), s.frame_rect(dlg), *rects],
           patches=[(image, r) for r in rects],
           pointers=[(entry[0] + 40, centre(entry)[1])],
           numbers=[(1, entry[2] + 24, centre(entry)[1]),
                    (2, centre(add)[0], add[1] - 22),
                    (3, value_x, row[3] + 18),
                    (4, centre(remove)[0], remove[1] - 22),
                    (5, centre(close)[0], close[1] - 22)])


@scene
def timings_from_dialog(s: Studio):
    """The Timings… button and the right-click menu of an expression entry."""
    from ...classes.outputsignaldlg import OutputSignalDlg
    from ...classes.timingsdlg import TimingsDlg
    s.load("SPI_CPOL0_CPHA0.marked.tcl")
    s.window(700, 420, x=40, y=40)
    yield 0.5
    s.later(OutputSignalDlg, s.app, s.app.signals.find("MOSI"))
    yield 1.0
    dlg = s.dialog(OutputSignalDlg)
    s.move(dlg, 60, 60)
    yield 0.4
    button = find(dlg, ttk.Button, "Timings…")
    button.invoke()
    yield 0.8
    tim = s.dialog(TimingsDlg)
    frame = s.frame_rect(dlg)
    s.move(tim, frame[2] + 14, frame[1] + 120)
    yield 0.4
    ## The right-click menu of the max output delay at the falling edge.
    falling = find(dlg, ttk.Labelframe, "@ Clock Falling")
    entry = find(falling, ttk.Entry)
    menu = entry.timing_menu.build()
    ex, ey = entry.winfo_rootx() + 30, entry.winfo_rooty() + 12
    menu.post(ex, ey)
    menu.activate(2)
    yield 0.4
    menu_rect = s.frame_rect(menu)
    pick = s.entry_rect(menu, menu.entrycget(2, "label"))
    b = s.rect(button)
    s.snap(OUT / "timings_from_dialog.png",
           [frame, s.frame_rect(tim), menu_rect],
           pointers=[(centre(b)[0], centre(b)[1]), (ex, ey),
                     (pick[0] + 30, centre(pick)[1])],
           numbers=[(1, centre(b)[0], b[1] - 22),
                    (2, ex - 26, ey - 18),
                    (3, menu_rect[2] + 26, centre(pick)[1])])
    menu.unpost()


@scene
def timing_vars_vs_tmark_labels(s: Studio):
    s.load("SPI_CPOL0_CPHA0.marked.tcl")
    s.window(900, 520)
    yield 0.6
    image, rects, entry, dlg, row = yield from _settings(
        s, "marker", "timings", height=580)
    tree = dlg.tree
    last = tree.get_children(tree.selection()[0])[-1]
    end = row_rect(s, tree, last)
    x = row[0] + 330
    s.snap(OUT / "timing_vars_vs_tmark_labels.png",
           [s.frame_rect(s.root), s.frame_rect(dlg), *rects],
           patches=[(image, r) for r in rects],
           labels=[("These are NOT timing variables,", x, row[3] + 40,
                    (0, 0, 200), 15),
                   ("but the values of the timing marker labels", x,
                    row[3] + 62, (0, 0, 200), 15)],
           boxes=[((row[0] + 4, row[3], row[0] + 300, end[3] + 2),
                   (0, 0, 200))])


# ----------------------------------------------------------------------
# 18 — write SDC
# ----------------------------------------------------------------------
@scene
def write_sdc(s: Studio):
    import os
    s.load("SPI_CPOL0_CPHA0.tcl")
    s.window(800, 480)
    os.chdir(stage_dir())
    yield 0.5
    image, rects, entry = yield from bar_open(
        s, "File", "Write SDC…", s.app._write_sdc_dialog)
    s.move(FD, rects[0][2] + 40, s.frame_rect(s.root)[1] + 90)
    yield 0.5
    name, ok = fd_rect(s, "f2.ent"), fd_rect(s, "f2.ok")
    s.snap(OUT / "write_sdc.png",
           [s.frame_rect(s.root), s.frame_rect(FD), *rects],
           patches=[(image, r) for r in rects],
           pointers=[(entry[0] + 40, centre(entry)[1])],
           numbers=[(1, rects[1][0] - 22, centre(rects[1])[1]),
                    (2, entry[2] + 24, centre(entry)[1]),
                    (3, name[0] + 160, name[1] - 20),
                    (4, ok[2] + 26, centre(ok)[1])])


# ----------------------------------------------------------------------
# 19 — import VCDs
# ----------------------------------------------------------------------
VCD_MIN = "TimeIt/data/VCDs/import_vcd.min.vcd"
VCD_MAX = "TimeIt/data/VCDs/import_vcd.max.vcd"


@scene
def import_vcd_files(s: Studio):
    from ...classes.importvcddlg import ImportVCDDlg
    s.window(800, 420)
    yield 0.4
    image, rects, entry = yield from bar_open(
        s, "File", "Import VCDs…", s.app._import_vcd_dialog)
    dlg = s.dialog(ImportVCDDlg)
    dlg._min_var.set(VCD_MIN)
    dlg._max_var.set(VCD_MAX)
    s.move(dlg, rects[0][2] + 30, s.frame_rect(s.root)[1] + 110)
    yield 0.5
    entries = [w for w in dlg.winfo_children()]
    imp = s.rect(find(dlg, ttk.Button, "Import"))
    min_e = s.rect(find(dlg, ttk.Entry))
    browse = [w for w in _all(dlg) if isinstance(w, ttk.Button)
              and w.cget("text") == "Browse…"]
    b0, b1 = s.rect(browse[0]), s.rect(browse[1])
    s.snap(OUT / "import_vcd_files.png",
           [s.frame_rect(s.root), s.frame_rect(dlg), *rects],
           patches=[(image, r) for r in rects],
           pointers=[(entry[0] + 40, centre(entry)[1])],
           numbers=[(1, rects[1][0] - 22, centre(rects[1])[1]),
                    (2, entry[2] + 24, centre(entry)[1]),
                    (3, b0[2] + 26, centre(b0)[1]),
                    (3, b1[2] + 26, centre(b1)[1]),
                    (4, imp[0] - 26, centre(imp)[1])])


def _all(widget):
    for child in widget.winfo_children():
        yield child
        yield from _all(child)


@scene
def import_vcd_characterization(s: Studio):
    from ...classes.importvcddlg import ImportVCDDlg
    s.window(800, 420, x=900, y=700)
    yield 0.4
    s.later(s.app._import_vcd_dialog)
    yield 0.8
    dlg = s.dialog(ImportVCDDlg)
    dlg._min_var.set(VCD_MIN)
    dlg._max_var.set(VCD_MAX)
    s.later(dlg._ok)
    yield 1.5
    char = next(t for t in s.toplevels() if t.winfo_viewable()
                and not isinstance(t, ImportVCDDlg))
    s.move(char, 60, 60)
    yield 0.5
    s.snap(OUT / "import_vcd_characterization.png", [s.frame_rect(char)],
           margin=8)


## The two VCD viewer strips (min, max) of the former picture: they come
## from a simulator, not from TimeIt, and are kept as they are.
VCD_VIEWER_STRIPS = Path(__file__).with_name("import_vcds_viewer.png")
VCD_WAVES_X = (262, 895)        # time axis of the strips, in that picture


@scene
def import_vcds(s: Studio):
    """The waveforms of the example pair as imported, under the same
    waveforms seen in a VCD viewer, on the same time axis."""
    from PIL import Image
    from ...classes.importvcddlg import ImportVCDDlg
    from ...classes.importvcdchardlg import ImportVCDCharDlg
    s.window(900, 560, x=40, y=40)
    ## Room for the longest names (DATA_i<3:0>).
    s.tcl("set_app_var -name settings.waveform.nmargin -value {130}")
    yield 0.4
    s.later(s.app._import_vcd_dialog)
    yield 0.8
    dlg = s.dialog(ImportVCDDlg)
    dlg._min_var.set(VCD_MIN)
    dlg._max_var.set(VCD_MAX)
    s.later(dlg._ok)
    yield 1.5
    char = s.dialog(ImportVCDCharDlg)
    s.later(char._ok)
    yield 1.5
    s.canvas_height(400)
    s.app._scale_fit()
    yield 0.6
    c = s.canvas
    items = [i for i in c.find_all() if c.bbox(i) and c.type(i) != "text"]
    x0 = min(c.bbox(i)[0] for i in items)
    x1 = max(c.bbox(i)[2] for i in items)
    canvas = s.rect(c)
    shot = s.grab().crop((canvas[0] + 2, canvas[1] + 2, canvas[2] - 2,
                          canvas[3] - 2))
    a, b = s.canvas_to_root(x0, 0)[0] - canvas[0] - 2, \
        s.canvas_to_root(x1, 0)[0] - canvas[0] - 2
    factor = (VCD_WAVES_X[1] - VCD_WAVES_X[0]) / (b - a)
    shot = shot.resize((round(shot.width * factor),
                        round(shot.height * factor)), Image.LANCZOS)
    left = VCD_WAVES_X[0] - round(a * factor)
    strips = Image.open(VCD_VIEWER_STRIPS).convert("RGB")
    width = max(strips.width, left + shot.width)
    out = Image.new("RGB", (width, strips.height + shot.height + 6), "white")
    out.paste(strips, (0, 0))
    out.paste(shot, (left, strips.height + 6))
    from PIL import ImageDraw, ImageFont
    from .studio import FONT_BOLD
    draw = ImageDraw.Draw(out)
    draw.text((width - 10, strips.height + 6 + shot.height // 2),
              "Import VCDs", fill=(0, 0, 230), anchor="rm",
              font=ImageFont.truetype(FONT_BOLD.replace("-Bold", ""), 20))
    out.save(OUT / "import_vcds.png", optimize=True)
    print(f"  wrote import_vcds.png {out.width}x{out.height}")


# ----------------------------------------------------------------------
# 20 — PWL signals
# ----------------------------------------------------------------------
@scene
def pwl_signals(s: Studio):
    yield from _export(s, "pwl_example.tcl", "pwl_signals.png", dpi=110)


@scene
def pwl_dialog(s: Studio):
    from ...classes.pwlsignaldlg import PWLSignalDlg
    s.tcl("create_clock -name clk -topology source -period {10} -rise_at {0}"
          " -fall_at {5} -show 10 -visible")
    s.window(760, 440)
    yield 0.4
    cx, cy = s.canvas_to_root(150, 150)
    image, rects, entry = yield from ctx_open(
        s, cx, cy, ("New Signal", "PWL (analog)..."),
        s.canvas._create_new_signal, "pwl")
    dlg = s.dialog(PWLSignalDlg)
    dlg.height_tkvar.set(100)
    for row, (name, path, colour, style) in zip(dlg.rows, (
            ("VDD", "TimeIt/scripts/pwl/vdd.pwl", "blue", "solid"),
            ("IDD", "TimeIt/scripts/pwl/idd.pwl", "red", "dash"))):
        row["name"].set(name)
        row["file"].set(path)
        row["color"].set(colour)
        row["lstyle"].set(style)
    beside(s, dlg, dx=-200, dy=0)
    yield 0.5
    height = s.rect(find(dlg, ttk.Spinbox))
    first = s.rect(find(dlg, ttk.Labelframe, "Signal 1"))
    second = s.rect(find(dlg, ttk.Labelframe, "Signal 2"))
    ok = s.rect(find(dlg, ttk.Button, "Ok"))
    s.snap(OUT / "pwl_dialog.png",
           [s.frame_rect(s.root), s.frame_rect(dlg), *rects],
           patches=[(image, r) for r in rects],
           pointers=[(entry[0] + 30, centre(entry)[1])],
           numbers=[(1, entry[2] + 26, centre(entry)[1]),
                    (2, height[2] + 120, centre(height)[1]),
                    (3, first[2] + 26, centre(first)[1]),
                    (3, second[2] + 26, centre(second)[1]),
                    (4, ok[2] + 26, centre(ok)[1])])


# ----------------------------------------------------------------------
# 21 — logic and sampled signals
# ----------------------------------------------------------------------
@scene
def logic_signals(s: Studio):
    yield from _export(s, "logic_example.tcl", "logic_signals.png")


def _derived_dialog(s: Studio, name, out):
    s.load("logic_example.tcl")
    s.window(700, 400, x=1000, y=700)
    yield 0.6
    sig = s.app.signals.find(name)
    s.canvas._current_tags = s.canvas.gettags(
        next(i for i in s.canvas.find_all()
             if s.canvas.type(i) == "text"
             and s.canvas.itemcget(i, "text") == name))
    s.later(s.canvas._edit_signal)
    yield 1.0
    dlg = s.dialog()
    s.move(dlg, 60, 60)
    yield 0.4
    s.snap(OUT / out, [s.frame_rect(dlg)], margin=8)


@scene
def logic_signal_dlg(s: Studio):
    yield from _derived_dialog(s, "busy", "logic_signal_dlg.png")


@scene
def sampled_signal_dlg(s: Studio):
    yield from _derived_dialog(s, "busy_q", "sampled_signal_dlg.png")


def tab_rects(s: Studio, nb) -> list:
    """Screen rectangles of the tabs of a ttk.Notebook (probed: Tk gives no
    tab geometry)."""
    nb.update_idletasks()
    rects, current, start = [], None, None
    y = 8
    for x in range(0, nb.winfo_width()):
        try:
            idx = nb.index(f"@{x},{y}")
        except tk.TclError:
            idx = None
        if idx != current:
            if current is not None:
                rects.append((start, x))
            current, start = idx, x
    x0, y0 = nb.winfo_rootx(), nb.winfo_rooty()
    return [(x0 + a, y0, x0 + b, y0 + 22) for a, b in rects]


# ----------------------------------------------------------------------
# 23 — bidirectional signals
# ----------------------------------------------------------------------
@scene
def bidir_example(s: Studio):
    yield from _export(s, "bidir_example.tcl", "bidir_example.png", dpi=110)


@scene
def create_inout(s: Studio):
    s.window(700, 420)
    s.tcl(CLOCK)
    yield 0.5
    cx, cy = s.canvas_to_root(150, 160)
    image, rects, entry = yield from ctx_open(
        s, cx, cy, ("New Signal", "Bidir..."),
        s.canvas._create_new_signal, "inout")
    dlg = s.dialog()
    main = s.frame_rect(s.root)
    s.move(dlg, main[2] - 140, main[1] + 20)
    yield 0.5
    spot = lambda text: s.title_spot(find(dlg, ttk.Labelframe, text))
    tabs = tab_rects(s, dlg.notebook)
    row_y = centre(tabs[0])[1]
    n4 = s.title_spot(find(dlg.in_form.frame, ttk.Labelframe, "Clocks"))
    n5 = (tabs[1][2] + 28, row_y)
    ok = s.rect(find(dlg, ttk.Button, "Ok"))
    s.snap(OUT / "create_inout.png",
           [main, s.frame_rect(dlg), *rects],
           patches=[(image, r) for r in rects],
           pointers=[(entry[0] + 30, centre(entry)[1])],
           numbers=[(1, entry[2] + 26, centre(entry)[1]),
                    (2, *spot("Signal")),
                    (3, *spot("Input and output delays as")),
                    (4, *n4), (5, *n5),
                    (6, ok[2] + 26, centre(ok)[1])])


# ----------------------------------------------------------------------
def main(argv=None) -> int:
    global OUT
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path, default=Path("."))
    parser.add_argument("--list", action="store_true")
    parser.add_argument("--one", help=argparse.SUPPRESS)
    parser.add_argument("names", nargs="*")
    args = parser.parse_args(argv)
    sys.stdout.reconfigure(line_buffering=True)
    if args.list:
        print("\n".join(SCENES))
        return 0
    OUT = args.out
    if args.one:
        import faulthandler
        ## A scene stuck outside the Tk event loop: show where, then quit.
        faulthandler.dump_traceback_later(45, exit=True)
        Studio().run(SCENES[args.one])
        return 0
    names = args.names or list(SCENES)
    unknown = [n for n in names if n not in SCENES]
    if unknown:
        print("unknown:", " ".join(unknown), file=sys.stderr)
        return 2
    failed = []
    for name in names:
        print(name)
        ## A fresh application per scene: nothing leaks from one to the next.
        if subprocess.run([sys.executable, "-m", __spec__.name, "--out",
                           str(OUT), "--one", name]).returncode:
            failed.append(name)
    if failed:
        print("FAILED:", " ".join(failed), file=sys.stderr)
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
