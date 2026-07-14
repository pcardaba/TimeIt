from __future__ import annotations
import io
import tkinter as tk


class Timings:
    """
    Application user timings container.
    """

    def __init__(self, root: tk.Misc | None = None) -> None:

        self.topapp = root
        self.console = None
        # ---- Timings ----
        self.tvars  = {
        }
        self.tvars_desc  = {
        }

        self.eval_buffer = io.StringIO()
        
    def clear(self) -> None:
        """Drop every timing variable, in the model and in the interpreter.

        Called by "remove -all", so that loading a diagram does not inherit the
        timing variables of the one it replaces (they would then be saved back
        into it).
        """
        console = self.topapp.console if self.topapp is not None else None
        for name in list(self.tvars):
            if console is None:
                break
            try:
                console.interp.eval("unset " + name)
            except tk.TclError:
                ## A variable whose expression never resolved was never set.
                pass

        self.tvars.clear()
        self.tvars_desc.clear()

    def write(self, fileref):
        for k, v in self.tvars.items():
            fileref.write(f"set_app_var -name timings.{k} \\\n")
            if k in self.tvars_desc:
                fileref.write(f"   -desc {{{self.tvars_desc[k]}}} \\\n")
            fileref.write(f"   -value {{{v}}}\n")
            

    def evaluate(self):
        self.console = self.topapp.console
        if self.console is None:
            return
        self.write(self.eval_buffer)
        try:
            self.console.interp.eval(self.eval_buffer.getvalue())
        except tk.TclError as e:
            self.console.append_log(f"Error: {e}\n", "error")  
        self.eval_buffer.seek(0)
        self.eval_buffer.truncate(0)
        
    
