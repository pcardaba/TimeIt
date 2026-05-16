# How to delete a signal

Deleting a signal removes its waveform, all associated annotations, and all timing markers that reference it.

## Via the canvas context menu

1. **Right-click** on the signal label or waveform row you want to delete.
2. Select **Delete** from the context menu.
3. A confirmation dialog appears — click **OK** to confirm.

> **TODO:** Add annotated screenshot showing the right-click context menu with Delete highlighted, and the confirmation dialog.

> **Note:** If the signal is referenced by a timing variable used in other signals, a warning is shown before deletion to prevent silent breakage.

## Via the TCL console

Use the `remove` command:

```tcl
remove -name signal_name
```

> **TODO:** Confirm the exact command name and syntax against `classes/tclremove.py` and update above.

### Remove all signals

```tcl
remove -all
```

> **TODO:** Confirm this syntax.

## What gets deleted

When a signal is deleted:

- Its waveform is erased from the canvas.
- All waveform annotations attached to its elements are removed.
- All timing markers that reference any of its elements are removed.
- If the signal name was used as a TCL variable (e.g. a named timing marker referencing it), that variable is unset from the console.

## Tips

- Deletion is **not undoable** in the current version — save your diagram before making large structural changes.
- To temporarily hide a signal without deleting it, use the **visibility** toggle instead (see [How to modify a signal](13_modify_signal.md)).

---

*Previous: [How to move a signal](11_move_signal.md) | Next: [How to modify a signal](13_modify_signal.md)*
