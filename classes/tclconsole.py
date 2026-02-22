import tkinter as tk
from tkinter import ttk
import os
from .tclcommands import TclCommands

class TclConsole(ttk.Frame):

    FULL_LOG_FILE = "timeit_full.log"
    CMD_LOG_FILE = "timeit_commands.log"

    def __init__(self, master=None, **kwargs):
        super().__init__(master, **kwargs)

        self.topapp = master
        
        # Embedded Tcl interpreter
        self.interp = tk.Tcl()

        self.tcl_commands = TclCommands(self)
        # Command history
        self.history = []
        self.history_index = None

        # Buffer for multi-line blocks
        self.buffer = []

        # Known commands for completion and highlighting
        self.commands = [
            "set", "unset", "proc", "if", "elseif", "else",
            "while", "foreach", "for", "switch", "puts",
            "create_clock", "create_input", "create_output",
            "set_app_var", "create_timing_marker"
        ]

        # Build UI and config
        self._build_ui()
        self._configure_tags()
        self._bind_events()
        self._register_commands()

        # Clear old logs
        for path in (self.FULL_LOG_FILE, self.CMD_LOG_FILE):
            try:
                os.remove(path)
            except FileNotFoundError:
                pass

        # Configure grid expansion inside this frame
        self.rowconfigure(0, weight=1)  # text grows
        self.rowconfigure(1, weight=0)  # entry never shrinks away
        self.columnconfigure(0, weight=1)

        # Enforce minimum window size once UI is constructed
        # self.after(100, self._set_minimum_window_size)

        # Initial message
        self.append_log("# TimeIt Tcl history window.\n", "comment")

    # ----------------------------------------------------------------------
    # UI
    # ----------------------------------------------------------------------
    def _build_ui(self):

        # Output history text pane (no scrollbar)
        self.output = tk.Text(self, width=40, height=4, wrap="word", undo=False)
        self.output.grid(row=0, column=0, sticky="nsew")
        self.output.configure(state="disabled")

        self.output.grid_propagate(False)

        # Bottom bar with prompt + entry
        bottom = ttk.Frame(self)
        bottom.grid(row=1, column=0, sticky="ew", pady=3)
        bottom.columnconfigure(1, weight=1)  # entry expands horizontally

        self.prompt_label = ttk.Label(bottom, text="%", width=2)
        self.prompt_label.grid(row=0, column=0, sticky="w")

        self.entry = ttk.Entry(bottom)
        self.entry.grid(row=0, column=1, sticky="ew")
        self.entry.focus_set()

    # ----------------------------------------------------------------------
    # Minimum window size calculation
    # ----------------------------------------------------------------------
