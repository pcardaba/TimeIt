import tkinter as tk
from tkinter import ttk
import os

class ClockSignalDlg(tk.Toplevel):
    def __init__(self, parent, signal=None):
        super().__init__(parent, padx=10)
        self.topapp  = parent
        self._signal = signal
        self.title("Clock Signal")
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
        self.clkname_tkvar    = tk.StringVar()
        self.visible_tkvar    = tk.BooleanVar(value=True)
        self.color_tkvar      = tk.StringVar(value="black")
        self.clkperiod_tkvar  = tk.StringVar()
        self.clkrise_tkvar    = tk.StringVar()
        self.clkfall_tkvar    = tk.StringVar()
        self.lwidth_tkvar     = tk.IntVar(value=2)
        self.rise_unc_tkvar   = tk.StringVar()
        self.fall_unc_tkvar   = tk.StringVar()
        self.amplitude_tkvar  = tk.IntVar(value=40)
        self.cycles_tkvar     = tk.IntVar(value=10)
        self.topology_tkvar   = tk.StringVar(value="clockin")
        self.inputdly_tkvar   = tk.StringVar()
        self.outputdly_tkvar  = tk.StringVar()
        if self._signal is not None:
            s = self._signal
            self.clkname_tkvar.set(s.name)
            self.visible_tkvar.set(s.visible)
            self.color_tkvar.set(s.color)
            self.clkperiod_tkvar.set(s.period)
            self.clkrise_tkvar.set(s.rise_at)
            self.clkfall_tkvar.set(s.fall_at)
            self.lwidth_tkvar.set(s.lwidth)
            self.rise_unc_tkvar.set("" if s.rise_uncertainty is None else s.rise_uncertainty)
            self.fall_unc_tkvar.set("" if s.fall_uncertainty is None else s.fall_uncertainty)
            self.cycles_tkvar.set(s.cycles)
            self.inputdly_tkvar.set("" if s.input_dly is None else s.input_dly)
            self.outputdly_tkvar.set("" if s.output_dly is None else s.output_dly)
            self.topology_tkvar.set(s.topology)
            self.amplitude_tkvar.set(s.amplitude)        
        # ---
        self.grid_rowconfigure(0, minsize=10)
        crow = 1
        # --- Topology label frame.
        lf_topo = ttk.Labelframe(self, text='Topology')    
        src_dir = os.path.dirname(os.path.abspath(__file__))
        base_path = os.path.join(src_dir, "../data")
        self.images = {
            "clockin": tk.PhotoImage(file=base_path+"/clock_as_input.png"),
            "clockout": tk.PhotoImage(file=base_path+"/clock_as_output.png"),
            "clockinout": tk.PhotoImage(file=base_path+"/clock_as_inout.png"),
        }
        # --- Topology illustration images
        self.lbimg_topo = ttk.Label(lf_topo, image=self.images["clockin"])
        self.lbimg_topo.grid(row=1, rowspan=99, column=0, sticky="nswe", padx=2, pady=2)
        # --- Topology choice Radio buttons ---
        lfrow=10
        for choice, value in [
            ("Clock as Input", "clockin"),
            ("Clock as Output", "clockout"),
            ("Clock as Inout", "clockinout"),
        ]:
            ttk.Radiobutton(
                lf_topo,
                text=choice,
                value=value,
                variable=self.topology_tkvar,
                command=self._update_topology
            ).grid(row=lfrow, column=1, sticky="w", padx=5)
            lfrow+=2

        lf_topo.grid(row=crow, column=0, columnspan=99, sticky="nswe", padx=2, pady=2)
        crow += 1
        self.grid_rowconfigure(crow, minsize=10)
        crow += 1
        ## -> Row : Name, Visible, Color
        # clk name field...
        ttk.Label(self, text="Name").grid(row=crow, column=0, sticky="e")
        e_name = ttk.Entry(self, textvariable=self.clkname_tkvar, width=12)
        e_name.grid(row=crow, column=1, sticky="w", padx=2, pady=2)
        # Color ...
        ttk.Label(self, text="Color").grid(row=crow, column=2, sticky="e")
        cb_color = ttk.Combobox(
            self, textvariable=self.color_tkvar,
            values=("black", "green", "red", "blue", "orange", "purple"),
            width=10, state="readonly",
        )
        cb_color.grid(row=crow, column=3, sticky="w", padx=2, pady=2)
        # Line width...
        ttk.Label(self, text="Line width").grid(row=crow, column=4, sticky="e")
        sp_lw = ttk.Spinbox(
            self, from_=1, to=20, textvariable=self.lwidth_tkvar, width=2
        )
        sp_lw.grid(row=crow, column=5, sticky="w", padx=2, pady=2)
        # visibility checkbox...
        chk_visible = ttk.Checkbutton(
            self, text="Visible", variable=self.visible_tkvar
        )
        chk_visible.grid(row=crow, column=6, sticky="w", padx=2, pady=2)
        # Row : Cycles, Amplitude,
        crow += 1
        # -- Cycles (num of cycles to show.)
        ttk.Label(self, text="Cycles").grid(row=crow, column=2, sticky="e")
        sp_cycles = ttk.Spinbox(
            self, from_=2, to=100, textvariable=self.cycles_tkvar, width=3
        )
        sp_cycles.grid(row=crow, column=3, sticky="w", padx=2, pady=2)
        # -- Ampliture
        ttk.Label(self, text="Amplitude").grid(row=crow, column=4, sticky="e")
        sp_amp = ttk.Spinbox(
            self, from_=10, to=300, textvariable=self.amplitude_tkvar, width=3
        )
        sp_amp.grid(row=crow, column=5, sticky="w", padx=2, pady=2)
        ## -> Row: Period, Rise, Uncertainty ...
        crow += 1
        ## Period (is a text because we allow numerical and symbolic)
        ttk.Label(self, text="Period").grid(row=crow, column=0, sticky="w")
        e_period = ttk.Entry(self, textvariable=self.clkperiod_tkvar, width=10)
        e_period.grid(row=crow, column=1, sticky="w", padx=2, pady=2)
        ## Rise at...
        ttk.Label(self, text="Rise @").grid(row=crow, column=2, sticky="e")
        e_rise = ttk.Entry(self, textvariable=self.clkrise_tkvar, width=12)
        e_rise.grid(row=crow, column=3, sticky="w", padx=2, pady=2)
        ## Rise uncertainty.
        ttk.Label(self, text="Uncertainty").grid(row=crow, column=4, sticky="w")
        e_rise_unc = ttk.Entry(self, textvariable=self.rise_unc_tkvar, width=12)
        e_rise_unc.grid(row=crow, column=5, columnspan=2, sticky="w", padx=2, pady=2)
        ## -> Row: Fall at, uncertainty ...
        crow += 1
        ttk.Label(self, text="Fall @").grid(row=crow, column=2, sticky="e")
        e_fall = ttk.Entry(self, textvariable=self.clkfall_tkvar, width=12)
        e_fall.grid(row=crow, column=3, sticky="w", padx=2, pady=2)
        ## Fall uncertainty.
        ttk.Label(self, text="Uncertainty").grid(row=crow, column=4, sticky="w")
        e_fall_unc = ttk.Entry(self, textvariable=self.fall_unc_tkvar, width=12)
        e_fall_unc.grid(row=crow, column=5, columnspan=2, sticky="w", padx=2, pady=2)
        crow += 1
        ## Output delay
        self.l_output_dly = ttk.Label(self, text="Output Delay")
        self.l_output_dly.grid(row=crow, column=1, columnspan=2, sticky="e")
        self.e_output_dly = ttk.Entry(self, textvariable=self.outputdly_tkvar, width=12)
        self.e_output_dly.grid(row=crow, column=3, columnspan=2, sticky="w", padx=2, pady=2)
        ## Input delay
        self.l_input_dly = ttk.Label(self, text="Input Delay")
        self.l_input_dly.grid(row=crow, column=4, sticky="e")
        self.e_input_dly = ttk.Entry(self, textvariable=self.inputdly_tkvar, width=12)
        self.e_input_dly.grid(row=crow, column=5, columnspan=2, sticky="w", padx=2, pady=2)
        
        crow += 1
        ## Cancel, Apply, OK
        b_frame=ttk.Frame(self)
        b_frame.grid(row=crow, column=0, columnspan=6, sticky="nswe")
        b_frame.grid_rowconfigure(0, minsize=20)
        b_frame.grid_rowconfigure(2, minsize=10)
        b_frame.grid_columnconfigure(0, minsize=100)
        b_cancel=ttk.Button(b_frame, text="Cancel", command=self.dismiss)
        b_cancel.grid(row=1,column=2,sticky="we")
        b_apply=ttk.Button(b_frame, text="Apply", command=self.apply)
        b_apply.grid(row=1,column=3)
        b_ok=ttk.Button(b_frame, text="Ok", command=self.ok)
        b_ok.grid(row=1,column=4,sticky="we")
        
        self._update_topology()
        self._align_bg_colors()

    def _align_bg_colors(self):
        ## In Windows the bg color of the dlg window is different from ttk.Frames
        ## In Linux they are aligned but not in Windows and that creates color.
        ## discrepancies.
        frame = ttk.Frame(self)
        style = ttk.Style()
        frame_class = frame.winfo_class()
        ttk_frame_bg = style.lookup(frame_class, "background")
        self.config(bg=ttk_frame_bg)        
        
    # -------------------------------------------------------------------
    # Sync model from Tk variables
    # -------------------------------------------------------------------
    def _build_command(self):
        cmd = "create_clock"
        # A clock requires a name. If no name is given nothing happens.
        clkname = self.clkname_tkvar.get()
        if clkname is None or clkname == "":
            return ""
        cmd += " -name "+clkname
        # Chosen clock Topology
        topology = self.topology_tkvar.get()
        cmd += " -topology "+topology
        # A clock requires a period. If no period is given nothing happens.
        clkperiod = self.clkperiod_tkvar.get()
        if clkperiod is None or clkperiod == "":
            return ""
        cmd += " -period {"+clkperiod+"}"
        # A clock requires a waveform.
        riseat = self.clkrise_tkvar.get()
        if riseat is None or riseat == "":
            cmd += " -rise_at 0"
        else:
            cmd += " -rise_at {"+riseat+"}"
        fallat = self.clkfall_tkvar.get()
        if fallat is None or fallat == "":
            cmd += " -fall_at {("+clkperiod+")/2.0}"
        else:
            cmd += " -fall_at {"+fallat+"}"
        # A clock may have rising/fall uncertainties
        uncertainty = self.rise_unc_tkvar.get()
        if uncertainty is not None and not uncertainty == "":
            cmd += " -rise_uncertainty {"+uncertainty+"}"
        uncertainty = self.fall_unc_tkvar.get()
        if uncertainty is not None and not uncertainty == "":
            cmd += " -fall_uncertainty {"+uncertainty+"}"
        # Input delay
        if topology == "clockin" or topology == "clockinout":
            dly = self.inputdly_tkvar.get()
            if dly is not None and not dly == "":
                cmd += " -input_dly {"+dly+"}"
        # Output delay
        if topology == "clockout" or topology == "clockinout":
            dly = self.outputdly_tkvar.get()
            if dly is not None and not dly == "":
                cmd += " -output_dly {"+dly+"}"
        # Trace color:
        color = self.color_tkvar.get()
        cmd += " -color "+color
        # Amplitude:
        amplitude = self.amplitude_tkvar.get()
        if amplitude is None or amplitude <= 2:
            amplitude = 40
        cmd += " -amplitude "+str(amplitude)
        # Line width:
        lwidth = self.lwidth_tkvar.get()
        if lwidth is None or lwidth <= 0:
            lwidth = 2
        cmd += " -lwidth "+str(lwidth)
        # Visible.
        if self.visible_tkvar.get():
            cmd += " -visible"
        # Cycles
        cycles = self.cycles_tkvar.get()
        if cycles is None or cycles < 2:
            cycles = 2
        cmd += " -show "+str(cycles)
        
        return cmd
    
    def _update_topology(self):
        selected = self.topology_tkvar.get()
        self.lbimg_topo.configure(image=self.images[selected])
        if selected == "clockin":
            self.l_input_dly.configure(state="normal")
            self.e_input_dly.configure(state="normal")
            self.l_output_dly.configure(state="disabled")
            self.outputdly_tkvar.set("")
            self.e_output_dly.configure(state="disabled")
        if selected == "clockout":
            self.l_input_dly.configure(state="disabled")
            self.inputdly_tkvar.set("")
            self.e_input_dly.configure(state="disabled")
            self.l_output_dly.configure(state="normal")
            self.e_output_dly.configure(state="normal")
        if selected == "clockinout":
            self.l_input_dly.configure(state="normal")
            self.e_input_dly.configure(state="normal")
            self.l_output_dly.configure(state="normal")
            self.e_output_dly.configure(state="normal")
        
    def dismiss(self):
        self.grab_release()
        self.destroy()

    def cancel(self):
        ## The dialog windows was cancelled therefore created signal is not taken.
        self.dismiss()
        
    def apply(self):
        cmd = self._build_command()
        if cmd != "":
            self.topapp.console.execute(cmd)
        #for k, v in self.parent.signals.items():
        #    if v is self.signal:
        #        old_key = k
        #        self.parent.signals.pop(old_key)
        #        break
        #self.parent.signals[self.signal.name]=self.signal
        #self.parent.draw_signals()

    def ok(self):
        self.apply()
        self.dismiss()
