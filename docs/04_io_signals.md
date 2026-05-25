# How to create input / output signal(s)

Input and output signals represent data paths relative to a reference clock. They are created with `create_input` and `create_output` in the TCL console.

---

## Input signals — `create_input`

An input signal is driven by an external source and captured by internal flip-flops. Delays can be specified as being external, this is typical of a pre-layout/synthesis view, or internal when, after implementation (post-layout/synthesis), the internal delays are known.

Specifying with external delays is the typical situation when constraining I/Os for implementation.

## GUI procedure

![TimeIt create input](screenshots/create_input.png)

1. <kbd>Mouse Right-click</kbd> in the canvas area. Select **New Signal→Input...**
2. Select internal or external delays specification mode.  
3. Complete the input description. Not all fields are mandatory (see command documentation). Both, rising and falling delays are not mandatory. It is important to highlight here than when launching edges are specified, capturing clock edge is induced by the presence or absence of the rising/falling clock delays. Example: If you specify a positive launching clock edge list: 1P 2P 3P ..., and you state falling clock edge input delays, the tool will assume that data in launched at 1P and captured at the next falling edge. If your system is posedge(launch)-posedge(capture), you shall not provide falling clock delays. Both, rising and falling clock delays are typically given for DDR interface.
4. Referenced clock edges list (white space separated) that correspond to the data launch. Example: 1P 3P 8P, means that the corresponding data type is lauched at clock edge 1P, 3P, 8P. Follow the illustrated clock edge nomenclature.  

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

![TimeIt create input example](screenshots/create_input_example.png)


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

![TimeIt create input example2](screenshots/create_input_example2.png)

Notice that in this example, *data_i* is specified considering input internal delays and *addr<31:0>* is specified considering external delays.

---

## Output signals — `create_output`

An output signal is launched by internal flip-flops and read by an external receiver.

Delays can be specified as being external, this is typical of a pre-layout/synthesis view, or internal when, after implementation (post-layout/synthesis), the internal delays are known.

Specifying with external delays is the typical situation faced when constraining I/Os for implementation.

Output buffers can be tri-state. When using internal delays, **output** propagation delays may differ from **output enable (oe)** delays. The tool gives the possibility to make the distinction in between different output and output enable delays. 

## GUI procedure

![TimeIt create output](screenshots/create_output.png)

1. <kbd>Mouse Right-click</kbd> in the canvas area. Select **New Signal→Output...**
2. Select internal or external delays specification mode.  
3. Complete the output signal description. Not all fields are mandatory (see command documentation). Both, rising and falling delays are not mandatory. It is important to highlight here than when launching edges are specified, capturing clock edge is induced by the presence or absence of the rising/falling clock delays. Example: If you specify a positive launching clock edge list: 1P 2P 3P ..., and you state falling clock edge input delays, the tool will assume that data in launched at 1P and captured at the next falling edge. If your system is posedge(launch)-posedge(capture), you shall not provide falling clock delays. Both, rising and falling clock delays are typically given for DDR interface.
4. If the signal has from/to hi-z transitions output enable delays shall be given otherwise they will be considered as 0. 
5. Referenced clock edges list (white space separated) that correspond to the **data launch**. Example: 1P 3P 8P, means that the corresponding data type is lauched at clock edge 1P, 3P, 8P. Follow the illustrated clock edge nomenclature.  


### Command syntax

```
create_output -name output_name
              [-specify (internal)|external]
              -refclock ref_clk
              [-rclk_outputdly_max {outdly_expr}]
              [-rclk_outputdly_min {outdly_expr}]
              [-fclk_outputdly_max {outdly_expr}]
              [-fclk_outputdly_min {output_expr}]
              [-rclk_oedly_max {oedly_expr}]
              [-rclk_oedly_min {oedly_expr}]
              [-fclk_oedly_max {oedly_expr}]
              [-fclk_oedly_min {oedly_expr}]
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


### Step-by-step example

```tcl
set out_delay(max) 5
set out_delay(min) 4
set oe_delay(max) 3
set oe_delay(min) 1

create_output -name "data_o<7:0>" \
              -specify internal \
              -refclock clk \
              -data_edges {1P 2P} \
              -hiz_edges {0 3P} \
              -rclk_outputdly_max {$out_delay(max)} \
              -rclk_outputdly_min {$out_delay(min)} \
              -rclk_oedly_max {$oe_delay(max)} \
              -rclk_oedly_min {$oe_delay(min)} \
              -visible
```
[Download example script file](screenshots/create_output_example.tcl)

![TimeIt create output example](screenshots/create_output_example.png)

---

## Notes

- `-specify internal` vs `external` changes the interpretation of delays — read the built-in help carefully.
- Run `create_input -help` or `create_output -help` in the console for the full built-in reference.

---

*Previous: [How to create clock signal(s)](03_clock_signal.md) | Next: [How to create timing markers](05_timing_markers.md)*
