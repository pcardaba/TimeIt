# Changelog

All notable changes to TimeIt are documented in this file.

This changelog starts at v2.0.0. For earlier releases, see the git history.

## [Unreleased]

### Added

- **`scripts/timeit_socket.tcl`: a remote console over a TCP socket.** Sourced
  from the console, the script listens on port 7777 (or the next free one, up
  to ten tries; the port bound is reported in the history pane) and turns every
  connection into a TimeIt console: each line received is run as if typed in
  the console, with the same command set, echoed in the history pane and
  written to the command log, and whatever the console prints for it is sent
  back. The local console keeps working alongside. Binds to `127.0.0.1` by
  default; `::timeit_socket::start <port> 0.0.0.0` opens it to other hosts.
  Any program that can open a socket can drive TimeIt this way: `nc`, a script,
  an IDE, or an AI agent. See [Remote console over a socket](docs/22_socket.md).
- **`console_eval <script>`.** Runs a script exactly as a line typed in the
  console (echoed, logged, result or error printed) and returns everything the
  console printed for it. It is the seam the socket script is built on.
- **`write_script [-file {path}] [-copy]`.** Saves the diagram as a script from
  the console: with `-file` the file becomes the current file as File → Write
  Script… does, a bare `write_script` rewrites the current file (Ctrl+S), and
  `-copy` writes a copy leaving the current file alone. Never written back in a
  saved script, not undoable. Also the way a program on the socket reads the
  complete state of the diagram.
- **Utility scripts.** A script whose first line is `# TimeIt utility script`
  is sourced by File → Load Script without becoming the current file and
  without the "clears the diagram" warning, so Ctrl+S can never overwrite it
  with the diagram. `scripts/timeit_socket.tcl` is one.
- **`ai-portable/timeit-interactive/`: a portable agent skill.** A `SKILL.md`
  (Agent Skills format, as read by Claude Code and others) that teaches an AI
  assistant to drive TimeIt through the socket console, learn the command set
  from `help`, and check its work with `export_canvas`, with a bundled
  stdlib-only client (`timeit_client.py`) and a launcher that starts TimeIt
  with the server open (`timeit_serve.py`). See `ai-portable/README.md`.

## [v2.5.0] - 2026-09-13

Signals can now be computed from other signals instead of only being drawn
from a list of edges. Nothing breaks: v2.4.0 scripts load unchanged.

### Added

- **`create_logic -op and|or|xor|nand|nor|not -inputs {sig ...}`.** Combines
  any number of signals, or inverts one, into a new waveform. The operands
  are merged in the time domain rather than snapped to a clock grid, so
  signals launched by different or unrelated clocks combine correctly.
  Unknown propagates through the operator except where a controlling value
  masks it (`0 AND x` is `0`, `1 OR x` is `1`), and the min/max transition
  windows of the operands count as unknown, so the result shows the real
  uncertainty. A hi-Z operand resolves to `1` when it was created
  `-pulled_up` and to unknown otherwise. `-tpd_max` / `-tpd_min` delay the
  result and their spread widens every transition window, like the delays of
  an I/O signal. Clocks, buses and PWL signals are rejected as operands, and
  so is any definition that would close a dependency loop.
- **`create_sampled -source <signal> -clock <clock> [-edge rising|falling]`.**
  Resamples a signal the way a flip-flop does, holding each captured value
  until the next sampling edge. At every edge the source is examined over
  the half-open aperture `[t - setup, t + hold)`: anything other than one
  stable value across the whole aperture captures as unknown and stays
  unknown until the next edge, which is how a setup or hold violation
  appears on the diagram. `-setup`, `-hold`, `-tco_max` and `-tco_min` are
  Tcl expressions defaulting to 0. Sampling on a gated clock holds through
  the suppressed pulses, a bus source may be resampled, and the source may
  itself be a derived signal.
- **Derived signals compose.** Their waveform is expressed exactly like a
  basic signal's, so one can be measured by a timing marker, be annotated,
  or feed another derived signal.
- **Removing a signal a derived signal reads is refused** (`remove -signal`
  and the Delete Signal menu), with a message naming the derived signals to
  remove or edit first. The same rule refuses re-creating such a signal
  under another class. The `move_signal` rules now cover operands as well:
  a derived signal stays below what it reads, so a saved script always
  reloads intact.
- **`set_attribute` understands the derived signals.** `op`, `inputs`,
  `tpd_max`/`tpd_min` of a logic signal and `source`, `clock`, `edge`,
  `setup`/`hold`/`tco_max`/`tco_min` of a sampled signal are resolved and
  validated exactly like the corresponding `create_*` options, so a typo is
  refused instead of dropping the signal at the next redraw.
