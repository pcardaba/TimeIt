from __future__ import annotations

from pathlib import Path
from typing import Any, Dict

import tkinter as tk

from .signal import Signal
from .pwlsignal import PWLSignal, PWLTrace, PWLFileError
from .tclcommandbase import TclCommandBase, OptSpec


class TclCreatePwl(TclCommandBase):
    """create_pwl: a waveform slot holding one or more PWL (analog) traces."""

    command_name = "create_pwl"

    def __init__(self, tcl):
        super().__init__(tcl)
        self.defaults = {"visible": False}
        self.spec = {
            "-files":   OptSpec("files", True, self._split_list),
            "-names":   OptSpec("names", True, self._split_list),
            "-height":  OptSpec("height", True, int),
            "-lwidth":  OptSpec("lwidth", True, int),
            "-use_uid": OptSpec("uid", True, int),
            "-visible": OptSpec("visible", False, lambda _: True),
        }

    # ----------------------------
    # Helpers
    # ----------------------------
    def _split_list(self, raw) -> list[str]:
        """A Tcl list into Python strings (file names may hold spaces)."""
        return [str(item) for item in self.console.interp.splitlist(str(raw))]

    def _script_dir(self) -> Path | None:
        """Directory of the script being sourced (None from the console).

        Relative PWL file paths are resolved against it, so a saved diagram
        can travel together with its PWL files.
        """
        try:
            script = self.console.interp.eval("info script")
        except tk.TclError:
            return None
        if not script:
            return None
        return Path(script).resolve().parent

    def _existing_slot(self, opts: Dict[str, Any]) -> PWLSignal | None:
        """The slot this command updates, None when it creates a new one."""
        uid = opts.get("uid")
        if uid is not None:
            found = self.topapp.signals.find_by_uid(str(uid))
            if found is not None:
                if found.type != "pwl":
                    raise ValueError(
                        f"uid {uid} belongs to {found.name}, which is not a "
                        f"PWL signal")
                return found
        found = self.topapp.signals.find(opts["names"][0])
        if found is not None and found.type != "pwl":
            raise ValueError(
                f"{found.name} already exists and is not a PWL signal")
        return found

    def _find_name_owner(self, name: str) -> Signal | None:
        """The signal (or PWL slot) already using `name`."""
        owner = self.topapp.signals.find(name)
        if owner is not None:
            return owner
        for sig in self.topapp.signals.values():
            if sig.type == "pwl" and sig.find_trace(name) is not None:
                return sig
        return None

    # ----------------------------
    # Validation / execution
    # ----------------------------
    def validate(self, opts: Dict[str, Any]) -> None:
        self.require(opts, "files", "names")
        names = opts["names"]
        files = opts["files"]
        if len(names) != len(files):
            raise ValueError(
                f"-names has {len(names)} entries but -files has "
                f"{len(files)}: both lists must have the same length")
        if len(set(names)) != len(names):
            raise ValueError("-names contains duplicated names")

        height = opts.get("height")
        if height is not None and height < 10:
            raise ValueError("-height must be >= 10 pixels")
        lwidth = opts.get("lwidth")
        if lwidth is not None and lwidth < 1:
            raise ValueError("-lwidth must be >= 1")

        slot = self._existing_slot(opts)
        ## Signal names are unique diagram-wide, traces included.
        for name in names:
            owner = self._find_name_owner(name)
            if owner is not None and owner is not slot:
                raise ValueError(f"signal name {name} already exists")

    def execute(self, opts: Dict[str, Any]) -> str:
        names: list[str] = opts["names"]
        files: list[str] = opts["files"]
        slot = self._existing_slot(opts)

        ## Every file is read before anything is modified: an unreadable
        ## file leaves the diagram untouched.
        tunits = self.topapp.settings.waveform["tunits"]
        base_dir = self._script_dir()
        traces: list[PWLTrace] = []
        for name, file in zip(names, files):
            trace = PWLTrace(name, file)
            try:
                trace.load(tunits, base_dir)
            except PWLFileError as exc:
                raise ValueError(f"-files: {exc}") from exc
            if slot is not None:
                old = slot.find_trace(name)
                if old is not None:
                    trace.copy_style_from(old)
            traces.append(trace)

        uid = opts.get("uid")
        if uid is not None and Signal.static_id <= uid:
            Signal.static_id = uid + 1

        if slot is None:
            slot = PWLSignal(names[0])
            slot.set_tcl_console(self.console)
            if uid is not None:
                slot.uid = uid
            new = True
        else:
            new = False

        slot.traces = traces
        ## Value markers on a trace that went away go with it.
        for key, marker in list(slot.vmarkers.items()):
            if marker.trace_name not in names:
                del slot.vmarkers[key]

        self.apply_attrs(slot, opts, skip={"names", "files", "uid"})

        if new:
            self.topapp.signals.add(slot.name, slot)
        elif slot.name != names[0]:
            self.topapp.signals.rename(slot.name, names[0])
            slot.name = names[0]

        self.topapp.redraw()
        return ""
