import tkinter as tk
from tkinter import ttk

class TimingMarkerDlg(tk.Toplevel):
    def __init__(self, parent, marker):
        super().__init__(parent, padx=10)
        self.title("Timing Marker")
        self.topapp = parent
        self.settings = self.topapp.settings
        self.marker = marker
        self._build_dlg()
        # Disable resizing in both directions
        self.resizable(False, False)
        self.protocol("WM_DELETE_WINDOW", self.dismiss) # intercept close button
        self.transient(parent)   # dialog window is related to main
        self.wait_visibility() # can't grab until window appears, so we wait
        self.grab_set()        # ensure all input goes to our window
        self.wait_window()     # block until window is destroyed

    def _build_dlg(self):
        # -- tkvars
        self.labelchoice_tkvar = tk.StringVar(value="timing")
        self.name_tkvar        = tk.StringVar(value=self.marker.name)
        self.stylechoice_tkvar = tk.StringVar(value=self.marker.style)
        
        # self.grid_rowconfigure(0, minsize=10)
        crow = 1
        # --- Label frame.
        lf_label = ttk.Labelframe(self, text="Marker Label")
        lfrow = 1
        ttk.Radiobutton(
            lf_label,
            text="Name: ",
            value="name",
            variable=self.labelchoice_tkvar,
        ).grid(row=lfrow, column=1, sticky="w", padx=5)
        e_name = ttk.Entry(lf_label, textvariable=self.name_tkvar, width=8)
        e_name.grid(row=lfrow, column=2, sticky="e", padx=2, pady=2)
        lfrow = 2
        ttk.Radiobutton(
            lf_label,
            text="Timing: ",
            value="timing",
            variable=self.labelchoice_tkvar,
        ).grid(row=lfrow, column=1, sticky="w", padx=5)
        mark_timing =  format(self.marker.timing, self.settings.marker["float_format"])
        mark_timing += self.settings.waveform["tunits"]
        ttk.Label(lf_label, text=mark_timing).grid(row=lfrow, column=2, sticky="e", padx=4, pady=2)
        #--
        lf_label.grid(row=crow, column=0, sticky="nswe", padx=2, pady=2)
        #--
        lf_style = ttk.Labelframe(self, text="Marker Style")
        lfrow = 1
        ttk.Label(lf_style, text="<inner_both>").grid(row=lfrow, column=1, sticky="we", padx=2, pady=2)
        ttk.Label(lf_style, text="<inner_right>").grid(row=lfrow, column=2, sticky="we", padx=2, pady=2)
        ttk.Label(lf_style, text="<inner_left>").grid(row=lfrow, column=3, sticky="we", padx=2, pady=2)
        ttk.Label(lf_style, text="<outer>").grid(row=lfrow, column=4, sticky="we", padx=2, pady=2)
        lfrow += 1
        ttk.Radiobutton(
            lf_style,
            value="inner_both",
            variable=self.stylechoice_tkvar,
        ).grid(row=lfrow, column=1, sticky="")
        ttk.Radiobutton(
            lf_style,
            value="inner_right",
            variable=self.stylechoice_tkvar,
        ).grid(row=lfrow, column=2, sticky="")
        ttk.Radiobutton(
            lf_style,
            value="inner_left",
            variable=self.stylechoice_tkvar,
        ).grid(row=lfrow, column=3, sticky="")
        ttk.Radiobutton(
            lf_style,
            value="outer",
            variable=self.stylechoice_tkvar,
        ).grid(row=lfrow, column=4, sticky="")
        
        lf_style.grid(row=crow, column=1, sticky="nsew", padx=2, pady=2)
        # --
        crow += 1
        
    def dismiss(self):
        self.grab_release()
        self.destroy()

    def cancel(self):
        ## The dialog windows was cancelled therefore created signal is not taken.
        self.dismiss()
        
    def apply(self):
        pass

    def ok(self):
        pass