- **Both are available from the GUI** under **New Signal → Logic…** and
  **New Signal → Sampled…**, with the input or source pre-filled from the
  right-clicked signal, and reopen for editing through **Edit Signal** like
  any other signal. The pickers only offer choices the command would accept.
- See [How to create logic and sampled signals](docs/21_logic_signals.md) and
  the [`logic_example.tcl`](scripts/logic_example.tcl) example.

### Changed

- **Double-clicking a signal name opens its edit dialog**, the same one the
  context menu reaches, for every signal type. Previously a double-click on a
  name did nothing and editing was only reachable through the right-click
  menu. Double-clicking a waveform element still opens its annotation dialog.

### Notes

- Derived signals are omitted from `write_sdc`: they model internal nodes,
  not I/O pins. They can not gate a clock (`-enabled_by` still takes an input
  or output only).

## [v2.4.0] - 2026-09-10

Analog waveforms come to TimeIt: the new `create_pwl` command overlays
piece-wise-linear traces (voltage, current, temperature...) in a single
waveform slot, each with oscilloscope-style scale and offset knobs, and value
markers read back a trace's interpolated value at any point. PWL signals are
documentation only — `write_sdc` ignores them.

Nothing breaks: v2.3.0 scripts load unchanged.

### Added

- **PWL (analog) signals.** `create_pwl -names {...} -files {...}` draws one
  or more piece-wise linear waveforms (voltage, current, temperature...) in a
  single waveform slot, read from two-column text files (time, value) that
  accept time units, engineering notation and SPICE-style SI prefixes
  (`10mV`, `400e-3`, `5MEG`). Every trace is normalized to the slot and has
  its own `color`, `lstyle`, `lwidth`, `scale`, `offset` and `visible`
  attributes (set with `set_attribute` on the trace name), scale and offset
  acting like the vertical knobs of an oscilloscope. **New Signal → PWL (analog)...** is the dialog
  counterpart (up to 5 traces per slot). PWL signals are documentation
  signals: `write_sdc` ignores them. See `docs/20_pwl_signals.md`.
- **Value markers** on PWL traces: right-click a trace and **Add Value
  Marker** to read its interpolated value there (`1.2V`, `120mA`). The label
  can be dragged (a thin line keeps it tied to the marked point) and its text
  edited with a double-click. Saved as `create_value_marker`, removed with
  `remove -vmarker`.
- Ovals (the colored dots of PWL labels and value markers) are now exported
  in every format.

### Changed

- **PWL dialog and value-marker refinements.** The **New Signal → PWL
  (analog)...** form was simplified, and value-marker rendering and their
  `set_attribute` handling were tightened up.

## [v2.3.0] - 2026-08-31

**File → Import VCDs…** reproduces in TimeIt the waveforms of a real HDL (or
gate-level) simulation from a min/max pair of VCD (Value Change Dump, IEEE
1364) files. The imported signals become regular TimeIt clocks, inputs and
outputs that can then be edited, annotated, measured, saved and exported like
any hand-made diagram.

Nothing breaks: v2.2.0 scripts load unchanged.

### Added

- **`File → Import VCDs…`.** Takes two VCD files — a best-case (min delays)
  and a worst-case (max delays) dump of the same stimulus (give the same file
  twice if no min/max spread is wanted). TimeIt parses both, checks their
  consistency (common signals, at least one undistorted periodic clock,
  identical value sequences, every max delay ≥ its min counterpart) and
  normalizes differing `$timescale` units before comparing.
- **Signal characterization dialog.** Lists every common signal with the
  characteristics found and a proposed role — type (`clock` / `input` /
  `output`), clock topology (source vs. generated, with detected derived
  clocks pre-linked to their master), and launch / capture clocks for data
  signals — for review and correction before the import. The detected
  classification and delay ranges are also printed to the console.
- Min/max delay spread is imported as clock uncertainty / delay ranges on the
  resulting signals. See `docs/19_import_vcd.md`.

## [v2.2.0] - 2026-07-25

Generated clocks can now be gated and inverted, and diagrams can bootstrap their
own SDC I/O constraints with the new `write_sdc` command. Several editing and
data-safety rough edges are also smoothed out: timing markers open their edit
dialog on a double-click, unsaved sessions warn before they are discarded, and
your own Tcl variables survive a round trip through **File → Write Script...**.

Nothing breaks: v2.1.0 scripts load unchanged.

### Added

