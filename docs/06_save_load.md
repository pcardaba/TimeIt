# How to save and load

TimeIt diagrams are stored as plain TCL script files. Any diagram you build in the console is fully reproducible by re-running the same script.

## Saving

### Via the menu

**File → Write Script...** writes the current diagram state to a `.tcl` file.

![TimeIt write scrip](screenshots/write_script.png)

It is also possible to save by using <kbd>Shift-s</kbd>. Current TimeIt waveform file is shown in windows title bar.

![TimeIt current file](screenshots/current_file.png)

### Via the TCL console

> ⚠️ **Warning:** There is no TCL command associated to **Write Script...** yet


## Loading

### Via the menu

**File → Load Script…** opens a file chooser. Select a previously saved `.tcl` file; TimeIt will execute it and reconstruct the diagram.

### Via the TCL console

You can source any TCL file from the console:

```tcl
source "my_diagram.tcl"
```

## Tips

- Because the save format is plain TCL, you can edit diagram files in any text editor.
- TCL variables (e.g. `set Fclk 100e6`) placed at the top of the file act as parameters — change a single variable to update all signals that reference it.
- Keep scripts under version control (git) to track diagram history.

---

*Previous: [How to create timing markers](05_timing_markers.md) | Next: [How to show the background grid](07_grid.md)*
