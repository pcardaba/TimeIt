"""
Shared infrastructure for Tcl command handlers.

Design:
- TclCommands is the command host (owns console/topapp and registers handlers).
- Each concrete command (e.g. TclCreateClock) inherits BaseTclCommand and
  implements a small amount of domain logic (validate + execute).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Dict, Tuple


@dataclass(frozen=True)
class OptSpec:
    """
    Specification for a Tcl-style option.

    Attributes
    ----------
    key:
        The key name stored in the parsed options dictionary
        (and often an attribute on the target object).
    takes_value:
        If True, the option consumes the next token as its value.
    caster:
        Converts the raw token into the desired Python type (defaults
        to identity).
    """
    key: str
    takes_value: bool
    caster: Callable[[Any], Any] = lambda x: x


class TclCommandBase:
    """
    Base class for Tcl command handlers.

    Concrete commands should override:
    - command_name
    - spec (mapping: option token -> OptSpec)
    - defaults (optional)
    - validate(opts)
    - execute(opts)
    """

    command_name: str = ""
    spec: Dict[str, OptSpec] = {}
    defaults: Dict[str, Any] = {}

    def __init__(self, tcl_commands: TclCommands):
        # tcl_commands is typically an instance of TclCommands
        self.tcl = tcl_commands
        self.console = tcl_commands.console
        self.topapp = tcl_commands.topapp

    # ----------------------------
    # Public entry point
    # ----------------------------
    def run_cmd(self, *args):
        # Help: handle once, early (so it doesn't depend on spec)
        if "-help" in args:
            self.console._show_command_help(self.command_name)
            return ""

        try:
            opts = dict(self.defaults)
            opts.update(self._parse_args(args))
            self.validate(opts)
            return self.execute(opts)
        except ValueError as e:
            self.console.append_log(f"Error: {e}\n", "error")
            return ""

    # ----------------------------
    # Parsing
    # ----------------------------
    def _parse_args(self, args: Tuple[Any, ...]) -> Dict[str, Any]:
        out: Dict[str, Any] = {}
        i, n = 0, len(args)

        while i < n:
            tok = args[i]
            spec = self.spec.get(tok)
            if spec is None:
                raise ValueError(f"Unknown {tok} option")

            if spec.takes_value:
                if i + 1 >= n:
                    raise ValueError(f"{tok} expects a value")
                raw = args[i + 1]
                try:
                    out[spec.key] = spec.caster(raw)
                except Exception as e:
                    raise ValueError(f"Invalid value for {tok}: {raw} ({e})") from e
                i += 2
            else:
                # flag option
                out[spec.key] = spec.caster(True)
                i += 1

        return out

    def _resolve_refclock(self, ref_name: Any):
        """Resolve -refclock argument into an existing signal object."""
        name = str(ref_name)
        obj = self.topapp.signals.find(name)
        if obj is None:
            raise ValueError(f"{name} refclock not found")
        return obj

    @staticmethod
    def _split_edges(v: Any):
        """
        Convert Tcl list-ish string into a Python list.

        Supports:
          - "1 2 3"        -> ["1","2","3"]
          - "{1 2 3}"      -> ["1","2","3"]
          - "{}"           -> []
          - {"a b" c}      -> ["a b","c"]
        """
        s = str(v).strip()
        if not s:
            return []

        # Strip one level of outer braces if present
        if s.startswith("{") and s.endswith("}"):
            s = s[1:-1].strip()
            if not s:
                return []

        items = []
        buf = []
        in_quotes = False
        escape = False

        def flush():
            if buf:
                items.append("".join(buf))
                buf.clear()

        for ch in s:
            if escape:
                buf.append(ch)
                escape = False
                continue

            if ch == "\\":
                escape = True
                continue

            if ch == '"':
                in_quotes = not in_quotes
                continue

            if not in_quotes and ch.isspace():
                flush()
                continue

            buf.append(ch)

        flush()
        return items
    
    # ----------------------------
    # Validation helpers
    # ----------------------------
    def require(self, opts: Dict[str, Any], *keys: str) -> None:
        for k in keys:
            v = opts.get(k)
            if v is None or v == "":
                raise ValueError(f"-{k} is required")

    def allow(self, opts: Dict[str, Any], key: str, allowed: set) -> None:
        v = opts.get(key)
        if v is not None and v not in allowed:
            raise ValueError(f"{v} is not a valid value for -{key}")

    # ----------------------------
    # Apply helpers
    # ----------------------------
    def apply_attrs(self, obj: Any, opts: Dict[str, Any], *,
                    skip: set[str] | None = None) -> None:
        """
        Apply all options whose key exists as an attribute on obj.
        """
        if skip is None:
            skip = set()
        for k, v in opts.items():
            if k in skip:
                continue
            if hasattr(obj, k):
                setattr(obj, k, v)

    # ----------------------------
    # Overridables
    # ----------------------------
    def validate(self, opts: Dict[str, Any]) -> None:
        return None

    def execute(self, opts: Dict[str, Any]) -> str:
        raise NotImplementedError
