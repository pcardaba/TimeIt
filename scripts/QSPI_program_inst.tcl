# TimeIt generated script
# =======================
# version commit: (ad8e342)
# datetime: 2026-05-24 14:52:16

remove -all

set_window_size -width 1490 -height 744

set_canvas_scale 0.9

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
set_app_var -name settings.grid.y_clock_name -value {clkref}
set_app_var -name settings.grid.y_align_posedge -value {False}
set_app_var -name settings.grid.y_align_negedge -value {True}
set_app_var -name settings.grid.y_show_edge_numbers -value {True}
set_app_var -name settings.grid.y_show_cycle -value {False}
set_app_var -name settings.grid.y_show_cycle_format -value {%n}
set_app_var -name settings.grid.y_time_division -value {10}
set_app_var -name timings.period \
   -desc {Ref. clock period} \
   -value {50}

create_clock -name clkref  \
   -topology clockin \
   -period {$period}  \
   -rise_at {0}  \
   -fall_at {$period/2.0}  \
   -show 27  \
   -color black  \
   -amplitude 40  \
   -lwidth 2  \
   -use_uid 0  

create_input -name CSN  \
   -specify external  \
   -launch_clock clkref  \
   -capture_clock clkref \
   -rclk_inputdly_max {0}  \
   -rclk_inputdly_min {0}  \
   -high_edges {0}  \
   -low_edges {2P}  \
   -color black  \
   -amplitude 40  \
   -lwidth 2  \
   -use_uid 1     -visible 

create_input -name SCK  \
   -specify external \
   -launch_clock clkref  \
   -capture_clock clkref \
   -rclk_inputdly_max {0}  \
   -rclk_inputdly_min {0}  \
   -fclk_inputdly_max {0}  \
   -fclk_inputdly_min {0}  \
   -data_edges {0}  \
   -high_edges {3P 4P 5P 6P 7P 8P 9P 10P 11P 12P 13P 15P 16P 17P 18P 19P 20P 21P 22P 23P 24P 25P 26P}  \
   -low_edges {2N 3N 4N 5N 6N 7N 8N 9N 10N 11N 12N 13N 15N 16N 17N 18N 19N 20N 21N 22N 23N 24N 25N 26N}  \
   -color black  \
   -amplitude 40  \
   -lwidth 2  \
   -use_uid 2     -visible 

set_attribute -signal {SCK} \
       -name top_padding  -value 30

create_output -name SI/SO0  \
   -specify internal  \
   -launch_clock clkref  \
   -capture_clock clkref \
   -rclk_outputdly_max {0}  \
   -rclk_outputdly_min {0}  \
   -fclk_outputdly_max {$period*0.1}  \
   -fclk_outputdly_min {0}  \
   -rclk_oedly_max {0}  \
   -rclk_oedly_min {0}  \
   -fclk_oedly_max {0}  \
   -fclk_oedly_min {0}  \
   -data_edges {0 10N 11N 12N 13N 14N 15N 16N 17N 18N 19N 20N 21N 22N 23N 24N 25N 26N 27N}  \
   -high_edges {4N 8N}  \
   -low_edges {1N 6N 9N}  \
   -color black  \
   -amplitude 40  \
   -lwidth 2  \
   -use_uid 3     -visible 

set_attribute -signal {SI/SO0} \
       -name top_padding  -value 30

create_output -name SO1  \
   -specify internal  \
   -launch_clock clkref  \
   -capture_clock clkref \
   -rclk_outputdly_max {0}  \
   -rclk_outputdly_min {0}  \
   -fclk_outputdly_max {$period*0.1}  \
   -fclk_outputdly_min {0}  \
   -rclk_oedly_max {0}  \
   -rclk_oedly_min {0}  \
   -fclk_oedly_max {0}  \
   -fclk_oedly_min {0}  \
   -data_edges {18N 19N 20N 21N 22N 23N 24N 25N 26N 27N}  \
   -hiz_edges {0}  \
   -color black  \
   -amplitude 40  \
   -lwidth 2  \
   -use_uid 28     -visible 

create_output -name SO2  \
   -specify internal  \
   -launch_clock clkref  \
   -capture_clock clkref \
   -rclk_outputdly_max {0}  \
   -rclk_outputdly_min {0}  \
   -fclk_outputdly_max {$period*0.1}  \
   -fclk_outputdly_min {0}  \
   -rclk_oedly_max {0}  \
   -rclk_oedly_min {0}  \
   -fclk_oedly_max {0}  \
   -fclk_oedly_min {0}  \
   -data_edges {18N 19N 20N 21N 22N 23N 24N 25N 26N 27N}  \
   -hiz_edges {0}  \
   -color black  \
   -amplitude 40  \
   -lwidth 2  \
   -use_uid 29     -visible 

