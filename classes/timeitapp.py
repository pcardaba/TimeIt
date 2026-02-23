# TimeIt application main frame.
import tkinter as tk
from tkinter import filedialog, messagebox

from .settings import Settings
from .settingsdlg import SettingsDlg
from .timings import Timings
from .timingsdlg import TimingsDlg
from .signalsstore import SignalsStore

from .tclconsole import TclConsole
from .waveformsview import WaveformsView
from .virtualcanvas import VirtualCanvas

class TimeItApp(tk.PanedWindow):
    """Main application UI container (top-level frame)."""
    
    def __init__(self, parent: tk.Tk):
        super().__init__(parent, orient=tk.VERTICAL)
        
        # Members:
        # -------
        self.parent = parent
        # TCL console + Waveform canvas frame:
        self.console: TclConsole | None = None
        self.signals = SignalsStore()
        self.settings = Settings(self)
        self.timings = Timings(self)
        self.canvas_frame: WaveformsView | None = None
        self.canvas: tk.Canvas | None = None
        self.vcanvas = VirtualCanvas(self)
        self._build_ui()
    # -------------------------------------------------------------------
    # UI construction
    # -------------------------------------------------------------------
    def _build_ui(self) -> None:
        self.parent.title("TimeIt")
        self.parent.rowconfigure(0, weight=1)
        self.parent.columnconfigure(0, weight=1)
        self.grid(row=0, column=0, sticky="nsew")

        self._build_menubar()
        self._build_canvas()
        self._build_console()

    # -------------------------------------------------------------------
    # Menubar construction
    # -------------------------------------------------------------------
    def _build_menubar(self) -> None:
        menubar = tk.Menu(self.parent)
        self.parent.config(menu=menubar)

        # File menu
        # ---------
        file_menu = tk.Menu(menubar, tearoff=False)
        menubar.add_cascade(label="File", menu=file_menu)
        file_menu.add_command(label="Load Script…", command=self.load_script_dialog)
        file_menu.add_command(label="Write Script…", command=self.write_script_dialog)
        file_menu.add_command(label="Export Canvas...", command=self._not_implemented)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.parent.destroy)

        # Edit menu
        # ---------
        edit_menu = tk.Menu(menubar, tearoff=False)
        menubar.add_cascade(label="Edit", menu=edit_menu)
        edit_menu.add_command(label="Settings...", command=lambda: SettingsDlg(self,self.settings))
        edit_menu.add_command(label="Timings...", command=self.open_timings)

    def _build_canvas(self) -> None:
        self.canvas_frame = WaveformsView(self, width=800, height=250, bg="white")
        self.canvas = self.canvas_frame.canvas
        self.add(self.canvas_frame)
        # self.signals.set_on_change(self.canvas.redraw)
        
    def _build_console(self) -> None:
        self.console = TclConsole(self)
        self.add(self.console)
        self.paneconfig(self.console, minsize=100)
    
    def redraw(self) -> None:
        # Always redraw in virtual canvas first.
        self.vcanvas.redraw()
        self.canvas.redraw()

    def write_script_dialog(self):
        path = filedialog.asksaveasfilename(
            title="Write Script",
            defaultextension=".tcl",
            filetypes=[("Tcl script", "*.tcl"), ("Text", "*.txt"), ("All files", "*.*")]
        )
        if not path:   # user cancelled
            return

        try:
            with open(path, "w", encoding="utf-8", newline="\n") as f:
                # Optional header
                f.write("# TimeIt generated script\n")
                f.write("# =======================\n\n")
                self.canvas.write_script(f)               

        except OSError as e:
            messagebox.showerror("Write Script", f"Could not write file:\n{e}")
            
    def load_script_dialog(self):
        path = filedialog.askopenfilename(
            title="Load Script",
            defaultextension=".tcl",
            filetypes=[("Tcl script", "*.tcl"), ("Text", "*.txt"), ("All files", "*.*")]
        )
        if not path:   # user cancelled
            return

        try:
            self.console.interp.eval("source "+path)
        except  tk.TclError as e:
            self.console.append_log(f"Error: {e}\n", "error")
        
    def open_timings(self):
        dlg = TimingsDlg(self, self.timings)
        self.wait_window(dlg)
        
    def _not_implemented(self) -> None:
        # replace with logging or a proper dialog later
        pass
