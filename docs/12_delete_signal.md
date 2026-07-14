# How to delete a signal

Deleting a signal removes its waveform, all associated annotations, and all timing markers that reference it.

## Via the canvas context menu

1. **Right-click** on the signal label or waveform row you want to delete.
2. Select **Delete** from the context menu.

> ⚠️ **Warning:** Beware that not confirmation dialog will appear to confirm waveform deletion.

> ⚠️ **Warning:** Special attention shall be taken when removing clock signals. When deleting a clock signal, all signals that refer to will also be removed. No confirmation dialog will appear.

## Via the TCL console

The `remove` command deletes objects from the diagram.

### Remove a signal

A signal is removed by the **uid** it was created with (the `-use_uid` option of `create_clock`, `create_input` and `create_output`):

```tcl
# Example:
remove -signal {2}
remove -signal {2 5}
```

### Remove other objects

The same command removes the other objects of the diagram, and the options may be combined in a single command:

```tcl
# Example:
remove -tmarker {0 1}                 ;# timing markers, by uid
remove -split {0}                     ;# waveform splits, by uid
remove -annotation {uid_2_11}         ;# an annotation, by the element it annotates
remove -timing_var {tSU tHO}          ;# timing variables, by NAME
remove -signal {2}  -tmarker {0}      ;# combined
```

An unknown uid (or timing variable name) is reported in the console, and the other objects are still removed. Run `remove -help` for the full syntax.

### Remove everything

```tcl
remove -all
```

This is the quickest way to clear all and start over with an empty canvas: it erases the signals, timing markers, waveform splits, annotations **and** timing variables. It is also the command every saved script starts with, so loading a diagram never inherits anything from the one it replaces.

## What gets deleted

When a signal is deleted:

- Its waveform is erased from the canvas.
- All waveform annotations attached to its elements are removed.
- All timing markers that reference any of its elements are removed.
- If the signal name was used as a TCL variable (e.g. a named timing marker referencing it), that variable is unset from the console.

## Tips

- A deletion done from the GUI is **undoable**: press **Ctrl-Z** (Edit → Undo) to bring the signal back, with its markers and annotations. A `remove` command typed in the console is not undoable.
- To temporarily hide a signal without deleting it, use the **visibility** toggle instead (see [How to modify a signal](13_modify_signal.md)).

---

*Previous: [How to move a signal](11_move_signal.md) | Next: [How to modify a signal](13_modify_signal.md)*
