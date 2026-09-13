# TimeIt example script
# =====================
# Logic and sampled signals : create_logic and create_sampled
#
# Everything is drawn against a single 10 ns reference clock :
#
#   req, ack   external inputs, arriving 1 to 2 ns after their launch edge
#   busy       req AND ack, delayed by the gate propagation delay. The spread
#              between tANDmin and tANDmax widens every transition window
#   busy_n     NOT busy : a logic signal built on another logic signal
#   idle       NOR of req and ack : a controlling value masks the unknown of
#              the other input (1 NOR x = 0)
#   busy_q     busy resampled by a flip-flop clocked on clk. Every transition
#              of busy is far from a sampling edge, so nothing is violated and
#              the output only shows the tCOmin/tCOmax window
#   late       an input that settles only 1 ns before the sampling edge
#   late_q     late resampled by the same flip-flop. The transition falls
#              inside the [t - tSU, t + tHO) aperture at the 20 ns and 50 ns
#              edges, so those two edges capture an unknown value and hold it
#              until the next edge
#
# See docs/21_logic_signals.md for the description of both commands.

remove -all

set_window_size -width 1100 -height 750

set_canvas_scale 9.0

set_app_var -name settings.waveform.tilt -value {2}
set_app_var -name settings.waveform.nmargin -value {110}
set_app_var -name settings.waveform.interslot -value {20}
set_app_var -name settings.waveform.top_padding -value {20}
set_app_var -name settings.waveform.tunits -value {ns}
set_app_var -name settings.grid.y_grid_enabled -value {True}
set_app_var -name settings.grid.y_mode -value {clock}
set_app_var -name settings.grid.y_line_style -value {dash}
set_app_var -name settings.grid.y_clock_name -value {clk}
set_app_var -name settings.grid.y_align_posedge -value {True}
set_app_var -name settings.grid.y_show_edge_numbers -value {True}

set_app_var -name timings.tCLK \
   -desc {Reference clock period} \
   -value {10}
set_app_var -name timings.tINmax \
   -desc {Input maximum arrival delay} \
   -value {2}
set_app_var -name timings.tINmin \
   -desc {Input minimum arrival delay} \
   -value {1}
set_app_var -name timings.tLATEmax \
   -desc {Late input maximum arrival delay} \
   -value {$tCLK-1}
set_app_var -name timings.tLATEmin \
   -desc {Late input minimum arrival delay} \
   -value {$tCLK-2}
set_app_var -name timings.tANDmax \
   -desc {AND gate maximum propagation delay} \
   -value {2.0}
set_app_var -name timings.tANDmin \
   -desc {AND gate minimum propagation delay} \
   -value {1.0}
set_app_var -name timings.tINVpd \
   -desc {Inverter propagation delay} \
   -value {1.0}
set_app_var -name timings.tSU \
   -desc {Capturing flip-flop setup requirement} \
   -value {2.0}
set_app_var -name timings.tHO \
   -desc {Capturing flip-flop hold requirement} \
   -value {1.0}
set_app_var -name timings.tCOmax \
   -desc {Capturing flip-flop longest clock to output delay} \
   -value {2.5}
set_app_var -name timings.tCOmin \
   -desc {Capturing flip-flop shortest clock to output delay} \
   -value {1.0}

create_clock -name clk  \
   -topology source \
   -period {$tCLK}  \
   -rise_at {0}  \
   -fall_at {$tCLK/2}  \
   -show 10  \
   -color black  \
   -amplitude 40  \
   -lwidth 2  \
   -visible

# --- Inputs of the logic functions ---------------------------------------

create_input -name req  \
   -specify external  \
   -launch_clock clk  \
   -rclk_inputdly_max {$tINmax}  \
   -rclk_inputdly_min {$tINmin}  \
   -high_edges {3P}  \
   -low_edges {0 8P}  \
   -color black  \
   -amplitude 40  \
   -lwidth 2  \
   -visible

create_input -name ack  \
   -specify external  \
   -launch_clock clk  \
   -rclk_inputdly_max {$tINmax}  \
   -rclk_inputdly_min {$tINmin}  \
   -high_edges {5P}  \
   -low_edges {0 9P}  \
   -color black  \
   -amplitude 40  \
   -lwidth 2  \
   -visible

# --- Logic signals ------------------------------------------------------
#
# busy is unknown while an input is switching and the other one is high
# (1 AND x = x), so a stippled unknown box appears on each of its edges. The
# fall of ack at 9P leaves it undisturbed, because req is already low by then
# and a controlling value masks the unknown (0 AND x = 0). The tANDmin/tANDmax
# spread widens each transition window.

create_logic -name busy  \
   -op and  \
   -inputs {req ack}  \
   -tpd_max {$tANDmax}  \
   -tpd_min {$tANDmin}  \
   -color blue  \
   -amplitude 40  \
   -lwidth 2  \
   -visible

create_logic -name busy_n  \
   -op not  \
   -inputs {busy}  \
   -tpd_max {$tINVpd}  \
   -color blue  \
   -amplitude 40  \
   -lwidth 2  \
   -visible

create_logic -name idle  \
   -op nor  \
   -inputs {req ack}  \
   -color purple  \
   -amplitude 40  \
   -lwidth 2  \
   -visible

# --- Sampled signals ----------------------------------------------------
#
# busy_q is unknown before its first sampling edge, as a flip-flop is before it
# is first clocked, then follows busy one clock later. The grey window on each
# of its transitions is the spread between tCOmin and tCOmax.

create_sampled -name busy_q  \
   -source busy  \
   -clock clk  \
   -edge rising  \
   -setup {$tSU}  \
   -hold {$tHO}  \
   -tco_max {$tCOmax}  \
   -tco_min {$tCOmin}  \
   -color green  \
   -amplitude 40  \
   -lwidth 2  \
   -visible

# late is launched on the 2P and 5P edges of clk but arrives 8 to 9 ns later,
# so it settles 1 ns before the next sampling edge while the flip-flop needs
# tSU = 2 ns of setup.

create_input -name late  \
   -specify external  \
   -launch_clock clk  \
   -rclk_inputdly_max {$tLATEmax}  \
   -rclk_inputdly_min {$tLATEmin}  \
   -high_edges {2P}  \
   -low_edges {0 5P}  \
   -color red  \
   -amplitude 40  \
   -lwidth 2  \
   -visible

create_sampled -name late_q  \
   -source late  \
   -clock clk  \
   -edge rising  \
   -setup {$tSU}  \
   -hold {$tHO}  \
   -tco_max {$tCOmax}  \
   -tco_min {$tCOmin}  \
   -color red  \
   -amplitude 40  \
   -lwidth 2  \
   -visible


# --- End of example script. ---
