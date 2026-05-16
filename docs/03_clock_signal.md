# How to create clock signal(s)

Clock signals are the timing reference for every other signal in the diagram. Use the `create_clock` command in the TCL console.

## Command syntax

```
create_clock  -name clock_name
              [-topology (clockin)|clockout|clockinout]
              -period {period_expr}
              [-rise_at {rise_edge_expr}]
              [-fall_at {fall_edge_expr}]
              [-rise_uncertainty {rise_unc_expr}]
              [-fall_uncertainty {fall_unc_expr}]
              [-input_dly {input_delay}]
              [-output_dly {output_delay}]
              [-color (black)|green|red|blue|orange|purple]
              [-amplitude amp_value]
              [-lwidth line_width]
              [-visible]
              [-show num_cycles]
              [-help]
```

## Key parameters

| Parameter | Description |
|---|---|
| `-name` | **Mandatory.** Unique name for the clock signal. |
| `-topology` | `clockin` (default): external clock feeding the interface. `clockout`: internal clock going out. `clockinout`: internal clock feeding both port and capture FFs. |
| `-period` | **Mandatory.** Clock period expression (e.g. `{10}` for 10 ns). |
| `-rise_at` | Rising edge time. Default: `0`. |
| `-fall_at` | Falling edge time. Default: `period/2`. |
| `-rise_uncertainty` | Peak-to-peak rising edge uncertainty. Default: `0`. |
| `-fall_uncertainty` | Peak-to-peak falling edge uncertainty. Default: `0`. |
| `-show` | Number of clock cycles to display. |
| `-color` | Waveform colour: `black` (default), `green`, `red`, `blue`, `orange`, `purple`. |
| `-amplitude` | Waveform height in pixels (default 40). |
| `-lwidth` | Line width in pixels (default 2). |
| `-visible` | Include flag to make the signal visible immediately. |

## Step-by-step example

### 1. Simple 10 ns clock

Type in the TCL console:

```tcl
create_clock -name clk -period {10} -visible
```

> **TODO:** Add screenshot showing the command entered in the console and the resulting clock waveform on the canvas.

### 2. Clock defined by frequency variable

```tcl
set Fclkout 100e6
create_clock -name clkout \
             -topology clockout \
             -period {1e9/$Fclkout} \
             -rise_at 0 \
             -fall_at {1e9/(2*$Fclkout)} \
             -visible
```

> **TODO:** Add screenshot.

### 3. Clock with edge uncertainty

```tcl
create_clock -name clk \
             -period {10} \
             -rise_uncertainty {0.2} \
             -fall_uncertainty {0.2} \
             -visible
```

> **TODO:** Add screenshot showing the uncertainty shading on the edges.

## Notes

- All timing values must use the same unit consistently (e.g. always ns or always ps).
- TCL variable expressions are enclosed in `{}` so that they are evaluated lazily by the TCL engine.
- Run `create_clock -help` in the console for the full built-in reference.

---

*Previous: [How to launch TimeIt](02_launch.md) | Next: [How to create input/output signal(s)](04_io_signals.md)*
