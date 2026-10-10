# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2024 Pablo Cardaba

"""A Tk canvas that speaks logical pixels.

The diagram is a document: amplitudes, paddings, marker positions and the
canvas scale are saved in the script, and must mean the same on every
screen. ``ScaledCanvas`` therefore keeps the UI scale (see ``uiscale``) out
of everything that draws on it or reads it back:

- coordinates, line widths, dashes, arrow shapes and fonts go *in* in logical
  pixels and are multiplied on the way to Tk;
- ``coords()``, ``bbox()`` (whole pixels), ``itemcget()``, ``canvasx()``/``canvasy()``,
  ``winfo_width()``/``winfo_height()`` and the ``x``/``y`` of pointer events
  come *out* in logical pixels.

So the signals, markers and the exporter are written as if the factor were
always 1.0, and a drawing exported at 200 % equals the one exported at
100 %. What stays in device pixels is what belongs to the widget rather
than to the drawing: the widget options (``width``, ``scrollregion``...),
``event.x_root``/``y_root`` and ``place()`` of a child widget; use
``to_device()`` for those.

With a factor of 1.0 every method is a plain pass-through.
"""

from __future__ import annotations

import tkinter as tk

import itertools
import math

from . import uiscale

## Names of the fonts created here. Tk's automatic "font<N>" names are also
## the ones tkinter's Font picks for itself.
_font_ids = itertools.count(1)

## Item options holding a distance.
_DISTANCE_OPTIONS = frozenset(
    ("width", "activewidth", "disabledwidth", "height", "arrowshape"))
_DASH_OPTIONS = frozenset(("dash", "activedash", "disableddash"))

## Items drawn with a 1 pixel outline when no width is given.
_OUTLINED_ITEMS = frozenset(("arc", "line", "oval", "polygon", "rectangle"))

_POINTER_EVENTS = frozenset((
    tk.EventType.ButtonPress, tk.EventType.ButtonRelease, tk.EventType.Motion,
    tk.EventType.Enter, tk.EventType.Leave, tk.EventType.MouseWheel))

_CREATE_METHODS = ("create_arc", "create_bitmap", "create_image",
                   "create_line", "create_oval", "create_polygon",
                   "create_rectangle", "create_text", "create_window")


