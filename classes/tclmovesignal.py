from __future__ import annotations

from .tclcommandbase import TclCommandBase, OptSpec


class TclMoveSignal(TclCommandBase):
    """Implements the ``move_signal`` Tcl command.

    Syntax
    ------
    move_signal  -name <signal>  -direction up|down

    Signal order is otherwise implicit in the order the create_* commands
    appear in a script; this is what lets the GUI "Move Up"/"Move Down"
    actions be expressed as a command.
    """

    command_name = "move_signal"

    _allowed_directions = {"up", "down"}

    spec = {
        "-name":      OptSpec("name", True, str),
        "-direction": OptSpec("direction", True, lambda v: str(v).strip().lower()),
    }

    def validate(self, opts):
        self.require(opts, "name", "direction")
        self.allow(opts, "direction", self._allowed_directions)

        ## The order rules (a signal stays below the clocks it refers to) live
        ## in the store, so the GUI and this command enforce the same ones.
        error = self.topapp.signals.move_error(opts["name"], opts["direction"])
        if error is not None:
            raise ValueError(error.replace("\n", " "))

    def execute(self, opts):
        self.topapp.signals.move(opts["name"], opts["direction"])
        self.topapp.redraw()
        return ""
