# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2024 Pablo Cardaba

"""Drive a live TimeIt and compose the screenshots of the user guide.

A screenshot is a *scene*: a generator function that drives the application
(load a script, right-click, open a cascade, open a dialog...) and yields the
number of seconds to wait for Tk to draw. It ends with ``studio.snap()``,
which captures the whole (virtual) screen, keeps the windows of interest,
and draws the guidance on top: numbered circles in the order the user clicks,
arrows and mouse pointers.

Run through make_screenshots.sh: it provides a private X display, a window
manager and ``TIMEIT_SCALE=1``. Every scene runs in a fresh process.

Coordinates are root (screen) pixels; the virtual display is unscaled, so
canvas logical pixels are screen pixels too.
"""

from __future__ import annotations

import os
import re
import subprocess
import tempfile
import tkinter as tk
from pathlib import Path
from tkinter import ttk

from PIL import Image, ImageDraw, ImageFont

from ...classes import uiscale
from ...classes.timeitapp import TimeItApp

REPO = Path(__file__).resolve().parents[2]
SCRIPTS = REPO / "scripts"

## Guidance style (the one of the former LibreOffice compositions).
CIRCLE_RADIUS = 21
CIRCLE_FILL = (114, 159, 207)
CIRCLE_OUTLINE = (52, 101, 164)
NUMBER_COLOR = (0, 0, 200)
ARROW_COLOR = (52, 101, 164)
FONT_BOLD = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"

Rect = tuple[int, int, int, int]          # x0, y0, x1, y1 (screen pixels)


def union(*rects: Rect) -> Rect:
    return (min(r[0] for r in rects), min(r[1] for r in rects),
            max(r[2] for r in rects), max(r[3] for r in rects))


