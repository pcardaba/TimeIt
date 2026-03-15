from __future__ import annotations

import tkinter as tk
from tkinter import font as tkfont


class Settings:
    """
    Application settings container.

    One instance should be created by TimeItApp
    and shared explicitly (no singleton).
    """

    def __init__(self, root: tk.Misc | None = None) -> None:
        # ---- Fonts ----
        # Creating a tk Font requires a Tk interpreter.
        # root should normally be the main Tk instance.
        self.parent = root
        # Get default font family name in the current system.
        family = tkfont.nametofont("TkDefaultFont").actual()["family"]

        # ---- Waveform layout settings ----
        self.waveform  = {
            "tilt"           : 2, 
            "nmargin"        : 100,
            "interslot"      : 10, 
            "top_padding"    : 20,
            "bottom_padding" : 10,
            "left_padding"   : 10,
            "right_padding"  : 5, 
            "font"           : {
                "family": family,
                "size": 11,
                "weight": "bold",
                "slant": "roman",
            },
            "tunits"         : "ns" 
        }
        # Waveform settings descriptions 
        self.waveform_desc = {
            # waveform
            "tilt"          : "Edges and transitions tilt (in px)",
            "nmargin"       : "Signal names left margin",
            "interslot"     : "Space between waveform slots",
            "top_padding"   : "Top padding of waveform canvas",
            "bottom_padding": "Bottom padding of waveform canvas",
            "left_padding"  : "Left padding of waveform canvas",
            "right_padding" : "Right padding of waveform canvas",
            "tunits"        : "Time units",
            "font"          : "Font settings",
        }
        # ---- Selection settings ---
        self.selection = {
            "click_tolerance": 2,         
            "from_color"     : "#00FF00", 
            "to_color"       : "#FF0000", 
            "lwidth"         : 2,
            "dash"           : (6, 4),
        }
        # Selection settings descriptions 
        self.selection_desc = {
            "click_tolerance":  "Click tolerance at selection",
            "from_color"     :  "First-click (from) selection color",
            "to_color"       :  "Further-clicks (to) selection color",
            "lwidth"         :  "Selection line width",
            "dash"           :  "Dashed line pattern  ex. (6, 4)",
        }
        # ---- Marker settings ---
        self.marker = {
            "lwidth"         : 1,
            "color"          : "black",
            "drag_color"     : "blue",
            "font"           : {
                "family": family,
                "size": 10,
                "weight": "normal",
                "slant": "roman",
            },
            "leg_tail"       : 8,
            "outer_length"   : 20,
            "arrow_shape"    : (10, 12, 4),
            "float_format"   : ".1f",
            "timings"        : {},
        }
        # Selection settings descriptions 
        self.marker_desc = {
            "lwidth"         : "Timing markers line width",
            "color"          : "Timing markers color",
            "drag_color"     : "Timing marker color when dragging",
            "font"           : "Timing markers font attributes",
            "leg_tail"       : "Timing mark's legs tails length",
            "outer_length"   : "Outer marks arrow style legnth",
            "arrow_shape"    : "(d1,d2,d3): d1 baseline length. d2  outline length, d3 width",
            "float_format"   : "Timing float to str decimals after trucation",
            "timings"        : "Timings of marker labeled in the canvas.",
        }
        # ---- Grid settings ---
        self.grid = {
            # Global enable
            "x_grid_enabled" : False,
            "y_grid_enabled" : False,
            # X-grid appearance and spacing
            "x_line_style"   : "solid",
            "x_line_width"   : 1,
            "x_line_color"   : "#808080",
            "x_units_per_division" : 10,
            "x_subdivisions" : 5,
            # Y-grid mode
            "y_mode": "clock", # "clock" or "timebase"
            # Y-grid appearance and spacing
            "y_line_style" : "solid",
            "y_line_width" : 1,
            "y_line_color" : "#808080",
            "y_subdivisions" : 5,
            # Clock-aligned mode
            "y_clock_name" : "",
            "y_align_posedge" : True,
            "y_align_negedge" : False,
            "y_show_edge_numbers" : False,
            "y_show_cycle_numbers" : False,
            # Time-base mode
            "y_time_division" : 10,
        }

        self.grid_desc = {
            "x_grid_enabled" : "Horizontal grid enable.",
            "y_grid_enabled" : "Vertical grid enable.",
            # X-grid appearance and spacing
            "x_line_style"   : "'solid', 'dash', 'dot', 'dashdot'",
            "x_line_width"   : "Horizontal grid line width (px)",
            "x_line_color"   : "Horizontal grid line color. Color name or #<rgb> hex nums",
            "x_units_per_division" : "Amplitude units represents a division",
            "x_subdivisions" : "How many points per division",
            # Y-grid mode
            "y_mode": "Vertical grid aligned with 'clock' or 'timebase'",
            # Y-grid appearance and spacing
            "y_line_style" : "'solid', 'dash', 'dot', 'dashdot'",
            "y_line_width" : "Vertical grid line width (px)",
            "y_line_color" : "Vertical grid line color. Color name or #<rgb> hex nums",
            "y_subdivisions" : "How many points per division",
            # Clock-aligned mode
            "y_clock_name" : "If 'y_mode=clock', which is the clock to be aligned with",
            "y_align_posedge" : "If 'y_mode=clock', align y-grid with posedges.",
            "y_align_negedge" : "If 'y_mode=clock', align y-grid with negedges.",
            "y_show_edge_numbers" : "Display 'y_clock_name' edge numbers",
            "y_show_cycle_numbers" : "Display 'y_clock_name' cycle numbers",
            # Time-base mode
            "y_time_division" : "If 'y_mode=timebase', how many time units represents a division",
        }
    
        
    def get_font(self, font_dict):
        return tkfont.Font(
            root=self.parent,
            family=font_dict["family"],
            size=font_dict["size"],
            weight=font_dict["weight"],
            slant=font_dict["slant"],
        )

    def write(self, fileref):
        def emit(obj, prefix):
            # If it's a dict, recurse into its items
            if isinstance(obj, dict):
                for k, v in obj.items():
                    if k == "timings":
                        continue
                    emit(v, f"{prefix}.{k}")
                return

            # If it's a list/tuple, either serialize as one value or expand (choose one)
            # Option A: serialize whole list as a single value:
            if isinstance(obj, (list, tuple)):
                val_str = ",".join(map(str, obj))  
                fileref.write(f"set_app_var -name {prefix} -value {{{val_str}}}\n")
                return

            # Leaf value: write it
            fileref.write(f"set_app_var -name {prefix} -value {{{obj}}}\n")

        emit(self.waveform, "settings.waveform")
        emit(self.selection, "settings.selection")
        emit(self.marker, "settings.marker")
        emit(self.grid, "settings.grid")


