# TimeIt generated script
# =======================
# version commit: (v1.1.0)
# datetime: 2026-07-13 21:31:28

remove -all

set_window_size -width 1216 -height 594

set_canvas_scale 2.5

set_app_var -name settings.waveform.tilt -value {2}
set_app_var -name settings.waveform.nmargin -value {100}
set_app_var -name settings.waveform.interslot -value {50}
set_app_var -name settings.waveform.top_padding -value {60}
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
set_app_var -name settings.grid.y_clock_name -value {refclock}
set_app_var -name settings.grid.y_align_posedge -value {True}
set_app_var -name settings.grid.y_align_negedge -value {False}
set_app_var -name settings.grid.y_show_edge_numbers -value {False}
set_app_var -name settings.grid.y_show_cycle -value {False}
set_app_var -name settings.grid.y_show_cycle_format -value {%n}
set_app_var -name settings.grid.y_time_division -value {10}
set_app_var -name timings.tREF_T \
   -desc {Reference (hidden) clock period} \
   -value {20}
set_app_var -name timings.tVALmax \
   -desc {MOSI from clock to data valid} \
   -value {8}
set_app_var -name timings.tVALmin \
   -desc {MOSI from clock to data invalid} \
   -value {5}
set_app_var -name timings.tSU \
   -desc {MISO setup delay} \
   -value {10}
set_app_var -name timings.tHO \
   -desc {MISO hold delay} \
   -value {2}

create_clock -name refclock  \
   -topology source \
   -period {$tREF_T}  \
   -rise_at {0}  \
   -fall_at {$tREF_T/2}  \
   -show 21  \
   -color black  \
   -amplitude 40  \
   -lwidth 2  \
   -use_uid 0  

create_output -name CS_N  \
   -specify external  \
   -launch_clock refclock  \
   -capture_clock refclock  \
   -rclk_outputdly_max {$tREF_T-3}  \
   -rclk_outputdly_min {0}  \
   -rclk_oedly_max {0}  \
   -rclk_oedly_min {0}  \
   -fclk_oedly_max {0}  \
   -fclk_oedly_min {0}  \
   -high_edges {20P 0}  \
   -low_edges {3P}  \
   -color black  \
   -amplitude 40  \
   -lwidth 2  \
   -use_uid 1     -visible 

create_output -name SCK  \
   -specify external  \
   -launch_clock refclock  \
   -capture_clock refclock  \
   -rclk_outputdly_max {$tREF_T}  \
   -rclk_outputdly_min {0}  \
   -rclk_oedly_max {0}  \
   -rclk_oedly_min {0}  \
   -fclk_oedly_max {0}  \
   -fclk_oedly_min {0}  \
   -high_edges {4P 6P 8P 10P 12P 14P 16P 18P}  \
   -low_edges {0 5P 7P 9P 11P 13P 15P 17P 19P}  \
   -color black  \
   -amplitude 40  \
   -lwidth 2  \
   -use_uid 2     -visible 

create_output -name MOSI  \
   -specify external  \
   -launch_clock refclock  \
   -capture_clock refclock  \
   -rclk_outputdly_max {$tREF_T-$tVALmax}  \
   -rclk_outputdly_min {-$tVALmin}  \
   -rclk_oedly_max {0}  \
   -rclk_oedly_min {0}  \
   -fclk_oedly_max {0}  \
   -fclk_oedly_min {0}  \
   -data_edges {3P 5P 7P 9P 11P 13P 15P 17P}  \
   -hiz_edges {0 19P}  \
   -color black  \
   -amplitude 40  \
   -lwidth 2  \
   -use_uid 3     -visible 

create_input -name MISO  \
   -specify external  \
   -launch_clock refclock  \
   -capture_clock refclock  \
   -rclk_inputdly_max {$tREF_T-$tSU}  \
   -rclk_inputdly_min {-$tREF_T+$tHO}  \
   -data_edges {3P 5P 7P 9P 11P 13P 15P 17P}  \
   -unknown_edges {0 19P}  \
   -color black  \
   -amplitude 40  \
   -lwidth 2  \
   -use_uid 4     -visible 


create_timing_marker -name {tCSN_L}  \
   -from full:uid_1_2  \
   -to full:uid_1_4  \
   -at -22  \
   -style inner_both  \
   -anchor from  \
   -label_x 0  \
   -label_y 0 

create_timing_marker -name {tLEAD}  \
   -from full:uid_1_2  \
   -to full:uid_2_2  \
   -at 70  \
   -style inner_both  \
   -anchor from  \
   -label_x 0  \
   -label_y -6 

create_timing_marker -name {tSCK}  \
   -from full:uid_2_6  \
   -to full:uid_2_10  \
   -at -22  \
   -style inner_both  \
   -anchor from  \
   -label_x 0  \
   -label_y -6 

create_timing_marker -name {tLAG}  \
   -from full:uid_2_32  \
   -to full:uid_1_4  \
   -at 70  \
   -style inner_both  \
   -anchor to  \
   -label_x 0  \
   -label_y -6 

create_timing_marker -name {tON}  \
   -from full:uid_1_2  \
   -to start:uid_3_2  \
   -at -22  \
   -style outer  \
   -anchor to  \
   -label_x -46  \
   -label_y 8 

create_timing_marker -name {tVAL}  \
   -from full:uid_2_4  \
   -to start:uid_3_5  \
   -at -22  \
   -style outer  \
   -anchor to  \
   -label_x 55  \
   -label_y 8 

create_timing_marker -name {tD}  \
   -from start:uid_3_7  \
   -to full:uid_2_10  \
   -at -22  \
   -style outer  \
   -anchor from  \
   -label_x 64  \
   -label_y 8 

create_timing_marker -name {tOFF}  \
   -from full:uid_2_32  \
   -to start:uid_3_19  \
   -at -22  \
   -style outer  \
   -anchor to  \
   -label_x 58  \
   -label_y 8 

create_timing_marker -name {tSU}  \
   -from start:uid_4_8  \
   -to full:uid_2_10  \
   -at 70  \
   -style outer  \
   -anchor from  \
   -label_x -62  \
   -label_y 8 

create_timing_marker -name {tHO}  \
   -from full:uid_2_10  \
   -to end:uid_4_8  \
   -at -22  \
   -style outer  \
   -anchor to  \
   -label_x 48  \
   -label_y 8 


# --- End of generated script. ---

