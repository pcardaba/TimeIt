import tkinter as tk
from tkinter import ttk
import os

class OutputSignalDlg(tk.Toplevel):
    def __init__(self, parent, signal=None):
        super().__init__(parent, padx=10)
        self.topapp = parent
        self._signal = signal
        self.title("Output Signal")
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
        self.name_tkvar       = tk.StringVar()
        self.visible_tkvar    = tk.BooleanVar(value=True)
        self.color_tkvar      = tk.StringVar(value="black")
        self.lwidth_tkvar     = tk.IntVar(value=2)
        self.launch_tkvar     = tk.StringVar()
        self.capture_tkvar    = tk.StringVar()
        self.amplitude_tkvar  = tk.IntVar(value=40)
        self.output_max_dly_r_tkvar =  tk.StringVar()
        self.output_min_dly_r_tkvar =  tk.StringVar()
        self.latency_max_r_tkvar = tk.StringVar()
        self.latency_min_r_tkvar = tk.StringVar()
        self.output_max_dly_f_tkvar =  tk.StringVar()
        self.output_min_dly_f_tkvar =  tk.StringVar()
        self.latency_max_f_tkvar  = tk.StringVar()
        self.latency_min_f_tkvar = tk.StringVar()
        self.data_edges_tkvar = tk.StringVar()
        self.hiz_edges_tkvar = tk.StringVar()
        self.high_edges_tkvar = tk.StringVar()
        self.low_edges_tkvar = tk.StringVar()
        self.unknown_edges_tkvar = tk.StringVar()
        self.topology_tkvar   = tk.StringVar(value="internal")
        self.pulled_up_tkvar  = tk.BooleanVar(value=False)
        self.oedly_max_r_tkvar = tk.StringVar()
        self.oedly_min_r_tkvar = tk.StringVar()
        self.oedly_max_f_tkvar = tk.StringVar()
        self.oedly_min_f_tkvar = tk.StringVar()
        # ---
        ## Every clock is a candidate. Once one of the launch/capture clocks is
        ## chosen, only the clocks related to it remain candidates for the other.
        self._clock_names = [name for name, sig in self.topapp.signals.items()
                             if sig.type == "clock"]

        if self._signal is not None:
            s = self._signal
            self.name_tkvar.set(s.name)
            if s.launch_clock is not None:
                self.launch_tkvar.set(s.launch_clock.name)
            if s.capture_clock is not None:
                self.capture_tkvar.set(s.capture_clock.name)
            self.visible_tkvar.set(s.visible)
            self.color_tkvar.set(s.color)
            self.amplitude_tkvar.set(s.amplitude)
            self.lwidth_tkvar.set(s.lwidth)
            self.output_max_dly_r_tkvar.set("" if s.rclk_outputdly_max is None else s.rclk_outputdly_max)   
            self.output_min_dly_r_tkvar.set("" if s.rclk_outputdly_min is None else s.rclk_outputdly_min)
            self.output_max_dly_f_tkvar.set("" if s.fclk_outputdly_max is None else s.fclk_outputdly_max)   
            self.output_min_dly_f_tkvar.set("" if s.fclk_outputdly_min is None else s.fclk_outputdly_min)
            self.latency_max_r_tkvar.set("" if s.rclk_latency_max is None else s.rclk_latency_max)  
            self.latency_min_r_tkvar.set("" if s.rclk_latency_min is None else s.rclk_latency_min)  
            self.latency_max_f_tkvar.set("" if s.fclk_latency_max is None else s.fclk_latency_max)  
            self.latency_min_f_tkvar.set("" if s.fclk_latency_min is None else s.fclk_latency_min) 
            self.data_edges_tkvar.set("" if s.data_edges is None else " ".join(s.data_edges))  
            self.hiz_edges_tkvar.set("" if s.hiz_edges is None else " ".join(s.hiz_edges))
            self.high_edges_tkvar.set("" if s.high_edges is None else " ".join(s.high_edges))  
            self.low_edges_tkvar.set("" if s.low_edges is None else " ".join(s.low_edges))  
            self.unknown_edges_tkvar.set("" if s.unknown_edges is None else " ".join(s.unknown_edges))  
            self.topology_tkvar.set(s.specify)
            self.pulled_up_tkvar.set(getattr(s, 'pulled_up', False))
            self.oedly_max_r_tkvar.set("" if getattr(s, 'rclk_oedly_max', None) is None else s.rclk_oedly_max)
            self.oedly_min_r_tkvar.set("" if getattr(s, 'rclk_oedly_min', None) is None else s.rclk_oedly_min)
            self.oedly_max_f_tkvar.set("" if getattr(s, 'fclk_oedly_max', None) is None else s.fclk_oedly_max)
            self.oedly_min_f_tkvar.set("" if getattr(s, 'fclk_oedly_min', None) is None else s.fclk_oedly_min)

        self.grid_rowconfigure(0, minsize=10)
        crow = 1
        # --- Topology label frame.
        lf_topo = ttk.Labelframe(self, text='Output delay as')    
        src_dir = os.path.dirname(os.path.abspath(__file__))
        base_path = os.path.join(src_dir, "../data")
        self.images = {
            "internal": tk.PhotoImage(file=base_path+"/output_internal_dly.png"),
            "external": tk.PhotoImage(file=base_path+"/output_external_dly.png"),
        }
        # --- Topology illustration images
        self.lbimg_topo = ttk.Label(lf_topo, image=self.images["internal"])
        self.lbimg_topo.grid(row=1, rowspan=99, column=0, sticky="nswe", padx=2, pady=2)
        # --- Topology choice Radio buttons ---
        lfrow=10
        for choice, value in [
            ("Output internal delay", "internal"),
            ("Output external delay", "external"),
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
        # --- Launch/Capture clocks label frame.
        self._build_clocks_frame(self, row=crow)
        crow += 1
        self.grid_rowconfigure(crow, minsize=10)
        crow += 1
        ## -> Row : Name, Visible, Color
        # clk name field...
        ttk.Label(self, text="Name").grid(row=crow, column=0, sticky="e")
        e_name = ttk.Entry(self, textvariable=self.name_tkvar, width=12)
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
        # Row : Amplitude, Pulled-up
        crow += 1
        # -- Pulled-up (right below Visible)
        chk_pulled_up = ttk.Checkbutton(
            self, text="Pulled-up", variable=self.pulled_up_tkvar
        )
        chk_pulled_up.grid(row=crow, column=6, sticky="w", padx=2, pady=2)
        # -- Ampliture
        ttk.Label(self, text="Amplitude").grid(row=crow, column=4, sticky="e")
        sp_amp = ttk.Spinbox(
            self, from_=10, to=300, textvariable=self.amplitude_tkvar, width=3
        )
        sp_amp.grid(row=crow, column=5, sticky="w", padx=2, pady=2)
        crow += 1
        ## -> Clock rising/falling delays, side by side.
        lf_delays = ttk.Frame(self)
        lf_delays.grid(row=crow, column=0, columnspan=99, sticky="ew", padx=2, pady=10)
        lf_delays.columnconfigure(0, weight=1)
        lf_delays.columnconfigure(1, weight=1)
        ## -> Rising clock delays.
        lf_clockrise = ttk.Labelframe(lf_delays, text='@ Clock Rising')
        lf_clockrise.grid(row=0, column=0, sticky="nsew", padx=(0, 4))
        lf_clockrise.columnconfigure(0, weight=1)
        self._add_maxmin_group(lf_clockrise, 1, "Output delay",
                               self.output_max_dly_r_tkvar, self.output_min_dly_r_tkvar)
        # Output Enable and Clock Latency are only active when topology is "internal"
        self.w_oedly_r = self._add_maxmin_group(lf_clockrise, 2, "Output Enable Delay",
                                                self.oedly_max_r_tkvar,
                                                self.oedly_min_r_tkvar)
        self.w_latency_r = self._add_maxmin_group(lf_clockrise, 3, "Clock Latency",
                                                  self.latency_max_r_tkvar,
                                                  self.latency_min_r_tkvar)
        ## -> Falling clock delays.
        lf_clockfall = ttk.Labelframe(lf_delays, text='@ Clock Falling')
        lf_clockfall.grid(row=0, column=1, sticky="nsew", padx=(4, 0))
        lf_clockfall.columnconfigure(0, weight=1)
        self._add_maxmin_group(lf_clockfall, 1, "Output delay",
                               self.output_max_dly_f_tkvar, self.output_min_dly_f_tkvar)
        self.w_oedly_f = self._add_maxmin_group(lf_clockfall, 2, "Output Enable Delay",
                                                self.oedly_max_f_tkvar,
                                                self.oedly_min_f_tkvar)
        self.w_latency_f = self._add_maxmin_group(lf_clockfall, 3, "Clock Latency",
                                                  self.latency_max_f_tkvar,
                                                  self.latency_min_f_tkvar)

        ## -> Sensitive edges list ...
        crow += 1
        ## 
        self.icon = {
            "data": tk.PhotoImage(file=base_path+"/data_validx20.png"),
            "hiz": tk.PhotoImage(file=base_path+"/data_hizx20.png"),
            "low": tk.PhotoImage(file=base_path+"/data_lowx20.png"),
            "high": tk.PhotoImage(file=base_path+"/data_highx20.png"),
            "unknown": tk.PhotoImage(file=base_path+"/data_unknownx20.png"),
        }
        lf_edges = ttk.Labelframe(self, text='Launch Clock Edges Lists')
        self.edges_img = tk.PhotoImage(file=base_path+"/edge_nomenclature.png")
        ttk.Label(lf_edges, image=self.edges_img).grid(row=1, column=2,
                                                       sticky="we", padx=2,
                                                       rowspan=5)
        ## lf: row
        row = 1
        ttk.Label(lf_edges, image=self.icon["data"]).grid(row=row, column=0, sticky="e")
        e_data_edges = ttk.Entry(lf_edges, textvariable=self.data_edges_tkvar, width=24)
        e_data_edges.grid(row=row, column=1, sticky="w", padx=2, pady=2)
        ## +
        row += 1
        ttk.Label(lf_edges, image=self.icon["hiz"]).grid(row=row, column=0, sticky="e")
        e_hiz_edges = ttk.Entry(lf_edges, textvariable=self.hiz_edges_tkvar, width=24)
        e_hiz_edges.grid(row=row, column=1, sticky="w", padx=2, pady=2)
        ## +
        row += 1
        ttk.Label(lf_edges, image=self.icon["high"]).grid(row=row, column=0, sticky="e")
        e_high_edges = ttk.Entry(lf_edges, textvariable=self.high_edges_tkvar, width=24)
        e_high_edges.grid(row=row, column=1, sticky="w", padx=2, pady=2)
        ## +
        row += 1
        ttk.Label(lf_edges, image=self.icon["low"]).grid(row=row, column=0, sticky="e")
        e_low_edges = ttk.Entry(lf_edges, textvariable=self.low_edges_tkvar, width=24)
        e_low_edges.grid(row=row, column=1, sticky="w", padx=2, pady=2)
        ## +
        row += 1
        ttk.Label(lf_edges, image=self.icon["unknown"]).grid(row=row, column=0, sticky="e")
        e_unknown_edges = ttk.Entry(lf_edges, textvariable=self.unknown_edges_tkvar, width=24)
        e_unknown_edges.grid(row=row, column=1, sticky="w", padx=2, pady=2)
        ## --
        lf_edges.grid(row=crow, column=0, columnspan=99, sticky="ew", padx=2, pady=10)      
        # ==
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

    # -------------------------------------------------------------------
    # Launch / Capture clocks
    # -------------------------------------------------------------------
    def _build_clocks_frame(self, parent, row):
        """The launch/capture clock choices, on a single row."""
        lf_clocks = ttk.Labelframe(parent, text="Clocks")
        lf_clocks.grid(row=row, column=0, columnspan=99, sticky="ew", padx=2, pady=2)
        ## Each half takes an end of the row: Launch to the west, Capture east.
        lf_clocks.columnconfigure(0, weight=1)
        lf_clocks.columnconfigure(1, weight=1)

        launch = ttk.Frame(lf_clocks)
        launch.grid(row=0, column=0, sticky="w", padx=2, pady=2)
        ttk.Label(launch, text="Launch").grid(row=0, column=0, sticky="e", padx=2)
        self.cb_launch = ttk.Combobox(launch, textvariable=self.launch_tkvar,
                                      width=12, state="readonly")
        self.cb_launch.grid(row=0, column=1, sticky="e", padx=2)
        self.cb_launch.bind("<<ComboboxSelected>>", self._update_clock_choices)

        capture = ttk.Frame(lf_clocks)
        capture.grid(row=0, column=1, sticky="e", padx=2, pady=2)
        ttk.Label(capture, text="Capture").grid(row=0, column=0, sticky="e", padx=2)
        self.cb_capture = ttk.Combobox(capture, textvariable=self.capture_tkvar,
                                       width=12, state="readonly")
        self.cb_capture.grid(row=0, column=1, sticky="w", padx=2)
        self.cb_capture.bind("<<ComboboxSelected>>", self._update_clock_choices)

        self._update_clock_choices()

    def _related_clock_names(self, name):
        """Clocks that may go with `name` (same source clock)."""
        clock = self.topapp.signals.find(name)
        if clock is None or clock.type != "clock":
            return self._clock_names
        return [n for n in self._clock_names
                if clock.is_related_to(self.topapp.signals.find(n))]

    def _update_clock_choices(self, event=None):
        """Data can only be launched and captured by related clocks."""
        launch = self.launch_tkvar.get()
        capture = self.capture_tkvar.get()
        ## The clock just chosen prevails: the other one is dropped if unrelated.
        widget = None if event is None else event.widget
        if widget is self.cb_launch:
            if capture and capture not in self._related_clock_names(launch):
                self.capture_tkvar.set("")
                capture = ""
        elif widget is self.cb_capture:
            if launch and launch not in self._related_clock_names(capture):
                self.launch_tkvar.set("")
                launch = ""
        ## Each choice restricts the choices left for the other one.
        self.cb_capture["values"] = self._related_clock_names(launch)
        self.cb_launch["values"] = self._related_clock_names(capture)

    def _add_maxmin_group(self, parent, row, text, max_tkvar, min_tkvar, width=9):
        """Nested delay group: a 'text' Labelframe with 'Max/min [max]/[min]'.

        Returns the created widgets, so that the caller can enable/disable
        the whole group at once (see _set_state).
        """
        lf = ttk.Labelframe(parent, text=text)
        lf.grid(row=row, column=0, sticky="ew", padx=4, pady=2)
        ## Both entries share the extra width evenly.
        lf.columnconfigure(1, weight=1)
        lf.columnconfigure(3, weight=1)
        l_maxmin = ttk.Label(lf, text="Max/min")
        l_maxmin.grid(row=0, column=0, sticky="e", padx=2, pady=2)
        e_max = ttk.Entry(lf, textvariable=max_tkvar, width=width)
        e_max.grid(row=0, column=1, sticky="ew")
        l_sep = ttk.Label(lf, text="/")
        l_sep.grid(row=0, column=2)
        e_min = ttk.Entry(lf, textvariable=min_tkvar, width=width)
        e_min.grid(row=0, column=3, sticky="ew", padx=(0, 2))
        return (lf, l_maxmin, e_max, l_sep, e_min)

    @staticmethod
    def _set_state(widgets, enabled):
        """Enable/disable a group of widgets. A Labelframe has no -state."""
        for w in widgets:
            if isinstance(w, ttk.Labelframe):
                w.state(["!disabled"] if enabled else ["disabled"])
            else:
                w.configure(state="normal" if enabled else "disabled")

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
        cmd = "create_output"
        # A clock requires a name. If no name is given nothing happens.
        name = self.name_tkvar.get()
        if name is None or name == "":
            return ""
        cmd += " -name "+name
        
        # Chosen delay specification
        topology = self.topology_tkvar.get()
        cmd += " -specify "+ topology

        # Launch and capture clocks. Both are required.
        launch = self.launch_tkvar.get()
        capture = self.capture_tkvar.get()
        if not launch or not capture:
            return ""
        cmd += " -launch_clock "+launch
        cmd += " -capture_clock "+capture


        # Rise output delay max. -rclk_outputdly_max 
        dly = self.output_max_dly_r_tkvar.get()
        max_found = False
        if dly is not None and not dly == "":
            cmd += " -rclk_outputdly_max {"+dly+"}"
            max_found = True
            
        # Rise output delay min. -rclk_outputdly_min 
        dly = self.output_min_dly_r_tkvar.get()
        min_found = False
        if dly is not None and not dly == "":
            cmd += " -rclk_outputdly_min {"+dly+"}"
            min_found = True

        ## If none is used then it is ok. If only one is used
        ## then the other is considered 0
        if max_found and not min_found:
            cmd += " -rclk_outputdly_min {0}"
        if min_found and not max_found:
            dly = self.output_min_dly_r_tkvar.get()
            cmd += " -rclk_outputdly_max {"+dly+"}"
            
        # Fall output delay max. -fclk_outputdly_max 
        dly = self.output_max_dly_f_tkvar.get()
        max_found = False
        if dly is not None and not dly == "":
            cmd += " -fclk_outputdly_max {"+dly+"}"
            max_found = True
            
        # Fall output delay min. -fclk_outputdly_min 
        dly = self.output_min_dly_f_tkvar.get()
        min_found = False
        if dly is not None and dly != "":
            cmd += " -fclk_outputdly_min {"+dly+"}"
            min_found = True
            
        ## If none is used then it is ok. If only one is used
        ## then the other is considered 0 or min.
        if max_found and not min_found:
            cmd += " -fclk_outputdly_min {0}"
        if min_found and not max_found:
            dly = self.output_min_dly_f_tkvar.get()
            cmd += " -fclk_outputdly_max {"+dly+"}"
        
        if topology == "internal":
            max_found = False
            min_found = False
            # Rise latency max. -rclk_latency_max 
            dly = self.latency_max_r_tkvar.get()
            if dly is not None and not dly == "":
                cmd += " -rclk_latency_max {"+dly+"}"
                max_found = True
                
            # Rise latency min. -rclk_latency_min 
            dly = self.latency_min_r_tkvar.get()
            if dly is not None and not dly == "":
                cmd += " -rclk_latency_min {"+dly+"}"
                min_found = True
                
            if max_found and not min_found:
                cmd += " -rclk_latency_min {0}"
            if min_found and not max_found:
                dly = self.latency_min_r_tkvar.get()
                cmd += " -rclk_latency_max {"+dly+"}"
                
            max_found = False
            min_found = False
            # Fall latency max. -fclk_latency_max 
            dly = self.latency_max_f_tkvar.get()
            if dly is not None and not dly == "":
                cmd += " -fclk_latency_max {"+dly+"}"
                max_found = True
                
            # Fall latency min. -fclk_latency_min 
            dly = self.latency_min_f_tkvar.get()
            if dly is not None and not dly == "":
                cmd += " -fclk_latency_min {"+dly+"}"
                min_found = True

            if max_found and not min_found:
                cmd += " -fclk_latency_min {0}"
            if min_found and not max_found:
                dly = self.latency_min_f_tkvar.get()
                cmd += " -fclk_latency_max {"+dly+"}"

            # Output enable delay rise. -rclk_oedly_max / -rclk_oedly_min
            max_found = False
            min_found = False
            dly = self.oedly_max_r_tkvar.get()
            if dly is not None and dly != "":
                cmd += " -rclk_oedly_max {"+dly+"}"
                max_found = True
            dly = self.oedly_min_r_tkvar.get()
            if dly is not None and dly != "":
                cmd += " -rclk_oedly_min {"+dly+"}"
                min_found = True
            if max_found and not min_found:
                cmd += " -rclk_oedly_min {0}"
            if min_found and not max_found:
                dly = self.oedly_min_r_tkvar.get()
                cmd += " -rclk_oedly_max {"+dly+"}"

            # Output enable delay fall. -fclk_oedly_max / -fclk_oedly_min
            max_found = False
            min_found = False
            dly = self.oedly_max_f_tkvar.get()
            if dly is not None and dly != "":
                cmd += " -fclk_oedly_max {"+dly+"}"
                max_found = True
            dly = self.oedly_min_f_tkvar.get()
            if dly is not None and dly != "":
                cmd += " -fclk_oedly_min {"+dly+"}"
                min_found = True
            if max_found and not min_found:
                cmd += " -fclk_oedly_min {0}"
            if min_found and not max_found:
                dly = self.oedly_min_f_tkvar.get()
                cmd += " -fclk_oedly_max {"+dly+"}"

        # data edges 
        edges = self.data_edges_tkvar.get()
        if edges is not None and edges != "":
            cmd += " -data_edges {"+edges+"}"

        # hiz edges 
        edges = self.hiz_edges_tkvar.get()
        if edges is not None and edges != "":
            cmd += " -hiz_edges {"+edges+"}"

        # high edges 
        edges = self.high_edges_tkvar.get()
        if edges is not None and edges != "":
            cmd += " -high_edges {"+edges+"}"

        # low edges 
        edges = self.low_edges_tkvar.get()
        if edges is not None and edges != "":
            cmd += " -low_edges {"+edges+"}"

        # unknown edges 
        edges = self.unknown_edges_tkvar.get()
        if edges is not None and edges != "":
            cmd += " -unknown_edges {"+edges+"}"
            
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
        # Pulled-up.
        if self.pulled_up_tkvar.get():
            cmd += " -pulled_up"
        return cmd
    
    def _update_topology(self):
        selected = self.topology_tkvar.get()
        self.lbimg_topo.configure(image=self.images[selected])
        self._set_state(self.w_latency_r + self.w_latency_f
                        + self.w_oedly_r + self.w_oedly_f,
                        selected == "internal")
        if selected == "external":
            self.latency_max_r_tkvar.set("")
            self.latency_max_f_tkvar.set("")
            self.latency_min_r_tkvar.set("")
            self.latency_min_f_tkvar.set("")
            self.oedly_max_r_tkvar.set("")
            self.oedly_min_r_tkvar.set("")
            self.oedly_max_f_tkvar.set("")
            self.oedly_min_f_tkvar.set("")
        
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
