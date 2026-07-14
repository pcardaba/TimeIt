# This class implements the TimeIt create_clock TCL command.

from __future__ import annotations

from typing import Any, Dict

from .signal import Signal
from .clocksignal import ClockSignal
from .gclocksignal import GClockSignal
from .tclcommandbase import TclCommandBase, OptSpec


class TclCreateClock(TclCommandBase):
    command_name = "create_clock"

    defaults = {"visible": False, "topology": "clockin"}

    ## Source (root/primary) clocks are ClockSignal, generated (derived)
    ## clocks are GClockSignal.
    _source_topologies = {"source", "clockin"}
    _generated_topologies = {"clockout", "clockinout"}
    _allowed_topologies = _source_topologies | _generated_topologies

    ## Options only meaningful for a source clock (waveform given explicitly).
    _source_opts = ("period", "rise_at", "fall_at",
                    "rise_uncertainty", "fall_uncertainty")
    ## Options only meaningful for a generated clock (waveform derived).
    _generated_opts = ("master", "edges", "divide_by", "input_dly",
                       "output_dly", "invert")

    def __init__(self, tcl):
        super().__init__(tcl)

        self.spec = {
            "-topology": OptSpec("topology", True, str),
            "-name": OptSpec("name", True, str),
            # Source clock waveform
            "-period": OptSpec("period", True, str),
            "-rise_at": OptSpec("rise_at", True, str),
            "-fall_at": OptSpec("fall_at", True, str),
            "-rise_uncertainty": OptSpec("rise_uncertainty", True, str),
            "-fall_uncertainty": OptSpec("fall_uncertainty", True, str),
            # Generated clock
            "-master": OptSpec("master", True, str),
            "-edges": OptSpec("edges", True, self._split_edges),
            "-divide_by": OptSpec("divide_by", True, int),
            "-invert": OptSpec("invert", False, lambda _v: True),
            "-input_dly": OptSpec("input_dly", True, str),
            "-output_dly": OptSpec("output_dly", True, str),
            # Display
            "-color": OptSpec("color", True, str),
            "-amplitude": OptSpec("amplitude", True, int),
            "-lwidth": OptSpec("lwidth", True, int),
            "-show": OptSpec("cycles", True, int),
            "-use_uid": OptSpec("uid", True, int),
            "-visible": OptSpec("visible", False, lambda _v: True),
        }

    # ----------------------------
    # Validation
    # ----------------------------
    def validate(self, opts: Dict[str, Any]) -> None:
        # Required
        self.require(opts, "name")
        # Allowed values
        self.allow(opts, "topology", self._allowed_topologies)

        topology = opts["topology"]
        if topology in self._generated_topologies:
            self._reject(opts, self._source_opts,
                         f"-topology {topology} is a generated clock")
            self.require(opts, "master")

            edges = opts.get("edges")
            divide_by = opts.get("divide_by")
            if edges is not None and divide_by is not None:
                raise ValueError("-edges and -divide_by are mutually exclusive")
            if edges is None and divide_by is None:
                raise ValueError(f"-edges or -divide_by is required for "
                                 f"-topology {topology}")
            if edges is not None:
                self._check_edges(edges)
            if divide_by is not None and divide_by < 1:
                raise ValueError("-divide_by must be >= 1")

            if topology == "clockout" and opts.get("input_dly") is not None:
                raise ValueError("-input_dly is not allowed for -topology clockout")
        else:
            self._reject(opts, self._generated_opts,
                         f"-topology {topology} is a source clock")
            self.require(opts, "period")

    def _reject(self, opts: Dict[str, Any], keys, reason: str) -> None:
        for key in keys:
            if opts.get(key) is not None:
                raise ValueError(f"-{key} is not allowed: {reason}")

    def _check_edges(self, edges) -> None:
        if len(edges) != 3:
            raise ValueError("-edges expects 3 values {rise fall cycle_end}")
        try:
            values = [int(e) for e in edges]
        except ValueError:
            raise ValueError(f"-edges expects integer values ({edges} given)") from None
        if values[0] < 1:
            raise ValueError("-edges values start at 1 (first master clock edge)")
        if not values[0] < values[1] < values[2]:
            raise ValueError("-edges values must be in increasing order")

    def _resolve_master(self, name: Any) -> ClockSignal:
        master = self.topapp.signals.find(str(name))
        if master is None:
            raise ValueError(f"{name} master clock not found")
        if master.type != "clock" or master.is_generated:
            raise ValueError(f"{name} is not a source clock")
        return master

    # ----------------------------
    # Execution
    # ----------------------------
    def execute(self, opts: Dict[str, Any]) -> str:
        name = opts["name"]
        topology = opts["topology"]

        generated = topology in self._generated_topologies
        cls = GClockSignal if generated else ClockSignal

        master = None
        if generated:
            # Resolved first: nothing is modified if the master is not usable.
            master = self._resolve_master(opts["master"])
            if master.name == name:
                raise ValueError(f"{name} can not be its own master clock")

        signal = self.topapp.signals.find(name)
        if signal is not None and type(signal) is not cls:
            # The topology moved the clock from source to generated (or the
            # other way round): rebuild it as the right class, in place.
            signal = self._retype(signal, cls(name))
        elif signal is None:
            signal = cls(name)
            signal.set_tcl_console(self.console)
        else:
            # Clear the attributes that may be cleared,
            alist = ["rise_uncertainty", "fall_uncertainty",
                     "input_dly", "output_dly"]
            for attr in alist:
                if hasattr(signal, attr):
                    setattr(signal, attr, None)

        # Maintain UID semantics from the original implementation
        uid = opts.get("uid")
        if uid is not None and Signal.static_id < uid:
            # If using user_uids Signal static UID must be highest
            Signal.static_id = uid + 1

        # Apply parsed options to the signal object. The generated clock
        # specification is applied below, it needs more than a plain setattr.
        self.apply_attrs(signal, opts,
                         skip={"master", "edges", "divide_by", "invert"})

        if generated:
            ## A flag is simply absent when not given: assigned explicitly so
            ## that re-creating the clock without -invert clears it.
            signal.invert = bool(opts.get("invert", False))
            if signal.master is not None and signal.master is not master:
                signal.master.remove_related_obj(signal)
            signal.master = master
            # Deleting the master clock deletes the clocks generated from it.
            master.add_related_obj(signal)

            if opts.get("divide_by") is not None:
                signal.set_divide_by(opts["divide_by"])
            else:
                signal.set_edges(opts["edges"])

        # Derive direction from topology
        signal.direction = {
            "source": "source",
            "clockin": "input",
            "clockout": "output",
        }.get(topology, "inout")

        # Always add the signal to the topapp catalog last
        self.topapp.signals.add(name, signal)

        self.topapp.redraw()
        return ""

    def _retype(self, old: Signal, new: Signal) -> Signal:
        """Replace `old` by `new` (same name, other class), keeping identity.

        The uid is kept so that markers/annotations attached to the signal
        still find it, and the signals store keeps the signal at the same
        position (a clock must stay above the signals referring to it).
        """
        new.set_tcl_console(self.console)
        new.uid = old.uid
        for attr in ("visible", "style", "cycles", "top_padding", "annotations"):
            setattr(new, attr, getattr(old, attr))

        # A generated clock that becomes a source clock is no longer derived.
        old_master = getattr(old, "master", None)
        if old_master is not None:
            old_master.remove_related_obj(old)

        # Re-point what referred to the old object (inputs/outputs launched or
        # captured by it, clocks generated from it, timing markers, ...).
        for obj in list(old.get_related_objs()):
            new.add_related_obj(obj)
            old.remove_related_obj(obj)
            for attr in ("launch_clock", "capture_clock", "master"):
                if getattr(obj, attr, None) is old:
                    setattr(obj, attr, new)

        self.topapp.signals.replace(old.name, new)
        return new
