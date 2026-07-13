# This class implements the TimeIt common TCL commands.
import tkinter as tk

from .tclcreateclock import TclCreateClock
from .tclcreateinput import TclCreateInput
from .tclcreateoutput import TclCreateOutput
from .tclcreatetimingmarker import TclCreateTimingMarker
from .tclcreatewaveformsplit import TclCreateWaveformSplit
from .tclcreatewaveformannotation import TclCreateWaveformAnnotation
from .tclsetattribute import TclSetAttribute

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

        # Optional registry for generic dispatch (useful when adding many commands)
        self._registry = {
            "create_clock": self.create_clock,
            "create_input": self.create_input,
            "create_output": self.create_output,
            "create_timing_marker": self.create_timing_marker,
            "create_waveform_split": self.create_waveform_split,
            "create_waveform_annotation": self.create_waveform_annotation,
            "set_attribute": self.set_attribute,
        }

    # ----------------------------------------------------------------------
    # TCL commands bond in Python
    # ----------------------------------------------------------------------           
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
        scale = float(args[0])
        self.topapp.set_canvas_scale(scale)
    
    def remove(self, *args):
        i = 0
        while i < len(args):
            if args[i] == '-all':
                self.topapp.remove_all()
                return ""
            
            self.console.append_log(f"Error: Unknown {args[i]} option\n",
                                    "error")
            return ""

