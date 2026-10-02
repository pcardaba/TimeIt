# TimeIt quick start for agents

The concepts behind the command options. `help <command>` in TimeIt is the authoritative syntax; this page explains what the options mean. Read it once per session.

## Model

- A diagram is a list of **signals** drawn against time, plus markers, splits and annotations. Everything is created by a Tcl command and the saved file is that list of commands (`remove -all` first, then `set_app_var`, `create_clock`, `create_input` …).
- **Time units**: one unit for the whole diagram (default ns, `set_app_var -name settings.waveform.tunits -value {ps}` changes it). Every timing option is a Tcl expression evaluated by TimeIt, written in braces: `{10}`, `{$Tclk/2}`, `{1e9/$Fref}`.
- **Timing variables** are the parameters of a diagram: `set_app_var -name timings.Tclk -value {10} -desc {Clock period}`, then `$Tclk` anywhere. They must be defined before what uses them, are shown in Edit → Timings, and are the only variables saved with the diagram (a plain `set x 1` is lost on save).

## Clocks

`create_clock -name clk -topology source -period {$Tclk} -rise_at {0} -fall_at {$Tclk/2} -show 8 -visible`

- `-topology source` (root clock) or `clockin` (external clock feeding the chip; the default). `-rise_uncertainty` / `-fall_uncertainty` draw jitter windows. `-show N` draws N cycles.
- **Generated clocks** derive from a master: `-topology clockout|clockinout -master clk -divide_by 2` (or `-edges {1 3 5}` with SDC semantics, `-invert` to complement). `clockout` is generated inside the chip and goes out; `clockinout` also comes back in to capture inputs. `-output_dly`/`-input_dly` model the pad delays.
- **Gated clocks**: `-enabled_by <signal> -enable_active low` shows pulses only while the enable is at its active level (SPI chip select style). Only generated clocks can be gated.

## Inputs and outputs

`create_input -name d -launch_clock clk -high_edges {2P} -low_edges {0 5P} -visible`
`create_output -name q -launch_clock clk -rclk_outputdly_max {$Tco_max} -rclk_outputdly_min {$Tco_min} -data_edges {1P 2P 3P} -visible`

- `-launch_clock` is the clock whose edges the signal changes on; `-capture_clock` the one sampling it. Give one and it plays both roles. Both must share a source clock.
- **Edge lists** number the edges of the launch clock. A bare number is the n-th edge of any polarity from 0; `<cycle>P` / `<cycle>N` is the rising/falling edge of a cycle, starting at cycle 1:

  ```
            ___     ___     ___
  clk   ___/   \___/   \___/   \___
          0   1   2   3   4   5
          0   1P  1N  2P  2N  3P
  ```

  Lists say where the waveform *changes*: `-high_edges` / `-low_edges` for single-bit control (goes high / goes low there), `-data_edges` for a bus (new data value there), `-hiz_edges` (turns high impedance), `-unknown_edges` (becomes X). A signal usually starts with an edge `0` entry that sets its initial state.
- **Delays** draw the transition windows: `-rclk_inputdly_max/min` for the rising clock edge, `-fclk_...` for the falling one (outputs: `-rclk_outputdly_max/min`). Which edge they refer to depends on `-specify`: internal input delays and external output delays hang on the *capturing* edge (setup/hold, counted backwards from it), external input delays and internal output delays run forward from the *launching* edge named in the edge lists. `-rclk_oedly_*` is the output-enable delay for hi-Z transitions.
- `-specify external` means the delays are interface requirements (like SDC `set_input_delay`); `internal` (default) means STA-extracted path delays, and `-rclk_latency_*` / `-fclk_latency_*` add the capturing flip-flop's clock latency.
- A gated clock's edges are numbered over its *drawn* pulses, so a signal referencing it follows the enabled burst.

## Other objects

- **Derived signals** compute a waveform from others: `create_logic -name en -op and -inputs {a b} -visible`, `create_sampled -name q -source d -clock clk -edge rising -setup {$Tsu} -hold {$Th} -visible` (a setup/hold violation shows as X).
- **Timing markers** measure between two waveform elements by their uid (`create_timing_marker -name tSU -from start:uid_1_3 -to start:uid_2_1`). The uids are in the script that `write_script -file {...} -copy` writes (`-use_uid` on each signal, elements numbered from it), so read that file to find them.
- **Annotations** and **splits**: `create_waveform_annotation -on <object> -text {...}`, `create_waveform_split ...`. `create_pwl` draws an analog trace from a PWL file; `create_value_marker` labels a value on it.
- **Layout**: `move_signal`, `set_attribute -signal <name> -name <attr> -value {...}`, `set_canvas_scale`, `set_window_size`, `redraw`.
- **Output**: `export_canvas -file {/abs/path.png|svg|pdf}` (what the user sees, cropped; use it to check your work), `write_sdc -file {...}` (constraint starting point).
- **Removal**: `remove -signal {uid ...}`, `-timing_var {name ...}`, `-tmarker`, `-annotation`, `-split`; `remove -all` clears everything.

## Common mistakes

- Forgetting `-visible`: the signal exists but is not drawn.
- Using a timing variable before `set_app_var` defined it: "can't read" error. Define variables first.
- Mixing units, or writing a bare expression without braces so your shell or the client evaluates it.
- Referencing a clock that does not exist yet: create clocks before the signals that use them, and a master before its generated clock.
- Sending `remove -all` on a diagram the user is working on.
