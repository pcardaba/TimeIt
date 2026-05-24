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
        self.require(opts, "name", "value")

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

    def execute(self, opts):
        signal = self._resolve_signal(opts["signal"])
        attr_name = opts["name"]
        raw_value = opts["value"]

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
