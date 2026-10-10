# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2024 Pablo Cardaba

"""Where a dialog opens: over the window it was asked from.

A toplevel that does not ask for a position gets the one the window manager
likes: a cascade slot of the primary monitor on Windows, the middle of some
monitor on X11. With two screens the dialog then comes up on the one the
application is not on. Every dialog therefore asks for its position before it
is shown (``place``): centred over its owner or, for a window meant to be
used together with its owner, next to it.

The position is kept inside the monitor the owner is on. Tk only knows the
whole desktop (the *virtual root*, all the monitors together), so the
monitors are asked to the system: ``xrandr`` on X11, the Win32 API on
Windows. When they can not be told, the desktop is the limit.

All the sizes here are device pixels (they come from and go to ``winfo`` and
``wm geometry``), except the gap, which is logical.
"""

from __future__ import annotations

import re
import subprocess
import sys
import tkinter as tk

from . import uiscale

## A rectangle: (x, y, width, height).
Rect = tuple[int, int, int, int]

## Logical pixels between a window and the one placed beside it.
GAP = 8

## The position in a `wm geometry` ("804x360+3600+-20"), from the top left
## corner of the desktop; a position from the right or the bottom is not read.
_WM_POSITION = re.compile(r"\+(-?\d+)\+(-?\d+)$")

## Device pixels a frame can sensibly add on one side: more is not a frame.
_MAX_DECORATION = 400

## A monitor in `xrandr --listmonitors`:
##  " 0: +*DP-0 2560/597x1440/336+1920+0  DP-0" -> 2560x1440 at +1920+0
_XRANDR_MONITOR = re.compile(r"\s(\d+)/\d+x(\d+)/\d+\+(-?\d+)\+(-?\d+)\s")


# ----------------------------------------------------------------------
# Geometry (no Tk)
# ----------------------------------------------------------------------
def _clamp(x: int, y: int, size: tuple[int, int], screen: Rect) -> tuple[int, int]:
    """(x, y) moved so a window of ``size`` is inside ``screen``. A window
    larger than the screen keeps its top left corner (its title bar) in."""
    width, height = size
    sx, sy, swidth, sheight = screen
    x = max(sx, min(x, sx + swidth - width))
    y = max(sy, min(y, sy + sheight - height))
    return x, y


def centered(size: tuple[int, int], owner: Rect, screen: Rect) -> tuple[int, int]:
    """Top left corner of a window of ``size`` centred over ``owner``."""
    width, height = size
    ox, oy, owidth, oheight = owner
    return _clamp(ox + (owidth - width) // 2, oy + (oheight - height) // 2,
                  size, screen)


def beside(size: tuple[int, int], owner: Rect, screen: Rect,
           gap: int = 0) -> tuple[int, int]:
    """Top left corner of a window of ``size`` next to ``owner``, their tops
    level: on its right, else on its left, else on the side with more room
    (the two then overlap as little as the screen allows)."""
    width = size[0]
    ox, oy, owidth, _ = owner
    sx, _, swidth, _ = screen
    room_right = sx + swidth - (ox + owidth)
    room_left = ox - sx
    if room_right >= width + gap:
        x = ox + owidth + gap
    elif room_left >= width + gap:
        x = ox - gap - width
    elif room_right >= room_left:
        x = sx + swidth - width
    else:
        x = sx
    return _clamp(x, oy, size, screen)


def parse_xrandr_monitors(text: str) -> list[Rect]:
    """The monitors listed by ``xrandr --listmonitors``."""
    return [(int(x), int(y), int(width), int(height))
            for width, height, x, y in _XRANDR_MONITOR.findall(text)]


def monitor_of(owner: Rect, monitors: list[Rect]) -> Rect | None:
    """The monitor showing the largest part of ``owner``, None when it is on
    none of them."""
    ox, oy, owidth, oheight = owner
    best, best_area = None, 0
    for monitor in monitors:
        mx, my, mwidth, mheight = monitor
        shared_w = min(ox + owidth, mx + mwidth) - max(ox, mx)
        shared_h = min(oy + oheight, my + mheight) - max(oy, my)
        if shared_w > 0 and shared_h > 0 and shared_w * shared_h > best_area:
            best, best_area = monitor, shared_w * shared_h
    return best


# ----------------------------------------------------------------------
# The screen a window is on
# ----------------------------------------------------------------------
def _x11_monitors() -> list[Rect]:
    try:
        out = subprocess.run(["xrandr", "--listmonitors"], capture_output=True,
                             text=True, timeout=2, check=False).stdout
    except (OSError, subprocess.SubprocessError):
        return []
    return parse_xrandr_monitors(out)


