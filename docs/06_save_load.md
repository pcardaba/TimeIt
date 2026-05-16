# How to save and load

TimeIt diagrams are stored as plain TCL script files. Any diagram you build in the console is fully reproducible by re-running the same script.

## Saving

### Via the menu

**File → Save** (or **File → Save As…**) writes the current diagram state to a `.tcl` file.

> **TODO:** Add screenshot of the File menu with Save highlighted.

### Via the TCL console

> **TODO:** Confirm whether a `save` TCL command is available and document it here.

```tcl
# Example (confirm exact command name):
save "my_diagram.tcl"
```

## Loading

### Via the menu

**File → Open…** opens a file chooser. Select a previously saved `.tcl` file; TimeIt will execute it and reconstruct the diagram.

> **TODO:** Add screenshot of the Open dialog.

### Via the command line at startup

Pass the script path as an argument when launching TimeIt:

```bash
python main.py my_diagram.tcl
```

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
