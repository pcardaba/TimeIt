
create_clock -name myclok \
	     -topology clockin \
	     -period {100} \
	     -rise_at {50} \
	     -fall_at {100} \
	     -rise_uncertainty 0 \
	     -fall_uncertainty 0 \
	     -input_dly 0 \
	     -color black \
	     -amplitude 40 \
	     -lwidth 2 \
	     -visible \
	     -show 10

create_clock -name clk \
	     -topology clockin \
	     -period {100} \
	     -rise_at {50} \
	     -fall_at {100} \
	     -rise_uncertainty 0 \
	     -fall_uncertainty {20} \
	     -input_dly 0 \
	     -color black \
	     -amplitude 40 \
	     -lwidth 2 \
	     -visible \
	     -show 10


create_input -name myin \
	     -specify internal \
	     -refclock myclok \
	     -rclk_inputdly_max {20} \
	     -rclk_inputdly_min {10} \
	     -fclk_inputdly_max 0 \
	     -fclk_inputdly_min 0 \
	     -rclk_latency_max 0 \
	     -rclk_latency_min 0 \
	     -fclk_latency_max 0 \
	     -fclk_latency_min 0 \
	     -data_edges {2P 6P 7P} \
	     -unknown_edges {0 9P} \
	     -low_edges {5P 8P} \
	     -high_edges {1P 3P 4P} \
	     -color black \
	     -amplitude 40 \
	     -lwidth 2 \
	     -visible

create_input -name myin2 \
	     -specify internal \
	     -refclock myclok \
	     -rclk_inputdly_max {20} \
	     -rclk_inputdly_min {10} \
	     -fclk_inputdly_max 0 \
	     -fclk_inputdly_min 0 \
	     -rclk_latency_max 0 \
	     -rclk_latency_min 0 \
	     -fclk_latency_max 0 \
	     -fclk_latency_min 0 \
	     -data_edges {2P 6P 7P} \
	     -low_edges {0 5P 8P} \
	     -high_edges {1P 3P 4P} \
	     -color black \
	     -amplitude 40 \
	     -lwidth 2 \
	     -visible

## Only rising (SDR) capture
create_output -name myout1 \
	      -specify internal \
	      -refclock myclok \
	      -rclk_outputdly_max {30} \
	      -rclk_outputdly_min {-20} \
	      -hiz_edges {0 4P} \
	      -data_edges {1P 2P 3P} \
	      -color black \
	      -amplitude 40 \
	      -lwidth 2 \
	      -visible
## DDR capture
create_output -name myout2 \
    -specify internal \
    -refclock myclok \
    -rclk_outputdly_max {20} \
    -rclk_outputdly_min {-15} \
    -fclk_outputdly_max {16} \
    -fclk_outputdly_min {-11} \
    -unknown_edges {0} \
    -hiz_edges {4P} \
    -data_edges {1P 1N 2P 2N} \
    -low_edges {6P} \
    -high_edges {8P} \
    -color black \
    -amplitude 40 \
    -lwidth 2 \
    -visible


create_output -name gclk \
	      -specify external \
	      -refclock myclok \
	      -rclk_outputdly_max {100} \
	      -rclk_outputdly_min {0} \
	      -high_edges {1P 3P 5P 7P} \
	      -low_edges {2P 4P 6P 8P} \
	      -color black \
	      -amplitude 40 \
	      -lwidth 2 \
	      -visible

