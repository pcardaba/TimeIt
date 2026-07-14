# This class implements the TimeIt common TCL commands.
import tkinter as tk

from .tclcreateclock import TclCreateClock
from .tclcreateinput import TclCreateInput
from .tclcreateoutput import TclCreateOutput
from .tclcreatetimingmarker import TclCreateTimingMarker
from .tclcreatewaveformsplit import TclCreateWaveformSplit
from .tclcreatewaveformannotation import TclCreateWaveformAnnotation
from .tclsetattribute import TclSetAttribute
from .tclexportcanvas import TclExportCanvas
from .tclmovesignal import TclMoveSignal
from .tclcommandbase import TclCommandBase

class TclCommands:

    def __init__(self, parent):
        self.console = parent
        self.topapp = self.console.topapp
        self.create_clock = TclCreateClock(self)
        self.create_input = TclCreateInput(self)
        self.create_output = TclCreateOutput(self)
        self.create_timing_marker = TclCreateTimingMarker(self)
        self.create_waveform_split = TclCreateWaveformSplit(self)
        self.create_waveform_annotation = TclCreateWaveformAnnotation(self)
        self.set_attribute = TclSetAttribute(self)
        self.export_canvas = TclExportCanvas(self)
        self.move_signal = TclMoveSignal(self)

        # Optional registry for generic dispatch (useful when adding many commands)
        self._registry = {
            "create_clock": self.create_clock,
            "create_input": self.create_input,
            "create_output": self.create_output,
            "create_timing_marker": self.create_timing_marker,
            "create_waveform_split": self.create_waveform_split,
            "create_waveform_annotation": self.create_waveform_annotation,
            "set_attribute": self.set_attribute,
            "export_canvas": self.export_canvas,
            "move_signal": self.move_signal,
        }

    ## Commands implemented as plain methods here (the ones in _registry are
    ## TclCommandBase handlers). Both make up the list shown by "help".
    _plain_commands = (
        "help",
        "puts",
        "remove",
        "set_app_var",
        "set_canvas_scale",
        "set_window_size",
    )

    def command_names(self):
        """Names of every TimeIt command registered in the interpreter."""
        return sorted(set(self._registry) | set(self._plain_commands))

    # ----------------------------------------------------------------------
    # TCL commands bond in Python
    # ----------------------------------------------------------------------
    def help(self, *args):
        if not args:
            self.console.append_log("Available commands:\n", "result")
            for name in self.command_names():
                self.console.append_log(f"  {name}\n", "result")
            self.console.append_log(
                "Use \"help <command_name>\" for the details of a command.\n",
                "result")
            return ""

        if len(args) > 1:
            self.console.append_log(
                "Error: help takes at most one command name\n", "error")
            return ""

        name = str(args[0])
        if name == "-help":
            name = "help"
        elif name not in self.command_names():
            self.console.append_log(f"Error: Unknown command {name}\n", "error")
            return ""

        ## "help <cmd>" is just "<cmd> -help": both print data/<cmd>.help.txt.
        self.console._show_command_help(name)
        return ""

    def puts(self, *args):
        newline = True
        channel = "stdout"
        idx = 0

        if idx < len(args) and args[idx] == "-nonewline":
            newline = False
            idx += 1

        if idx < len(args) - 1:
            channel = args[idx]
            idx += 1

        text = args[idx] if idx < len(args) else ""
        text_to_write = text if not newline else text + "\n"

        tag = "stdout" if channel == "stdout" else \
            "stderr" if channel == "stderr" else \
            "result"

        self.console.append_log(text_to_write, tag)
        return ""    
    

    def eval_command(self, cmd_name: str, *args):
        """
        Generic dispatcher (optional).
        Not used. Kept just in case we want to call commands:
            tcl_commands.eval_command("create_clock", "-name", "clk", ...)
        """
        handler = self._registry.get(cmd_name)
        if handler is None:
            self.console.append_log(f"Error: Unknown command {cmd_name}\n", "error")
            return ""
        return handler.run_cmd(*args)

    def _convert_text(self, txt: str, value):
        t = type(value)

        if t is bool:
            lowered = txt.lower()
            if lowered in ("true", "1", "yes", "y", "on"):
                return True
            if lowered in ("false", "0", "no", "n", "off"):
                return False
            raise ValueError("Expected a boolean (true/false, yes/no, 1/0).")

        if t is int:
            return int(txt, 10)

        if t is float:
            return float(txt)

        if t is str:
            return txt

        if t is tuple:
            raw = txt.strip()
            if raw.startswith("(") and raw.endswith(")"):
                raw = raw[1:-1]
            parts = []
            for p in raw.split(","):
                cleaned = p.strip()
                if cleaned:
                    parts.append(int(cleaned))
            if not parts:
                return tuple([6,4]) # default

            return tuple(parts)
        
    def set_app_var(self, *args):
        if "-help" in args:
            self.console._show_command_help("set_app_var")
            return ""

        opts = {}
        i = 0
        while i < len(args):
            if args[i] == '-name':
                key = "name"
                val = args[i+1]
                opts[key] = val
                i += 2
                continue
            if args[i] == '-value':
                key = "value"
                val = args[i+1]
                opts[key] = val
                i += 2
                continue
            if args[i] == '-desc':
                key = "desc"
                val = args[i+1]
                opts[key] = val
                i += 2
                continue
            self.console.append_log(f"Error: Unknown {args[i]} option\n", "error")
            return ""
        
        if "name" not in opts or "value" not in opts:
            self.console.append_log(f"Error: need both (-name and -value) options", "error")
            return ""

        splitname = opts["name"].split(".")
        if splitname[0] == "settings":
            settings = self.topapp.settings
            category = splitname[1]
            d = getattr(settings, category, None)
            if d is None:
                self.console.append_log(f"Error: {category} not found in settings", "error")
                return ""
            d_entry = splitname[2]
            if d_entry not in d:
                self.console.append_log(f"Error: {d_entry} is not known setting", "error")
                return ""       
            if type(d[d_entry]) == dict:
                d = d[d_entry] # Normally this shall be "font".
                d_entry = splitname[3]
                if d_entry not in d:
                    self.console.append_log(f"Error: {d_entry} is not known setting", "error")
                    return ""
            d[d_entry] = self._convert_text(opts["value"], d[d_entry])
            try:
                self.console.interp.eval("set "+opts["name"]+" {"+opts["value"]+"}")
            except tk.TclError as e:
                self.console.append_log(f"Error: {e}\n", "error")
        elif  splitname[0] == "timings":
            timings = self.topapp.timings
            var = splitname[1]
            val = opts["value"]
            timings.tvars[var] = val
            if "desc" in opts:
                timings.tvars_desc[var] = opts["desc"]
            else:
                # Setting a new value keeps the description the variable had.
                timings.tvars_desc.setdefault(var, "")
            cmd = "set "+var+" [expr {"+opts["value"]+"}]"
            try:
                self.console.interp.eval(cmd)
            except tk.TclError as e:
                self.console.append_log(f"Error: {e}\n", "error")  
        else:
            self.console.append_log(f"Error: Application var {splitname[0]} not known",
                                    "error")
        return ""    

    def set_window_size(self, *args):
        if "-help" in args:
            self.console._show_command_help("set_window_size")
            return ""

        i = 0
        width = -100
        height = -100
        while i < len(args):
            if args[i] == '-width':
                width = int(args[i+1])
                i += 2
                continue
            if args[i] == '-height':
                height = int(args[i+1])
                i += 2
                continue
 
            self.console.append_log(f"Error: Unknown {args[i]} option\n",
                                    "error")
            return ""

        self.topapp.set_window_size(width, height)


    def set_canvas_scale(self, *args):
        if "-help" in args:
            self.console._show_command_help("set_canvas_scale")
            return ""

        scale = float(args[0])
        self.topapp.set_canvas_scale(scale)
    
    ## Objects the "remove" command can delete. All are given by uid, except
    ## the timing variables, which are given by name.
    _removable = ("-signal", "-split", "-tmarker", "-annotation", "-timing_var")

    def remove(self, *args):
        if "-help" in args:
            self.console._show_command_help("remove")
            return ""

        uids = {}
        i = 0
        while i < len(args):
            tok = args[i]
            if tok == '-all':
                self.topapp.remove_all()
                return ""

            if tok in self._removable:
                if i + 1 >= len(args):
                    self.console.append_log(f"Error: {tok} expects a uid list\n",
                                            "error")
                    return ""
                uids[tok] = TclCommandBase._split_edges(args[i + 1])
                i += 2
                continue

            self.console.append_log(f"Error: Unknown {tok} option\n",
                                    "error")
            return ""

        if not uids:
            self.console.append_log(
                "Error: remove needs -all, -signal, -split, -tmarker, "
                "-annotation or -timing_var\n", "error")
            return ""

        ## Everything a signal owns comes first: removing a signal also removes
        ## the markers measuring it and the annotations on it, and their uids
        ## would then be gone.
        for uid in uids.get("-tmarker", []):
            self._remove_tmarker(uid)
        for uid in uids.get("-split", []):
            self._remove_split(uid)
        for uid in uids.get("-annotation", []):
            self._remove_annotation(uid)
        for uid in uids.get("-signal", []):
            self._remove_signal(uid)
        ## Last: dropping a timing variable can make the signals whose timings
        ## refer to it undrawable, and the renderer then culls them.
        for name in uids.get("-timing_var", []):
            self._remove_timing_var(name)

        self.topapp.redraw()
        return ""

    def _uid_error(self, option: str, uid: str, what: str) -> None:
        self.console.append_log(f"Error: {option} {uid}: no {what} with this uid\n",
                                "error")

    def _remove_signal(self, uid) -> None:
        signal = self.topapp.signals.find_by_uid(str(uid))
        if signal is None:
            self._uid_error("-signal", uid, "signal")
            return
        self.topapp.canvas.remove_signal(signal)

    def _remove_split(self, uid) -> None:
        split = None
        if str(uid).isdigit():
            split = self.topapp.canvas.splits.get(int(uid))
        if split is None:
            self._uid_error("-split", uid, "waveform split")
            return
        self.topapp.canvas.remove_split(split)

    def _remove_tmarker(self, uid) -> None:
        marker = self.topapp.canvas.markers.get(f"tmarker_uid_{uid}")
        if marker is None:
            self._uid_error("-tmarker", uid, "timing marker")
            return
        self.topapp.canvas.remove_marker(marker)

    def _remove_annotation(self, uid) -> None:
        ## An annotation is identified by the waveform element it annotates
        ## ("uid_<signal_uid>_<element_id>"), which is also where it is stored.
        wf_uid = str(uid)
        parts = wf_uid.split("_")
        signal = None
        if len(parts) > 1 and parts[1].isdigit():
            signal = self.topapp.signals.find_by_uid(parts[1])

        if signal is None or signal.annotations.pop(wf_uid, None) is None:
            self._uid_error("-annotation", wf_uid, "annotation")

    def _remove_timing_var(self, name) -> None:
        name = str(name)
        timings = self.topapp.timings

        if name not in timings.tvars:
            self.console.append_log(
                f"Error: -timing_var {name}: no timing variable with this name\n",
                "error")
            return

        timings.tvars.pop(name)
        timings.tvars_desc.pop(name, None)
        try:
            self.console.interp.eval("unset " + name)
        except tk.TclError as e:
            self.console.append_log(f"Error: Unable to unset {name}: {e}\n",
                                    "error")