def centre(rect: Rect) -> tuple[int, int]:
    return ((rect[0] + rect[2]) // 2, (rect[1] + rect[3]) // 2)


_ROOT: list = []


class Studio:
    """One TimeIt application and the means to stage it."""

    def __init__(self) -> None:
        self.root = tk.Tk()
        _ROOT[:] = [self.root]
        uiscale.setup(self.root)
        self.app = TimeItApp(self.root)
        style = ttk.Style(self.root)
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass
        uiscale.apply_ttk_style(style)
        self.canvas = self.app.canvas
        self.error: BaseException | None = None
        self._scene = None

    # ------------------------------------------------------------------
    # Running a scene
    # ------------------------------------------------------------------
    def run(self, scene) -> None:
        """Play the generator `scene(self)`, then close the application."""
        self._scene = scene(self)
        self.root.after(300, self._step)
        self.root.after(60000, self._timeout)
        self.root.mainloop()
        if self.error is not None:
            raise self.error

    def _step(self) -> None:
        try:
            delay = next(self._scene)
        except StopIteration:
            self._finish()
            return
        except BaseException as exc:  # noqa: BLE001 - reported by run()
            self.error = exc
            self._finish()
            return
        self.root.after(int((delay or 0) * 1000), self._step)

    def _timeout(self) -> None:
        self.error = TimeoutError("the scene did not finish")
        self._finish()

    def _finish(self) -> None:
        ## Close whatever is open: dialogs first (they hold the grab),
        ## including the Tcl-only ones (file dialogs, message boxes).
        call = self.root.tk.call

        def tops(path):
            found = []
            for child in self.root.tk.splitlist(call("winfo", "children",
                                                     path)):
                found.extend(tops(child))
                if call("winfo", "toplevel", child) == child \
                        and call("winfo", "class", child) != "Menu":
                    found.append(child)
            return found

        for path in tops("."):
            try:
                call("destroy", path)
            except tk.TclError:
                pass
        try:
            self.root.grab_release()
        except tk.TclError:
            pass
        self.root.after(50, self.root.quit)

    def later(self, func, *args) -> None:
        """Run `func` from the event loop: for what blocks (modal dialogs)."""
        self.root.after(1, lambda: func(*args))

    # ------------------------------------------------------------------
    # Application
    # ------------------------------------------------------------------
    def window(self, width=960, height=560, x=40, y=40):
        """Place the main window (client area size)."""
        self.root.geometry(f"{width}x{height}+{x}+{y}")
        self.root.update_idletasks()

    def canvas_height(self, height: int) -> None:
        """Give the canvas `height` pixels (the sash between the canvas and
        the console; extra window height goes to the console)."""
        self.root.update_idletasks()
        self.app.sash_place(0, 0, height)
        self.root.update_idletasks()

    def load(self, script: str | Path) -> None:
        """Load a script as File → Load Script does (title, log...)."""
        ## Relative to the launch directory (the parent of the repository),
        ## as a user would give it: no absolute path in the history pane.
        path = Path(script)
        if not path.is_absolute():
            path = SCRIPTS / path
        self.app._load_script(os.path.relpath(path, REPO.parent))

    def tcl(self, command: str) -> None:
        """Run a command through the console (logged in the history pane)."""
        self.app.console.execute(command)

    def toplevels(self, widget=None) -> list[tk.Toplevel]:
        found = []
        for child in (widget or self.root).winfo_children():
            if isinstance(child, tk.Toplevel) and not isinstance(child, tk.Menu):
                found.append(child)
            found.extend(self.toplevels(child))
        return found

    def dialog(self, kind=None) -> tk.Toplevel:
        """The open dialog (of class `kind`, or whose title is `kind`)."""
        for top in self.toplevels():
            if not top.winfo_exists() or not top.winfo_viewable():
                continue
            if kind is None or (isinstance(kind, str) and top.title() == kind) \
                    or (isinstance(kind, type) and isinstance(top, kind)):
                return top
        raise LookupError(f"no open dialog {kind!r}")

    def move(self, top: tk.Toplevel, x: int, y: int) -> None:
        """Move a toplevel (its client area) to x, y."""
        if isinstance(top, str):            # a Tcl-only toplevel
            self.root.tk.call("wm", "geometry", top, f"+{x}+{y}")
        else:
            top.geometry(f"+{x}+{y}")
        self.root.update_idletasks()

    # ------------------------------------------------------------------
    # Canvas
    # ------------------------------------------------------------------
    def canvas_to_root(self, x: float, y: float) -> tuple[int, int]:
        """Screen point of a canvas (scrolled, logical) point."""
        c = self.canvas
        return (int(c.winfo_rootx() + x - c.canvasx(0)),
                int(c.winfo_rooty() + y - c.canvasy(0)))

    def item_rect(self, tag) -> Rect:
        """Screen rectangle of a canvas item / tag."""
        x0, y0, x1, y1 = self.canvas.bbox(tag)
        a = self.canvas_to_root(x0, y0)
        b = self.canvas_to_root(x1, y1)
        return (a[0], a[1], b[0], b[1])

    def label_rect(self, name: str) -> Rect:
        """Screen rectangle of the name of a signal on the canvas."""
        for item in self.canvas.find_all():
            if self.canvas.type(item) == "text" \
                    and self.canvas.itemcget(item, "text") == name:
                return self.item_rect(item)
        raise LookupError(f"no label {name!r}")

    def select(self, tag, additive=False) -> Rect:
        """Select the canvas item `tag` as a (Ctrl-)click does."""
        item = self.canvas.find_withtag(tag)[0]
        self.canvas._select_item(item, additive=additive)
        return self.item_rect(item)

    def rclick(self, x: int, y: int, ctrl=False) -> None:
        """Right-click at screen point x, y of the canvas: context menu."""
        c = self.canvas
        ## The real pointer goes there first: the item under it ("current")
        ## is what the context menu works on.
        c.event_generate("<Motion>", warp=True, x=x - c.winfo_rootx(),
                         y=y - c.winfo_rooty())
        self.root.update()
        c.event_generate("<Button-3>", x=x - c.winfo_rootx(),
                         y=y - c.winfo_rooty(), rootx=x, rooty=y,
                         state=4 if ctrl else 0)

    # ------------------------------------------------------------------
    # Menus
    # ------------------------------------------------------------------
    @staticmethod
    def index(menu: tk.Menu, label) -> int:
        """Index of the entry `label` (or `label` itself when an int: the
        entries showing an image have no label)."""
        if isinstance(label, int):
            return label
        last = menu.index("end")
        for i in range(last + 1):
            if menu.type(i) in ("command", "cascade", "radiobutton",
                                "checkbutton") \
                    and menu.entrycget(i, "label") == label:
                return i
        raise LookupError(f"no entry {label!r}")

    def entry_rect(self, menu: tk.Menu, label: str) -> Rect:
        """Screen rectangle of an entry of a posted menu."""
        i = self.index(menu, label)
        x0, y0 = menu.winfo_rootx(), menu.winfo_rooty()
        top = menu.yposition(i)
        bottom = (menu.yposition(i + 1) if i < menu.index("end")
                  else menu.winfo_height() - 2)
        return (x0 + 2, y0 + top, x0 + menu.winfo_width() - 2, y0 + bottom)

    def activate(self, menu: tk.Menu, label: str) -> Rect:
        """Highlight an entry, as the pointer over it does."""
        menu.activate(self.index(menu, label))
        return self.entry_rect(menu, label)

    def cascade(self, menu: tk.Menu, label: str) -> tk.Menu:
        """Open a cascade of a posted menu, entry highlighted."""
        i = self.index(menu, label)
        menu.activate(i)
        menu.tk.call(menu._w, "postcascade", i)
        return menu.nametowidget(menu.entrycget(i, "menu"))

    def menubar(self, label: str) -> tuple[tk.Menu, Rect]:
        """Drop the menu `label` of the menu bar down; returns it and the
        rectangle of its title in the bar."""
        bar = self.root.nametowidget(self.root.cget("menu"))
        i = self.index(bar, label)
        sub = bar.nametowidget(bar.entrycget(i, "menu"))
        ## The menu bar shown is a clone of `bar`, child of the toplevel.
        clone = next(w for w in self.root.tk.splitlist(
            self.root.tk.call("winfo", "children", ".")) if "#" in w)
        cx = int(self.root.tk.call(clone, "xposition", i))
        nx = (int(self.root.tk.call(clone, "xposition", i + 1))
              if i < bar.index("end") else cx + 50)
        x0 = int(self.root.tk.call("winfo", "rootx", clone))
        y0 = int(self.root.tk.call("winfo", "rooty", clone))
        h = int(self.root.tk.call("winfo", "height", clone))
        self.root.tk.call(clone, "activate", i)
        postcommand = sub.cget("postcommand")
        if postcommand:
            self.root.tk.eval(postcommand)
        sub.post(x0 + cx, y0 + h)
        return sub, (x0 + cx, y0, x0 + nx, y0 + h)

    def close_menubar(self, menu: tk.Menu) -> None:
        menu.unpost()
        clone = next(w for w in self.root.tk.splitlist(
            self.root.tk.call("winfo", "children", ".")) if "#" in w)
        self.root.tk.call(clone, "activate", "none")

    def unpost(self, *menus: tk.Menu) -> None:
        for menu in menus:
            menu.unpost()
        try:
            self.root.tk.call("grab", "release", self.root.tk.call("grab",
                                                                   "current"))
        except tk.TclError:
            pass

    @staticmethod
    def title_spot(frame: ttk.Labelframe, gap=30) -> tuple[int, int]:
        """A point on the top border of a labelframe, right after its title:
        where a number designates the frame without hiding a field."""
        from tkinter import font as tkfont
        text = frame.cget("text")
        width = tkfont.nametofont("TkDefaultFont").measure(text)
        return (frame.winfo_rootx() + 8 + width + gap, frame.winfo_rooty() + 8)

    def tk_rect(self, path: str) -> Rect:
        """Screen rectangle of a widget given by its Tcl path."""
        call = self.root.tk.call
        x, y = int(call("winfo", "rootx", path)), int(call("winfo", "rooty", path))
        return (x, y, x + int(call("winfo", "width", path)),
                y + int(call("winfo", "height", path)))

    def export(self, out: Path, dpi=150) -> None:
        """Export the whole canvas as File → Export Canvas does."""
        self.root.update()
        self.app.console.interp.eval(
            f"export_canvas -file {{{out}}} -dpi {dpi}")
        print(f"  wrote {out.name} (export)")

    @staticmethod
    def rect(widget: tk.Misc) -> Rect:
        """Screen rectangle of a widget (no decoration)."""
        x, y = widget.winfo_rootx(), widget.winfo_rooty()
        return (x, y, x + widget.winfo_width(), y + widget.winfo_height())

    # ------------------------------------------------------------------
    # Capture
    # ------------------------------------------------------------------
    @staticmethod
    def frame_rect(top: tk.Misc) -> Rect:
        """Screen rectangle of a toplevel with its window manager frame."""
        if isinstance(top, str):            # a Tcl-only toplevel (file dialog)
            wid = int(_ROOT[0].tk.call("wm", "frame", top), 16)
        elif hasattr(top, "wm_frame"):
            wid = int(top.wm_frame(), 16)
        else:
            wid = top.winfo_id()
        tree = subprocess.run(["xwininfo", "-tree", "-id", str(wid)],
                              capture_output=True, text=True).stdout
        parent = re.search(r"Parent window id: (0x[0-9a-f]+)( \(the root)?",
                           tree)
        target = wid if parent is None or parent.group(2) else \
            int(parent.group(1), 16)
        info = subprocess.run(["xwininfo", "-id", str(target)],
                              capture_output=True, text=True).stdout
        num = {key: int(re.search(rf"{key}:\s+(-?\d+)", info).group(1))
               for key in ("Absolute upper-left X", "Absolute upper-left Y",
                           "Width", "Height")}
        x, y = num["Absolute upper-left X"], num["Absolute upper-left Y"]
        return (x, y, x + num["Width"], y + num["Height"])

    def grab(self) -> Image.Image:
        """The whole screen, as it is now."""
        self.root.update_idletasks()
        self.root.update()
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "screen.png")
            subprocess.run(["import", "-window", "root", path], check=True)
            return Image.open(path).convert("RGB")

    def snap(self, out: Path, keep: list[Rect], *, numbers=(), arrows=(),
             pointers=(), patches=(), margin=24, boxes=(),
             labels=()) -> None:
        """Capture the screen and compose the screenshot `out`.

        keep      rectangles that must be in the picture (windows, menus...)
        patches   (image, rect) pieces of earlier grabs pasted over the
                  capture, e.g. a menu that had to be closed to open the
                  dialog it leads to
        numbers   (n, x, y): a numbered circle centred at x, y
        arrows    (x0, y0, x1, y1): from the circle to what it designates
        pointers  (x, y): a mouse pointer whose tip is at x, y
        boxes     (rect, colour): a highlight frame around a rectangle
        labels    (text, x, y[, colour[, size[, anchor]]]): a caption
        """
        image = self.grab()
        for piece, rect in patches:
            image.paste(piece.crop(rect), rect[:2])
        draw = ImageDraw.Draw(image)
        for rect, colour in boxes:
            draw.rounded_rectangle(rect, radius=4, outline=colour, width=3)
        for x0, y0, x1, y1, *colour in arrows:
            _arrow(draw, x0, y0, x1, y1, *colour)
        for x, y in pointers:
            _pointer(draw, x, y)
        for text, x, y, *opt in labels:
            colour = opt[0] if len(opt) > 0 else ARROW_COLOR
            size = opt[1] if len(opt) > 1 else 16
            anchor = opt[2] if len(opt) > 2 else "lm"
            draw.text((x, y), text, fill=colour, anchor=anchor,
                      font=ImageFont.truetype(FONT_BOLD, size))
        font = ImageFont.truetype(FONT_BOLD, 22)
        circles = []
        for n, x, y in numbers:
            r = CIRCLE_RADIUS
            draw.ellipse((x - r, y - r, x + r, y + r), fill=CIRCLE_FILL,
                         outline=CIRCLE_OUTLINE, width=2)
            draw.text((x, y), str(n), fill=NUMBER_COLOR, font=font,
                      anchor="mm")
            circles.append((x - r, y - r, x + r, y + r))
        x0, y0, x1, y1 = union(*keep, *circles)
        crop = (max(0, x0 - margin), max(0, y0 - margin),
                min(image.width, x1 + margin), min(image.height, y1 + margin))
        if os.environ.get("SNAP_FULL"):
            image.save(out.with_suffix(".full.png"))
        image.crop(crop).save(out, optimize=True)
        print(f"  wrote {out.name} {crop[2] - crop[0]}x{crop[3] - crop[1]}")


def _arrow(draw: ImageDraw.ImageDraw, x0, y0, x1, y1,
           colour=ARROW_COLOR) -> None:
    """A line from x0, y0 ending in an arrow head at x1, y1."""
    import math
    draw.line((x0, y0, x1, y1), fill=colour, width=3)
    angle = math.atan2(y1 - y0, x1 - x0)
    size = 12
    left = (x1 - size * math.cos(angle - 0.45), y1 - size * math.sin(angle - 0.45))
    right = (x1 - size * math.cos(angle + 0.45), y1 - size * math.sin(angle + 0.45))
    draw.polygon((left, (x1, y1), right), fill=colour)


## The classic arrow cursor, tip at 0, 0.
_CURSOR = ((0, 0), (0, 17), (4, 13), (7, 20), (10, 19), (7, 12), (12, 12))


def _pointer(draw: ImageDraw.ImageDraw, x, y) -> None:
    draw.polygon([(x + px, y + py) for px, py in _CURSOR], fill="white",
                 outline="black")