- **`write_sdc -file {path}`.** Generates a partial SDC (Synopsys Design
  Constraints) file from the diagram's input and output signals:
  `set_input_delay` / `set_output_delay` statements (converting internal
  delays to their external equivalent, and taking the worst case of data and
  output-enable delays for tri-stated outputs), plus `set_multicycle_path`
  statements whenever a signal's launch and capture clocks differ. Diagram
  timing variables are re-declared so the statements stay symbolic, and
  diagram clocks are sketched as commented-out `create_clock` /
  `create_generated_clock` templates. Signals clocked by a gated clock are
  constrained from the free-running waveform, as STA assumes. This is what
  **File → Write SDC...** now runs; the generated file is a bootstrap aid,
  not a ready-to-use constraint deck — see
  [Writing an SDC constraint file](docs/18_write_sdc.md).
- **Generated clocks can be gated.** `create_clock -enabled_by
  <enable_signal> [-enable_active high|low]` gates a generated clock with an
  existing input/output signal, the same way a latch-based ICG does: a pulse
  is only emitted when the enable is at its active level at the pulse's
  leading edge, and the clock parks at its idle level while disabled. Edge
  numbering counts only the visible (drawn) edges, so signals referencing the
  gated clock track the enabled burst. Gating can also be set or cleared on
  an existing clock with `set_attribute -name enabled_by`.
- **Generated clocks can be inverted.** `create_clock -invert` complements a
  generated clock — it falls where the direct clock would rise and vice
  versa — with the same semantics as SDC's `create_generated_clock -invert`.
  Combines with either `-edges` or `-divide_by`.
- **`redraw`.** Forces a full repaint of every signal, timing marker, split
  and annotation on both canvases. Only needed after driving the diagram
  from plain Tcl `set` commands that bypass the app's own change tracking.
- **Timing markers open their edit dialog on double-click**, matching every
  other editable diagram element.
- **Unsaved-session warnings.** Loading a script or exiting the application
  while the diagram differs from its last saved/loaded state now asks
  whether to save first, with the load/exit cancellable from the prompt.
  View-only changes (window resize, zoom) do not count as modifications.
- **User Tcl variables survive Write Script.** Plain `set` variables you
  define yourself (in the console or a sourced script) are now re-emitted by
  **File → Write Script...** in a `# --- User variables ---` section ahead of
  anything that could reference them, so `remove -all` at the top of the
  reloaded script no longer drops them.

## [v2.1.0] - 2026-07-14

The console log pane becomes a faithful trace of the session: **every GUI action
that changes the diagram now runs its equivalent TCL command, and that command is
logged in the pane**, exactly as if it had been typed. What the log records is
therefore what actually happened, and `classes/timeit_commands.log` is a valid
script that rebuilds the diagram. Most of this release is the command language
catching up with the GUI, so that no action is left without a command.

Nothing breaks: v2.0.0 scripts load unchanged.

### Added

- **`help`.** `help` alone lists the commands TimeIt adds to the interpreter;
  `help <command_name>` prints that command's help notice, exactly as
  `<command_name> -help` does.
- **`export_canvas`.** Exports the waveform canvas from a script or the console:
  `-file`, `-format (auto)|png|jpg|svg|pdf|ps|eps` (deduced from the file
  extension by default), `-dpi`, `-quality`, `-background`. This is what the
  File→Export Canvas… menu now runs.
- **`move_signal -name <signal> -direction up|down`.** Moves a signal one
  position up or down. Signal order was otherwise implicit in the order the
  `create_*` commands appear in a script, so the Move Up / Move Down menu actions
  had no command. A move that would put a signal above the clocks it refers to
  is refused, in the GUI and in the console alike.
- **In-place update of timing markers and waveform splits.**
  `create_timing_marker` and `create_waveform_split` accept `-use_uid`: when a
  marker or a split already carries that uid it is **updated** instead of a new
  one being created, and the options that are not given keep their current
  value. This is what expresses a restyle, a re-anchor, a rename or a drag as a
  command. Both objects now serialize their uid, so uids survive save/load.
- **`remove -annotation {uid}`** (an annotation is identified by the waveform
  element it annotates, e.g. `uid_2_11`) and **`remove -timing_var {name}`**
  (by name; the variable is also unset in the interpreter).
- **GUI actions are logged.** Creating and editing signals, timing markers,
  splits and annotations; deleting them; reordering signals; un-hiding a signal;
  editing the settings, the grid and the timing variables; exporting the canvas;
  loading a script — each issues its command through the console and echoes it
  with the `%` prefix. Up-arrow recalls a GUI-issued command to re-run or edit
  it. Only the view-only actions (canvas zoom, window resize) are not logged;
  they are saved with the diagram anyway.
- Help notices for `puts`, `set_window_size` and `set_canvas_scale`, which had
  none, so every command TimeIt registers is now documented.

