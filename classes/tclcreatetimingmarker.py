# This class implements the TimeIt create_timing_marker TCL command.

from .timingmarker import TimingMarker

class TclCreateTimingMarker:
    def __init__(self, parent):
        self.console = parent.console
        self.topapp = self.console.topapp
        
    def run_cmd(self, *args):
        opts = {}
        i = 0
        while i < len(args):
            if '-help' in args:
                self.console._show_command_help("create_timing_marker")
                return ""
            if args[i] == '-name':
                key = "name"
                val = args[i+1]
                opts[key] = val
                i += 2
                continue
            if args[i] == '-style':
                key = "style"
                val = args[i+1]                
                if val not in {"outer", "inner_both", "inner_left", "inner_right"}:
                    self.console.append_log(f"Error: {val} is not recognized as marker style\n",
                                            "error")
                    return ""
                opts[key] = val
                i += 2
                continue
            arghit = 0
            for e in ("from", "to"):
                if args[i] == f"-{e}":
                    key1 = f"{e}_at"
                    key2 = f"{e}_uid"
                    val = args[i+1].split(":")
                    val1 = val[0]
                    val2 = val[1] if len(val) == 2 else val1
                    if len(val) == 1:
                        val1 = "full"
                    if val1 not in {"full", "start", "middle", "end"}:
                        self.console.append_log(f"Error: {val1} is not recognized point of measure\n",
                                                "error")
                        return ""
                    opts[key1] = val1
                    opts[key2] = val2
                    i += 2
                    arghit += 1
                    break
            if arghit:
                continue
            if args[i] == '-at':
                key = "y"
                val = args[i+1]
                opts[key] = int(val)
                i += 2
                continue
            arghit = 0
            for e in ("x", "y"):
                if args[i] == f"-label_{e}":
                    key = f"label_rel{e}"
                    val = args[i+1]
                    opts[key] = int(val)
                    i += 2
                    arghit += 1
                    break
            if arghit:
                continue

            self.console.append_log(f"Error: Unknown {args[i]} option\n", "error")
            return ""

        marker = TimingMarker(name=opts["name"],
                              from_uid=opts["from_uid"],
                              from_at=opts["from_at"],
                              to_uid=opts["to_uid"],
                              to_at=opts["to_at"])

        for k in ("style", "y", "label_relx", "label_rely"):
            setattr(marker, k, opts[k])

        self.topapp.canvas.create_timing_marker(marker)
        return marker.uidtag()

