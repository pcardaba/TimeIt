from __future__ import annotations

import tkinter as tk
from tkinter import ttk
from pathlib import Path

from .tclcommands import TclCommands


class TclConsole(ttk.Frame):
    """A small embedded Tcl console with history, logging and basic highlighting."""

    def __init__(self, master: tk.Misc | None = None, **kwargs) -> None:
        super().__init__(master, **kwargs)

        self.topapp = master
        
        # Embedded Tcl interpreter
        self.interp = tk.Tcl()

        self.tcl_commands = TclCommands(self)
        
        # Command history
        self.history: list[str] = []
        self.history_index: int | None = None

        # Buffer for multi-line blocks
        self.buffer: list[str] =  []

        # Known commands for completion and highlighting
        self.commands = [
            "set",
            "unset",
            "proc",
            "if",
            "elseif",
            "else",
            "while",
            "foreach",
            "for",
            "switch",
            "puts",
            "create_clock",
            "create_input",
            "create_output",
            "set_app_var",
            "create_timing_marker",
            "set_window_size",
            "set_canvas_scale",
        ]

        # Log files (placed next to this module by default)
        base_dir = Path(__file__).resolve().parent
        self.full_log_path = base_dir / "timeit_full.log"
        self.cmd_log_path = base_dir / "timeit_commands.log"

        # Build UI and config
        self._build_ui()
        self._configure_tags()
        self._bind_events()
        self._register_commands()

        # Clear old logs
        for p in (self.full_log_path, self.cmd_log_path):
            try:
                p.unlink()
            except FileNotFoundError:
                pass
            except OSError:
                # Logging should never break the UI
                pass

        # Configure grid expansion inside this frame
        self.rowconfigure(0, weight=1)  # text grows
        self.rowconfigure(1, weight=0)  # entry never shrinks away
        self.columnconfigure(0, weight=1)

        # Initial message
        self.append_log("# TimeIt Tcl history window.\n", "comment")

    # ----------------------------------------------------------------------
    # Private methods
    # ----------------------------------------------------------------------
    def _build_ui(self) -> None:
        self._output = tk.Text(self, width=40, height=4, wrap="word", undo=False)
        self._output.grid(row=0, column=0, sticky="nsew")
        self._output.configure(state="disabled")
        self._output.grid_propagate(False)

        bottom = ttk.Frame(self)
        bottom.grid(row=1, column=0, sticky="ew", pady=3)
        bottom.columnconfigure(1, weight=1)

        self.prompt_label = ttk.Label(bottom, text="%", width=2)
        self.prompt_label.grid(row=0, column=0, sticky="w")

        self.entry = ttk.Entry(bottom)
        self.entry.grid(row=0, column=1, sticky="ew")
        self.entry.focus_set()

    # ----------------------------------------------------------------------
    # Text tags
    # ----------------------------------------------------------------------
    def _configure_tags(self) -> None:
        # NOTE: colors are UI choices; keep as-is for now.
        self._output.tag_configure("prompt", foreground="#00aa00")
        self._output.tag_configure("command", foreground="#000000")
        self._output.tag_configure("result", foreground="#555555")
        self._output.tag_configure("error", foreground="#ff0000")
        self._output.tag_configure("keyword", foreground="#00bfff")
        self._output.tag_configure("comment", foreground="#888888")
        self._output.tag_configure("stdout", foreground="#00008b")
        self._output.tag_configure("stderr", foreground="#ff0000")

    # ----------------------------------------------------------------------
    # Events
    # ----------------------------------------------------------------------
    def _bind_events(self) -> None:
        self.entry.bind("<Return>", self._on_enter)
        self.entry.bind("<Shift-Return>", self._on_shift_enter)
        self.entry.bind("<Up>", self._on_history_up)
        self.entry.bind("<Down>", self._on_history_down)
        self.entry.bind("<Tab>", self._on_tab_complete)

        
    # ----------------------------------------------------------------------
    # Tcl command registration
    # ----------------------------------------------------------------------
    def _register_commands(self) -> None:
        """  Tcl command registration """
        self.interp.createcommand("create_clock", self.tcl_commands.create_clock.run_cmd)
        self.interp.createcommand("create_input", self.tcl_commands.create_input.run_cmd)
        self.interp.createcommand("create_output", self.tcl_commands.create_output.run_cmd)
        self.interp.createcommand("create_timing_marker",
                                  self.tcl_commands.create_timing_marker.run_cmd)
        self.interp.createcommand("set_app_var", self.tcl_commands.set_app_var)
        self.interp.createcommand("set_window_size", self.tcl_commands.set_window_size)
        self.interp.createcommand("set_canvas_scale", self.tcl_commands.set_canvas_scale)
        self.interp.createcommand("puts", self.tcl_commands.puts)

        self.interp.eval(
            """
            proc puts_stdout {msg} { puts stdout $msg }
            proc puts_stderr {msg} { puts stderr $msg }
            """
        )

    # ----------------------------------------------------------------------
    # Logging + output
    # ----------------------------------------------------------------------
    def _safe_append_file(self, path: Path, text: str) -> None:
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            with path.open("a", encoding="utf-8", newline="\n") as f:
                f.write(text)
        except OSError:
            # Never crash the UI because a log file can't be written.
            pass

    def _echo_command_line(self, line: str, *, continuation: bool = False) -> None:
        prefix = "> " if continuation else "% "

        self._safe_append_file(self.cmd_log_path, line + "\n")
        self._safe_append_file(self.full_log_path, prefix + line + "\n")

        self._output.configure(state="normal")
        self._output.insert("end", prefix, "prompt")
        start = self._output.index("end-1c")
        self._output.insert("end", line + "\n", "command")
        end = self._output.index("end-1c")
        self._output.configure(state="disabled")
        self._output.see("end")

        self._highlight_command_line(start, end)

    def _highlight_command_line(self, start: str, end: str) -> None:
        """ Syntax highlighting """
        self._output.tag_remove("keyword", start, end)
        self._output.tag_remove("comment", start, end)

        line_text = self._output.get(start, end)

        # Simple comment detection (Tcl uses # for comments)
        comment_pos = line_text.find("#")
        if comment_pos != -1:
            cstart = f"{start}+{comment_pos}c"
            self._output.tag_add("comment", cstart, end)
            line_text = line_text[:comment_pos]

        # Highlight keywords (token-ish boundary check)
        for kw in self.commands:
            idx = 0
            while True:
                idx = line_text.find(kw, idx)
                if idx == -1:
                    break

                before_ok = idx == 0 or not line_text[idx - 1].isalnum()
                after_ok = (idx + len(kw) == len(line_text)) or not line_text[idx + len(kw)].isalnum()

                if before_ok and after_ok:
                    kstart = f"{start}+{idx}c"
                    kend = f"{start}+{idx + len(kw)}c"
                    self._output.tag_add("keyword", kstart, kend)

                idx += len(kw)
                
    def _is_block_incomplete(self, txt: str) -> bool:
        """ Multiline detection """
        brace = 0
        bracket = 0
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

    def _on_shift_enter(self, event: tk.Event) -> str:
        line = self.entry.get()
        self.entry.delete(0, tk.END)

        self.buffer.append(line)
        self._echo_command_line(line, continuation=True)
        self.prompt_label.config(text=">")
        return "break"

    def _on_enter(self, event: tk.Event) -> str:
        line = self.entry.get()
        self.entry.delete(0, tk.END)

        # If user pressed Enter on an empty line and we already have a buffer,
        # execute the block as-is (common REPL behavior).
        if not line and self.buffer:
            full = "\n".join(self.buffer)
            return self.execute(full)

        self.buffer.append(line)
        full = "\n".join(self.buffer)

        self._echo_command_line(line, continuation=(len(self.buffer) > 1))

        if self._is_block_incomplete(full):
            self.prompt_label.config(text=">")
            return "break"

        return self.execute(full)

    def _on_history_up(self, event: tk.Event) -> str:
        if not self.history:
            return "break"

        if self.history_index is None:
            self.history_index = len(self.history) - 1
        else:
            self.history_index = max(0, self.history_index - 1)

        self.entry.delete(0, tk.END)
        self.entry.insert(0, self.history[self.history_index])
        return "break"

    def _on_history_down(self, event: tk.Event) -> str:
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

    def _on_tab_complete(self, event: tk.Event) -> str:
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

    def _show_command_help(self, command_name: str) -> None:
        """Load and display help text for a given command name."""
        base_path = (Path(__file__).resolve().parent / ".." / "data").resolve()
        filename = base_path / f"{command_name}.help.txt"

        try:
            content = filename.read_text(encoding="utf-8")
        except FileNotFoundError:
            self.append_log(f"No help available for {command_name}\n", "error")
            return
        except OSError as exc:
            self.append_log(f"Help load error: {exc}\n", "error")
            return

        self.append_log(content, "result")


    
    ############################################################################    
    # ----------------------------------------------------------------------
    # Public methods 
    # ----------------------------------------------------------------------
    def append_log(self, text: str, tag: Optional[str] = None) -> None:
        self._safe_append_file(self.full_log_path, text)
        
        self._output.configure(state="normal")
        self._output.insert("end", text, tag)
        self._output.configure(state="disabled")
        self._output.see("end")

    def execute(self, full: str) -> str:
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
        except tk.TclError as exc:
            self.append_log(f"Error: {exc}\n", "error")

        return "break"


