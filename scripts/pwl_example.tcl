# PWL (analog) signals example
# ============================
# The PWL files are given relative to this script: "source" resolves them
# against the directory of the script being sourced.

remove -all

set_app_var -name settings.waveform.tunits -value {ns}

create_clock -name clk  \
   -topology clockin \
   -period {20}  \
   -rise_at {0}  \
   -fall_at {10}  \
   -show 12  \
   -color black  \
   -amplitude 40  \
   -use_uid 0     -visible

create_input -name por_n  \
   -specify external  \
   -launch_clock clk  \
   -rclk_inputdly_max {2}  \
   -rclk_inputdly_min {1}  \
   -low_edges {0}  \
   -high_edges {5P}  \
   -color black  \
   -amplitude 40  \
   -use_uid 1     -visible

# Supply voltage and current share one waveform slot.
create_pwl -names {VDD IDD}  \
   -files {pwl/vdd.pwl pwl/idd.pwl}  \
   -height 100  \
   -use_uid 2     -visible
set_attribute -signal {VDD} -name color -value {blue}
set_attribute -signal {IDD} -name color -value {red}
set_attribute -signal {IDD} -name lstyle -value {dash}
set_attribute -signal {IDD} -name scale -value {0.8}

# Temperature alone, attenuated and shifted downwards.
create_pwl -names {TEMP}  \
   -files {pwl/temp.pwl}  \
   -height 60  \
   -use_uid 3     -visible
set_attribute -signal {TEMP} -name color -value {orange}
set_attribute -signal {TEMP} -name scale -value {0.6}
set_attribute -signal {TEMP} -name offset -value {-0.15}

create_value_marker -signal {VDD}  \
   -use_uid 0  \
   -at 130.0  \
   -label_x 0  \
   -label_y 18

create_value_marker -signal {IDD}  \
   -use_uid 1  \
   -at 40.0  \
   -label_x 30  \
   -label_y -14

create_value_marker -signal {TEMP}  \
   -use_uid 2  \
   -at 200.0  \
   -text {Tj max}  \
   -label_x -10  \
   -label_y -16
