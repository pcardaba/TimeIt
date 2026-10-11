# TimeIt generated script
# =======================
# version commit: (v2.8.0-7-g22a4652)
# datetime: 2026-10-11 14:39:48

remove -all

set_window_size -width 1458 -height 734

set_canvas_scale 2.7

# --- User variables ---
array set data_o {setup 13 hold 9}

set_app_var -name settings.waveform.tilt -value {2}
set_app_var -name settings.waveform.nmargin -value {100}
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
set_app_var -name settings.grid.y_clock_name -value {fastclk}
set_app_var -name settings.grid.y_align_posedge -value {True}
set_app_var -name settings.grid.y_align_negedge -value {False}
set_app_var -name settings.grid.y_show_edge_numbers -value {True}
set_app_var -name settings.grid.y_show_cycle -value {False}
set_app_var -name settings.grid.y_show_cycle_format -value {%n}
set_app_var -name settings.grid.y_time_division -value {10}
set_app_var -name timings.Tfastclk \
   -desc {Fast clock period} \
   -value {10}
set_app_var -name timings.data_o(setup) \
   -desc {data_o setup value} \
   -value {13}
set_app_var -name timings.data_o(hold) \
   -desc {data_o hold value} \
   -value {9}

create_clock -name fastclk  \
   -topology clockin \
   -period {$Tfastclk}  \
   -rise_at {$Tfastclk/2}  \
   -fall_at {$Tfastclk}  \
   -show 50  \
   -color black  \
   -amplitude 40  \
   -lwidth 2  \
   -use_uid 0     -visible 

create_clock -name slowclk  \
   -topology clockout \
   -master fastclk  \
   -divide_by 16  \
   -show 3  \
   -color black  \
   -amplitude 40  \
   -lwidth 2  \
   -use_uid 1     -visible 

create_output -name data1_o  \
   -specify external  \
   -launch_clock fastclk  \
   -capture_clock slowclk  \
   -rclk_outputdly_max {$data_o(setup)}  \
   -rclk_outputdly_min {-$data_o(hold)}  \
   -rclk_oedly_max {0}  \
   -rclk_oedly_min {0}  \
   -fclk_oedly_max {0}  \
   -fclk_oedly_min {0}  \
   -high_edges {1P 33P}  \
   -low_edges {0 17P}  \
   -color black  \
   -amplitude 40  \
   -lwidth 2  \
   -use_uid 3     -visible 

create_output -name data2_o  \
   -specify external  \
   -launch_clock fastclk  \
   -capture_clock slowclk  \
   -rclk_outputdly_max {$data_o(setup)}  \
   -rclk_outputdly_min {-$data_o(hold)}  \
   -rclk_oedly_max {0}  \
   -rclk_oedly_min {0}  \
   -fclk_oedly_max {0}  \
   -fclk_oedly_min {0}  \
   -high_edges {4P 36P}  \
   -low_edges {0 20P}  \
   -color black  \
   -amplitude 40  \
   -lwidth 2  \
   -use_uid 4     -visible 



# --- End of generated script. ---

