# TimeIt generated script
# =======================
# Internal versus external output delays against an inserted capture clock.
# capture_clk is divided by 2 from launch_clk and comes out 3 later (-output_dly).
#   data4 : INTERNAL delays (clock-to-output 4..6 plus a launch clock latency of
#           2..3): the windows run forward from the launch_clk edges only, the
#           capture clock plays no part. Shift capture_clk and the windows stay
#           put: in a real system the capture can be missed.
#   data2 : EXTERNAL delays (setup 3 / hold 2): the windows hang on the
#           capture_clk edges, insertion delay included.
# version commit: (v2.6.0)
# datetime: 2026-10-02 22:55:26

remove -all

set_window_size -width 1285 -height 997

set_canvas_scale 9.0

set_app_var -name settings.waveform.tilt -value {2}
set_app_var -name settings.waveform.nmargin -value {200}
set_app_var -name settings.waveform.interslot -value {30}
set_app_var -name settings.waveform.top_padding -value {20}
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
set_app_var -name settings.grid.y_clock_name -value {}
set_app_var -name settings.grid.y_align_posedge -value {True}
set_app_var -name settings.grid.y_align_negedge -value {False}
set_app_var -name settings.grid.y_show_edge_numbers -value {False}
set_app_var -name settings.grid.y_show_cycle -value {False}
set_app_var -name settings.grid.y_show_cycle_format -value {%n}
set_app_var -name settings.grid.y_time_division -value {10}

create_clock -name launch_clk  \
   -topology source \
   -period {10}  \
   -rise_at {5}  \
   -fall_at {10}  \
   -show 20  \
   -color black  \
   -amplitude 40  \
   -lwidth 2  \
   -use_uid 0     -visible 

create_clock -name capture_clk  \
   -topology clockout \
   -master launch_clk  \
   -divide_by 2  \
   -output_dly {3}  \
   -show 10  \
   -color black  \
   -amplitude 40  \
   -lwidth 2  \
   -use_uid 1     -visible 

create_output -name data4  \
   -specify internal  \
   -launch_clock launch_clk  \
   -capture_clock capture_clk  \
   -rclk_outputdly_max {6}  \
   -rclk_outputdly_min {4}  \
   -rclk_oedly_max {0}  \
   -rclk_oedly_min {0}  \
   -fclk_oedly_max {0}  \
   -fclk_oedly_min {0}  \
   -rclk_latency_max {3}  \
   -rclk_latency_min {2}  \
   -data_edges {1P 2P 3P 4P 5P 6P 7P 8P 9P 10P}  \
   -color black  \
   -amplitude 40  \
   -lwidth 2  \
   -use_uid 27     -visible 

create_output -name data2  \
   -specify external  \
   -launch_clock launch_clk  \
   -capture_clock capture_clk  \
   -rclk_outputdly_max {3}  \
   -rclk_outputdly_min {-2}  \
   -fclk_outputdly_max {3}  \
   -fclk_outputdly_min {-2}  \
   -rclk_oedly_max {0}  \
   -rclk_oedly_min {0}  \
   -fclk_oedly_max {0}  \
   -fclk_oedly_min {0}  \
   -data_edges {1P 2P 3P 4P 5P 6P 7P 8P 9P 10P}  \
   -color black  \
   -amplitude 40  \
   -lwidth 2  \
   -use_uid 3     -visible 


create_waveform_annotation -on uid_1_1 \
  -text {Generated clock w/ output delay} \
  -font_size 11 \
  -rel_x -117 \
  -rel_y -35 

create_waveform_annotation -on uid_27_1 \
  -text {Output (internal delays spec)} \
  -font_size 11 \
  -rel_x -208 \
  -rel_y 19 

create_waveform_annotation -on uid_3_1 \
  -text {Output (external delays spec)} \
  -font_size 11 \
  -rel_x -203 \
  -rel_y 20 


# --- End of generated script. ---

