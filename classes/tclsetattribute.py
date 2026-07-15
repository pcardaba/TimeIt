from __future__ import annotations

from .tclcommandbase import TclCommandBase, OptSpec


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
        """Resolve a signal by name or by uid tag (e.g. 'uid_2')."""
        sig = self.topapp.signals.find(ref)
        if sig is not None:
            return sig
        if ref.startswith("uid_"):
            uid_str = ref[len("uid_"):]
            sig = self.topapp.signals.find_by_uid(uid_str)
        if sig is None:
            raise ValueError(f"Signal '{ref}' not found")
        return sig

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
