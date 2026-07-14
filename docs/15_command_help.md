# How to see command help notices

Every TCL command in TimeIt has a built-in help notice that describes its syntax, options, and examples.

## Getting help for a specific command

Add the `-help` flag to any command in the TCL console:

```tcl
create_clock -help
create_input -help
create_output -help
create_timing_marker -help
create_waveform_annotation -help
```

The help text is printed directly in the console output area.

![TimeIt help](screenshots/help.png)


## Listing all available commands

The `help` command, used alone, lists the commands TimeIt adds to the TCL interpreter:

```tcl
# Example:
help
```

Only the command names are listed. To read the help notice of one of them, pass its name to `help`:

```tcl
# Example:
help create_clock
```

This is exactly equivalent to `create_clock -help`.

## The command log

The console pane is not only for the commands you type: **every GUI action that has an equivalent TCL command runs that command through the console, and the command is logged in the pane**, prefixed with `%` exactly like a typed one.

So creating a clock from the dialog, adding a split, timing two edges, deleting a signal, changing a setting or a timing variable, exporting the canvas or loading a script all leave a line behind:

```tcl
% create_clock -name clk -topology source -period {10} -rise_at {0} -fall_at {5} -visible -show 4
% create_waveform_split -at 25.0
% create_timing_marker -from start:uid_0_0 -to end:uid_0_1
% remove -signal {1}
```

This makes the pane a trace of the session. You can use it to see how something was done, to press **Up-arrow** in the command line to recall and re-run a past action, or to recover work after a crash: the log is also written to `classes/timeit_commands.log`, without the `%` prefix, so that file is a valid script you can `source` back to rebuild the diagram.

Every GUI action that changes the diagram is logged. The only actions that are not are the ones that change nothing in it — zooming the canvas and resizing the window — and those are saved with the diagram anyway.

## Tips

- The `-help` flag works even if other mandatory arguments are missing — you do not need to fill in a full command just to read its help.
- The same help text is stored as plain `.txt` files in the `data/` directory of the TimeIt installation, so you can also read them in any text editor.

---

*Previous: [How to lay out signals in the canvas](14_layout.md) | Next: [How to scale waveform canvas](16_scale_canvas.md) | Back to [Introduction](00_introduction.md)*
