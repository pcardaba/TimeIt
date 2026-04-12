from __future__ import annotations

import tkinter as tk

class Grid:
    
    LINE_STYLES = {
        "solid": None,
        "dash": (6, 3),
        "dot": (1, 2),
        "dashdot": (6, 3, 1, 3),
    }
    
    def __init__( self, settings: Settings, signals: SignalsStore) -> None:
        self.settings = settings
        self.signals = signals
        
    def draw(self, canvas) -> None:
        canvas.delete("grid")
        # Start with x-grid
        if self.settings.grid["x_grid_enabled"]:
            self.draw_x_grid(canvas)
        if self.settings.grid["y_grid_enabled"]:
            if self.settings.grid["y_mode"]=="clock":
                self.draw_y_grid_clockbased(canvas)
            else:
                self.draw_y_grid_timebased(canvas)
                
    def draw_x_grid(self, canvas) -> None:
        _, _, lrx, lry = canvas.bbox("all")
        x_start = self.settings.waveform["left_padding"]
        x_start += self.settings.waveform["nmargin"]
        x_end = lrx
        y_start = 0;
        y_end = lry;

        y = y_end
        while y > 0:
            canvas.create_line(
                x_start, y, # Upper left corner
                x_end, y, # Upper right corner
                tags=("grid", "x-grid"),
            )
            y -= self.settings.grid["x_units_per_division"]
    
        dash = self.LINE_STYLES[self.settings.grid["x_line_style"]]
        canvas.itemconfigure("x-grid",
                             fill=self.settings.grid["x_line_color"],
                             width=self.settings.grid["x_line_width"],
                             dash=dash,
                             )

    def draw_y_grid_timebased(self, canvas) -> None:
        _, _, lrx, lry = canvas.bbox("all")
        x_start = self.settings.waveform["left_padding"]
        x_start += self.settings.waveform["nmargin"]
        x_end = lrx + 10
        y_start = 0
        y_end = lry;
        x = x_start
        tdiv = self.settings.grid["y_time_division"]
        step = 0
        tunits =  self.settings.waveform["tunits"]
        
        while x < x_end:
            canvas.create_text(
                x, y_end+12, 
                text=str(step*tdiv)+tunits,
                tags=("grid", "y-grid", "y-grid-tmark"),
            )
            canvas.create_line(
                x, y_end,
                x, y_start,
                tags=("grid", "y-grid", "y-grid-line"),
            )
            step += 1
            x = x_start + step*tdiv*canvas.scale_factor 

        canvas.itemconfigure("y-grid-tmark",
                             font=self.settings.get_font(self.settings.marker["font"]),
                             anchor="center",
                             fill=self.settings.grid["y_line_color"],
                             )
        dash = self.LINE_STYLES[self.settings.grid["y_line_style"]]
        canvas.itemconfigure("y-grid-line",
                             fill=self.settings.grid["y_line_color"],
                             width=self.settings.grid["y_line_width"],
                             dash=dash,
                             )


    def draw_y_grid_clockbased(self, canvas) -> None:
        _, _, lrx, lry = canvas.bbox("all")
        x_start = self.settings.waveform["left_padding"]
        x_start += self.settings.waveform["nmargin"]
        x_end = lrx + 10
        y_end = lry;

        tdiv = self.settings.grid["y_time_division"]
        step = 0
        tunits =  self.settings.waveform["tunits"]
        clk_name = self.settings.grid["y_clock_name"]
        visible = self.signals.find(clk_name).visible

        # Two annotation rows above the grid lines:
        #   row 1 (top)   – cycle numbers
        #   row 2 (below) – edge numbers
        CYCLE_Y = 8
        EDGE_Y  = 20
        LABEL_MARGIN = 8  # pixels below the lowest label before lines begin

        if self.settings.grid["y_show_edge_numbers"]:
            y_start = EDGE_Y + LABEL_MARGIN
        elif self.settings.grid["y_show_cycle_numbers"]:
            y_start = CYCLE_Y + LABEL_MARGIN
        else:
            y_start = CYCLE_Y

        if not visible:
            # Temporarily unhide...
            canvas.itemconfigure(f"{clk_name}_waveform", state="normal")

        items = []
        if self.settings.grid["y_align_posedge"]:
            items = canvas.find_withtag(f"{clk_name}_Pedges")
        enum = 0
        for i in items:
            enum += 1
            ulx,uly,brx,bry = canvas.bbox(i)
            x = (brx+ulx)/2
            if self.settings.grid["y_show_edge_numbers"]:
                canvas.create_text(
                    x, EDGE_Y,
                    text=f"{enum}P",
                    tags=("grid", "y-grid", "y-grid-emark"),
                )
            canvas.create_line(
                x, y_end,
                x, y_start,
                tags=("grid", "y-grid", "y-grid-line"),
            )

        items = []
        if self.settings.grid["y_align_negedge"]:
            items = canvas.find_withtag(f"{clk_name}_Nedges")
        enum = 0
        for i in items:
            enum += 1
            ulx,uly,brx,bry = canvas.bbox(i)
            x = (brx+ulx)/2
            if self.settings.grid["y_show_edge_numbers"]:
                canvas.create_text(
                    x, EDGE_Y,
                    text=f"{enum}N",
                    tags=("grid", "y-grid", "y-grid-emark"),
                )
            canvas.create_line(
                x, y_end,
                x, y_start,
                tags=("grid", "y-grid", "y-grid-line"),
            )

        # Draw cycle numbers centered in each clock period.
        # Waveforms start at time 0, so cycle 1 centre is at period/2,
        # cycle N centre is at (N - 0.5) * period.
        if self.settings.grid["y_show_cycle_numbers"]:
            clk_signal = self.signals.find(clk_name)
            try:
                period = clk_signal._tcl_eval_float(clk_signal.period,
                                                     context="Grid")
            except Exception:
                period = None

            if period and period > 0:
                x0 = x_start
                scale = canvas.scale_factor
                cycle_num = 1
                cx = x0 + (period / 2.0) * scale
                while cx < x_end:
                    canvas.create_text(
                        cx, CYCLE_Y,
                        text=str(cycle_num),
                        tags=("grid", "y-grid", "y-grid-cmark"),
                    )
                    cycle_num += 1
                    cx = x0 + (cycle_num - 0.5) * period * scale

        # Restore state ...
        if not visible:
            canvas.itemconfigure(f"{clk_name}_waveform", state="hidden")

        dash = self.LINE_STYLES[self.settings.grid["y_line_style"]]
        canvas.itemconfigure("y-grid-line",
                             fill=self.settings.grid["y_line_color"],
                             width=self.settings.grid["y_line_width"],
                             dash=dash,
                             )
        canvas.itemconfigure("y-grid-emark",
                             font=self.settings.get_font(self.settings.marker["font"]),
                             anchor="center",
                             fill=self.settings.grid["y_line_color"],
                             )
        canvas.itemconfigure("y-grid-cmark",
                             font=self.settings.get_font(self.settings.marker["font"]),
                             anchor="center",
                             fill=self.settings.grid["y_line_color"],
                             )
        
