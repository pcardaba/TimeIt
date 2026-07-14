# Changelog

All notable changes to TimeIt are documented in this file.

This changelog starts at v2.0.0. For earlier releases, see the git history.

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
