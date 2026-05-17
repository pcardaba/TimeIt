# TimeIt generated script
# =======================
# version commit: (269da0e)
# datetime: 2026-05-17 11:59:25

remove -all

set_window_size -width 1167 -height 447

set_canvas_scale 15.2

set_app_var -name settings.waveform.tilt -value {2}
set_app_var -name settings.waveform.nmargin -value {100}
set_app_var -name settings.waveform.interslot -value {40}
set_app_var -name settings.waveform.top_padding -value {60}
set_app_var -name settings.waveform.bottom_padding -value {10}
set_app_var -name settings.waveform.left_padding -value {10}
set_app_var -name settings.waveform.right_padding -value {5}
set_app_var -name settings.waveform.font.family -value {Arial}
set_app_var -name settings.waveform.font.size -value {12}
set_app_var -name settings.waveform.font.weight -value {bold}
set_app_var -name settings.waveform.font.slant -value {roman}
set_app_var -name settings.waveform.tunits -value {ns}
set_app_var -name settings.selection.click_tolerance -value {2}
set_app_var -name settings.selection.from_color -value {#00FF00}
set_app_var -name settings.selection.to_color -value {#FF0000}
set_app_var -name settings.selection.lwidth -value {2}
set_app_var -name settings.selection.dash -value {6,4}
set_app_var -name settings.marker.lwidth -value {1}
set_app_var -name settings.marker.color -value {black}
set_app_var -name settings.marker.drag_color -value {blue}
set_app_var -name settings.marker.font.family -value {Arial}
set_app_var -name settings.marker.font.size -value {12}
set_app_var -name settings.marker.font.weight -value {normal}
set_app_var -name settings.marker.font.slant -value {roman}
set_app_var -name settings.marker.leg_tail -value {8}
set_app_var -name settings.marker.outer_length -value {20}
set_app_var -name settings.marker.arrow_shape -value {10,12,4}
set_app_var -name settings.marker.float_format -value {.1f}
set_app_var -name settings.grid.x_grid_enabled -value {False}
set_app_var -name settings.grid.y_grid_enabled -value {False}
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
set_app_var -name settings.grid.y_clock_name -value {}
set_app_var -name settings.grid.y_align_posedge -value {True}
set_app_var -name settings.grid.y_align_negedge -value {False}
set_app_var -name settings.grid.y_show_edge_numbers -value {False}
set_app_var -name settings.grid.y_show_cycle -value {False}
set_app_var -name settings.grid.y_show_cycle_format -value {%n}
set_app_var -name settings.grid.y_time_division -value {10}
set_app_var -name timings.tMDC \
   -desc {MDC clock period} \
   -value {100}

create_clock -name SWCLK  \
   -topology clockin \
   -period {20}  \
   -rise_at {10}  \
   -fall_at {20}  \
   -rise_uncertainty {1}  \
   -show 3  \
   -color black  \
   -amplitude 40  \
   -lwidth 2  \
   -use_uid 0     -visible 

create_input -name SWDIO  \
   -specify external  \
   -refclock SWCLK  \
   -fclk_inputdly_max {5}  \
   -fclk_inputdly_min {-2}  \
   -data_edges {1N}  \
   -hiz_edges {0 2N}  \
   -color black  \
   -amplitude 40  \
   -lwidth 2  \
   -use_uid 1     -visible 


create_timing_marker -name {tCK}  \
   -from full:uid_0_4  \
   -to full:uid_0_8  \
   -at -36  \
   -style inner_both  \
   -anchor from  \
   -label_x 0  \
   -label_y 0 

create_timing_marker -name {tCKH}  \
   -from full:uid_0_6  \
   -to full:uid_0_8  \
   -at -15  \
   -style inner_both  \
   -anchor to  \
   -label_x 0  \
   -label_y 0 

create_timing_marker -name {tHOSW}  \
   -from full:uid_0_6  \
   -to start:uid_1_4  \
   -at -13  \
   -style inner_right  \
   -anchor to  \
   -label_x 0  \
   -label_y 0 

create_timing_marker -name {tSUSW}  \
   -from full:uid_0_6  \
   -to start:uid_1_3  \
   -at -13  \
   -style inner_right  \
   -anchor to  \
   -label_x 3  \
   -label_y 0 

create_timing_marker -name {tVALSW}  \
   -from full:uid_0_4  \
   -to start:uid_1_3  \
   -at 210  \
   -style inner_right  \
   -anchor none  \
   -label_x 0  \
   -label_y -3 

create_timing_marker -name {tDIOHZ}  \
   -from full:uid_0_8  \
   -to end:uid_1_4  \
   -at 208  \
   -style inner_right  \
   -anchor none  \
   -label_x 0  \
   -label_y 0 

create_waveform_annotation -on uid_1_1 \
  -text {(input/output)} \
  -font_size 12 \
  -rel_x -189 \
  -rel_y 21 


# --- End of generated script. ---

