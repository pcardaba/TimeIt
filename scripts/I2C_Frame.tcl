# TimeIt generated script
# =======================
# version commit: (v1.1.0)
# datetime: 2026-07-13 21:29:53

remove -all

set_window_size -width 1548 -height 681

set_canvas_scale 7.2

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
   -period {10}  \
   -rise_at {0}  \
   -fall_at {5}  \
   -show 16  \
   -color black  \
   -amplitude 40  \
   -lwidth 2  \
   -use_uid 0  

create_output -name I2C_SDA  \
   -specify internal  \
   -launch_clock CLKref  \
   -capture_clock CLKref  \
   -rclk_outputdly_max {0}  \
   -rclk_outputdly_min {0}  \
   -fclk_outputdly_max {2}  \
   -fclk_outputdly_min {2}  \
   -rclk_oedly_max {0}  \
   -rclk_oedly_min {0}  \
   -fclk_oedly_max {0}  \
   -fclk_oedly_min {0}  \
   -data_edges {4N 7P 8N 11P 12N 13N}  \
   -high_edges {0 3P 6N 10N 15N}  \
   -low_edges {2P 5N 9N 14N}  \
   -color black  \
   -amplitude 40  \
   -lwidth 2  \
   -use_uid 3     -visible 

create_output -name I2C_SCK  \
   -specify internal  \
   -launch_clock CLKref  \
   -capture_clock CLKref  \
   -rclk_outputdly_max {0}  \
   -rclk_outputdly_min {0}  \
   -fclk_outputdly_max {0}  \
   -fclk_outputdly_min {0}  \
   -rclk_oedly_max {0}  \
   -rclk_oedly_min {0}  \
   -fclk_oedly_max {0}  \
   -fclk_oedly_min {0}  \
   -high_edges {0 3N 5P 6P 7N 9P 10P 11N 13P 14P 15P}  \
   -low_edges {2N 4N 5N 6N 8N 9N 10N 12N 13N 14N}  \
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
   -from middle:uid_4_4  \
   -to middle:uid_4_8  \
   -at 85  \
   -style inner_both  \
   -anchor to  \
   -label_x 3  \
   -label_y 26 

create_timing_marker -name {R/W}  \
   -from middle:uid_4_8  \
   -to middle:uid_4_12  \
   -at 85  \
   -style inner_both  \
   -anchor to  \
   -label_x 1  \
   -label_y 26 

create_timing_marker -name {ACK}  \
   -from middle:uid_4_12  \
   -to middle:uid_4_16  \
   -at 84  \
   -style inner_both  \
   -anchor to  \
   -label_x 0  \
   -label_y 25 

create_timing_marker -name {DATA}  \
   -from middle:uid_4_16  \
   -to middle:uid_4_24  \
   -at 85  \
   -style inner_both  \
   -anchor to  \
   -label_x -12  \
   -label_y 24 

create_timing_marker -name {ACK}  \
   -from middle:uid_4_24  \
   -to middle:uid_4_28  \
   -at 85  \
   -style inner_both  \
   -anchor to  \
   -label_x -1  \
   -label_y 24 

create_timing_marker -name {DATA}  \
   -from middle:uid_4_28  \
   -to middle:uid_4_36  \
   -at 84  \
   -style inner_both  \
   -anchor to  \
   -label_x 5  \
   -label_y 24 

create_timing_marker -name {ACK}  \
   -from middle:uid_4_36  \
   -to middle:uid_4_40  \
   -at 84  \
   -style inner_both  \
   -anchor to  \
   -label_x 3  \
   -label_y 25 

create_timing_marker -name {STOP}  \
   -from start:uid_4_42  \
   -to middle:uid_3_30  \
   -at 71  \
   -style inner_both  \
   -anchor from  \
   -label_x -1  \
   -label_y 26 

create_waveform_split  -at 30.0132496872519  -amplitude 6.0  -gap 5.0  -overflow 0.15  -lwidth 2

create_waveform_split  -at 69.64342092922183  -amplitude 6.0  -gap 5.0  -overflow 0.15  -lwidth 2

create_waveform_split  -at 109.85324947589096  -amplitude 6.0  -gap 5.0  -overflow 0.15  -lwidth 2

create_waveform_annotation -on uid_4_6 \
  -text {1 - 7} \
  -font_size 12 \
  -rel_x -3 \
  -rel_y 42 

create_waveform_annotation -on uid_4_10 \
  -text {8} \
  -font_size 12 \
  -rel_x 3 \
  -rel_y 37 

create_waveform_annotation -on uid_4_14 \
  -text {9} \
  -font_size 12 \
  -rel_x 1 \
  -rel_y 37 

create_waveform_annotation -on uid_4_18 \
  -text {1 - 7} \
  -font_size 12 \
  -rel_x 2 \
  -rel_y 40 

create_waveform_annotation -on uid_4_22 \
  -text {8} \
  -font_size 12 \
  -rel_x 3 \
  -rel_y 39 

create_waveform_annotation -on uid_4_26 \
  -text {9} \
  -font_size 12 \
  -rel_x 2 \
  -rel_y 39 

create_waveform_annotation -on uid_4_30 \
  -text {1 - 7} \
  -font_size 12 \
  -rel_x 3 \
  -rel_y 41 

create_waveform_annotation -on uid_4_34 \
  -text {8} \
  -font_size 12 \
  -rel_x 1 \
  -rel_y 37 

create_waveform_annotation -on uid_4_38 \
  -text {9} \
  -font_size 12 \
  -rel_x -1 \
  -rel_y 35 


# --- End of generated script. ---

