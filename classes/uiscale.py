# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2024 Pablo Cardaba

"""UI scale: one factor behind every pixel size of the application.

Tk draws in device pixels and knows nothing about the scaling the desktop
applies to other toolkits, so on a HiDPI screen the application comes out
tiny (Linux) or bitmap-stretched and blurry (Windows). The application
therefore owns its scaling: every size is written in *logical* pixels, the
pixels of a 96 dpi screen at 100 %, and multiplied by one factor on the way
to Tk.

The factor is 1.0 until ``setup()`` runs (``main.py`` calls it), so anything
that boots a ``TimeItApp`` on its own Tk root, the tests first of all, keeps
the unscaled behaviour unless it asks otherwise with ``set_scale()``.

Fonts are the reason this can not be left to Tk: a size in points is turned
into pixels from the real dpi on Windows and from ``Xft.dpi`` on X11, and the
two disagree. A size in pixels (negative, for Tk) bypasses both, so every
scaled font is given in pixels.

Nothing saved or exported depends on the factor: scripts, settings and the
exported drawings stay in logical pixels (see ``ScaledCanvas``).
"""

from __future__ import annotations

import os
import subprocess
import sys
import tkinter as tk
from tkinter import font as tkfont
from tkinter import ttk

## Environment variable that forces the factor (e.g. TIMEIT_SCALE=1.5).
ENV_VAR = "TIMEIT_SCALE"

MIN_SCALE = 1.0
MAX_SCALE = 4.0

## Logical pixels per point: the 96 dpi of an unscaled screen.
PX_PER_POINT = 96.0 / 72.0

_scale: float = 1.0
_layout_patched: bool = False


# ----------------------------------------------------------------------
# The factor
# ----------------------------------------------------------------------
def scale() -> float:
    """The current UI scale factor (1.0 = unscaled)."""
    return _scale


def set_scale(value: float) -> None:
    """Force the factor. ``setup()`` does it for the application; tests call
    it directly, before the widgets are created."""
    global _scale
    _scale = _normalize(value)
    if _scale != 1.0:
        _patch_layout()


def _normalize(value: float) -> float:
    value = min(max(float(value), MIN_SCALE), MAX_SCALE)
    ## A dpi a few percent off 96 is not a scaled desktop.
    return 1.0 if value < 1.05 else round(value, 2)


def px(value):
    """Logical pixels -> device pixels (an int, never rounded down to 0)."""
    if _scale == 1.0:
        return value
    scaled = round(value * _scale)
    if scaled == 0 and value:
        return 1 if value > 0 else -1
    return scaled


def unpx(value):
    """Device pixels -> logical pixels (an int)."""
    if _scale == 1.0:
        return value
    return round(value / _scale)


# ----------------------------------------------------------------------
# Fonts and images
# ----------------------------------------------------------------------
def font_size(points: int) -> int:
    """Tk font size of a widget font of ``points`` (logical) points."""
    if _scale == 1.0 or points <= 0:
        return points
    return -round(points * PX_PER_POINT * _scale)


def logical_font_size(points: int) -> int:
    """Tk font size of a canvas font: logical pixels, which ``ScaledCanvas``
    scales when it draws. Unlike points, they measure the same on every
    platform, and the drawing code lays text out from those measures."""
    if _scale == 1.0 or points <= 0:
        return points
    return -round(points * PX_PER_POINT)


def font(family: str, points: int, *styles: str) -> tuple:
    """A widget font description, e.g. ``font("TkFixedFont", 9, "bold")``.

    ``points`` 0 is the size of the default font, as for Tk.
    """
    size = font_size(points)
    if points == 0 and _scale != 1.0:
        ## Tk's own "default size" is not scaled: take the default font's.
        size = int(tkfont.nametofont("TkDefaultFont").cget("size"))
    return (family, size) + styles


def load_image(path) -> tk.PhotoImage:
    """A PhotoImage enlarged to the UI scale.

    Tk only zooms images by whole factors, so a fractional scale uses the
    nearest one (150 % doubles the image, 125 % leaves it as it is).
    """
    image = tk.PhotoImage(file=str(path))
    factor = round(_scale)
    if factor > 1:
        image = image.zoom(factor)
    return image


