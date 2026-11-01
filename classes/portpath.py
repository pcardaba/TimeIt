# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2024 Pablo Cardaba

"""File names that survive a trip between operating systems.

Saved diagrams are Tcl scripts and some commands name files in them
(``create_pwl -files``, ``export_canvas -file``...). A script written on Linux
has to load on Windows and the other way round, so a file name in a script
follows these rules, whatever the system that wrote or reads it:

* ``/`` is the separator written. ``\\`` is read as a separator too, so a
  name typed on Windows (``pwl\\vdd.pwl``) also works on Linux.
* A relative name is relative to the directory of the script that holds it,
  which is how a diagram travels together with its files. TimeIt writes every
  name relative to the saved script when the file allows it (same drive).
* An absolute name only means something on the system that wrote it. When it
  does not exist here, its trailing components are looked up from the
  directory of the script (``/home/me/proj/pwl/vdd.pwl`` read from
  ``D:/work/proj/diagram.tcl`` finds ``D:/work/proj/pwl/vdd.pwl``).
* Windows ignores the case of file names and Linux does not: a name whose
  case does not match the file on disk still finds it when the match is
  unambiguous.

This module is Tk-free (pure ``os``/``pathlib``) so it is unit tested alone.
"""

from __future__ import annotations

import os
import re
from pathlib import Path

## "C:" or "C:/..." (a Windows drive), on any system.
_DRIVE = re.compile(r"^[A-Za-z]:(?=/|$)")


def normalize(name: str) -> str:
    """``name`` with ``/`` separators and no repeated separator.

    The leading ``//`` of a Windows UNC name (``//server/share``) is kept.
    Nothing is resolved: a relative name stays relative.
    """
    text = str(name).strip().replace("\\", "/")
    unc = text.startswith("//")
    text = re.sub(r"/{2,}", "/", text)
    if unc:
        text = "/" + text
    return text


def native(name: str) -> str:
    """``name`` usable by ``open()`` here: normalized, ``~`` expanded.

    For the files a command writes (``export_canvas -file``...), whose
    relative names stay relative to the working directory.
    """
    return os.path.expanduser(normalize(name))


def is_absolute(name: str) -> bool:
    """True for an absolute name of *any* system (``/x``, ``~/x``, ``C:/x``,
    ``//server/share``), not only of the running one."""
    text = normalize(name)
    return text.startswith(("/", "~")) or bool(_DRIVE.match(text))


def _tail_parts(text: str) -> list[str]:
    """Components of a normalized absolute name, without its anchor (root,
    drive, ``~user`` or UNC ``//server/share``)."""
    if text.startswith("//"):
        text = "/".join(text[2:].split("/")[2:])
    elif text.startswith("~"):
        text = text.partition("/")[2]
    elif _DRIVE.match(text):
        text = text[2:]
    return [part for part in text.split("/") if part not in ("", ".")]


def _match_case(path: Path) -> Path | None:
    """``path`` with the case of each component fixed from the disk.

    Walks down from the deepest existing parent; a component that is not
    found as written is taken from the directory listing when exactly one
    entry matches it ignoring case. None when that fails.
    """
    anchor = path
    missing: list[str] = []
    while not anchor.exists():
        if anchor.parent == anchor:
            return None
        missing.insert(0, anchor.name)
        anchor = anchor.parent
    current = anchor
    for part in missing:
        exact = current / part
        if exact.exists():
            current = exact
            continue
        try:
            entries = os.listdir(current)
        except OSError:
            return None
        folded = part.casefold()
        found = [entry for entry in entries if entry.casefold() == folded]
        if len(found) != 1:
            return None
        current = current / found[0]
    return current


def locate(name: str, base_dir: str | Path | None = None) -> tuple[Path, bool]:
    """The file ``name`` designates in a script whose directory is
    ``base_dir`` (None: the working directory).

    Returns ``(path, relocated)``: ``path`` is absolute (symbolic links are
    kept, ``..`` is folded). ``relocated`` is True when the file was found
    elsewhere than where ``name`` literally points, by its trailing
    components under ``base_dir`` or ignoring case. When nothing exists, the
    literal place is returned, so that the error names what was asked for.
    """
    raw = str(name).strip()
    text = normalize(raw)
    absolute = is_absolute(text)
    base = Path(base_dir) if base_dir is not None else Path.cwd()

    def place(candidate: str) -> Path:
        path = Path(os.path.expanduser(candidate))
        if not path.is_absolute():
            ## A foreign absolute name (C:/x on Linux, /x on Windows) is
            ## not anchored here: taken as is, it is relative to the working
            ## directory or the current drive, and it is relocated below.
            path = path if absolute else base / path
        return Path(os.path.abspath(path))

    literal = place(text)
    if literal.exists():
        return literal, False
    ## On Linux "\" is a valid character of a file name: such a file exists
    ## under the name as typed.
    if raw != text and os.sep == "/":
        verbatim = place(raw)
        if verbatim.exists():
            return verbatim, False

    candidates: list[Path] = []
    if absolute:
        parts = _tail_parts(text)
        candidates = [Path(os.path.abspath(base.joinpath(*parts[i:])))
                      for i in range(len(parts))]
    else:
        candidates = [literal]
    for candidate in candidates:
        if candidate.is_file():
            return candidate, True
    for candidate in candidates:
        fixed = _match_case(candidate)
        if fixed is not None and fixed.is_file():
            return Path(os.path.abspath(fixed)), True
    return literal, False


def resolve(name: str, base_dir: str | Path | None = None) -> Path:
    """The absolute path of ``name`` (see ``locate``)."""
    return locate(name, base_dir)[0]


def for_script(path: str | Path, base_dir: str | Path | None) -> str:
    """How a script in ``base_dir`` names the file at ``path``.

    Relative to ``base_dir`` with ``/`` separators whenever possible, which
    is what makes a diagram portable. Absolute (still with ``/``) when there
    is no ``base_dir`` or when the file is on another Windows drive.
    """
    path = os.path.abspath(os.path.expanduser(str(path)))
    if base_dir is not None:
        try:
            return normalize(os.path.relpath(path, os.path.abspath(base_dir)))
        except ValueError:      # another drive: no relative path exists
            pass
    return normalize(path)
