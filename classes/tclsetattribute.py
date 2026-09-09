from __future__ import annotations

from .tclcommandbase import TclCommandBase, OptSpec
from .pwlsignal import PWLTrace, PWLFileError


class TclSetAttribute(TclCommandBase):
    command_name = "set_attribute"

    spec = {
        "-signal": OptSpec("signal", True, str),
        "-name":   OptSpec("name",   True, str),
        "-value":  OptSpec("value",  True, str),
    }

    def validate(self, opts):
        # Exactly one object-type selector must be present; currently only -signal
        if not opts.get("signal"):
            raise ValueError("-signal is required")
        self.require(opts, "name")
        ## An empty -value is meaningful for enabled_by (it ungates the
        ## clock); everywhere else a value is required.
        if opts.get("name") == "enabled_by":
            if opts.get("value") is None:
                raise ValueError("-value is required")
        else:
            self.require(opts, "value")

    def _resolve_signal(self, ref: str):
        """Resolve a signal by name or by uid tag (e.g. 'uid_2').

        A PWL trace name resolves to the PWL slot showing it.
        """
        sig = self.topapp.signals.find(ref)
        if sig is not None:
            return sig
        if ref.startswith("uid_"):
            uid_str = ref[len("uid_"):]
            sig = self.topapp.signals.find_by_uid(uid_str)
        if sig is None:
            for candidate in self.topapp.signals.values():
                if candidate.type == "pwl" and candidate.find_trace(ref):
                    return candidate
        if sig is None:
            raise ValueError(f"Signal '{ref}' not found")
        return sig

    _trace_attrs = ("color", "lstyle", "lwidth", "scale", "offset", "file",
                    "visible")

    def _set_trace_attr(self, slot, ref: str, attr_name: str,
                        raw_value: str) -> None:
        """Set a per-trace attribute of a PWL slot (trace given by name)."""
        trace = slot.find_trace(ref)
        if trace is None:
            raise ValueError(
                f"'{attr_name}' is a PWL trace attribute: give the trace "
                f"name with -signal (traces of {slot.name}: "
                f"{', '.join(slot.trace_names())})")
        if attr_name == "visible":
            trace.visible = self.tcl._convert_text(raw_value, True)
        elif attr_name == "lwidth":
            try:
                value = int(raw_value)
            except ValueError:
                raise ValueError("lwidth must be an integer") from None
            if value < 1:
                raise ValueError("lwidth must be >= 1")
            trace.lwidth = value
        elif attr_name == "lstyle":
            if raw_value not in PWLTrace.LINE_STYLES:
                raise ValueError(
                    "lstyle must be one of: "
                    + ", ".join(PWLTrace.LINE_STYLES))
            trace.lstyle = raw_value
        elif attr_name in ("scale", "offset"):
            try:
                value = float(raw_value)
            except ValueError:
                raise ValueError(f"{attr_name} must be a number") from None
            if attr_name == "scale" and value <= 0.0:
                raise ValueError("scale must be > 0")
            setattr(trace, attr_name, value)
        elif attr_name == "file":
            ## Re-read from the new file before touching the trace.
            probe = PWLTrace(trace.name, raw_value)
            try:
                probe.load(self.topapp.settings.waveform["tunits"],
                           self.tcl.create_pwl._script_dir())
            except PWLFileError as exc:
                raise ValueError(str(exc)) from exc
            probe.copy_style_from(trace)
            slot.traces[slot.traces.index(trace)] = probe
        else:
            trace.color = raw_value

    def _set_enabled_by(self, signal, raw_value: str) -> None:
        """Gate a clock with an enable signal (empty value ungates it)."""
        if signal.type != "clock" or not signal.is_generated:
            raise ValueError("enabled_by only applies to generated clock "
                             "signals (source clocks can not be gated)")

        name = raw_value.strip()
        if name in ("", "{}"):
            signal.enabled_by = None
            return

        enable = self.topapp.signals.find(name)
        if enable is None:
            raise ValueError(f"Signal '{name}' not found")
        self.check_gate_signal(signal, enable)
        signal.enabled_by = enable

    def execute(self, opts):
        signal = self._resolve_signal(opts["signal"])
        attr_name = opts["name"]
        raw_value = opts["value"]

        ## The gating attributes need resolution/validation: the generic
        ## path below would store a raw string.
        if attr_name == "enabled_by":
            self._set_enabled_by(signal, raw_value)
            self.topapp.redraw()
            return ""
        if attr_name == "enable_active":
            if signal.type != "clock" or not signal.is_generated:
                raise ValueError("enable_active only applies to generated "
                                 "clock signals (source clocks can not be "
                                 "gated)")
            if raw_value not in ("high", "low"):
                raise ValueError("enable_active must be 'high' or 'low'")
            signal.enable_active = raw_value
            self.topapp.redraw()
            return ""

        ## On a PWL slot the trace attributes are addressed by trace name;
        ## the slot itself (its own visible/height/...) by uid. Only
        ## "visible" exists at both levels: any other trace attribute given
        ## by uid is an error (the slot has no color/lwidth of its own).
        if signal.type == "pwl" and attr_name in self._trace_attrs \
           and not (attr_name == "visible"
                    and opts["signal"].startswith("uid_")):
            self._set_trace_attr(signal, opts["signal"], attr_name, raw_value)
            self.topapp.redraw()
            return ""

        if not hasattr(signal, attr_name):
            raise ValueError(
                f"Attribute '{attr_name}' not found on signal '{signal.name}'"
            )

        current = getattr(signal, attr_name)
        # When the current value is None the type cannot be inferred; keep as str.
        if current is None:
            casted = raw_value
        else:
            casted = self.tcl._convert_text(raw_value, current)

        setattr(signal, attr_name, casted)
        self.topapp.redraw()
        return ""