class ScaledCanvas(tk.Canvas):

    def __init__(self, master=None, **kwargs) -> None:
        ## Fixed for the life of the widget: the items are drawn with it.
        self._ui: float = uiscale.scale()
        ## Font attributes -> (logical font name, device font name), and the
        ## way back for itemcget().
        self._ui_fonts: dict[tuple, tuple[str, str]] = {}
        self._ui_logical_font: dict[str, str] = {}
        ## Item id -> logical dash pattern. Tk can not be asked: it reads a
        ## pattern back truncated as soon as a number has two digits
        ## ("12 6" comes back as "12 "), which is what a scaled one has.
        self._ui_dash: dict[int, tuple] = {}
        super().__init__(master, **kwargs)
        if self._ui != 1.0:
            ## The frame around the drawing is part of the widget size the
            ## time scale is fitted to: it has to grow with the rest.
            for option in ("highlightthickness", "borderwidth"):
                self[option] = uiscale.px(int(float(self[option])))

    # ------------------------------------------------------------------
    # Conversions
    # ------------------------------------------------------------------
    def to_device(self, value: float) -> int:
        """Logical pixels -> device pixels, for what Tk takes unscaled."""
        if self._ui == 1.0:
            return value
        return round(value * self._ui)

    def device_bbox(self, *args):
        """``bbox()`` in device pixels (e.g. for the scrollregion)."""
        return tk.Canvas.bbox(self, *args)

    def _in(self, value):
        """Scale the numbers of a (possibly nested) coordinate list."""
        if isinstance(value, (tuple, list)):
            return [self._in(v) for v in value]
        if isinstance(value, dict):
            return self._options_in(value)
        if isinstance(value, bool):
            return value
        if isinstance(value, (int, float)):
            return value * self._ui
        if isinstance(value, str):
            try:
                return float(value) * self._ui
            except ValueError:
                return value
        return value

    def _out(self, values):
        if values is None:
            return None
        return type(values)(v / self._ui for v in values)

    @staticmethod
    def _dash_of(options: dict):
        """The logical dash pattern set by ``options``: a tuple, () when it
        is cleared, None when the options do not touch it."""
        for key, value in options.items():
            if key.lstrip("-") == "dash":
                if isinstance(value, (tuple, list)) and value:
                    return tuple(value)
                return ()
        return None

    def _options_in(self, options: dict) -> dict:
        scaled = {}
        for key, value in options.items():
            name = key.lstrip("-")
            if value is None or value == "":
                pass
            elif name in _DISTANCE_OPTIONS:
                if isinstance(value, str):
                    value = value.replace(",", " ").split()
                value = self._in(value)
                if isinstance(value, list) and len(value) == 1:
                    value = value[0]
            elif name in _DASH_OPTIONS:
                if isinstance(value, (tuple, list)):
                    value = tuple(max(1, round(v * self._ui)) for v in value)
            elif name == "font":
                value = self._device_font(value)
            scaled[key] = value
        return scaled

    # ------------------------------------------------------------------
    # Fonts
    # ------------------------------------------------------------------
    def _font_attributes(self, font) -> tuple:
        """(family, logical pixel size, weight, slant, underline, overstrike)
        of a font given as a named font or as a description."""
        names = self.tk.splitlist(self.tk.call("font", "names"))
        name = str(font)
        if name in names:
            raw = self.tk.splitlist(self.tk.call("font", "configure", name))
            cfg = {str(raw[i]).lstrip("-"): raw[i + 1] for i in range(0, len(raw), 2)}
            family, size = str(cfg["family"]), int(cfg["size"])
            weight, slant = str(cfg["weight"]), str(cfg["slant"])
            underline, overstrike = int(cfg["underline"]), int(cfg["overstrike"])
        else:
            parts = (list(font) if isinstance(font, (tuple, list))
                     else list(self.tk.splitlist(font)))
            family = str(parts[0]) if parts else "TkDefaultFont"
            try:
                size = int(parts[1])
            except (IndexError, ValueError):
                size = 0
            styles = [str(p) for p in parts[2:]]
            weight = "bold" if "bold" in styles else "normal"
            slant = "italic" if "italic" in styles else "roman"
            underline = int("underline" in styles)
            overstrike = int("overstrike" in styles)

        if size > 0:
            size = round(size * uiscale.PX_PER_POINT)
        elif size < 0:
            size = -size
        else:
            ## The platform default size: take what Tk resolves it to.
            points = int(self.tk.call("font", "actual", font, "-size"))
            size = round(abs(points) * uiscale.PX_PER_POINT)
        return family, size, weight, slant, underline, overstrike

    def _device_font(self, font) -> str:
        key = self._font_attributes(font)
        if key not in self._ui_fonts:
            family, size, weight, slant, underline, overstrike = key
            names = []
            for pixels in (size, max(1, round(size * self._ui))):
                names.append(str(self.tk.call(
                    "font", "create", f"TimeItCanvasFont{next(_font_ids)}",
                    "-family", family, "-size", -pixels,
                    "-weight", weight, "-slant", slant,
                    "-underline", underline, "-overstrike", overstrike)))
            self._ui_fonts[key] = (names[0], names[1])
            self._ui_logical_font[names[1]] = names[0]
        return self._ui_fonts[key][1]

    # ------------------------------------------------------------------
    # Items
    # ------------------------------------------------------------------
    def coords(self, *args):
        if self._ui == 1.0:
            return super().coords(*args)
        if len(args) > 1:
            args = (args[0], *self._in(args[1:]))
        return self._out(super().coords(*args))

    def bbox(self, *args):
        """Bounding box in whole logical pixels, rounded outwards: integers
        as Tk returns them, and the same ones at every scale."""
        box = super().bbox(*args)
        if self._ui == 1.0 or box is None:
            return box
        x1, y1, x2, y2 = box
        return (math.floor(x1 / self._ui), math.floor(y1 / self._ui),
                math.ceil(x2 / self._ui), math.ceil(y2 / self._ui))

    def move(self, *args):
        if self._ui != 1.0:
            args = (args[0], *self._in(args[1:]))
        return super().move(*args)

    def moveto(self, tagOrId, x="", y=""):
        if self._ui != 1.0:
            x, y = self._in(x), self._in(y)
        return super().moveto(tagOrId, x, y)

    def scale(self, *args):
        ## (tagOrId, xOrigin, yOrigin, xScale, yScale): only the origin is a
        ## coordinate.
        if self._ui != 1.0 and len(args) >= 3:
            args = (args[0], *self._in(args[1:3]), *args[3:])
        return super().scale(*args)

    def itemconfigure(self, tagOrId, cnf=None, **kw):
        if self._ui != 1.0:
            dash = self._dash_of({**(cnf if isinstance(cnf, dict) else {}), **kw})
            if dash is not None:
                for item in self.find_withtag(tagOrId):
                    self._ui_dash[item] = dash
            if isinstance(cnf, dict):
                cnf = self._options_in(cnf)
            kw = self._options_in(kw)
        return super().itemconfigure(tagOrId, cnf, **kw)

    itemconfig = itemconfigure

    def itemcget(self, tagOrId, option):
        value = super().itemcget(tagOrId, option)
        if self._ui == 1.0 or value in (None, ""):
            return value
        name = option.lstrip("-")
        if name == "font":
            return self._ui_logical_font.get(str(value), value)
        if name in _DISTANCE_OPTIONS:
            try:
                parts = [float(p) / self._ui for p in str(value).split()]
            except ValueError:
                return value
            if len(parts) == 1:
                return str(parts[0])        # "2.0", as Tk writes a width
            return " ".join(f"{p:g}" for p in parts)
        if name == "dash":
            items = self.find_withtag(tagOrId)
            dash = self._ui_dash.get(items[0]) if items else None
            if dash:
                return " ".join(str(d) for d in dash)
        return value

    def delete(self, *args):
        if self._ui_dash:
            if "all" in args:
                self._ui_dash.clear()
            else:
                for tag in args:
                    for item in self.find_withtag(tag):
                        self._ui_dash.pop(item, None)
        return super().delete(*args)

    # ------------------------------------------------------------------
    # Searching and view
    # ------------------------------------------------------------------
    def find_overlapping(self, x1, y1, x2, y2):
        if self._ui != 1.0:
            x1, y1, x2, y2 = self._in((x1, y1, x2, y2))
        return super().find_overlapping(x1, y1, x2, y2)

    def find_enclosed(self, x1, y1, x2, y2):
        if self._ui != 1.0:
            x1, y1, x2, y2 = self._in((x1, y1, x2, y2))
        return super().find_enclosed(x1, y1, x2, y2)

    def find_closest(self, x, y, halo=None, start=None):
        if self._ui != 1.0:
            x, y = self._in((x, y))
            if halo is not None:
                halo = self._in(halo)
        return super().find_closest(x, y, halo, start)

    def canvasx(self, screenx, gridspacing=None):
        """Logical canvas x of a logical widget x (an ``event.x``)."""
        if self._ui == 1.0:
            return super().canvasx(screenx, gridspacing)
        return super().canvasx(screenx * self._ui, gridspacing) / self._ui

    def canvasy(self, screeny, gridspacing=None):
        if self._ui == 1.0:
            return super().canvasy(screeny, gridspacing)
        return super().canvasy(screeny * self._ui, gridspacing) / self._ui

    def winfo_width(self):
        """Width of the widget in logical pixels: the drawing code fits the
        time scale to it."""
        width = super().winfo_width()
        return width if self._ui == 1.0 else max(1, round(width / self._ui))

    def winfo_height(self):
        height = super().winfo_height()
        return height if self._ui == 1.0 else max(1, round(height / self._ui))

    # ------------------------------------------------------------------
    # Events
    # ------------------------------------------------------------------
    def _logical_events(self, func):
        """Wrap a handler so that pointer events carry logical ``x``/``y``."""
        if self._ui == 1.0 or not callable(func):
            return func

        def handler(event):
            if event.type in _POINTER_EVENTS:
                ## Whole logical pixels: the drags accumulate them into
                ## offsets that are saved as integers.
                if isinstance(event.x, int):
                    event.x = round(event.x / self._ui)
                if isinstance(event.y, int):
                    event.y = round(event.y / self._ui)
            return func(event)

        return handler

    def bind(self, sequence=None, func=None, add=None):
        return super().bind(sequence, self._logical_events(func), add)

    def tag_bind(self, tagOrId, sequence=None, func=None, add=None):
        return super().tag_bind(tagOrId, sequence, self._logical_events(func), add)


def _make_create(name: str):
    original = getattr(tk.Canvas, name)
    kind = name[len("create_"):]

    def create(self, *args, **kw):
        if self._ui == 1.0:
            return original(self, *args, **kw)
        dash = self._dash_of(kw)
        if kind in _OUTLINED_ITEMS and "width" not in kw:
            ## Tk's default is one device pixel.
            kw["width"] = 1
        item = original(self, *self._in(args), **self._options_in(kw))
        if dash:
            self._ui_dash[item] = dash
        return item

    create.__name__ = name
    create.__doc__ = original.__doc__
    return create


for _name in _CREATE_METHODS:
    setattr(ScaledCanvas, _name, _make_create(_name))
