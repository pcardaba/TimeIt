# TimeIt generated script
# =======================
# version commit: (144cb49)
# datetime: 2026-05-25 21:07:17

remove -all

set_window_size -width 804 -height 557

set_canvas_scale 24.2

set_app_var -name settings.waveform.tilt -value {2}
set_app_var -name settings.waveform.nmargin -value {140}
set_app_var -name settings.waveform.interslot -value {10}
set_app_var -name settings.waveform.top_padding -value {40}
set_app_var -name settings.waveform.bottom_padding -value {10}
set_app_var -name settings.waveform.left_padding -value {10}
set_app_var -name settings.waveform.right_padding -value {5}
set_app_var -name settings.waveform.font.family -value {DejaVu Sans}
set_app_var -name settings.waveform.font.size -value {11}
set_app_var -name settings.waveform.font.weight -value {bold}
set_app_var -name settings.waveform.font.slant -value {roman}
set_app_var -name settings.waveform.tunits -value {ns}
set_app_var -name settings.waveform.line_pullup -value {1000.0}
set_app_var -name settings.waveform.line_cap -value {1e-10}
set_app_var -name settings.selection.click_tolerance -value {2}
set_app_var -name settings.selection.from_color -value {#00FF00}
set_app_var -name settings.selection.to_color -value {#FF0000}
set_app_var -name settings.selection.lwidth -value {2}
set_app_var -name settings.selection.dash -value {6,4}
set_app_var -name settings.marker.lwidth -value {1}
set_app_var -name settings.marker.color -value {black}
set_app_var -name settings.marker.drag_color -value {blue}
set_app_var -name settings.marker.font.family -value {DejaVu Sans}
set_app_var -name settings.marker.font.size -value {10}
set_app_var -name settings.marker.font.weight -value {normal}
set_app_var -name settings.marker.font.slant -value {roman}
set_app_var -name settings.marker.leg_tail -value {8}
set_app_var -name settings.marker.outer_length -value {20}
set_app_var -name settings.marker.arrow_shape -value {10,12,4}
set_app_var -name settings.marker.float_format -value {.1f}
set_app_var -name settings.grid.x_grid_enabled -value {False}
set_app_var -name settings.grid.y_grid_enabled -value {True}
set_app_var -name settings.grid.x_line_style -value {solid}
set_app_var -name settings.grid.x_line_width -value {1}
set_app_var -name settings.grid.x_line_color -value {#808080}
set_app_var -name settings.grid.x_units_per_division -value {10}
set_app_var -name settings.grid.x_subdivisions -value {5}
set_app_var -name settings.grid.y_mode -value {clock}
set_app_var -name settings.grid.y_line_style -value {solid}
set_app_var -name settings.grid.y_line_width -value {1}
set_app_var -name settings.grid.y_line_color -value {#808080}
set_app_var -name settings.grid.y_subdivisions -value {5}
set_app_var -name settings.grid.y_clock_name -value {clk}
set_app_var -name settings.grid.y_align_posedge -value {True}
set_app_var -name settings.grid.y_align_negedge -value {False}
set_app_var -name settings.grid.y_show_edge_numbers -value {True}
set_app_var -name settings.grid.y_show_cycle -value {False}
set_app_var -name settings.grid.y_show_cycle_format -value {%n}
set_app_var -name settings.grid.y_time_division -value {10}

set_app_var -name timings.out_delay_max \
   -desc {Max output propagation delay} \
   -value {5}
set_app_var -name timings.out_delay_min \
   -desc {Min output propagation delay} \
   -value {4}
set_app_var -name timings.oe_delay_max \
   -desc {Max output enable delay} \
   -value {3}
set_app_var -name timings.oe_delay_min \
   -desc {Min output enable delay} \
   -value {1}

create_clock -name clk  \
   -topology clockin \
   -period {10}  \
   -rise_at {0}  \
   -fall_at {5}  \
   -show 10  \
   -color black  \
   -amplitude 40  \
   -lwidth 2  \
   -use_uid 0     -visible 

create_output -name data_o<7:0>  \
   -specify internal  \
   -launch_clock clk  \
   -rclk_outputdly_max {$out_delay_max}  \
   -rclk_outputdly_min {$out_delay_min}  \
   -rclk_oedly_max {$oe_delay_max}  \
   -rclk_oedly_min {$oe_delay_min}  \
   -fclk_oedly_max {0}  \
   -fclk_oedly_min {0}  \
   -data_edges {1P 2P}  \
   -hiz_edges {0 3P}  \
   -color black  \
   -amplitude 40  \
   -lwidth 2  \
   -use_uid 2     -visible 


create_timing_marker -name {}  \
   -from full:uid_0_2  \
   -to start:uid_2_2  \
   -at 62  \
   -style outer  \
   -anchor to  \
   -label_x 55  \
   -label_y 13 

create_timing_marker -name {}  \
   -from full:uid_0_2  \
   -to start:uid_2_3  \
   -at 92  \
   -style inner_both  \
   -anchor to  \
   -label_x 0  \
   -label_y 0 

create_timing_marker -name {}  \
   -from full:uid_0_7  \
   -to end:uid_2_3  \
   -at 67  \
   -style inner_both  \
   -anchor to  \
   -label_x 0  \
   -label_y 0 

create_timing_marker -name {}  \
   -from full:uid_0_7  \
   -to start:uid_2_5  \
   -at 92  \
   -style inner_both  \
   -anchor to  \
   -label_x 0  \
   -label_y 0 

create_timing_marker -name {}  \
   -from full:uid_0_12  \
   -to end:uid_2_6  \
   -at 76  \
   -style inner_both  \
   -anchor to  \
   -label_x 2  \
   -label_y 0 


# --- End of generated script. ---

