# TimeIt generated script
# =======================
# version commit: (v2.11.0-3-gb517383)
# datetime: 2026-11-21 17:25:07

remove -all

set_window_size -width 1250 -height 560

set_canvas_scale 3.1

# --- User variables ---
set txt D0
set uid uid_2_6

set_app_var -name settings.waveform.tilt -value {2}
set_app_var -name settings.waveform.nmargin -value {110}
set_app_var -name settings.waveform.interslot -value {50}
set_app_var -name settings.waveform.top_padding -value {70}
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
set_app_var -name settings.grid.y_line_style -value {dash}
set_app_var -name settings.grid.y_line_width -value {1}
set_app_var -name settings.grid.y_line_color -value {#808080}
set_app_var -name settings.grid.y_subdivisions -value {5}
set_app_var -name settings.grid.y_clock_name -value {SCK}
set_app_var -name settings.grid.y_align_posedge -value {True}
set_app_var -name settings.grid.y_align_negedge -value {True}
set_app_var -name settings.grid.y_show_edge_numbers -value {True}
set_app_var -name settings.grid.y_show_cycle -value {False}
set_app_var -name settings.grid.y_show_cycle_format -value {%n}
set_app_var -name settings.grid.y_time_division -value {10}
set_app_var -name timings.tCK \
   -desc {SCK clock period} \
   -value {40}
set_app_var -name timings.tSU \
   -desc {Slave SDIO setup time before SCK rising} \
   -value {8}
set_app_var -name timings.tH \
   -desc {Slave SDIO hold time after SCK rising} \
   -value {4}
set_app_var -name timings.tVmin \
   -desc {Slave SDIO valid after SCK falling (min)} \
   -value {3}
set_app_var -name timings.tVmax \
   -desc {Slave SDIO valid after SCK falling (max)} \
   -value {12}

create_clock -name SCK  \
   -topology source \
   -period {$tCK}  \
   -rise_at {$tCK/2}  \
   -fall_at {$tCK}  \
   -show 9  \
   -color black  \
   -amplitude 40  \
   -lwidth 2  \
   -use_uid 0     -visible 

create_output -name CS_N  \
   -specify internal  \
   -launch_clock SCK  \
   -capture_clock SCK  \
   -rclk_oedly_max {0}  \
   -rclk_oedly_min {0}  \
   -fclk_oedly_max {0}  \
   -fclk_oedly_min {0}  \
   -high_edges {0 8N}  \
   -low_edges {1}  \
   -color black  \
   -amplitude 40  \
   -lwidth 2  \
   -use_uid 1     -visible 

create_inout -name SDIO  \
   -specify external  \
   -in_launch_clock SCK  \
   -in_capture_clock SCK  \
   -fclk_inputdly_max {$tVmax}  \
   -fclk_inputdly_min {$tVmin}  \
   -in_data_edges {5N 6N 7N}  \
   -in_hiz_edges {0 8N}  \
   -out_launch_clock SCK  \
   -out_capture_clock SCK  \
   -rclk_outputdly_max {$tSU}  \
   -rclk_outputdly_min {-$tH}  \
   -out_data_edges {1N 2N 3N}  \
   -out_hiz_edges {0 4N}  \
   -color black  \
   -amplitude 40  \
   -lwidth 2  \
   -use_uid 2     -visible 

create_inout -name SDIO_bad  \
   -specify external  \
   -in_launch_clock SCK  \
   -in_capture_clock SCK  \
   -fclk_inputdly_max {$tVmax}  \
   -fclk_inputdly_min {$tVmin}  \
   -in_data_edges {4N 5N 6N}  \
   -in_hiz_edges {0 7N}  \
   -out_launch_clock SCK  \
   -out_capture_clock SCK  \
   -rclk_outputdly_max {$tSU}  \
   -rclk_outputdly_min {-$tH}  \
   -out_data_edges {1N 2N 3N}  \
   -out_hiz_edges {0 4N}  \
   -color black  \
   -amplitude 40  \
   -lwidth 2  \
   -use_uid 3     -visible 


create_timing_marker -name {tCK}  \
   -use_uid 0  \
   -from full:uid_0_2  \
   -to full:uid_0_6  \
   -at -22  \
   -style inner_both  \
   -anchor from  \
   -label_x 0  \
   -label_y 0 

create_timing_marker -name {tSU}  \
   -use_uid 1  \
   -from start:uid_2_9  \
   -to full:uid_0_6  \
   -at -14  \
   -style inner_both  \
   -anchor from  \
   -label_x 0  \
   -label_y 0 

create_timing_marker -name {tVmax}  \
   -use_uid 2  \
   -from full:uid_0_20  \
   -to start:uid_2_2  \
   -at -14  \
   -style inner_both  \
   -anchor to  \
   -label_x 0  \
   -label_y 0 

create_timing_marker -name {tTA}  \
   -use_uid 3  \
   -from start:uid_2_16  \
   -to end:uid_2_16  \
   -at 56  \
   -style inner_both  \
   -anchor from  \
   -label_x 0  \
   -label_y 0 

create_timing_marker -name {}  \
   -use_uid 4  \
   -from start:uid_3_17  \
   -to end:uid_3_17  \
   -at 70  \
   -style outer  \
   -anchor from  \
   -label_x 0  \
   -label_y 0 

create_waveform_annotation -on uid_2_9 \
  -text {C2} \
  -font_size 11 

create_waveform_annotation -on uid_2_11 \
  -text {C1} \
  -font_size 11 

create_waveform_annotation -on uid_2_13 \
  -text {C0} \
  -font_size 11 

create_waveform_annotation -on uid_2_2 \
  -text {D2} \
  -font_size 11 \
  -fill #DCEBFF 

create_waveform_annotation -on uid_2_4 \
  -text {D1} \
  -font_size 11 \
  -fill #DCEBFF 

create_waveform_annotation -on uid_2_6 \
  -text {D0} \
  -font_size 11 \
  -fill #DCEBFF 

create_waveform_annotation -on uid_3_17 \
  -text {contention} \
  -font_size 11 \
  -font_color red \
  -rel_y -32 


# --- End of generated script. ---

