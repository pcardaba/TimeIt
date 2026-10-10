# How to scale waveform canvas

The waveform canvas is scaled and scrolled with the mouse wheel, the **View** menu or the keyboard.

## Scaling (x-axis only)

Scaling is only supported along the **x-axis** (time axis). It is not possible to scale the canvas vertically.

| Action | Menu entry | Effect |
|--------|------------|--------|
| **Shift + Mouse Wheel up** | **View → Scale Up** | Zoom in (expand the time axis) |
| **Shift + Mouse Wheel down** | **View → Scale Down** | Zoom out (compress the time axis) |
| **Ctrl + F** | **View → Scale Fit** | Adjust the time scale so that the whole diagram fits the visible canvas |

**Scale Fit** fits everything that is drawn (waveforms, timing marker labels, grid) to the current width of the canvas and leaves the right padding of the settings (`settings.waveform.right_padding`) free. After resizing the window, use it again to fill the new width.

The scale is a view setting: it is saved with the diagram (`set_canvas_scale`), but changing it is neither an undo step nor an unsaved change.

## Scrolling along the time axis (x-axis)

When the diagram is wider than the canvas, a horizontal scroll bar appears below it. The diagram can also be scrolled with the keyboard:

| Action | Effect |
|--------|--------|
| **Left arrow** | Scroll towards the beginning of the diagram |
| **Right arrow** | Scroll towards the end of the diagram |

Each key press scrolls a tenth of the visible width; keep the key pressed to scroll continuously.

> **Note:** While a command is being typed in the TCL console the arrow keys move the text cursor of the command line instead. They scroll the canvas as long as the command line is empty.

## Scrolling (y-axis)

The canvas can be scrolled vertically to reveal signals that are outside the visible area.

| Action | Effect |
|--------|--------|
| **Mouse Wheel up** | Scroll canvas up |
| **Mouse Wheel down** | Scroll canvas down |

---

*Previous: [How to see command help notices](15_command_help.md) | Next: [How to use timing variables](17_timing_vars.md)*