def _win32_work_area(owner: Rect) -> Rect | None:
    """Windows: the work area (the monitor less the taskbar) of the monitor
    showing the largest part of ``owner``."""
    try:
        import ctypes
        from ctypes import wintypes

        class MonitorInfo(ctypes.Structure):
            _fields_ = [("cbSize", wintypes.DWORD),
                        ("rcMonitor", wintypes.RECT),
                        ("rcWork", wintypes.RECT),
                        ("dwFlags", wintypes.DWORD)]

        ## A private handle: the argument types set here stay out of
        ## `ctypes.windll.user32`, which is shared by the whole process.
        user32 = ctypes.WinDLL("user32")
        user32.MonitorFromRect.restype = wintypes.HANDLE
        user32.MonitorFromRect.argtypes = [ctypes.POINTER(wintypes.RECT),
                                           wintypes.DWORD]
        user32.GetMonitorInfoW.restype = wintypes.BOOL
        user32.GetMonitorInfoW.argtypes = [wintypes.HANDLE,
                                           ctypes.POINTER(MonitorInfo)]

        ox, oy, owidth, oheight = owner
        rect = wintypes.RECT(ox, oy, ox + owidth, oy + oheight)
        nearest = 2  # MONITOR_DEFAULTTONEAREST
        monitor = user32.MonitorFromRect(ctypes.byref(rect), nearest)
        info = MonitorInfo()
        info.cbSize = ctypes.sizeof(MonitorInfo)
        if not monitor or not user32.GetMonitorInfoW(monitor, ctypes.byref(info)):
            return None
        work = info.rcWork
        return (work.left, work.top, work.right - work.left, work.bottom - work.top)
    except (ImportError, AttributeError, OSError, ValueError):
        return None


def screen_of(window: tk.Misc, owner: Rect) -> Rect:
    """The rectangle a window opened from ``owner`` has to stay in: the
    monitor ``owner`` is on, the whole desktop when it can not be told."""
    screen = None
    if sys.platform == "win32":
        screen = _win32_work_area(owner)
    elif sys.platform != "darwin":
        screen = monitor_of(owner, _x11_monitors())
    if screen is None:
        screen = (window.winfo_vrootx(), window.winfo_vrooty(),
                  window.winfo_vrootwidth(), window.winfo_vrootheight())
    return screen


# ----------------------------------------------------------------------
# Placing
# ----------------------------------------------------------------------
def _decoration(toplevel: tk.Misc) -> tuple[int, int, int, int]:
    """Where the frame the window manager puts around ``toplevel`` starts,
    and how thick it is: (x, y, border, top).

    ``wm geometry`` positions the corner of that frame, ``winfo_rootx/y`` is
    the corner of the content: the difference is the side border and what is
    above the content (title bar and, on the main window, the menu bar).
    Without a frame, or when it can not be told, the content is all there is.
    """
    x, y = toplevel.winfo_rootx(), toplevel.winfo_rooty()
    match = _WM_POSITION.search(toplevel.wm_geometry())
    if match is None:
        return x, y, 0, 0
    border, top = x - int(match.group(1)), y - int(match.group(2))
    if not (0 <= border <= _MAX_DECORATION and 0 <= top <= _MAX_DECORATION):
        return x, y, 0, 0
    return x - border, y - top, border, top


def place(window: tk.Misc, owner: tk.Misc, side: bool = False) -> None:
    """Show the toplevel ``window`` over the toplevel of ``owner``: centred,
    or next to it with ``side`` (for a window used together with its owner).

    Call it once the content of ``window`` is built and before anything
    waits for it to be visible. The window stays hidden until its position
    is known, so it is not seen jumping from the place the window manager
    gave it. An owner that is not on screen leaves the choice to the window
    manager, as before.

    Both windows are measured with their frames, and ``window`` is given the
    frame of its owner: the bottom border is taken to be as thick as the
    side ones, and the menu bar of the main window counts as title. That is
    a little more than a dialog has, which only keeps it further from the
    edge of the screen.
    """
    window.wm_withdraw()
    window.update_idletasks()  # the size the content asks for
    anchor = owner.winfo_toplevel()
    if anchor.winfo_viewable():
        x, y, border, top = _decoration(anchor)
        extra = (2 * border, top + border)
        size = (window.winfo_reqwidth() + extra[0],
                window.winfo_reqheight() + extra[1])
        over = (x, y, anchor.winfo_width() + extra[0],
                anchor.winfo_height() + extra[1])
        screen = screen_of(window, over)
        if side:
            x, y = beside(size, over, screen, uiscale.px(GAP))
        else:
            x, y = centered(size, over, screen)
        window.wm_geometry(f"+{x}+{y}")
    window.wm_deiconify()
