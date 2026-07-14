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
        self.master_tkvar     = tk.StringVar()
        self.genspec_tkvar    = tk.StringVar(value="divide_by")
        self.edges_tkvar      = tk.StringVar(value="1 3 5")
        self.divideby_tkvar   = tk.IntVar(value=2)
        self.invert_tkvar     = tk.BooleanVar(value=False)

        # The source clocks a generated clock may derive from. A clock can not
        # be its own master, hence the edited signal is never a candidate.
        self._source_clocks = [
            name for name, sig in self.topapp.signals.items()
            if sig.type == "clock" and not sig.is_generated and sig is not self._signal
        ]

        if self._signal is not None:
            s = self._signal
            self.clkname_tkvar.set(s.name)
            self.visible_tkvar.set(s.visible)
            self.color_tkvar.set(s.color)
            self.lwidth_tkvar.set(s.lwidth)
            self.cycles_tkvar.set(s.cycles)
            self.topology_tkvar.set(s.topology)
            self.amplitude_tkvar.set(s.amplitude)
            if s.is_generated:
                self.inputdly_tkvar.set("" if s.input_dly is None else s.input_dly)
                self.outputdly_tkvar.set("" if s.output_dly is None else s.output_dly)
                if s.master is not None:
                    self.master_tkvar.set(s.master.name)
                self.edges_tkvar.set(" ".join(str(e) for e in s.edges))
                if s.divide_by is None:
                    self.genspec_tkvar.set("edges")
                else:
                    self.divideby_tkvar.set(s.divide_by)
                self.invert_tkvar.set(s.invert)
            else:
                self.clkperiod_tkvar.set(s.period)
                self.clkrise_tkvar.set(s.rise_at)
                self.clkfall_tkvar.set(s.fall_at)
                self.rise_unc_tkvar.set(
                    "" if s.rise_uncertainty is None else s.rise_uncertainty)
                self.fall_unc_tkvar.set(
                    "" if s.fall_uncertainty is None else s.fall_uncertainty)
        # ---
        self.grid_rowconfigure(0, minsize=10)
        crow = 1
        # --- Topology label frame.
        lf_topo = ttk.Labelframe(self, text='Topology')    
        src_dir = os.path.dirname(os.path.abspath(__file__))
        base_path = os.path.join(src_dir, "../data")
        self.images = {
            "source": tk.PhotoImage(file=base_path+"/clock_source.png"),
            "clockin": tk.PhotoImage(file=base_path+"/clock_as_input.png"),
            "clockout": tk.PhotoImage(file=base_path+"/clock_as_output.png"),
            "clockinout": tk.PhotoImage(file=base_path+"/clock_as_inout.png"),
        }
        # --- Topology illustration images
        self.lbimg_topo = ttk.Label(lf_topo, image=self.images["clockin"])
        self.lbimg_topo.grid(row=1, rowspan=99, column=0, sticky="nswe", padx=2, pady=2)
        # --- Topology choice Radio buttons ---
        lfrow=10
        self._topo_radios = {}
        for choice, value in [
            ("Source clock", "source"),
            ("Clock as Input", "clockin"),
            ("Clock as Output", "clockout"),
            ("Clock as Inout", "clockinout"),
        ]:
            rb = ttk.Radiobutton(
                lf_topo,
                text=choice,
                value=value,
                variable=self.topology_tkvar,
                command=self._update_topology
            )
            rb.grid(row=lfrow, column=1, sticky="w", padx=5)
            self._topo_radios[value] = rb
            lfrow+=2

        # A generated clock derives from a source clock: without any source
        # clock defined yet the generated topologies can not be chosen.
        if not self._source_clocks:
            for value in ("clockout", "clockinout"):
                self._topo_radios[value].configure(state="disabled")
            if self.topology_tkvar.get() in ("clockout", "clockinout"):
                self.topology_tkvar.set("clockin")

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
        ## -> Source clock group: the waveform is given explicitly.
        crow += 1
        self.lf_source = ttk.Labelframe(self, text="Source clock")
        self.lf_source.grid(row=crow, column=0, columnspan=99,
                            sticky="nswe", padx=2, pady=4)
        ## Period (is a text because we allow numerical and symbolic)
        ttk.Label(self.lf_source, text="Period").grid(row=0, column=0, sticky="w", padx=2)
        e_period = ttk.Entry(self.lf_source, textvariable=self.clkperiod_tkvar, width=10)
        e_period.grid(row=0, column=1, sticky="w", padx=2, pady=2)
        ## Rise at...
        ttk.Label(self.lf_source, text="Rise @").grid(row=0, column=2, sticky="e")
        e_rise = ttk.Entry(self.lf_source, textvariable=self.clkrise_tkvar, width=12)
        e_rise.grid(row=0, column=3, sticky="w", padx=2, pady=2)
        ## Rise uncertainty.
        ttk.Label(self.lf_source, text="Uncertainty").grid(row=0, column=4, sticky="w")
        e_rise_unc = ttk.Entry(self.lf_source, textvariable=self.rise_unc_tkvar, width=12)
        e_rise_unc.grid(row=0, column=5, sticky="w", padx=2, pady=2)
        ## Fall at ...
        ttk.Label(self.lf_source, text="Fall @").grid(row=1, column=2, sticky="e")
        e_fall = ttk.Entry(self.lf_source, textvariable=self.clkfall_tkvar, width=12)
        e_fall.grid(row=1, column=3, sticky="w", padx=2, pady=2)
        ## Fall uncertainty.
        ttk.Label(self.lf_source, text="Uncertainty").grid(row=1, column=4, sticky="w")
        e_fall_unc = ttk.Entry(self.lf_source, textvariable=self.fall_unc_tkvar, width=12)
        e_fall_unc.grid(row=1, column=5, sticky="w", padx=2, pady=2)

        ## -> Generated clock group: the waveform is derived from a source clock.
        crow += 1
        self.lf_gclock = ttk.Labelframe(self, text="Generated clock")
        self.lf_gclock.grid(row=crow, column=0, columnspan=99,
                            sticky="nswe", padx=2, pady=4)
        ## Master (source) clock this clock derives from.
        ttk.Label(self.lf_gclock, text="Master clock").grid(row=0, column=0,
                                                            sticky="w", padx=2)
        self.cb_master = ttk.Combobox(
            self.lf_gclock, textvariable=self.master_tkvar,
            values=tuple(self._source_clocks),
            width=12, state="readonly",
        )
        self.cb_master.grid(row=0, column=1, columnspan=2, sticky="w", padx=2, pady=2)
        ## Inverted (complemented) clock.
        self.chk_invert = ttk.Checkbutton(
            self.lf_gclock, text="Invert", variable=self.invert_tkvar
        )
        self.chk_invert.grid(row=0, column=3, sticky="w", padx=2, pady=2)
        ## How the clock derives from its master: edge list or divisor.
        self.rb_edges = ttk.Radiobutton(
            self.lf_gclock, text="Edges", value="edges",
            variable=self.genspec_tkvar, command=self._update_genspec,
        )
        self.rb_edges.grid(row=1, column=0, sticky="w", padx=2)
        self.e_edges = ttk.Entry(self.lf_gclock, textvariable=self.edges_tkvar, width=12)
        self.e_edges.grid(row=1, column=1, sticky="w", padx=2, pady=2)
        self.rb_divideby = ttk.Radiobutton(
            self.lf_gclock, text="Divide by", value="divide_by",
            variable=self.genspec_tkvar, command=self._update_genspec,
        )
        self.rb_divideby.grid(row=1, column=2, sticky="e", padx=2)
        self.sp_divideby = ttk.Spinbox(
            self.lf_gclock, from_=1, to=64, textvariable=self.divideby_tkvar, width=3
        )
        self.sp_divideby.grid(row=1, column=3, sticky="w", padx=2, pady=2)
        ## Output delay
        self.l_output_dly = ttk.Label(self.lf_gclock, text="Output Delay")
        self.l_output_dly.grid(row=2, column=0, sticky="w", padx=2)
        self.e_output_dly = ttk.Entry(self.lf_gclock,
                                      textvariable=self.outputdly_tkvar, width=12)
        self.e_output_dly.grid(row=2, column=1, sticky="w", padx=2, pady=2)
        ## Input delay
        self.l_input_dly = ttk.Label(self.lf_gclock, text="Input Delay")
        self.l_input_dly.grid(row=2, column=2, sticky="e", padx=2)
        self.e_input_dly = ttk.Entry(self.lf_gclock,
                                     textvariable=self.inputdly_tkvar, width=12)
        self.e_input_dly.grid(row=2, column=3, sticky="w", padx=2, pady=2)

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

        if topology in ("source", "clockin"):
            waveform = self._build_source_args()
        else:
            waveform = self._build_generated_args(topology)
        if waveform == "":
            return ""
        cmd += waveform

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

    def _build_source_args(self):
        """create_clock arguments of a source clock (explicit waveform)."""
        args = ""
        # A source clock requires a period. If no period is given nothing happens.
        clkperiod = self.clkperiod_tkvar.get()
        if clkperiod is None or clkperiod == "":
            return ""
        args += " -period {"+clkperiod+"}"
        # A clock requires a waveform.
        riseat = self.clkrise_tkvar.get()
        if riseat is None or riseat == "":
            args += " -rise_at 0"
        else:
            args += " -rise_at {"+riseat+"}"
        fallat = self.clkfall_tkvar.get()
        if fallat is None or fallat == "":
            args += " -fall_at {("+clkperiod+")/2.0}"
        else:
            args += " -fall_at {"+fallat+"}"
        # A clock may have rising/fall uncertainties
        uncertainty = self.rise_unc_tkvar.get()
        if uncertainty is not None and not uncertainty == "":
            args += " -rise_uncertainty {"+uncertainty+"}"
        uncertainty = self.fall_unc_tkvar.get()
        if uncertainty is not None and not uncertainty == "":
            args += " -fall_uncertainty {"+uncertainty+"}"
        return args

    def _build_generated_args(self, topology):
        """create_clock arguments of a generated clock (derived waveform)."""
        args = ""
        # A generated clock requires a master (source) clock.
        master = self.master_tkvar.get()
        if master is None or master == "":
            return ""
        args += " -master "+master
        # It derives from its master either by an edge list or by a divisor.
        if self.genspec_tkvar.get() == "edges":
            edges = self.edges_tkvar.get()
            if edges is None or edges.strip() == "":
                return ""
            args += " -edges {"+edges.strip()+"}"
        else:
            args += " -divide_by "+str(self.divideby_tkvar.get())
        # Inverted (complemented) clock
        if self.invert_tkvar.get():
            args += " -invert"
        # Input delay (only when the clock is fed back internally)
        if topology == "clockinout":
            dly = self.inputdly_tkvar.get()
            if dly is not None and not dly == "":
                args += " -input_dly {"+dly+"}"
        # Output delay
        dly = self.outputdly_tkvar.get()
        if dly is not None and not dly == "":
            args += " -output_dly {"+dly+"}"
        return args

    @staticmethod
    def _set_group_state(frame, enabled):
        """Enable/disable every input widget of a Labelframe."""
        for widget in frame.winfo_children():
            if isinstance(widget, ttk.Combobox):
                widget.configure(state="readonly" if enabled else "disabled")
            else:
                widget.configure(state="normal" if enabled else "disabled")

    def _update_topology(self):
        selected = self.topology_tkvar.get()
        self.lbimg_topo.configure(image=self.images[selected])

        # "source" and "clockin" are source clocks, "clockout" and "clockinout"
        # are generated clocks: only one of both groups applies.
        is_source = selected in ("source", "clockin")
        self._set_group_state(self.lf_source, is_source)
        self._set_group_state(self.lf_gclock, not is_source)

        if is_source:
            return

        self._update_genspec()
        # The clock only comes back in as an input with the "clockinout" topology.
        if selected == "clockout":
            self.l_input_dly.configure(state="disabled")
            self.inputdly_tkvar.set("")
            self.e_input_dly.configure(state="disabled")

    def _update_genspec(self):
        """A generated clock is given either by its edges or by a divisor."""
        by_edges = self.genspec_tkvar.get() == "edges"
        self.e_edges.configure(state="normal" if by_edges else "disabled")
        self.sp_divideby.configure(state="disabled" if by_edges else "normal")

    def dismiss(self):
        self.grab_release()
        self.destroy()

    def cancel(self):
        ## The dialog windows was cancelled therefore created signal is not taken.
        self.dismiss()
        
    def apply(self):
        cmd = self._build_command()
        if cmd != "":
            with self.topapp.undo.transaction():
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
