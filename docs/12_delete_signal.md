# How to delete a signal

Deleting a signal removes its waveform, all associated annotations, and all timing markers that reference it.

## Via the canvas context menu

1. **Right-click** on the signal label or waveform row you want to delete.
2. Select **Delete** from the context menu.

> ⚠️ **Warning:** Beware that not confirmation dialog will appear to confirm waveform deletion.

> ⚠️ **Warning:** Special attention shall be taken when removing clock signals. When deleting a clock signal, all signals that refer to will also be removed. No confirmation dialog will appear.

## Via the TCL console

> ⚠️ **Warning:** Current `remove` command implementation can not remove signals individually. It is not yet decided if that capability will be implemented in the future. Only `remove -all` (to erase all) is supported. 

### Remove all signals

```tcl
remove -all
```

This is the the quickest way to clear all and start over with an empty canvas.

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
