# How to create clock signal(s)

Clock signals are the timing reference for every other signal in the diagram. Use the `create_clock` command in the TCL console.
Even if you want to create an asynchronous signal you will need a clock to which it will refer. You can create unrelated clocks as references and hide them (they will not be `-visible` in the canvas). 

A clock signal can be created by using the GUI or by using the TCL command `create_clock`

## GUI procedure

![TimeIt create clock](screenshots/create_clocks.png)

1. <kbd>Mouse Right-click</kbd> in the canvas area. Select **New Signal→Clock...**
2. Select the clock topology of your device (if relevant).  
3. Complete the clock description. Not all fields are mandatory (see command documentation).

You can specify timings directly by using floating point numbers, but it is good practise to specify your timings by using timing variables. Timing variables shall be created before calling the `create_clock` form. You can always give numbers and then change to variables later.

More on timing variables here: [How to timing variables](16_timing_vars.md)

**Note:** Time units are specified in the *Waveforms Settings* (**Edit→Settings...**)  

![TimeIt waveform settings](screenshots/waveform_settings.png)

All timing numbers must be consistent with the chosen timing units.

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

### 1. Clock defined by frequency variable

```tcl
set Fclkout 100e6
set Tclkout [expr 1e9/$Fclkout]
create_clock -name clkout \
             -topology clockout \
             -period {$Tclkout} \
             -rise_at 0 \
             -fall_at {$Tclkout/2} \
             -visible
```

![TimeIt create_clock example](screenshots/create_clocks_example.png)

## Notes

- All timing values must use the same unit consistently (e.g. always ns or always ps).
- TCL variable expressions are enclosed in `{}` so that they are evaluated lazily by the TCL engine.
- Run `create_clock -help` in the console for the full built-in reference.

---

*Previous: [How to launch TimeIt](02_launch.md) | Next: [How to create input/output signal(s)](04_io_signals.md)*
