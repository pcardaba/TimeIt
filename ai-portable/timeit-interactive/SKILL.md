---
name: timeit-interactive
description: Drive TimeIt, the digital-hardware timing-diagram editor, from natural language by sending its Tcl commands over the socket console that scripts/timeit_socket.tcl opens. Use this skill whenever the user wants a timing diagram, waveform, clock/data/setup-hold drawing, bus or protocol diagram (SPI, I2C, DDR, JTAG, memory interfaces, chip I/O timing) created, modified, exported or explained in TimeIt, mentions TimeIt or a .tcl diagram script, or asks to connect to, start, or talk to a running TimeIt — even if they do not say "socket" or "Tcl".
---

# TimeIt interactive

TimeIt is a desktop editor for digital-hardware timing diagrams (clocks, inputs, outputs, buses, setup/hold windows, timing markers). It is driven entirely by an embedded Tcl console: every diagram *is* a script of `create_*` / `set_*` commands, and the GUI is a front-end over that console. When TimeIt has sourced `scripts/timeit_socket.tcl`, that console is also served on a TCP port, so you can build and edit the user's diagram by sending commands, and the user watches the result appear in the TimeIt window in real time. Everything you send is echoed in their console history, exactly as if they had typed it.

Project: https://github.com/pcardaba/TimeIt (GPL-3.0). Full user guide: https://github.com/pcardaba/TimeIt/tree/main/docs

## 1. Connect

Use the bundled client; it finds the server, sends each command with its newline, waits for the `% ` prompt, and prints the reply as the user's history pane shows it.

```bash
python3 scripts/timeit_client.py --probe                     # -> 127.0.0.1:7777 (or the fallback port)
python3 scripts/timeit_client.py 'help'                      # one command
python3 scripts/timeit_client.py 'cmd one' 'cmd two'         # several, in order
python3 scripts/timeit_client.py --file diagram.tcl          # a whole script
```

Paths are relative to this skill's directory. Exit status 1 means a reply contained an `Error:` line, 2 means no server was reachable.

If the probe finds nothing, TimeIt is either not running or has not sourced the socket script. Two ways forward:

- Ask the user to type `source /path/to/TimeIt/scripts/timeit_socket.tcl` in TimeIt's console (not File → Load Script, which would make the script the "current file" and let Ctrl+S overwrite it). The history pane then prints `timeit_socket: listening on 127.0.0.1:<port>`.
- If you run on the same machine as the user's display and have the TimeIt source tree, start it yourself in the background: `python3 scripts/timeit_serve.py --timeit-dir /path/to/TimeIt &` prints `listening on 127.0.0.1:<port>` once up. Say that you are opening a TimeIt window.

The default port is 7777; when busy, the server takes the next free one up to 7786, which is why the client probes that range. For a TimeIt on another machine pass `--host` (the server must have been started bound to 0.0.0.0 there; see the header of `timeit_socket.tcl`).

You can also talk to the server without the client (`nc localhost 7777`, or a socket in any language): plain text, one command per line, flush after each newline, reply ends with `% ` and a held multi-line block answers `> `. `exit` closes your connection, not TimeIt.

## 2. Learn the tool from the tool

Do not guess option names: the command set evolves, and TimeIt documents itself. Ask it:

```
help                    lists every TimeIt command
help create_clock       full notice of one command (same as: create_clock -help)
```

Read the notice of a command before using it for the first time in a session. Each notice has the syntax, every option with its meaning and default, and worked examples that are valid input. For the concepts behind the options (the edge notation, launch/capture clocks, internal vs external delays, timing variables) read `references/quickstart.md` in this skill once per session, then go to the online guide for depth:

| Need | Read |
|---|---|
| Concepts and vocabulary | docs/00_introduction.md |
| Clocks, generated and gated clocks | docs/03_clock_signal.md |
| Inputs and outputs, delays, edge lists | docs/04_io_signals.md |
| Timing markers (measurements) | docs/05_timing_markers.md |
| Parametric diagrams with timing variables | docs/17_timing_vars.md |
| Annotations, splits, layout | docs/09_annotations.md, docs/14_layout.md |
| Logic/sampled (derived) signals | docs/21_logic_signals.md |
| Analog PWL traces, value markers | docs/20_pwl_signals.md |
| Export, SDC generation | docs/08_export.md, docs/18_write_sdc.md |
| The socket console itself | docs/22_socket.md |

