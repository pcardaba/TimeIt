# TimeIt generated script
# =======================
# DDR capture cases. The same DDR data stream described three ways, all of
# which must draw the same waveform:
#   data1 : single clock (launch_clk launches and captures, rising delays only)
#   data2 : launched by launch_clk, captured on BOTH edges of capture_clk, the
#           clock divided by 2 from it (rising and falling delays given)
#   data3 : launched and captured by capture_clk on both of its edges
# din_ref / din repeat the data1 / data2 pair for an input with internal delays.
# data_sdr is the single-data-rate contrast: rising delays only, so every
# other launch edge, captured by the next rising edge of capture_clk.
# version commit: (v2.6.0)
# datetime: 2026-10-02 19:13:30

remove -all

set_window_size -width 1920 -height 997

set_canvas_scale 9.0

set_app_var -name settings.waveform.tilt -value {2}
set_app_var -name settings.waveform.nmargin -value {100}
set_app_var -name settings.waveform.interslot -value {10}
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
   -show 10  \
   -color black  \
   -amplitude 40  \
   -lwidth 2  \
   -use_uid 1     -visible 

create_output -name data1  \
   -specify external  \
   -launch_clock launch_clk  \
   -capture_clock launch_clk  \
   -rclk_outputdly_max {3}  \
   -rclk_outputdly_min {-2}  \
   -rclk_oedly_max {0}  \
   -rclk_oedly_min {0}  \
   -fclk_oedly_max {0}  \
   -fclk_oedly_min {0}  \
   -data_edges {1P 2P 3P 4P 5P 6P 7P 8P 9P 10P}  \
   -color black  \
   -amplitude 40  \
   -lwidth 2  \
   -use_uid 2     -visible 

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

create_output -name data3  \
   -specify external  \
   -launch_clock capture_clk  \
   -capture_clock capture_clk  \
   -rclk_outputdly_max {3}  \
   -rclk_outputdly_min {-2}  \
   -fclk_outputdly_max {3}  \
   -fclk_outputdly_min {-2}  \
   -rclk_oedly_max {0}  \
   -rclk_oedly_min {0}  \
   -fclk_oedly_max {0}  \
   -fclk_oedly_min {0}  \
   -data_edges {1P 1N 2P 2N 3P 3N 4P 4N 5P 5N}  \
   -color black  \
   -amplitude 40  \
   -lwidth 2  \
   -use_uid 4     -visible 

create_input -name din_ref  \
   -specify internal  \
   -launch_clock launch_clk  \
   -capture_clock launch_clk  \
   -rclk_inputdly_max {3}  \
   -rclk_inputdly_min {-2}  \
   -data_edges {1P 2P 3P 4P 5P 6P 7P 8P 9P 10P}  \
   -color black  \
   -amplitude 40  \
   -lwidth 2  \
   -use_uid 5     -visible 

create_input -name din  \
   -specify internal  \
   -launch_clock launch_clk  \
   -capture_clock capture_clk  \
   -rclk_inputdly_max {3}  \
   -rclk_inputdly_min {-2}  \
   -fclk_inputdly_max {3}  \
   -fclk_inputdly_min {-2}  \
   -data_edges {1P 2P 3P 4P 5P 6P 7P 8P 9P 10P}  \
   -color black  \
   -amplitude 40  \
   -lwidth 2  \
   -use_uid 6     -visible 

create_output -name data_sdr  \
   -specify external  \
   -launch_clock launch_clk  \
   -capture_clock capture_clk  \
   -rclk_outputdly_max {3}  \
   -rclk_outputdly_min {-2}  \
   -rclk_oedly_max {0}  \
   -rclk_oedly_min {0}  \
   -fclk_oedly_max {0}  \
   -fclk_oedly_min {0}  \
   -data_edges {1P 3P 5P 7P 9P}  \
   -color black  \
   -amplitude 40  \
   -lwidth 2  \
   -use_uid 7     -visible 



# --- End of generated script. ---