create_output -name SO3  \
   -specify internal  \
   -launch_clock clkref  \
   -capture_clock clkref \
   -rclk_outputdly_max {0}  \
   -rclk_outputdly_min {0}  \
   -fclk_outputdly_max {$period*0.1}  \
   -fclk_outputdly_min {0}  \
   -rclk_oedly_max {0}  \
   -rclk_oedly_min {0}  \
   -fclk_oedly_max {0}  \
   -fclk_oedly_min {0}  \
   -data_edges {18N 19N 20N 21N 22N 23N 24N 25N 26N 27N}  \
   -hiz_edges {0}  \
   -color black  \
   -amplitude 40  \
   -lwidth 2  \
   -use_uid 30     -visible 

create_timing_marker -name {instruction}  \
   -from full:uid_2_3  \
   -to full:uid_2_35  \
   -at 71  \
   -style inner_both  \
   -anchor from  \
   -label_x -4  \
   -label_y 2 

create_timing_marker -name {24-bit address}  \
   -from full:uid_2_35  \
   -to full:uid_2_63  \
   -at 187  \
   -style inner_both  \
   -anchor none  \
   -label_x 0  \
   -label_y 0 

create_timing_marker -name {Byte-1}  \
   -from full:uid_2_63  \
   -to end:uid_30_5  \
   -at 79  \
   -style inner_both  \
   -anchor to  \
   -label_x 0  \
   -label_y 0 

create_timing_marker -name {Byte-2}  \
   -from full:uid_2_71  \
   -to end:uid_30_9  \
   -at 79  \
   -style inner_both  \
   -anchor to  \
   -label_x 0  \
   -label_y -2 

create_timing_marker -name {Byte-3}  \
   -from full:uid_2_79  \
   -to end:uid_30_13  \
   -at 78  \
   -style inner_both  \
   -anchor to  \
   -label_x 0  \
   -label_y 0 

create_timing_marker -name {Byte-4}  \
   -from full:uid_2_87  \
   -to end:uid_30_17  \
   -at 77  \
   -style inner_both  \
   -anchor to  \
   -label_x 0  \
   -label_y 0 

create_waveform_split  -at 658.2539682539682  -amplitude 6.0  -gap 5.0  -overflow 0.15  -lwidth 2

create_waveform_split  -at 1302.0058811174122  -amplitude 6.0  -gap 5.0  -overflow 0.15  -lwidth 2

create_waveform_annotation -on uid_2_6 \
  -text {0} \
  -font_size 10 \
  -rel_x 1 \
  -rel_y -35 

create_waveform_annotation -on uid_2_10 \
  -text {1} \
  -font_size 10 \
  -rel_x 1 \
  -rel_y -35 

create_waveform_annotation -on uid_2_14 \
  -text {2} \
  -font_size 10 \
  -rel_x 1 \
  -rel_y -35 

create_waveform_annotation -on uid_2_18 \
  -text {3} \
  -font_size 10 \
  -rel_x 1 \
  -rel_y -35 

create_waveform_annotation -on uid_2_22 \
  -text {4} \
  -font_size 10 \
  -rel_x 1 \
  -rel_y -35 

create_waveform_annotation -on uid_2_26 \
  -text {5} \
  -font_size 10 \
  -rel_x 1 \
  -rel_y -35 

create_waveform_annotation -on uid_2_30 \
  -text {6} \
  -font_size 10 \
  -rel_x 1 \
  -rel_y -35 

create_waveform_annotation -on uid_2_34 \
  -text {7} \
  -font_size 10 \
  -rel_x 1 \
  -rel_y -35 

create_waveform_annotation -on uid_2_38 \
  -text {8} \
  -font_size 10 \
  -rel_x 1 \
  -rel_y -35 

create_waveform_annotation -on uid_2_42 \
  -text {9} \
  -font_size 10 \
  -rel_x 1 \
  -rel_y -35 

create_waveform_annotation -on uid_2_46 \
  -text {10} \
  -font_size 10 \
  -rel_y -35 

create_waveform_annotation -on uid_2_50 \
  -text {28} \
  -font_size 10 \
  -rel_x 1 \
  -rel_y -33 

create_waveform_annotation -on uid_2_54 \
  -text {29} \
  -font_size 10 \
  -rel_x 1 \
  -rel_y -33 

create_waveform_annotation -on uid_2_58 \
  -text {30} \
  -font_size 10 \
  -rel_y -34 

create_waveform_annotation -on uid_2_62 \
  -text {31} \
  -font_size 10 \
  -rel_y -35 

