# TimeIt generated script
# =======================

set_app_var -name settings.waveform.tilt -value {2}
set_app_var -name settings.waveform.nmargin -value {100}
set_app_var -name settings.waveform.interslot -value {10}
set_app_var -name settings.waveform.top_padding -value {10}
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
   -rise_uncertainty {0}  \
   -fall_uncertainty {0}  \
   -input_dly {0}  \
   -show 20  \
   -color black  \
   -amplitude 40  \
   -lwidth 2  \
   -use_uid 0     -visible 

create_output -name CS_N  \
   -specify internal  \
   -refclock refclock  \
   -rclk_outputdly_max {$tREF_T-2}  \
   -rclk_outputdly_min {0}  \
   -rclk_latency_max {0}  \
   -rclk_latency_min {0}  \
   -fclk_latency_max {0}  \
   -fclk_latency_min {0}  \
   -high_edges {19P 0}  \
   -low_edges {2P}  \
   -color black  \
   -amplitude 40  \
   -lwidth 2  \
   -use_uid 1     -visible 

create_output -name SCK  \
   -specify internal  \
   -refclock refclock  \
   -rclk_outputdly_max {$tREF_T}  \
   -rclk_outputdly_min {0}  \
   -rclk_latency_max {0}  \
   -rclk_latency_min {0}  \
   -fclk_latency_max {0}  \
   -fclk_latency_min {0}  \
   -high_edges {3P 5P 7P 9P 11P 13P 15P 17P}  \
   -low_edges {0 4P 6P 8P 10P 12P 14P 16P 18P}  \
   -color black  \
   -amplitude 40  \
   -lwidth 2  \
   -use_uid 2     -visible 

create_output -name MOSI  \
   -specify internal  \
   -refclock refclock  \
   -rclk_outputdly_max {$tREF_T-$tVALmax}  \
   -rclk_outputdly_min {-$tVALmin}  \
   -rclk_latency_max {0}  \
   -rclk_latency_min {0}  \
   -fclk_latency_max {0}  \
   -fclk_latency_min {0}  \
   -data_edges {2P 4P 6P 8P 10P 12P 14P 16P}  \
   -hiz_edges {0 18P}  \
   -color black  \
   -amplitude 40  \
   -lwidth 2  \
   -use_uid 3     -visible 

create_input -name MISO  \
   -specify external  \
   -refclock refclock  \
   -rclk_inputdly_max {$tREF_T-$tSU}  \
   -rclk_inputdly_min {-$tREF_T+$tHO}  \
   -fclk_inputdly_max {0}  \
   -fclk_inputdly_min {0}  \
   -data_edges {2P 4P 6P 8P 10P 12P 14P 16P}  \
   -unknown_edges {0 18P}  \
   -color black  \
   -amplitude 40  \
   -lwidth 2  \
   -use_uid 4     -visible 


# --- End of generated script. ---