#    def _set_minimum_window_size(self):
#        root = self.winfo_toplevel()
#
#        # Approximate character + line geometry
#        char_width_px = 8
#        line_height_px = 20
#
#        min_width = 25 * char_width_px       # 25 characters
#        min_height = (4 * line_height_px) + 40  # 4 lines + entry + padding
#
#        root.minsize(min_width, min_height)

    # ----------------------------------------------------------------------
    # Text tags
    # ----------------------------------------------------------------------
    def _configure_tags(self):
        self.output.tag_configure("prompt",  foreground="#00aa00")
        self.output.tag_configure("command", foreground="#000000")
        self.output.tag_configure("result",  foreground="#555555")
        self.output.tag_configure("error",   foreground="#ff0000")
        self.output.tag_configure("keyword", foreground="#00bfff")
        self.output.tag_configure("comment", foreground="#888888")
        self.output.tag_configure("stdout",  foreground="#00008b")
        self.output.tag_configure("stderr",  foreground="#ff0000")

    # ----------------------------------------------------------------------
    # Events
    # ----------------------------------------------------------------------
    def _bind_events(self):
        self.entry.bind("<Return>", self.on_enter)
        self.entry.bind("<Shift-Return>", self.on_shift_enter)
        self.entry.bind("<Up>", self.on_history_up)
        self.entry.bind("<Down>", self.on_history_down)
        self.entry.bind("<Tab>", self.on_tab_complete)

    # ----------------------------------------------------------------------
    # Tcl command registration
    # ----------------------------------------------------------------------
    def _register_commands(self):

        self.interp.createcommand("create_clock", self.tcl_commands.create_clock.run_cmd)
        self.interp.createcommand("create_input", self.tcl_commands.create_input.run_cmd)
        self.interp.createcommand("create_output", self.tcl_commands.create_output.run_cmd)
        self.interp.createcommand("create_timing_marker", self.tcl_commands.create_timing_marker.run_cmd)
        self.interp.createcommand("set_app_var", self.tcl_commands.set_app_var)
        self.interp.createcommand("puts", self.tcl_commands.puts)

        # Tcl convenience wrappers
        self.interp.eval("""
            proc puts_stdout {msg} { puts stdout $msg }
            proc puts_stderr {msg} { puts stderr $msg }
        """)

    # ----------------------------------------------------------------------
    # Logging + output
    # ----------------------------------------------------------------------
    def append_log(self, text, tag=None):
        # Log outputs to full log
        with open(self.FULL_LOG_FILE, "a", encoding="utf-8") as f:
            f.write(text)

        # Display
        self.output.configure(state="normal")
        self.output.insert("end", text, tag)
        self.output.configure(state="disabled")
        self.output.see("end")

    def _echo_command_line(self, line, continuation=False):
        prefix = "> " if continuation else "% "

        with open(self.CMD_LOG_FILE, "a", encoding="utf-8") as f:
            f.write(line + "\n")

        with open(self.FULL_LOG_FILE, "a", encoding="utf-8") as f:
            f.write(prefix + line + "\n")

        self.output.configure(state="normal")
        self.output.insert("end", prefix, "prompt")
        start = self.output.index("end-1c")
        self.output.insert("end", line + "\n", "command")
        end = self.output.index("end-1c")
        self.output.configure(state="disabled")
        self.output.see("end")

        self._highlight_command_line(start, end)

    # ----------------------------------------------------------------------
    # Syntax highlighting
    # ----------------------------------------------------------------------
    def _highlight_command_line(self, start, end):
        self.output.tag_remove("keyword", start, end)
        self.output.tag_remove("comment", start, end)

        line_text = self.output.get(start, end)

        # Simple comment detection
        comment_pos = line_text.find("#")
        if comment_pos != -1:
            cstart = f"{start}+{comment_pos}c"
            self.output.tag_add("comment", cstart, end)
            line_text = line_text[:comment_pos]

        # Highlight keywords
        for kw in self.commands:
            idx = 0
            while True:
                idx = line_text.find(kw, idx)
                if idx == -1:
                    break

                before_ok = idx == 0 or not line_text[idx - 1].isalnum()
                after_ok = idx + len(kw) == len(line_text) or \
                           not line_text[idx + len(kw)].isalnum()

                if before_ok and after_ok:
                    kstart = f"{start}+{idx}c"
                    kend = f"{start}+{idx + len(kw)}c"
                    self.output.tag_add("keyword", kstart, kend)

                idx += len(kw)

    # ----------------------------------------------------------------------
    # Multiline detection
    # ----------------------------------------------------------------------
    def is_block_incomplete(self, txt):
        brace = bracket = 0
        in_quote = False

        for ch in txt:
            if ch == '"':
                in_quote = not in_quote
            if not in_quote:
                if ch == "{":
                    brace += 1
                elif ch == "}":
                    brace -= 1
                elif ch == "[":
                    bracket += 1
                elif ch == "]":
                    bracket -= 1

        return brace > 0 or bracket > 0 or in_quote

    # ----------------------------------------------------------------------
    # Enter handlers
    # ----------------------------------------------------------------------
    def on_shift_enter(self, event):
        line = self.entry.get()
        self.entry.delete(0, tk.END)

        self.buffer.append(line)
        self._echo_command_line(line, continuation=True)
        self.prompt_label.config(text=">")
        return "break"

    def on_enter(self, event):
        line = self.entry.get()
        self.entry.delete(0, tk.END)

        if not line and self.buffer:
            full = "\n".join(self.buffer)
            return self.execute(full)

        self.buffer.append(line)
        full = "\n".join(self.buffer)

        continuation = len(self.buffer) > 1
        self._echo_command_line(line, continuation=continuation)

        if self.is_block_incomplete(full):
            self.prompt_label.config(text=">")
            return "break"

        return self.execute(full)

    def execute(self, full):
        full = full.rstrip()
        self.prompt_label.config(text="%")

        self.buffer.clear()

        if full:
            self.history.append(full)
        self.history_index = None

        try:
            result = self.interp.eval(full)
            if result:
                self.append_log(result + "\n", "result")
        except tk.TclError as e:
            self.append_log(f"Error: {e}\n", "error")

        return "break"

    # ----------------------------------------------------------------------
    # History navigation
    # ----------------------------------------------------------------------
    def on_history_up(self, event):
        if not self.history:
            return "break"
        if self.history_index is None:
            self.history_index = len(self.history) - 1
        else:
            self.history_index = max(0, self.history_index - 1)

        self.entry.delete(0, tk.END)
        self.entry.insert(0, self.history[self.history_index])
        return "break"

    def on_history_down(self, event):
        if self.history_index is None:
            return "break"

        self.history_index += 1

        if self.history_index >= len(self.history):
            self.history_index = None
            self.entry.delete(0, tk.END)
        else:
            self.entry.delete(0, tk.END)
            self.entry.insert(0, self.history[self.history_index])

        return "break"

    # ----------------------------------------------------------------------
    # Tab completion
    # ----------------------------------------------------------------------
    def on_tab_complete(self, event):
        text = self.entry.get()
        if not text.strip():
            return "break"

        parts = text.split()
        prefix = parts[-1]

        matches = [c for c in self.commands if c.startswith(prefix)]
        if not matches:
            return "break"

        if len(matches) == 1:
            parts[-1] = matches[0]
            self.entry.delete(0, tk.END)
            self.entry.insert(0, " ".join(parts))
        else:
            self.append_log("  " + "  ".join(matches) + "\n", "result")

        return "break"


    def _show_command_help(self, command_name):
        """
        Loads and sends the syntax file for a given command name.
        """
        src_dir = os.path.dirname(os.path.abspath(__file__))
        base_path = os.path.join(src_dir, "../data")
        filename = os.path.join(base_path, f"{command_name}.help.txt")

        with open(filename, "r", encoding="utf-8") as f:
            content = f.read()

        self.append_log(content, "result")
