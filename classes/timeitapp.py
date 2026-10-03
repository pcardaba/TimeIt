# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2024 Pablo Cardaba

from __future__ import annotations

import io
from pathlib import Path
from typing import TextIO
from datetime import datetime, timezone

import tkinter as tk
from tkinter import filedialog, messagebox

from .importvcddlg import ImportVCDDlg
from .importvcdchardlg import ImportVCDCharDlg
from .vcdconvert import propose_choices
from .vcdimport import VCDPairAnalysis, VCDParseError, parse_vcd_file
from .settings import Settings
from .settingsdlg import SettingsDlg
from .signalsstore import SignalsStore
from .tclconsole import TclConsole
from .timings import Timings
from .timingsdlg import TimingsDlg
from .virtualcanvas import VirtualCanvas
from .waveformsview import WaveformsView
from .undomanager import UndoManager, meaningful_lines
from .aboutdlg import AboutDlg
from ._version import __version__


class TimeItApp(tk.PanedWindow):
    """Main application UI container (top-level frame)."""
    
    def __init__(self, parent: tk.Tk):
        super().__init__(parent, orient=tk.VERTICAL)
        self.parent = parent
        
        # Members: Core model/state objects
        # -------
        self.signals = SignalsStore()
        self.settings = Settings(self)
        self.timings = Timings(self)
        self.vcanvas = VirtualCanvas(self)

        # UI widgets (constructed synchronously; never None)
        self._build_root_geometry()
        self._build_menubar()
        self._bindings()

        self._canvas_frame = self._build_canvas()
        self.console = self._build_console()
        self._file_path = "" # Current file
        ## True while the undo manager writes a snapshot (see UndoManager).
        self.snapshot_mode = False

        # Undo/redo (GUI-only) — needs canvas + console for write_script.
        self.undo = UndoManager(self)
        self.parent.protocol("WM_DELETE_WINDOW", self._on_close)

        # Reference state for the unsaved-changes prompt on exit; re-captured
        # after every successful load/save.
        self._clean_lines = self._session_lines()

    # -------------------------------------------------------------------
    # UI construction helpers
    # -------------------------------------------------------------------
    def _build_root_geometry(self) -> None:
        self.parent.title("TimeIt")
        self.parent.rowconfigure(0, weight=1)
        self.parent.columnconfigure(0, weight=1)
        self.grid(row=0, column=0, sticky="nsew")
        icon_path = Path(__file__).parent.parent / "data" / "timeit_icon.png"
        if icon_path.exists():
            self._icon = tk.PhotoImage(file=str(icon_path))
            self.parent.iconphoto(True, self._icon)

    def _build_menubar(self) -> None:
        menubar = tk.Menu(self.parent)
        self.parent.config(menu=menubar)

        file_menu = tk.Menu(menubar, tearoff=False)
        menubar.add_cascade(label="File", menu=file_menu)
        file_menu.add_command(label="Load Script…", command=self._load_script_dialog)
        file_menu.add_command(label="Import VCDs…", command=self._import_vcd_dialog)
        file_menu.add_command(label="Write Script…", command=self._write_script_dialog)
        file_menu.add_command(label="Export Canvas…", command=self._export_dialog)
        file_menu.add_command(label="Write SDC…", command=self._write_sdc_dialog)
        file_menu.add_separator()
        file_menu.add_command(label="Save", command=self._save, accelerator="Ctrl+S")
        file_menu.add_command(label="Exit", command=self._on_close)

        edit_menu = tk.Menu(menubar, tearoff=False, postcommand=self._update_edit_menu_state)
        menubar.add_cascade(label="Edit", menu=edit_menu)
        edit_menu.add_command(label="Settings…", command=lambda: SettingsDlg(self, self.settings))
        edit_menu.add_command(label="Timings…", command=self._open_timings)
        edit_menu.add_separator()
        edit_menu.add_command(label="Undo", command=self._undo, accelerator="Ctrl+Z")
        edit_menu.add_command(label="Redo", command=self._redo, accelerator="Ctrl+Y")
        self._edit_menu = edit_menu

        help_menu = tk.Menu(menubar, tearoff=False)
        menubar.add_cascade(label="Help", menu=help_menu)
        help_menu.add_command(label="About", command=lambda: AboutDlg(self.parent))

    def _build_canvas(self) -> WaveformsView:
        canvas_frame = WaveformsView(self, width=800, height=250, bg="white")
        self.add(canvas_frame)
        return canvas_frame

    def _build_console(self) -> TclConsole:
        console = TclConsole(self)
        self.add(console)
        self.paneconfig(console, minsize=100)
        return console

    def _bindings(self) -> None:
        self.parent.bind("<Control-s>", self._save)
        self.parent.bind("<Control-z>", self._undo)
        self.parent.bind("<Control-y>", self._redo)
    # -------------------------------------------------------------------
    # Session state (unsaved-changes / blank detection)
    # -------------------------------------------------------------------
    ## View-only state: excluded from the modified-session comparison so that
    ## resizing the window or zooming alone never counts as an unsaved change
    ## (same philosophy as undo, which does not track view-only operations).
    _VIEW_ONLY_COMMANDS = ("set_window_size", "set_canvas_scale")

    def _session_lines(self) -> list[str]:
        """Current session as normalized script lines (the save format)."""
        buf = io.StringIO()
        self.write_script(buf)
        return [line for line in meaningful_lines(buf.getvalue())
                if not line.startswith(self._VIEW_ONLY_COMMANDS)]

    def _session_is_blank(self) -> bool:
        """True when loading a script would not discard anything."""
        return (len(self.signals) == 0
                and not self.timings.tvars
                and not self.console.user_vars()
                and not any(key != "current" for key in self.canvas.markers)
                and not self.canvas.splits)

    def _session_modified(self) -> bool:
        return self._session_lines() != self._clean_lines

    def _mark_session_clean(self) -> None:
        self._clean_lines = self._session_lines()

    # -------------------------------------------------------------------
    # Private methods
    # -------------------------------------------------------------------
    def _write_script_dialog(self) -> bool:
        """Ask for a path and save. Returns True when a file was written."""
        path_str = filedialog.asksaveasfilename(
            title="Write Script",
            defaultextension=".tcl",
            filetypes=[("Tcl script", "*.tcl"), ("Text", "*.txt"), ("All files", "*.*")],
        )
        if not path_str:
            return False

        try:
            self.save_script(path_str)
        except OSError as exc:
            messagebox.showerror("Write Script", f"Could not write file:\n{exc}")
            return False
        return True

    def save_script(self, path_str: str, make_current: bool = True) -> None:
        """Write the diagram to ``path_str`` (raises OSError).

        With ``make_current`` the file becomes the current file: the title
        shows it, Ctrl+S writes there and the session counts as clean. The
        write_script command uses False for a copy.
        """
        path = Path(path_str)
        with path.open("w", encoding="utf-8", newline="\n") as f:
            self.write_script(f)
        if make_current:
            self.parent.title("TimeIt : "+path.name)
            self._file_path = path_str
            self._mark_session_clean()

    ## First line that marks a script as a utility (e.g. scripts/timeit_socket.tcl)
    ## rather than a diagram: File -> Load sources it without making it the
    ## current file, so Ctrl+S never overwrites it, and without the "clears
    ## the diagram" warning (it does not start with "remove -all").
    UTILITY_SCRIPT_MARK = "# TimeIt utility script"

    @classmethod
    def is_utility_script(cls, path: str | Path) -> bool:
        try:
            with Path(path).open(encoding="utf-8", errors="replace") as f:
                return f.readline().strip().startswith(cls.UTILITY_SCRIPT_MARK)
        except OSError:
            return False

    def _load_script_dialog(self) -> None:
        path_str = filedialog.askopenfilename(
            title="Load Script",
            defaultextension=".tcl",
            filetypes=[("Tcl script", "*.tcl"), ("Text", "*.txt"), ("All files", "*.*")],
        )
        if not path_str:
            return

        if not self.is_utility_script(path_str) and not self._session_is_blank():
            if not messagebox.askokcancel(
                "Load Script",
                "Loading a script clears the current diagram:\n"
                "all signals, timing markers, splits, annotations and\n"
                "variables (timing and user) will be removed and replaced\n"
                "by the content of the loaded file.\n\n"
                "Load anyway?",
                icon="warning",
                parent=self.parent,
            ):
                return

        self._load_script(path_str)

    def _load_script(self, path_str: str) -> bool:
        """Source ``path_str`` as File -> Load does (no dialogs). A diagram
        becomes the current file; a utility script is only sourced. Returns
        True when the script sourced cleanly."""
        cmd = "source {" + path_str +"}"
        ## Echoed, not executed through the console: the title is only updated
        ## when the script sources cleanly, which needs the exception here.
        ## The commands inside the script run through their handlers and are
        ## not echoed, so a load logs this single line.
        self.console.echo_command(cmd)
        try:
            self.console.interp.eval(cmd)
        except tk.TclError as exc:
            self.console.append_log(f"Error: {exc}\n", "error")
            return False
        if self.is_utility_script(path_str):
            self.console.append_log(
                f"# {Path(path_str).name} is a utility script: sourced, "
                "current file unchanged.\n", "comment")
            return True
        self.parent.title("TimeIt : "+Path(path_str).name)
        self._file_path = path_str
        ## A freshly loaded diagram is in sync with its file.
        self._mark_session_clean()
        return True

    def _import_vcd_dialog(self) -> None:
        dlg = ImportVCDDlg(self.parent)
        self.wait_window(dlg)
        if dlg.result is None:
            return
        min_path, max_path = dlg.result
        self.console.append_log(
            f"Import VCDs: min={min_path} max={max_path}\n")

        try:
            vcd_min = parse_vcd_file(min_path)
            vcd_max = parse_vcd_file(max_path)
        except (OSError, VCDParseError) as exc:
            self.console.append_log(f"Import VCDs error: {exc}\n", "error")
            messagebox.showerror("Import VCDs", str(exc), parent=self.parent)
            return

        analysis = VCDPairAnalysis(vcd_min, vcd_max)
        for w in analysis.warnings:
            self.console.append_log(f"Import VCDs warning: {w}\n", "comment")
        if not analysis.ok:
            for e in analysis.errors:
                self.console.append_log(f"Import VCDs error: {e}\n", "error")
            messagebox.showerror(
                "Import VCDs",
                "The VCD pair is not consistent:\n\n"
                + "\n".join(analysis.errors),
                parent=self.parent)
            return

        for line in analysis.report_lines():
            self.console.append_log(line + "\n", "result")

        proposals = propose_choices(analysis)
        displays = {s.name: s.display for s in analysis.signals}
        for name, choice in proposals.items():
            if choice.ddr_hint is not None:
                self.console.append_log(
                    f"Import VCDs warning: '{displays[name]}' also fits both "
                    f"edges of '{displays[choice.ddr_hint]}' (DDR) — the "
                    f"single-edge reading on '{displays[choice.launch]}' is "
                    "proposed; check its launch clock in the dialog.\n",
                    "comment")

        char_dlg = ImportVCDCharDlg(self.parent, analysis, proposals)
        self.wait_window(char_dlg)
        converter = char_dlg.result
        if converter is None:
            self.console.append_log("Import VCDs: cancelled.\n", "comment")
            return

        for w in converter.warnings:
            self.console.append_log(f"Import VCDs warning: {w}\n", "comment")
        with self.undo.transaction():
            for cmd in converter.commands:
                self.console.execute(cmd)
        self.console.append_log(
            f"Import VCDs: {len(converter.commands)} signals imported.\n",
            "result")

    def _save(self, event=None) -> bool:
        """Save to the current file (or ask for one). True when written."""
        if not self._file_path:
            return self._write_script_dialog()
        try:
            self.save_script(self._file_path)
        except OSError as exc:
            messagebox.showerror("Write Script", f"Could not write file:\n{exc}")
            return False
        return True

    def _undo(self, event=None):
        self.undo.undo()
        return "break"

    def _redo(self, event=None):
        self.undo.redo()
        return "break"

    def _update_edit_menu_state(self) -> None:
        self._edit_menu.entryconfig(
            "Undo", state="normal" if self.undo.can_undo() else "disabled")
        self._edit_menu.entryconfig(
            "Redo", state="normal" if self.undo.can_redo() else "disabled")

    def _on_close(self) -> None:
        if self._session_modified():
            answer = messagebox.askyesnocancel(
                "Exit",
                "The diagram has unsaved changes.\n\n"
                "Save it before exiting?\n"
                "(Yes: save and exit — No: exit without saving)",
                icon="warning",
                parent=self.parent,
            )
            if answer is None:            # Cancel: stay in the application.
                return
            if answer and not self._save():
                return                    # Save was cancelled or failed: stay.
        self.undo.cleanup()
        self.parent.destroy()

    def _export_dialog(self):
        path_str = filedialog.asksaveasfilename(
            title="Export Canvas",
            defaultextension=".png",
            initialfile="canvas_export",
            filetypes=[
                ("PNG image",               "*.png"),
                ("JPEG image",              "*.jpg;*.jpeg"),
                ("SVG vector",              "*.svg"),
                ("PDF document",            "*.pdf"),
                ("PostScript",              "*.ps"),
                ("Encapsulated PostScript", "*.eps"),
            ],
        )
        if not path_str:
            return

        self.console.execute("export_canvas -file {" + path_str + "}")

    def _write_sdc_dialog(self):
        stem = Path(self._file_path).stem if self._file_path else "constraints"
        path_str = filedialog.asksaveasfilename(
            title="Write SDC",
            defaultextension=".sdc",
            initialfile=f"{stem}.sdc",
            filetypes=[
                ("SDC constraints", "*.sdc"),
                ("All files",       "*.*"),
            ],
        )
        if not path_str:
            return

        self.console.execute("write_sdc -file {" + path_str + "}")

    def _open_timings(self) -> None:
        self.open_timings()

    def open_timings(self, owner: tk.Misc | None = None) -> TimingsDlg:
        """Show the *User Timings* window, opened under ``owner``.

        The window is not modal and there is one at a time. From the Edit
        menu it is a child of the main window. A modal signal dialog passes
        itself as ``owner``: a Tk grab only reaches the grab window and its
        descendants, so a timings window parented to the main window would be
        frozen while the dialog is up, whereas one parented to the dialog is
        usable next to it (the user fills the form and creates the variables
        it needs at the same time). An instance open under another owner is
        replaced; one under the dialog goes away with the dialog.
        """
        master = owner if owner is not None else self
        dlg = getattr(self, "_timings_dlg", None)
        if dlg is not None and dlg.winfo_exists():
            if dlg.master is master:
                dlg.lift()
                dlg.focus_force()
                return dlg
            dlg.destroy()
        self._timings_dlg = TimingsDlg(master, self.timings, topapp=self)
        # Do not wait. This window is not modal.
        return self._timings_dlg

    def timings_dlg(self) -> TimingsDlg | None:
        """The open *User Timings* window, if any."""
        dlg = getattr(self, "_timings_dlg", None)
        if dlg is not None and dlg.winfo_exists():
            return dlg
        return None
        
    # -------------------------------------------------------------------
    # Convenience accessors
    # -------------------------------------------------------------------
    @property
    def canvas(self):
        """Return the custom canvas from WaveformsView."""
        return self._canvas_frame.canvas

    # -------------------------------------------------------------------
    # Public methods
    # -------------------------------------------------------------------
    def redraw(self) -> None:
        """Redraws the virtual canvas then the visible canvas."""
        self.vcanvas.redraw()
        self.canvas.redraw()
        ## An open User Timings window follows the model: a variable set from
        ## the console, a load or an undo (every one of them ends in a redraw).
        dlg = self.timings_dlg()
        if dlg is not None:
            dlg.refresh()

    def write_script(self, f: TextIO) -> None:
        """Full script generation"""
        f.write("# TimeIt generated script\n")
        f.write("# =======================\n")
        f.write(f"# version commit: ({__version__})\n")
        ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        f.write(f"# datetime: {ts}\n\n")
        f.write(f"remove -all\n\n")
        f.write(
            f"set_window_size -width {self.parent.winfo_width()} "
            f"-height {self.parent.winfo_height()}\n\n"
        )
        self.canvas.write_script(f)   

    def set_window_size(self, width: int | None = None, height: int | None = None) -> None:
        """Resize the main window; None keeps the current dimension."""
        if width is None:
            width = self.parent.winfo_width()
        if height is None:
            height = self.parent.winfo_height()
        self.parent.geometry(f"{width}x{height}")

    def set_canvas_scale(self, scale: float) -> None:
        self.canvas.set_scale(scale)

    def remove_all(self) -> None:
        self.canvas.remove_all()
        self.vcanvas.remove_all()
        self.timings.clear()
        self.console.clear_user_vars()
        dlg = self.timings_dlg()
        if dlg is not None:
            dlg.refresh()
        
    def _not_implemented(self) -> None:
        # Replace with logging or a proper dialog later
        pass
