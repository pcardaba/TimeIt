# TimeIt generated script
# =======================
# version commit: (81a6793)
# datetime: 2026-05-17 16:15:12

remove -all

set_window_size -width 1548 -height 681

set_canvas_scale 0.1

set_app_var -name settings.waveform.tilt -value {4}
set_app_var -name settings.waveform.nmargin -value {100}
set_app_var -name settings.waveform.interslot -value {30}
set_app_var -name settings.waveform.top_padding -value {50}
set_app_var -name settings.waveform.bottom_padding -value {30}
set_app_var -name settings.waveform.left_padding -value {10}
set_app_var -name settings.waveform.right_padding -value {5}
set_app_var -name settings.waveform.font.family -value {Arial}
set_app_var -name settings.waveform.font.size -value {12}
set_app_var -name settings.waveform.font.weight -value {bold}
set_app_var -name settings.waveform.font.slant -value {roman}
set_app_var -name settings.waveform.tunits -value {ns}
set_app_var -name settings.waveform.line_pullup -value {500.0}
set_app_var -name settings.waveform.line_cap -value {1e-10}
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
set_app_var -name settings.grid.y_clock_name -value {CLKref}
set_app_var -name settings.grid.y_align_posedge -value {True}
set_app_var -name settings.grid.y_align_negedge -value {False}
set_app_var -name settings.grid.y_show_edge_numbers -value {True}
set_app_var -name settings.grid.y_show_cycle -value {False}
set_app_var -name settings.grid.y_show_cycle_format -value {%n}
set_app_var -name settings.grid.y_time_division -value {10}

create_clock -name CLKref  \
   -topology source \
   -period {1000}  \
   -rise_at {0}  \
   -fall_at {500}  \
   -show 16  \
   -color black  \
   -amplitude 40  \
   -lwidth 2  \
   -use_uid 0  

create_output -name I2C_SDA  \
   -specify internal  \
   -launch_clock CLKref  \
   -capture_clock CLKref \
   -rclk_outputdly_max {0}  \
   -rclk_outputdly_min {0}  \
   -fclk_outputdly_max {200}  \
   -fclk_outputdly_min {200}  \
   -rclk_oedly_max {0}  \
   -rclk_oedly_min {0}  \
   -fclk_oedly_max {200}  \
   -fclk_oedly_min {200}  \
   -data_edges {4N 7P 8N 11P 12N 13N}  \
   -hiz_edges {0 3P 6N 10N 15N}  \
   -low_edges {2P 5N 9N 14N}  \
   -pulled_up  \
   -color black  \
   -amplitude 40  \
   -lwidth 2  \
   -use_uid 3     -visible 

create_output -name I2C_SCK  \
   -specify internal  \
   -launch_clock CLKref  \
   -capture_clock CLKref \
   -rclk_outputdly_max {0}  \
   -rclk_outputdly_min {0}  \
   -fclk_outputdly_max {0}  \
   -fclk_outputdly_min {0}  \
   -rclk_oedly_max {0}  \
   -rclk_oedly_min {0}  \
   -fclk_oedly_max {0}  \
   -fclk_oedly_min {0}  \
   -hiz_edges {0 3N 5P 6P 7N 9P 10P 11N 13P 14P 15P}  \
   -low_edges {2N 4N 5N 6N 8N 9N 10N 12N 13N 14N}  \
   -pulled_up  \
   -color black  \
   -amplitude 40  \
   -lwidth 2  \
   -use_uid 4     -visible 


create_timing_marker -name {START}  \
   -from start:uid_3_1  \
   -to end:uid_4_1  \
   -at 72  \
   -style inner_both  \
   -anchor to  \
   -label_x -4  \
   -label_y 31 

create_timing_marker -name {ADDRESS}  \
   -from middle:uid_4_3  \
   -to middle:uid_4_7  \
   -at 85  \
   -style inner_both  \
   -anchor to  \
   -label_x 3  \
   -label_y 26 

create_timing_marker -name {R/W}  \
   -from middle:uid_4_7  \
   -to middle:uid_4_11  \
   -at 85  \
   -style inner_both  \
   -anchor to  \
   -label_x 1  \
   -label_y 26 

create_timing_marker -name {ACK}  \
   -from middle:uid_4_11  \
   -to middle:uid_4_15  \
   -at 84  \
   -style inner_both  \
   -anchor to  \
   -label_x 0  \
   -label_y 25 

create_timing_marker -name {DATA}  \
   -from middle:uid_4_15  \
   -to middle:uid_4_23  \
   -at 85  \
   -style inner_both  \
   -anchor to  \
   -label_x -12  \
   -label_y 24 

create_timing_marker -name {ACK}  \
   -from middle:uid_4_23  \
   -to middle:uid_4_27  \
   -at 85  \
   -style inner_both  \
   -anchor to  \
   -label_x -1  \
   -label_y 24 

create_timing_marker -name {DATA}  \
   -from middle:uid_4_27  \
   -to middle:uid_4_35  \
   -at 84  \
   -style inner_both  \
   -anchor to  \
   -label_x 5  \
   -label_y 24 

create_timing_marker -name {ACK}  \
   -from middle:uid_4_35  \
   -to middle:uid_4_39  \
   -at 84  \
   -style inner_both  \
   -anchor to  \
   -label_x 3  \
   -label_y 25 

create_timing_marker -name {STOP}  \
   -from start:uid_4_40  \
   -to middle:uid_3_29  \
   -at 71  \
   -style inner_both  \
   -anchor from  \
   -label_x 3  \
   -label_y 27 

create_waveform_split  -at 3005.553326153736  -amplitude 6.0  -gap 5.0  -overflow 0.15  -lwidth 2

create_waveform_split  -at 6985.763598662131  -amplitude 6.0  -gap 5.0  -overflow 0.15  -lwidth 2

create_waveform_split  -at 10950.46952806189  -amplitude 6.0  -gap 5.0  -overflow 0.15  -lwidth 2

create_waveform_annotation -on uid_4_6 \
  -text {1 - 7} \
  -font_size 12 \
  -rel_x -31 \
  -rel_y 44 

create_waveform_annotation -on uid_4_10 \
  -text {8} \
  -font_size 12 \
  -rel_x -16 \
  -rel_y 40 

create_waveform_annotation -on uid_4_14 \
  -text {9} \
  -font_size 12 \
  -rel_x -9 \
  -rel_y 39 

create_waveform_annotation -on uid_4_18 \
  -text {1 - 7} \
  -font_size 12 \
  -rel_x -26 \
  -rel_y 41 

create_waveform_annotation -on uid_4_22 \
  -text {8} \
  -font_size 12 \
  -rel_x -15 \
  -rel_y 39 

create_waveform_annotation -on uid_4_26 \
  -text {9} \
  -font_size 12 \
  -rel_x -13 \
  -rel_y 39 

create_waveform_annotation -on uid_4_30 \
  -text {1 - 7} \
  -font_size 12 \
  -rel_x -32 \
  -rel_y 41 

create_waveform_annotation -on uid_4_34 \
  -text {8} \
  -font_size 12 \
  -rel_x -14 \
  -rel_y 38 

create_waveform_annotation -on uid_4_38 \
  -text {9} \
  -font_size 12 \
  -rel_x -12 \
  -rel_y 36 


# --- End of generated script. ---

