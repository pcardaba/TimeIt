from __future__ import annotations

import tkinter as tk
from tkinter import colorchooser
from tkinter import ttk

from .settings import Settings

class GridSettingsDlg(tk.Toplevel):
    """
    Non-modal grid settings dialog.
    """

    LINE_STYLES = ("solid", "dash", "dot", "dashdot")

    def __init__( self, master: tk.Misc, settings: Settings) -> None:
        super().__init__(master)
        self.title("Grid Settings")
        self.resizable(False, False)
        # Non-modal:
        # - no grab_set()
        # - no wait_window()
        self.topapp = master
        self.settings = settings
        self._available_clocks: list[str] = []
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)

        self._build_variables(self.settings)
        self._build_ui()
        self._load_from_settings()
        self._update_enabled_states()

        self.protocol("WM_DELETE_WINDOW", self._on_cancel)

    # ------------------------------------------------------------------
    # Variables
    # ------------------------------------------------------------------
    def _build_variables(self, s: Settings) -> None:

        self._available_clocks = [name for name, sig in self.topapp.signals.items() if sig.type == "clock"]
        self.var_x_enabled = tk.BooleanVar(value=s.grid["x_grid_enabled"])
        self.var_y_enabled = tk.BooleanVar(value=s.grid["y_grid_enabled"])

        self.var_x_style = tk.StringVar(value=s.grid["x_line_style"])
        self.var_x_width = tk.IntVar(value=s.grid["x_line_width"])
        self.var_x_color = tk.StringVar(value=s.grid["x_line_color"])
        self.var_x_units_per_div = tk.IntVar(value=s.grid["x_units_per_division"])
        self.var_x_subdiv = tk.IntVar(value=s.grid["x_subdivisions"])

        self.var_y_style = tk.StringVar(value=s.grid["y_line_style"])
        self.var_y_width = tk.IntVar(value=s.grid["y_line_width"])
        self.var_y_color = tk.StringVar(value=s.grid["y_line_color"])
        self.var_y_subdiv = tk.IntVar(value=s.grid["y_subdivisions"])

        self.var_y_mode = tk.StringVar(value=s.grid["y_mode"])

        self.var_y_clock_name = tk.StringVar(value=s.grid["y_clock_name"])
        self.var_y_posedge = tk.BooleanVar(value=s.grid["y_align_posedge"])
        self.var_y_negedge = tk.BooleanVar(value=s.grid["y_align_negedge"])
        self.var_y_show_edge_numbers = tk.BooleanVar(value=s.grid["y_show_edge_numbers"])
        self.var_y_show_cycle_numbers = tk.BooleanVar(value=s.grid["y_show_cycle_numbers"])

        self.var_y_time_division = tk.IntVar(value=s.grid["y_time_division"])

    # ------------------------------------------------------------------
    # UI
    # ------------------------------------------------------------------
    def _build_ui(self) -> None:
        outer = ttk.Frame(self, padding=10)
        outer.grid(row=0, column=0, sticky="nsew")
        outer.columnconfigure(0, weight=1)
        outer.rowconfigure(0, weight=1)

        content = ttk.Frame(outer)
        content.grid(row=0, column=0, sticky="nsew")
        content.columnconfigure(0, weight=1)
        content.columnconfigure(1, weight=1)

        self._build_x_frame(content)
        self._build_y_frame(content)
        self._build_buttons(outer)

    def _build_x_frame(self, parent: ttk.Frame) -> None:
        frm = ttk.LabelFrame(parent, text="X-Grid", padding=10)
        frm.grid(row=0, column=0, sticky="nsew", padx=(0, 6), pady=(0, 8))
        frm.columnconfigure(1, weight=1)
        frm.columnconfigure(3, weight=1)

        self.chk_x_enable = ttk.Checkbutton(
            frm,
            text="Enable x-grid",
            variable=self.var_x_enabled,
            command=self._update_enabled_states,
        )
        self.chk_x_enable.grid(row=0, column=0, columnspan=4, sticky="w", pady=(0, 8))

        ttk.Label(frm, text="Line style:").grid(row=1, column=0, sticky="w", padx=(0, 6), pady=3)
        self.cmb_x_style = ttk.Combobox(
            frm,
            textvariable=self.var_x_style,
            values=self.LINE_STYLES,
            state="readonly",
            width=8,
        )
        self.cmb_x_style.grid(row=1, column=1, sticky="w", pady=3)

        ttk.Label(frm, text="Line width:").grid(row=1, column=2, sticky="e", padx=(12, 6), pady=3)
        self.spn_x_width = ttk.Spinbox(frm, from_=1, to=10, textvariable=self.var_x_width, width=2)
        self.spn_x_width.grid(row=1, column=3, sticky="w", pady=3)

        ttk.Label(frm, text="Color:").grid(row=2, column=0, sticky="w", padx=(0, 6), pady=3)
        color_row = ttk.Frame(frm)
        color_row.grid(row=2, column=1, columnspan=3, sticky="w", pady=3)
        color_row.columnconfigure(0, weight=1)

        self.ent_x_color = ttk.Entry(color_row, textvariable=self.var_x_color, width=10)
        self.ent_x_color.grid(row=0, column=0, sticky="w")
        self.btn_x_color = ttk.Button(
            color_row,
            text="Choose…",
            command=lambda: self._choose_color(self.var_x_color),
        )
        self.btn_x_color.grid(row=0, column=1, padx=(6, 0))

        ttk.Separator(frm).grid(row=3, column=0, columnspan=4, sticky="ew", pady=8)

        ttk.Label(frm, text="Units per division:").grid(
            row=4, column=0, columnspan=2, sticky="w", padx=(0, 6), pady=3
        )
        self.spn_x_units = ttk.Spinbox(
            frm, from_=1, to=100000, textvariable=self.var_x_units_per_div, width=3
        )
        self.spn_x_units.grid(row=4, column=2, sticky="w", pady=3)

        ttk.Label(frm, text="Sub-divisions per division:").grid(
            row=5, column=0, columnspan=2, sticky="w", padx=(0, 6), pady=3
        )
        self.spn_x_subdiv = ttk.Spinbox(frm, from_=1, to=100, textvariable=self.var_x_subdiv, width=3)
        self.spn_x_subdiv.grid(row=5, column=2, sticky="w", pady=3)

        self._x_widgets = [
            self.cmb_x_style,
            self.spn_x_width,
            self.ent_x_color,
            self.btn_x_color,
            self.spn_x_units,
            self.spn_x_subdiv,
        ]

    def _build_y_frame(self, parent: ttk.Frame) -> None:
        frm = ttk.LabelFrame(parent, text="Y-Grid", padding=10)
        frm.grid(row=0, column=1, sticky="nsew", padx=(6, 0), pady=(0, 8))
        frm.columnconfigure(0, weight=1)

        self.chk_y_enable = ttk.Checkbutton(
            frm,
            text="Enable y-grid",
            variable=self.var_y_enabled,
            command=self._update_enabled_states,
        )
        self.chk_y_enable.grid(row=0, column=0, sticky="w", pady=(0, 8))

        # Appearance
        appearance = ttk.Frame(frm)
        appearance.grid(row=1, column=0, sticky="ew")
        # appearance.columnconfigure(1, weight=1)
        # appearance.columnconfigure(3, weight=2)

        ttk.Label(appearance, text="Line style:").grid(row=0, column=0, sticky="w", padx=(0, 6), pady=3)
        self.cmb_y_style = ttk.Combobox(
            appearance,
            textvariable=self.var_y_style,
            values=self.LINE_STYLES,
            state="readonly",
            width=8,
        )
        self.cmb_y_style.grid(row=0, column=1, sticky="w", pady=3)

        ttk.Label(appearance, text="Line width:").grid(row=0, column=2, sticky="e", padx=(12, 6), pady=3)
        self.spn_y_width = ttk.Spinbox(appearance, from_=1, to=10, textvariable=self.var_y_width, width=3)
        self.spn_y_width.grid(row=0, column=3, sticky="w", pady=3)

        ttk.Label(appearance, text="Color:").grid(row=1, column=0, sticky="w", padx=(0, 0), pady=3)

        self.ent_y_color = ttk.Entry(appearance, textvariable=self.var_y_color, width=10)
        self.ent_y_color.grid(row=1, column=1, sticky="w")
        self.btn_y_color = ttk.Button(
            appearance,
            text="Choose…",
            command=lambda: self._choose_color(self.var_y_color),
        )
        self.btn_y_color.grid(row=1, column=2, padx=(6, 0))

        ttk.Label(appearance, text="Sub-divisions per division:").grid(
            row=2, column=0, columnspan=2, sticky="w", padx=(0, 0), pady=3
        )
        self.spn_y_subdiv = ttk.Spinbox(appearance, from_=1, to=100, textvariable=self.var_y_subdiv, width=3)
        self.spn_y_subdiv.grid(row=2, column=2, sticky="w", padx=(3,0), pady=3)

        ttk.Separator(frm).grid(row=2, column=0, sticky="ew", pady=8)

        # Mode selection
        mode = ttk.LabelFrame(frm, text="Y-Grid Source / Alignment", padding=10)
        mode.grid(row=3, column=0, sticky="nsew")
        mode.columnconfigure(0, weight=1)

        self.rb_y_clock = ttk.Radiobutton(
            mode,
            text="Grid aligned to existing clock signal",
            variable=self.var_y_mode,
            value="clock",
            command=self._update_enabled_states,
        )
        self.rb_y_clock.grid(row=0, column=0, sticky="w")

        self.clock_frame = ttk.Frame(mode)
        self.clock_frame.grid(row=1, column=0, sticky="ew", padx=(20, 0), pady=(4, 8))
        self.clock_frame.columnconfigure(1, weight=1)

        ttk.Label(self.clock_frame, text="Clock:").grid(row=0, column=0, sticky="w", padx=(0, 6), pady=3)

        self.cmb_y_clock = ttk.Combobox(
            self.clock_frame,
            textvariable=self.var_y_clock_name,
            values=self._available_clocks,
            state="readonly" if self._available_clocks else "disabled",
            width=12,
        )
        self.cmb_y_clock.grid(row=0, column=1, sticky="w", pady=3)

        edge_frame = ttk.Frame(self.clock_frame)
        edge_frame.grid(row=1, column=0, columnspan=2, sticky="w", pady=3)

        self.chk_y_posedge = ttk.Checkbutton(
            edge_frame,
            text="Positive edges",
            variable=self.var_y_posedge,
        )
        self.chk_y_posedge.grid(row=0, column=0, sticky="w", padx=(0, 12))

        self.chk_y_negedge = ttk.Checkbutton(
            edge_frame,
            text="Negative edges",
            variable=self.var_y_negedge,
        )
        self.chk_y_negedge.grid(row=0, column=1, sticky="w")

        ann_frame = ttk.Frame(self.clock_frame)
        ann_frame.grid(row=2, column=0, columnspan=2, sticky="w", pady=3)

        self.chk_y_show_edge_numbers = ttk.Checkbutton(
            ann_frame,
            text="Show clock edge numbers",
            variable=self.var_y_show_edge_numbers,
        )
        self.chk_y_show_edge_numbers.grid(row=0, column=0, sticky="w", padx=(0, 12))

        self.chk_y_show_cycle_numbers = ttk.Checkbutton(
            ann_frame,
            text="Show clock cycle numbers",
            variable=self.var_y_show_cycle_numbers,
        )
        self.chk_y_show_cycle_numbers.grid(row=0, column=1, sticky="w")

        self.rb_y_time = ttk.Radiobutton(
            mode,
            text="Time base grid",
            variable=self.var_y_mode,
            value="timebase",
            command=self._update_enabled_states,
        )
        self.rb_y_time.grid(row=2, column=0, sticky="w", pady=(4, 0))

        self.timebase_frame = ttk.Frame(mode)
        self.timebase_frame.grid(row=3, column=0, sticky="ew", padx=(20, 0), pady=(4, 0))
        self.timebase_frame.columnconfigure(1, weight=1)

        tunits = self.settings.waveform["tunits"]
        ttk.Label(self.timebase_frame, text=f"Time per division ({tunits}):").grid(
            row=0, column=0, sticky="w", padx=(0, 6), pady=3
        )
        self.ent_y_time_division = ttk.Entry(
            self.timebase_frame,
            textvariable=self.var_y_time_division,
            width=6,
        )
        self.ent_y_time_division.grid(row=0, column=1, sticky="w", pady=3)

        self._y_common_widgets = [
            self.cmb_y_style,
            self.spn_y_width,
            self.ent_y_color,
            self.btn_y_color,
            self.spn_y_subdiv,
            self.rb_y_clock,
            self.rb_y_time,
        ]

        self._y_clock_widgets = [
            self.cmb_y_clock,
            self.chk_y_posedge,
            self.chk_y_negedge,
            self.chk_y_show_edge_numbers,
            self.chk_y_show_cycle_numbers,
        ]

        self._y_timebase_widgets = [
            self.ent_y_time_division,
        ]

    def _build_buttons(self, parent: ttk.Frame) -> None:
        btns = ttk.Frame(parent)
        btns.grid(row=1, column=0, sticky="e", pady=(8, 0))

        self.btn_cancel = ttk.Button(btns, text="Cancel", command=self._on_cancel)
        self.btn_cancel.grid(row=0, column=0, padx=(0, 6))

        self.btn_apply = ttk.Button(btns, text="Apply", command=self._on_apply_clicked)
        self.btn_apply.grid(row=0, column=1)

    # ------------------------------------------------------------------
    # State update
    # ------------------------------------------------------------------
    def _update_enabled_states(self) -> None:
        x_enabled = self.var_x_enabled.get()
        y_enabled = self.var_y_enabled.get()
        y_mode = self.var_y_mode.get()

        self._set_widgets_state(self._x_widgets, "normal" if x_enabled else "disabled")
        self._set_widgets_state(self._y_common_widgets, "normal" if y_enabled else "disabled")

        if y_enabled and y_mode == "clock":
            clock_state = "readonly" if self._available_clocks else "disabled"
            self.cmb_y_clock.configure(state=clock_state)
            self._set_widgets_state(
                [w for w in self._y_clock_widgets if w is not self.cmb_y_clock],
                "normal",
            )
            self._set_widgets_state(self._y_timebase_widgets, "disabled")
        elif y_enabled and y_mode == "timebase":
            self.cmb_y_clock.configure(state="disabled")
            self._set_widgets_state(
                [w for w in self._y_clock_widgets if w is not self.cmb_y_clock],
                "disabled",
            )
            self._set_widgets_state(self._y_timebase_widgets, "normal")
        else:
            self.cmb_y_clock.configure(state="disabled")
            self._set_widgets_state(
                [w for w in self._y_clock_widgets if w is not self.cmb_y_clock],
                "disabled",
            )
            self._set_widgets_state(self._y_timebase_widgets, "disabled")

    @staticmethod
    def _set_widgets_state(widgets, state: str) -> None:
        for w in widgets:
            try:
                if isinstance(w, ttk.Combobox):
                    # readonly is handled separately when needed
                    if state == "disabled":
                        w.configure(state="disabled")
                    else:
                        w.configure(state="readonly")
                else:
                    w.configure(state=state)
            except tk.TclError:
                pass

    # ------------------------------------------------------------------
    # Color picker
    # ------------------------------------------------------------------
    def _choose_color(self, var: tk.StringVar) -> None:
        current = var.get().strip() or "#808080"
        _, color = colorchooser.askcolor(color=current, parent=self)
        if color:
            var.set(color)

    # ------------------------------------------------------------------
    # Settings transfer
    # ------------------------------------------------------------------
    def _load_from_settings(self) -> None:
        if not self.var_y_clock_name.get() and self._available_clocks:
            self.var_y_clock_name.set(self._available_clocks[0])

    def update_settings(self) -> Settings:
        self.settings.grid["x_grid_enabled"]=self.var_x_enabled.get()
        self.settings.grid["y_grid_enabled"]=self.var_y_enabled.get()
        
        self.settings.grid["x_line_style"]=self.var_x_style.get()
        self.settings.grid["x_line_width"]=self.var_x_width.get()
        self.settings.grid["x_line_color"]=self.var_x_color.get()
        self.settings.grid["x_units_per_division"]=self.var_x_units_per_div.get()
        self.settings.grid["x_subdivisions"]=self.var_x_subdiv.get()
        
        self.settings.grid["y_line_style"]=self.var_y_style.get()
        self.settings.grid["y_line_width"]=self.var_y_width.get()
        self.settings.grid["y_line_color"]=self.var_y_color.get()
        self.settings.grid["y_subdivisions"]=self.var_y_subdiv.get()
        
        self.settings.grid["y_mode"]=self.var_y_mode.get()
        self.settings.grid["y_clock_name"]=self.var_y_clock_name.get()
        self.settings.grid["y_align_posedge"]=self.var_y_posedge.get()
        self.settings.grid["y_align_negedge"]=self.var_y_negedge.get()
        self.settings.grid["y_show_edge_numbers"]=self.var_y_show_edge_numbers.get()
        self.settings.grid["y_show_cycle_numbers"]=self.var_y_show_cycle_numbers.get()
        
        self.settings.grid["y_time_division"]=self.var_y_time_division.get()

    # ------------------------------------------------------------------
    # Buttons
    # ------------------------------------------------------------------
    def _on_apply_clicked(self) -> None:
        self.update_settings()
        s = self.settings
        # Optional sanity checks
        if s.grid["y_grid_enabled"] and s.grid["y_mode"] == "clock":
            if not s.grid["y_align_posedge"] and not s.grid["y_align_negedge"]:
                tk.messagebox.showerror(
                    "Invalid grid settings",
                    "At least one clock edge type must be selected for y-grid alignment.",
                    parent=self,
                )
                return
            if not s.grid["y_clock_name"]:
                tk.messagebox.showerror(
                    "Invalid grid settings",
                    "Please select a clock for y-grid alignment.",
                    parent=self,
                )
                return

    def _on_cancel(self) -> None:
        self.destroy()


