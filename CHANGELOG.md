# Changelog

All notable changes to TimeIt are documented in this file.

This changelog starts at v2.0.0. For earlier releases, see the git history.

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
