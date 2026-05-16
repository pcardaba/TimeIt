# How to create input / output signal(s)

Input and output signals represent data paths relative to a reference clock. They are created with `create_input` and `create_output` in the TCL console.

---

## Input signals — `create_input`

An input signal is driven by an external source and captured by internal flip-flops.

### Command syntax

```
create_input  -name input_name
              [-specify (internal)|external]
              -refclock ref_clk
              [-rclk_inputdly_max {indly_expr}]
              [-rclk_inputdly_min {indly_expr}]
              [-fclk_inputdly_max {indly_expr}]
              [-fclk_inputdly_min {indly_expr}]
              [-rclk_latency_max {lat_expr}]
              [-rclk_latency_min {lat_expr}]
              [-fclk_latency_max {lat_expr}]
              [-fclk_latency_min {lat_expr}]
              [-data_edges {list_edges}]
              [-hiz_edges {list_edges}]
              [-high_edges {list_edges}]
              [-low_edges {list_edges}]
              [-unknown_edges {list_edges}]
              [-color (black)|green|red|blue|orange|purple]
              [-amplitude amp_value]
              [-lwidth line_width]
              [-visible]
              [-help]
```

### Key parameters

| Parameter | Description |
|---|---|
| `-name` | **Mandatory.** Signal name (may include bus notation, e.g. `addr_i<31:0>`). |
| `-specify` | `internal` (default): delays refer to internal logic (post-layout / STA). `external`: delays from external requirements (SDC `set_input_delay` style). |
| `-refclock` | **Mandatory.** Name of the reference clock signal. |
| `-rclk_inputdly_max/min` | Max/min input delay for signals launched on rising clock edges. |
| `-fclk_inputdly_max/min` | Max/min input delay for signals launched on falling clock edges. |
| `-rclk_latency_max/min` | Max/min clock latency to rising-edge capturing FFs (internal specify only). |
| `-fclk_latency_max/min` | Max/min clock latency to falling-edge capturing FFs (internal specify only). |
| `-data_edges` | Edge list where multi-bit data is launched. |
| `-hiz_edges` | Edge list where signal is tri-stated (Hi-Z). |
| `-high_edges` / `-low_edges` | Edge list where single-bit signal goes high / low. |
| `-unknown_edges` | Edge list where data value is unknown. |

### Edge list notation

Edges are numbered from the start of the diagram. A plain integer refers to any edge (rising or falling). Compound notation `NP` / `NN` refers to cycle `N` posedge / negedge.

```
Example clock:  __/‾‾‾\___/‾‾‾\___/
Edge index:    0  1   2  3   4   5
Compound:      0  1P  1N 2P  2N  3P
```

### Step-by-step example

#### External-specify bus input

```tcl
set in_delay 2.0
create_input -name "addr_i<31:0>" \
             -specify external \
             -refclock clk \
             -hiz_edges {0} \
             -data_edges {1P 2P 3P} \
             -unknown_edges {4P} \
             -rclk_inputdly_max {$in_delay} \
             -rclk_inputdly_min {$in_delay} \
             -visible
```

> **TODO:** Add screenshot showing the resulting input waveform on the canvas.

#### Internal-specify with latency

```tcl
create_input -name data_i \
             -specify internal \
             -refclock clk \
             -data_edges {1P 2P} \
             -rclk_inputdly_max {3.5} \
             -rclk_inputdly_min {1.0} \
             -rclk_latency_max {0.5} \
             -rclk_latency_min {0.1} \
             -visible
```

> **TODO:** Add screenshot.

---

## Output signals — `create_output`

An output signal is launched by internal flip-flops and read by an external receiver.

### Command syntax

```
create_output -name output_name
              [-specify (internal)|external]
              -refclock ref_clk
              [-rclk_outputdly_max {outdly_expr}]
              [-rclk_outputdly_min {outdly_expr}]
              [-fclk_outputdly_max {outdly_expr}]
              [-fclk_outputdly_min {outdly_expr}]
              [-rclk_latency_max {lat_expr}]
              [-rclk_latency_min {lat_expr}]
              [-fclk_latency_max {lat_expr}]
              [-fclk_latency_min {lat_expr}]
              [-data_edges {list_edges}]
              [-hiz_edges {list_edges}]
              [-high_edges {list_edges}]
              [-low_edges {list_edges}]
              [-unknown_edges {list_edges}]
              [-color (black)|green|red|blue|orange|purple]
              [-amplitude amp_value]
              [-lwidth line_width]
              [-visible]
              [-help]
```

> **TODO:** Confirm exact option names for `create_output` against the built-in help text and update above.

### Step-by-step example

```tcl
set out_delay 1.5
create_output -name "data_o<7:0>" \
              -specify external \
              -refclock clk \
              -data_edges {1P 2P 3P} \
              -rclk_outputdly_max {$out_delay} \
              -rclk_outputdly_min {$out_delay} \
              -visible
```

> **TODO:** Add screenshot.

---

## Notes

- `-specify internal` vs `external` changes the interpretation of delays — read the built-in help carefully.
- Run `create_input -help` or `create_output -help` in the console for the full built-in reference.

---

*Previous: [How to create clock signal(s)](03_clock_signal.md) | Next: [How to create timing markers](05_timing_markers.md)*
