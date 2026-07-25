# How to write an SDC constraint file

The `write_sdc` command turns the input and output signals of the diagram into a **partial** constraint file in SDC (Synopsys Design Constraints) format: `set_input_delay` / `set_output_delay` statements, and `set_multicycle_path` statements whenever a signal's launch and capture clocks differ.

The generated file is an **aid to bootstrap the I/O constraining work, not a ready-to-use constraint deck**: review every statement, complete the deck and rework it to match the real design before using it. A disclaimer comment at the top of the file restates this.

## What gets generated

In order:

1. **A header comment** with the disclaimer and the assumptions the file is built on.
2. **The timing variables** of the diagram, re-declared with plain `set` statements (SDC files are Tcl scripts), so that the delay statements can keep referencing them symbolically.
3. **Commented-out clock templates** — one `create_clock` / `create_generated_clock` line per diagram clock. Clock objects are **not** created by the file: they must exist before the I/O delay statements take effect, and the templates are only a starting point to adapt (in particular the `-source` of a generated clock is a guess).
4. **Per input signal**: `set_input_delay -clock <launch_clock> ...` — one statement per launch edge polarity in use (`-clock_fall` for falling launch edges, `-add_delay` from the second statement on).
5. **Per output signal**: `set_output_delay -clock <capture_clock> ...` — same structure, with `-clock_fall` referring to the capturing edge.
6. **Per signal whose launch and capture clocks differ**: a pair of `set_multicycle_path -setup/-hold` statements anchored to the port (`-from [get_ports ...]` for inputs, `-to [get_ports ...]` for outputs).

Each delay statement is followed by a comment giving the numeric values it resolves to, so the result can be checked against the diagram.

## Assumptions and conversions

- **Clocks are assumed propagated**: clock latency and any other clock network delay are *not* folded into the generated input/output delays.
- **Clock uncertainty is not included** in the delays either: declare it with `set_clock_uncertainty` on the clocks (the diagram uncertainties are recalled in a comment next to the clock templates).
- **External-specify signals** map directly: the given delays *are* the SDC input/output delays.
- **Internal-specify signals** are converted into the equivalent external delays using the launch/capture clock periods and the position of the capturing edge. The conversion is materialized in the file as a small `set <port>_offset_<P|N> <value>` helper variable holding the launch-to-capture edge separation, so the arithmetic stays visible:

  ```tcl
  set data_o_offset_P 40.0
  set_output_delay -clock {SCK} -max [expr {$data_o_offset_P - ($tCOmax)}] -min [expr {-($tCOmin)}] [get_ports {data_o}]
  ```

  Note that the capturing edge of an *internal*-specify output (and of an *external*-specify input) is not modeled by the diagram: it is assumed to be the next capture clock edge of the launch polarity, and the comment above the statement says so.
- **Tri-stated outputs with internal delays** take the worst case of the output and output enable delays (max of the max delays, min of the min delays), so the single `set_output_delay` covers both the data and the enable paths.
- **Multicycle paths**: the setup multiplier is the launch-to-capture separation counted in periods of the faster clock — `-start` when the launch clock is the faster one, `-end` when the capture clock is — and the hold multiplier is the period ratio minus one. Non-integer ratios or separations produce a `WARNING` comment instead of silently wrong numbers.
- **Gated clocks**: signals clocked by a gated clock are constrained from the **free-running (ungated) waveform**. This is what SDC/STA sees anyway — clock definitions are free running, gating removes pulses without moving them, and the tool conservatively assumes all pulses exist (the gating enable path itself is a netlist clock-gating check, not an I/O constraint). Data transfers are assumed to happen while the clock is not gated: **gating must not be used to create multicycle data transfers** (that is bad practice, and the generated multicycle statements deliberately ignore the gating pattern). A `NOTE` comment marks the affected ports.

## What gets skipped

- **Hidden (not visible) signals** are left out.
- Signals whose clocks or delay expressions can not be resolved, and signals with empty edge lists, are skipped, with a warning both in the console and as a comment in the file.

## Writing via the menu

Select **File → Write SDC…**, choose the file name (proposed from the current script name) and save.

## Writing via the TCL console

```tcl
# Write the constraints next to the launch directory
write_sdc -file {constraints.sdc}

# Absolute path
write_sdc -file {/project/synth/timeit_io.sdc}
```

Run `write_sdc -help` for the full syntax.

Writing the SDC does not change the diagram: the command is never written back in a saved script, and it is not undoable (there is nothing to undo).

## Tips

- Declare the delays as **timing variables** (see [How to use timing variables](17_timing_vars.md)): they are re-declared at the top of the generated SDC, so the delay statements stay symbolic and stay in sync when a value changes. Delay expressions referencing plain `set` variables will not resolve in the generated file.
- The `(resolves to ...)` comments under each statement give the numeric values: compare them against the drawn transition windows to validate the export (remember the drawing additionally includes latencies and uncertainties, which the SDC deliberately excludes).

---

*Previous: [How to use timing variables](17_timing_vars.md) | Back to [Introduction](00_introduction.md)*