### Changed

- **`remove -all` also clears the timing variables** and the measured values of
  the named timing markers (`settings.marker.timings`). Every saved script starts
  with `remove -all`, so loading a diagram no longer inherits either from the
  diagram it replaces — and no longer saves them back into it. A script that
  relied on its timing variables surviving `remove -all` must set them again
  after it (the generated scripts already do).
- The Settings and Grid dialogs apply their edits through `set_app_var`. The
  Grid dialog issues one command per **changed** setting only.
- Documentation: the command log (`docs/15_command_help.md`), `move_signal`
  (`11_move_signal.md`), `remove` by uid (`12_delete_signal.md`), marker update
  and removal (`05_timing_markers.md`), annotation removal (`09_annotations.md`),
  timing-variable removal (`17_timing_vars.md`). README rewritten.

### Fixed

- The Settings dialog changed a setting in the model without setting the
  corresponding TCL variable in the interpreter; the two could then disagree.
- The **Remove** button of the *User Timings* window raised a `KeyError` when the
  selected row had been added but never given a value.
- `set_canvas_scale -help` and `set_window_size -help` did not print help:
  `-help` was parsed as an argument.
- The Input and Output signal dialogs printed the command they built on the
  terminal's stdout, where a user launching the app from a desktop entry never
  saw it. The command now goes to the log pane, like every other one.

## [v2.0.0] - 2026-07-13

Major release. The clock model of the I/O signals changed: a data path is now
described by the clock that **launches** it and the clock that **captures** it,
instead of by a single reference clock. Diagrams written for v1.x do not load
until they are migrated (see *Migration* below).

### Breaking

- `create_input` / `create_output`: the `-refclock` option is **removed** and
  replaced by `-launch_clock` and `-capture_clock`. Both clocks must be related
  (they must share the same source clock); giving only one of them means the
  same clock launches and captures the data, which is the v1.x behaviour.

### Added

- **Generated clocks.** `create_clock` now creates either a *source* clock
  (topologies `source`, `clockin`, waveform given explicitly) or a *generated*
  clock (topologies `clockout`, `clockinout`, waveform derived from a master
  clock):
  - `-master` : the source clock the clock derives from.
  - `-edges {rise fall cycle_end}` : master clock edges generating this clock,
    with the same semantics as the SDC `create_generated_clock -edges` option.
  - `-divide_by divisor` : shorthand for `-edges {1 divisor+1 2*divisor+1}`.
  - `-output_dly` : delay the clock takes to come out of the interface.
  - `-input_dly` : `clockinout` only, delay of the clock fed back in.
- **Launch/capture rendering.** The capturing edge of a data path is now
  resolved against the capture clock waveform instead of being assumed to be
  half a period (or a period) away on the reference clock. The edge lists
  (`-data_edges`, ...) still always name **launch clock** edges.
- **`remove` by uid.** `remove` now accepts `-signal {uids}`, `-split {uids}`
  and `-tmarker {uids}`, which may be combined in a single command. Removing a
  signal still removes everything depending on it (its timing markers, and the
  clocks/signals derived from it).
- **Delete Split.** A waveform split can be deleted from the canvas context
  menu, by right-clicking on it.
- `remove -help` and `set_app_var -help`, with their `data/*.help.txt` reference
  pages (neither command had one).
- Documentation: *How to use timing variables* (`docs/17_timing_vars.md`).

### Fixed

- Input signals specified with **internal** delays, and output signals specified
  with **external** delays, used the uncertainty of the wrong clock edge when the
  data was launched on one polarity and captured on the other.
- Output signals specified with **internal** delays subtracted the falling clock
  uncertainty twice from the min delay of data launched on a falling edge.
- A timing marker anchored on a signal that could not be drawn crashed the tool
  with an empty Tcl error. The marker is now skipped and the cause is reported in
  the console.
- `set_app_var` cleared the description of a timing variable when its value was
  set again without `-desc`. The description is now kept; pass `-desc {}` to
  clear it.

### Changed

- The Input/Output signal dialogs are more compact and let the launch and the
  capture clock be selected.
- The clock, I/O signal and timing variable documentation was rewritten for the
  new model.
- The example scripts in `scripts/` were migrated to the new options.

### Migration from v1.x

Replace the `-refclock` option of every `create_input` / `create_output` by
`-launch_clock`, which preserves the v1.x behaviour exactly:

```tcl
# v1.x
create_input -name data_i -refclock clk ...

# v2.0.0 (same behaviour: clk both launches and captures)
create_input -name data_i -launch_clock clk ...
```

Give `-capture_clock` as well when the data is captured by a different (related)
clock.