# ----------------------------------------------------------------------
# Detection
# ----------------------------------------------------------------------
def enable_dpi_awareness() -> None:
    """Windows: declare the process DPI aware. Call before ``tk.Tk()``.

    Without it Windows reports 96 dpi and stretches the window bitmap, which
    is readable but blurry. No-op on the other systems.
    """
    if sys.platform != "win32":
        return
    try:
        import ctypes
        ctypes.windll.shcore.SetProcessDpiAwareness(1)
    except (ImportError, AttributeError, OSError):
        pass


def _font_dpi(root: tk.Misc) -> float:
    """The dpi Tk turns font points into pixels with.

    Measured rather than read, so that it holds on every platform: the real
    dpi on Windows, ``Xft.dpi`` on X11. Tk reports the size of a font given
    in pixels back in points.
    """
    pixels = 720
    try:
        points = float(root.tk.call("font", "actual", ("Helvetica", -pixels), "-size"))
    except (tk.TclError, ValueError):
        return 96.0
    if points <= 0:
        return 96.0
    return 72.0 * pixels / points


def _xfce_window_scale() -> int:
    """XFCE's window scaling factor (1 when it can not be read).

    XFCE scales GTK windows by this integer and leaves ``Xft.dpi`` alone, so
    it is invisible to Tk and has to be asked for.
    """
    if "XFCE" not in os.environ.get("XDG_CURRENT_DESKTOP", "").upper():
        return 1
    try:
        out = subprocess.run(
            ["xfconf-query", "-c", "xsettings", "-p", "/Gdk/WindowScalingFactor"],
            capture_output=True, text=True, timeout=2, check=False).stdout
        return max(1, int(out.strip()))
    except (OSError, ValueError, subprocess.SubprocessError):
        return 1


def detect(root: tk.Misc) -> float:
    """The factor this desktop asks for.

    ``TIMEIT_SCALE`` wins. Otherwise the font dpi gives it (Windows once DPI
    aware, and the X11 desktops that scale through ``Xft.dpi``), times the
    window scaling factor on XFCE.
    """
    forced = os.environ.get(ENV_VAR, "").strip()
    if forced:
        try:
            return _normalize(float(forced))
        except ValueError:
            pass

    ## macOS scales Tk windows itself (Tk works in points there).
    if sys.platform == "darwin":
        return 1.0

    value = _font_dpi(root) / 96.0
    if sys.platform != "win32":
        xfce = _xfce_window_scale()
        if xfce > 1:
            value *= xfce
        else:
            ## Other desktops export the GTK factor; most of them already
            ## fold it into Xft.dpi, hence not a product.
            try:
                value = max(value, float(os.environ.get("GDK_SCALE", "")))
            except ValueError:
                pass
    return _normalize(value)


# ----------------------------------------------------------------------
# Applying it
# ----------------------------------------------------------------------
def setup(root: tk.Misc, value: float | None = None) -> float:
    """Detect (or take) the factor and scale what Tk owns on ``root``: the
    named fonts every widget and menu defaults to, and the sizes of the
    classic widgets. Call once, before the application widgets are created.
    """
    set_scale(detect(root) if value is None else value)
    if _scale == 1.0:
        return _scale

    for name in tkfont.names(root):
        named = tkfont.nametofont(name, root=root)
        size = int(named.cget("size"))
        if size > 0:
            ## Points: converted from the logical 96 dpi, whatever dpi Tk
            ## would have used by itself.
            named.configure(size=font_size(size))
        elif size < 0:
            named.configure(size=-px(-size))

    root.option_add("*Scrollbar.width", px(11))
    root.option_add("*Panedwindow.sashWidth", px(3))
    return _scale


## Sizes of the ttk theme elements, as (style, option, default). The default
## is used when the theme does not set the option (clam leaves most unset).
_TTK_SIZES = (
    ("TCheckbutton", "indicatorsize", 10),
    ("TRadiobutton", "indicatorsize", 10),
    ("TCombobox", "arrowsize", 12),
    ("TSpinbox", "arrowsize", 10),
    ("TScrollbar", "arrowsize", 14),
    ("Sash", "sashthickness", 6),
    ("Treeview", "indent", 20),
)

