# How to move a signal

Signals can be reordered vertically in the canvas to arrange the diagram in a logical reading order.

## Via the canvas context menu


![TimeIt waveform up down](screenshots/waveform_updown.png)

1. **Right-click** on the signal label or waveform row you want to move.
2. Select **Move Up** or **Move Down** from the context menu.
3. Repeat until the signal is in the desired position.

## Via drag-and-drop

> ⚠️ **Warning:** Moving signal strips by drag-and-drop is not implemented yet.

## Via the TCL console

There is no command associated to move up/down action. Signals are displayed in the order they are created. Signals shall be created in the script in the same order the user wants them to appear. 

## Tips

- Moving a signal up or down also moves all of its timing markers and annotations that are anchored to it.
- The order of signals in the canvas reflects the order they appear in the saved `.tcl` file — you can also reorder them by editing the file directly.

---

*Previous: [How to copy a signal](10_copy_signal.md) | Next: [How to delete a signal](12_delete_signal.md)*
