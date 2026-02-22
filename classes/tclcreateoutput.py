# This class implements the TimeIt create_clock TCL command.
from .signal import Signal
from .outputsignal import OutputSignal

class TclCreateOutput:
    def __init__(self, parent):
        self.console = parent.console
        self.topapp = self.console.topapp
        
    def run_cmd(self, *args):
        opts = {}
        i = 0
        opts["visible"] = False
        while i < len(args):
            if '-help' in args:
                self.console._show_command_help("create_output")
                return ""
            if args[i] == '-specify':
                key = "specify"
                val = args[i+1]
                if val not in {"internal", "external"}:
                    self.console.append_log(f"Error: {val} is not recognized by -specify\n",
                                            "error")
                    return ""
                opts[key] = val
                i += 2
                continue
            
            
            if args[i] == '-refclock':
                key = "refclock"
                if args[i+1] in self.topapp.signals.names():
                    val = self.topapp.signals.find(args[i+1])
                else:
                    self.console.append_log(f"Error: {args[i+1]} refclock not found\n",
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

            valid = {f"{rf}_{il}_{mm}" for il in ["outputdly","latency"]
                                      for rf in ["rclk","fclk"]
                                      for mm in ["max","min"]}

            arg = args[i]
            if arg.startswith("-") and arg[1:] in valid:
                key = arg[1:]
                opts[key] = args[i+1]
                i += 2
                continue

            valid = ["data_edges", "hiz_edges", "high_edges", "low_edges", "unknown_edges"]
            if arg.startswith("-") and arg[1:] in valid:
                key = arg[1:]
                # Convert to list.
                opts[key] = set(args[i+1].split())
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
            if args[i] == '-use_uid':
                key = "uid"
                val = args[i+1]
                opts[key] = int(val)
                i += 2           
            if args[i] == '-visible':
                key = "visible"
                val = True
                opts[key] = val
                i += 1
                continue
            self.console.append_log(f"Error: Unknown {args[i]} option\n", "error")
            return ""

        if opts["refclock"] is None or opts["refclock"] == "":
            self.console.append_log(f"Error: Option -refclock is mandatory\n", "error")
            return ""
        
        signal = self.topapp.signals.find(opts["name"])
        if signal is None:
            signal = OutputSignal(opts["name"])
            signal.set_tcl_console(self.console)
            self.topapp.signals.add(opts["name"],signal)
            
        for key, value in opts.items():
            if key == "uid":
                # If using user_uids Signal static UID must be highest
                if Signal.static_id < value:
                    Signal.static_id = value + 1 
            if hasattr(signal, key):
                setattr(signal, key, value)   

        signal.direction = "output"
        # Add the output signal to the related objects of the refclock
        opts["refclock"].add_related_obj(signal)   
        # self.console.append_log(f"create_clock options: {opts}\n", "result")
        self.topapp.redraw()
        return ""