All under https://github.com/pcardaba/TimeIt/tree/main/docs (raw: https://raw.githubusercontent.com/pcardaba/TimeIt/main/docs/<file>). The example diagrams in https://github.com/pcardaba/TimeIt/tree/main/scripts are complete, loadable scripts and the best templates for a protocol the user names (SPI, I2C, JTAG, SWD, QSPI).

## 3. Build the diagram

The order matters because expressions are resolved when a command runs:

1. **Timing variables first**: `set_app_var -name timings.Tclk -value {10} -desc {clock period}`. Every later timing expression can use `$Tclk`. Prefer variables over literal numbers: the user can then retune the diagram from Edit → Timings, and they are the only variables saved with the diagram. Keep one time unit throughout (ns by default).
2. **Clocks**: `create_clock -name clk -topology source -period {$Tclk} -rise_at {0} -fall_at {$Tclk/2} -show 8 -visible`. Generated clocks (`-topology clockout -master clk -divide_by 2`) and gated clocks come after their master.
3. **Inputs and outputs** referenced to a clock: `create_input -name d -launch_clock clk -high_edges {2P} -low_edges {0 5P} -visible`. Buses use `-data_edges`, hi-Z `-hiz_edges`, unknown `-unknown_edges`. Delays (`-rclk_inputdly_max` …) draw the transition windows.
4. Then derived signals, annotations, splits, timing markers.

Practical points that save round trips:

- Timing expressions go in braces: `{$Tclk/2}`. Braces also delay evaluation to TimeIt's interpreter, which is what you want.
- A signal is hidden unless `-visible` is given.
- Re-running `create_*` with the same `-name` updates that signal; `set_attribute -signal <name> -name <attr> -value {...}` changes one attribute. `remove -signal {<uid...>}` deletes; `remove -all` wipes the whole diagram, so only send it when starting a diagram from scratch and the user agrees.
- Replies are the console's output: an empty reply means success for `create_*`. An `Error:` line names the option or object at fault; fix and resend that command only.
- Multi-line commands work (the server assembles a block until braces balance), but one command per client argument is easier to debug.
- Commands sent through the socket are not undo steps in the GUI, same as typed ones.

## 4. Check the result and hand over

- **Look at it**: `export_canvas -file /tmp/timeit_check.png` writes what the user sees (relative paths resolve from TimeIt's launch directory, so use an absolute path). View the image to verify edges, delays and labels before telling the user it is done. SVG and PDF are available for deliverables.
- **State**: `write_script -file /tmp/timeit_state.tcl -copy` writes the complete diagram as a script without touching the user's current file. Read it to learn what is already there (names, uids, timing variables, settings) before editing a diagram the user opened, and to confirm what you changed. A saved script starts with `remove -all` and reloads with File → Load Script or `source`.
- **Saving**: `write_script -file {/path/name.tcl}` saves and makes that the current file (the window title shows it, and Ctrl+S saves there from then on), and a bare `write_script` rewrites the current file like Ctrl+S. Ask where the user wants the diagram before choosing a path; use `-copy` when you only need a snapshot for yourself.
- SDC constraints: `write_sdc -file {...}` produces a starting point only; say so.

## Example

User: "Draw an SPI mode 0 write of one byte, 10 MHz SCLK, chip select active low."

```bash
python3 scripts/timeit_client.py \
 'set_app_var -name timings.Tsclk -value {100} -desc {SCLK period, 10 MHz}' \
 'create_clock -name sclk -topology source -period {$Tsclk} -rise_at {0} -fall_at {$Tsclk/2} -show 10 -visible' \
 'create_input -name cs_n -launch_clock sclk -high_edges {0 18} -low_edges {1} -visible' \
 'create_input -name mosi -launch_clock sclk -hiz_edges {0} -data_edges {1 3 5 7 9 11 13 15} -unknown_edges {17} -visible' \
 'export_canvas -file /tmp/spi_check.png'
```

Then view `/tmp/spi_check.png`, adjust (for instance the edge numbers if the data should change on falling edges, per the mode), and tell the user what was drawn and that Ctrl+S saves it.
