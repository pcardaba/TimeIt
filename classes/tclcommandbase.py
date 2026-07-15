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
            given = self._parse_args(args)
            opts.update(given)
            ## The options this invocation actually carried, defaults excluded.
            ## A command that updates an existing object must apply only these
            ## (see apply_given): the defaults would silently reset whatever
            ## the command did not mention.
            self._given = set(given)
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

    def _resolve_clock(self, clock_name: Any):
        """Resolve a clock option (-launch_clock, ...) into a clock signal."""
        name = str(clock_name)
        obj = self.topapp.signals.find(name)
        if obj is None:
            raise ValueError(f"{name} clock not found")
        if obj.type != "clock":
            raise ValueError(f"{name} is not a clock")
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

    def check_gate_signal(self, clock: Any, enable: Any) -> None:
        """Validate `enable` as the gating (ICG enable) signal of `clock`.

        The enable signal belongs to the clock domain of the clock it gates:
        its launch/capture clocks must be related to it. It can not be
        clocked by the gated clock itself: the gated (visible) edge numbering
        would become circular.
        """
        if getattr(enable, "type", None) not in ("input", "output"):
            raise ValueError(
                f"{getattr(enable, 'name', enable)} is not an input/output "
                f"signal: only those may gate a clock")

        for clk in (enable.launchclk, enable.captureclk):
            if clk is None:
                raise ValueError(
                    f"{enable.name} has no launch/capture clock")
            if clk is clock:
                raise ValueError(
                    f"{enable.name} is clocked by {clock.name}: the enable "
                    f"signal can not be clocked by the clock it gates")
            if not clk.is_related_to(clock):
                raise ValueError(
                    f"{enable.name} is not in the clock domain of "
                    f"{clock.name}: its launch/capture clock is not related "
                    f"to it")

    def check_io_clocks(self, opts: Dict[str, Any]) -> None:
        """Validate the launch/capture clocks of an I/O signal.

        Data can only be launched and captured by related clocks (clocks
        sharing the same source clock). Giving only one of both means that
        the same clock launches and captures (the former -refclock).
        """
        launch = opts.get("launch_clock")
        capture = opts.get("capture_clock")

        if launch is None and capture is None:
            raise ValueError("-launch_clock and/or -capture_clock is required")
        if launch is None:
            opts["launch_clock"] = capture
        elif capture is None:
            opts["capture_clock"] = launch
        elif not launch.is_related_to(capture):
            raise ValueError(
                f"{launch.name} (launch) and {capture.name} (capture) are not "
                f"related: they do not share the same source clock"
            )

    # ----------------------------
    # Apply helpers
    # ----------------------------
    def wire_io_clocks(self, signal: Any, opts: Dict[str, Any]) -> None:
        """Attach the launch/capture clocks to an I/O signal.

        Both are registered as related objects, so that deleting either of
        them also deletes the signal.
        """
        signal.launch_clock = opts["launch_clock"]
        signal.capture_clock = opts["capture_clock"]
        for clock in signal.related_clocks():
            clock.add_related_obj(signal)

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

    def apply_given(self, obj: Any, opts: Dict[str, Any], *,
                    skip: set[str] | None = None) -> None:
        """Apply only the options this invocation explicitly carried.

        Used when updating an existing object: "-use_uid 0 -at 7" must move
        the object without resetting the attributes it does not mention back
        to their defaults.
        """
        given = {k: v for k, v in opts.items() if k in self._given}
        self.apply_attrs(obj, given, skip=skip)

    # ----------------------------
    # Overridables
    # ----------------------------
    def validate(self, opts: Dict[str, Any]) -> None:
        return None

    def execute(self, opts: Dict[str, Any]) -> str:
        raise NotImplementedError
