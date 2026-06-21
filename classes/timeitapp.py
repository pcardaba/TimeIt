# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2024 Pablo Cardaba

from __future__ import annotations

from pathlib import Path
from typing import TextIO
from datetime import datetime, timezone

import tkinter as tk
from tkinter import filedialog, messagebox

from .settings import Settings
from .settingsdlg import SettingsDlg
from .signalsstore import SignalsStore
from .tclconsole import TclConsole
from .timings import Timings
from .timingsdlg import TimingsDlg
from .virtualcanvas import VirtualCanvas
from .waveformsview import WaveformsView
from .canvasexporter import CanvasExporter
from .undomanager import UndoManager
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

        # Undo/redo (GUI-only) — needs canvas + console for write_script.
        self.undo = UndoManager(self)
        self.parent.protocol("WM_DELETE_WINDOW", self._on_close)

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
        file_menu.add_command(label="Write Script…", command=self._write_script_dialog)
        file_menu.add_command(label="Export Canvas…", command=self._export_dialog)
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
    # Private methods
    # -------------------------------------------------------------------
    def _write_script_dialog(self) -> None:
        path_str = filedialog.asksaveasfilename(
            title="Write Script",
            defaultextension=".tcl",
            filetypes=[("Tcl script", "*.tcl"), ("Text", "*.txt"), ("All files", "*.*")],
        )
        if not path_str:
            return

        path = Path(path_str)
        try:
            with path.open("w", encoding="utf-8", newline="\n") as f:
                self.write_script(f)
                self.parent.title("TimeIt : "+path.name)
                self._file_path = path_str
        except OSError as exc:
            messagebox.showerror("Write Script", f"Could not write file:\n{exc}")

    def _load_script_dialog(self) -> None:
        path_str = filedialog.askopenfilename(
            title="Load Script",
            defaultextension=".tcl",
            filetypes=[("Tcl script", "*.tcl"), ("Text", "*.txt"), ("All files", "*.*")],
        )
        if not path_str:
            return

        cmd = "source {" + path_str +"}"
        try:
            self.console.interp.eval(cmd)
            self.parent.title("TimeIt : "+Path(path_str).name)
            self._file_path = path_str
        except tk.TclError as exc:
            self.console.append_log(f"Error: {exc}\n", "error")

    def _save(self, event=None):
        if not self._file_path:
            self._write_script_dialog()
            return
        path = Path(self._file_path)
        try:
            with path.open("w", encoding="utf-8", newline="\n") as f:
                self.write_script(f)
        except OSError as exc:
            messagebox.showerror("Write Script", f"Could not write file:\n{exc}")
        
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
        self.undo.cleanup()
        self.parent.destroy()

    def _export_dialog(self):
        exporter = CanvasExporter(self.canvas)
        exporter.export_dialog()
        
    def _open_timings(self) -> None:
        if getattr(self, "_timings_dlg", None) and self._timings_dlg.winfo_exists():
            self._timings_dlg.lift()
            self._timings_dlg.focus_force()
            return
        self._timings_dlg = TimingsDlg(self, self.timings)
        # Do not wait. This window is not modal.
        # self.wait_window(dlg)
        
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
        
    def _not_implemented(self) -> None:
        # Replace with logging or a proper dialog later
        pass