_TTK_PADDINGS = ("TButton", "TMenubutton", "TEntry", "TCombobox",
                 "TCheckbutton", "TRadiobutton", "TNotebook.Tab", "Heading")


def apply_ttk_style(style: ttk.Style) -> None:
    """Scale the pixel sizes of the current ttk theme. Call after
    ``theme_use()``: a theme switch resets them."""
    if _scale == 1.0:
        return

    for name, option, default in _TTK_SIZES:
        try:
            value = float(style.lookup(name, option) or default)
        except (ValueError, tk.TclError):
            value = default
        style.configure(name, **{option: px(value)})

    for name in _TTK_PADDINGS:
        padding = str(style.lookup(name, "padding") or "").split()
        try:
            scaled = [px(float(p)) for p in padding]
        except ValueError:
            continue
        if scaled:
            style.configure(name, padding=scaled)

    ## Rows follow the (already scaled) font instead of a fixed height.
    linespace = tkfont.nametofont("TkDefaultFont", root=style.master).metrics("linespace")
    style.configure("Treeview", rowheight=linespace + px(3))


# ----------------------------------------------------------------------
# Geometry managers
# ----------------------------------------------------------------------
def _scale_distance(value):
    if isinstance(value, (tuple, list)):
        return tuple(_scale_distance(v) for v in value)
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return px(value)
    if isinstance(value, str):
        ## "5" or "5 10" are pixels; "2m", "1c"... are physical distances
        ## that Tk converts by itself.
        parts = value.split()
        if parts and all(p.lstrip("-").isdigit() for p in parts):
            return " ".join(str(px(int(p))) for p in parts)
    return value


def _scale_options(cnf, kw, keys):
    if isinstance(cnf, dict) and cnf:
        cnf = {k: _scale_distance(v) if k in keys else v for k, v in cnf.items()}
    for key in keys:
        if key in kw:
            kw[key] = _scale_distance(kw[key])
    return cnf, kw


def _patch_layout() -> None:
    """Make ``grid``/``pack`` paddings and row/column minimum sizes logical.

    The dialogs set hundreds of them; scaling each one where it is written
    would leave the next one forgotten. Tkinter funnels them all through the
    few methods wrapped here, which multiply on the way in (only while the
    factor is not 1.0). ``grid_info()``/``pack_info()`` still report device
    pixels: do not feed them back into ``grid()``/``pack()``.
    """
    global _layout_patched
    if _layout_patched:
        return
    _layout_patched = True

    pad_keys = ("padx", "pady", "ipadx", "ipady")
    line_keys = ("minsize", "pad")

    def wrap_widget(original, keys):
        def configure(self, cnf={}, **kw):
            if _scale != 1.0:
                cnf, kw = _scale_options(cnf, kw, keys)
            return original(self, cnf, **kw)
        configure.__name__ = original.__name__
        configure.__doc__ = original.__doc__
        return configure

    def wrap_line(original, keys):
        def configure(self, index, cnf={}, **kw):
            if _scale != 1.0:
                cnf, kw = _scale_options(cnf, kw, keys)
            return original(self, index, cnf, **kw)
        configure.__name__ = original.__name__
        configure.__doc__ = original.__doc__
        return configure

    grid = wrap_widget(tk.Grid.grid_configure, pad_keys)
    tk.Grid.grid_configure = tk.Grid.grid = grid
    pack = wrap_widget(tk.Pack.pack_configure, pad_keys)
    tk.Pack.pack_configure = tk.Pack.pack = pack

    column = wrap_line(tk.Misc.grid_columnconfigure, line_keys)
    tk.Misc.grid_columnconfigure = tk.Misc.columnconfigure = column
    row = wrap_line(tk.Misc.grid_rowconfigure, line_keys)
    tk.Misc.grid_rowconfigure = tk.Misc.rowconfigure = row
