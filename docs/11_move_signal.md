# How to move a signal

Signals can be reordered vertically in the canvas to arrange the diagram in a logical reading order.

## Via the canvas context menu

1. **Right-click** on the signal label or waveform row you want to move.
2. Select **Move Up** or **Move Down** from the context menu.
3. Repeat until the signal is in the desired position.

> **TODO:** Add annotated screenshot showing the right-click context menu with Move Up / Move Down highlighted.

## Via drag-and-drop

> **TODO:** Confirm whether drag-and-drop reordering is supported and document the gesture here.

1. Click and hold the signal label on the left side of the canvas.
2. Drag it to the target position in the signal list.
3. Release to drop it.

## Via the TCL console

> **TODO:** Confirm whether a `move_signal` or `reorder` TCL command exists and document it.

```tcl
# Example (confirm exact command):
move_signal -name data_i -after clk
```

## Tips

- Moving a signal up or down also moves all of its timing markers and annotations that are anchored to it.
- The order of signals in the canvas reflects the order they appear in the saved `.tcl` file — you can also reorder them by editing the file directly.

---

*Previous: [How to copy a signal](10_copy_signal.md) | Next: [How to delete a signal](12_delete_signal.md)*