create_waveform_annotation -on uid_2_66 \
  -text {32} \
  -font_size 10 \
  -rel_y -34 

create_waveform_annotation -on uid_2_70 \
  -text {33} \
  -font_size 10 \
  -rel_y -33 

create_waveform_annotation -on uid_2_74 \
  -text {34} \
  -font_size 10 \
  -rel_y -33 

create_waveform_annotation -on uid_2_78 \
  -text {35} \
  -font_size 10 \
  -rel_x -2 \
  -rel_y -32 

create_waveform_annotation -on uid_2_82 \
  -text {36} \
  -font_size 10 \
  -rel_y -32 

create_waveform_annotation -on uid_2_86 \
  -text {37} \
  -font_size 10 \
  -rel_x -2 \
  -rel_y -35 

create_waveform_annotation -on uid_2_90 \
  -text {38} \
  -font_size 10 \
  -rel_x -1 \
  -rel_y -33 

create_waveform_annotation -on uid_2_94 \
  -text {39} \
  -font_size 10 \
  -rel_x -1 \
  -rel_y -35 

create_waveform_annotation -on uid_3_14 \
  -text {23} \
  -font_size 10 

create_waveform_annotation -on uid_3_16 \
  -text {22} \
  -font_size 10 

create_waveform_annotation -on uid_3_18 \
  -text {21} \
  -font_size 10 

create_waveform_annotation -on uid_3_22 \
  -text {3} \
  -font_size 10 

create_waveform_annotation -on uid_3_24 \
  -text {2} \
  -font_size 10 

create_waveform_annotation -on uid_3_26 \
  -text {1} \
  -font_size 10 

create_waveform_annotation -on uid_3_28 \
  -text {0} \
  -font_size 10 

create_waveform_annotation -on uid_3_30 \
  -text {4} \
  -font_size 10 

create_waveform_annotation -on uid_3_32 \
  -text {0} \
  -font_size 10 

create_waveform_annotation -on uid_3_34 \
  -text {4} \
  -font_size 10 

create_waveform_annotation -on uid_3_36 \
  -text {0} \
  -font_size 10 

create_waveform_annotation -on uid_3_38 \
  -text {4} \
  -font_size 10 

create_waveform_annotation -on uid_3_40 \
  -text {0} \
  -font_size 10 

create_waveform_annotation -on uid_3_42 \
  -text {4} \
  -font_size 10 

create_waveform_annotation -on uid_3_44 \
  -text {0} \
  -font_size 10 

create_waveform_annotation -on uid_28_3 \
  -text {5} \
  -font_size 10 

create_waveform_annotation -on uid_28_5 \
  -text {1} \
  -font_size 10 

create_waveform_annotation -on uid_28_7 \
  -text {5} \
  -font_size 10 

create_waveform_annotation -on uid_28_9 \
  -text {1} \
  -font_size 10 

create_waveform_annotation -on uid_28_11 \
  -text {5} \
  -font_size 10 

create_waveform_annotation -on uid_28_13 \
  -text {1} \
  -font_size 10 

create_waveform_annotation -on uid_28_15 \
  -text {5} \
  -font_size 10 

create_waveform_annotation -on uid_28_17 \
  -text {1} \
  -font_size 10 

create_waveform_annotation -on uid_29_3 \
  -text {6} \
  -font_size 10 

create_waveform_annotation -on uid_29_5 \
  -text {2} \
  -font_size 10 

create_waveform_annotation -on uid_29_7 \
  -text {6} \
  -font_size 10 

create_waveform_annotation -on uid_29_9 \
  -text {2} \
  -font_size 10 

create_waveform_annotation -on uid_29_11 \
  -text {6} \
  -font_size 10 

create_waveform_annotation -on uid_29_13 \
  -text {2} \
  -font_size 10 

create_waveform_annotation -on uid_29_15 \
  -text {6} \
  -font_size 10 

create_waveform_annotation -on uid_29_17 \
  -text {2} \
  -font_size 10 

create_waveform_annotation -on uid_30_3 \
  -text {7} \
  -font_size 10 

create_waveform_annotation -on uid_30_5 \
  -text {3} \
  -font_size 10 

create_waveform_annotation -on uid_30_7 \
  -text {7} \
  -font_size 10 

create_waveform_annotation -on uid_30_9 \
  -text {3} \
  -font_size 10 

create_waveform_annotation -on uid_30_11 \
  -text {7} \
  -font_size 10 

create_waveform_annotation -on uid_30_13 \
  -text {3} \
  -font_size 10 

create_waveform_annotation -on uid_30_15 \
  -text {7} \
  -font_size 10 

create_waveform_annotation -on uid_30_17 \
  -text {3} \
  -font_size 10 


# --- End of generated script. ---

