# This class implements the TimeIt create_clock TCL command.

from .signal import Signal
from .clocksignal import ClockSignal

class TclCreateClock:
    def __init__(self, parent):
        self.console = parent.console
        self.topapp = self.console.topapp
        
    def run_cmd(self, *args):
        opts = {}
        i = 0
        opts["visible"] = False
        while i < len(args):
            if '-help' in args:
                self.console._show_command_help("create_clock")
                return ""
            if args[i] == '-topology':
                key = "topology"
                val = args[i+1]
                print("-"+val+"-")
                if val not in {"clockin", "clockout", "clockinout"}:
                    self.console.append_log(f"Error: {val} is not recognized as clock topology\n",
                                            "error")
                    return ""
                opts[key] = val
                i += 2
                continue
            if args[i] == '-name':
                key = "name"
                val = args[i+1]
                opts[key] = val
                i += 2
                continue
            if args[i] == '-period':
                key = "period"
                val = args[i+1]
                opts[key] = val
                i += 2
                continue
            if args[i] == '-rise_at':
                key = "rise_at"
                val = args[i+1]
                opts[key] = val
                i += 2
                continue
            if args[i] == '-fall_at':
                key = "fall_at"
                val = args[i+1]
                opts[key] = val
                i += 2
                continue
            if args[i] == '-rise_uncertainty':
                key = "rise_uncertainty"
                val = args[i+1]
                opts[key] = val
                i += 2
                continue
            if args[i] == '-fall_uncertainty':
                key = "fall_uncertainty"
                val = args[i+1]
                opts[key] = val
                i += 2
                continue
            if args[i] == '-input_dly':
                key = "input_dly"
                val = args[i+1]
                opts[key] = val
                i += 2
                continue
            if args[i] == '-output_dly':
                key = "output_dly"
                val = args[i+1]
                opts[key] = val
                i += 2
                continue
            if args[i] == '-color':
                key = "color"
                val = args[i+1]
                opts[key] = val
                i += 2
                continue
            if args[i] == '-amplitude':
                key = "amplitude"
                val = args[i+1]
                opts[key] = int(val)
                i += 2
                continue
            if args[i] == '-lwidth':
                key = "lwidth"
                val = args[i+1]
                opts[key] = int(val)
                i += 2
                continue
            if args[i] == '-show':
                key = "cycles"
                val = args[i+1]
                opts[key] = int(val)
                i += 2
                continue
            if args[i] == '-use_uid':
                key = "uid"
                val = args[i+1]
                opts[key] = int(val)
                i += 2
                continue
            if args[i] == '-visible':
                key = "visible"
                val = True
                opts[key] = val
                i += 1
                continue

            self.console.append_log(f"Error: Unknown {args[i]} option\n", "error")
            return ""
        
        signal = self.topapp.signals.find(opts["name"])
        if signal is None:
            signal = ClockSignal(opts["name"])
            signal.set_tcl_console(self.console)
            self.topapp.signals.add(opts["name"], signal)
            
        for key, value in opts.items():
            if key == "uid":
                # If using user_uids Signal static UID must be highest
                if Signal.static_id < value:
                    Signal.static_id = value + 1
            if hasattr(signal, key):
                setattr(signal, key, value)   
        
        if signal.topology ==  "clockin":
            signal.direction = "input"
        elif signal.topology ==  "clockout":
            signal.direction = "output"
        else:
            signal.direction = "inout"       
            
        # self.console.append_log(f"create_clock options: {opts}\n", "result")
        self.topapp.redraw()
        return ""

