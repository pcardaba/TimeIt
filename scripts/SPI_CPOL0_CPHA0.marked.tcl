# TimeIt generated script
# =======================
# version commit: (38784a6)
# datetime: 2026-04-12 16:03:56

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
   -topology clockin \
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
   -refclock refclock  \
   -rclk_outputdly_max {$tREF_T-3}  \
   -rclk_outputdly_min {0}  \
   -high_edges {20P 0}  \
   -low_edges {3P}  \
   -color black  \
   -amplitude 40  \
   -lwidth 2  \
   -use_uid 1     -visible 

create_output -name SCK  \
   -specify external  \
   -refclock refclock  \
   -rclk_outputdly_max {$tREF_T}  \
   -rclk_outputdly_min {0}  \
   -high_edges {4P 6P 8P 10P 12P 14P 16P 18P}  \
   -low_edges {0 5P 7P 9P 11P 13P 15P 17P 19P}  \
   -color black  \
   -amplitude 40  \
   -lwidth 2  \
   -use_uid 2     -visible 

create_output -name MOSI  \
   -specify external  \
   -refclock refclock  \
   -rclk_outputdly_max {$tREF_T-$tVALmax}  \
   -rclk_outputdly_min {-$tVALmin}  \
   -data_edges {3P 5P 7P 9P 11P 13P 15P 17P}  \
   -hiz_edges {0 19P}  \
   -color black  \
   -amplitude 40  \
   -lwidth 2  \
   -use_uid 3     -visible 

create_input -name MISO  \
   -specify external  \
   -refclock refclock  \
   -rclk_inputdly_max {$tREF_T-$tSU}  \
   -rclk_inputdly_min {-$tREF_T+$tHO}  \
   -data_edges {3P 5P 7P 9P 11P 13P 15P 17P}  \
   -unknown_edges {0 19P}  \
   -color black  \
   -amplitude 40  \
   -lwidth 2  \
   -use_uid 4     -visible 


create_timing_marker -name {tCSN_L}  \
   -from end:uid_1_1  \
   -to end:uid_1_3  \
   -at 68  \
   -style outer  \
   -anchor from  \
   -label_x -52  \
   -label_y 9 

create_timing_marker -name {tSCK}  \
   -from full:uid_2_3  \
   -to full:uid_2_7  \
   -at -12  \
   -style inner_both  \
   -anchor from  \
   -label_x 0  \
   -label_y 0 

create_timing_marker -name {tVAL}  \
   -from full:uid_2_5  \
   -to start:uid_3_5  \
   -at 58  \
   -style outer  \
   -anchor to  \
   -label_x 53  \
   -label_y 11 

create_timing_marker -name {tSU}  \
   -from start:uid_4_8  \
   -to full:uid_2_11  \
   -at 73  \
   -style outer  \
   -anchor from  \
   -label_x 0  \
   -label_y 0 

create_timing_marker -name {tHO}  \
   -from full:uid_2_11  \
   -to end:uid_4_8  \
   -at -13  \
   -style outer  \
   -anchor to  \
   -label_x 43  \
   -label_y 9 

create_timing_marker -name {tON}  \
   -from end:uid_1_1  \
   -to start:uid_3_2  \
   -at 59  \
   -style outer  \
   -anchor to  \
   -label_x -39  \
   -label_y 7 

create_timing_marker -name {tOFF}  \
   -from full:uid_2_33  \
   -to start:uid_3_19  \
   -at 57  \
   -style outer  \
   -anchor to  \
   -label_x 51  \
   -label_y 9 

create_timing_marker -name {tCSN_H}  \
   -from end:uid_1_4  \
   -to end:uid_1_5  \
   -at 60  \
   -style outer  \
   -anchor from  \
   -label_x -52  \
   -label_y 11 

create_timing_marker -name {tD}  \
   -from start:uid_3_9  \
   -to full:uid_2_15  \
   -at 71  \
   -style inner_both  \
   -anchor to  \
   -label_x 1  \
   -label_y -4 


# --- End of generated script. ---

