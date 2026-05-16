# How to lay out signals in the canvas (waveform settings)

The Waveform Settings (or Timings Settings) dialog controls the global layout of all signals on the canvas: padding, slot height, inter-signal spacing, font, and more.

## Opening the settings dialog

**Edit → Waveform Settings…** (or **Edit → Timings Settings…**)

> **TODO:** Confirm the exact menu path and add a screenshot of the menu item highlighted.

## Settings overview

> **TODO:** Add an annotated screenshot of the full Waveform Settings dialog.

### Spacing and padding

| Setting | Description |
|---|---|
| `top_padding` | Vertical space above the first signal row (px) |
| `interslot` | Vertical space between consecutive signal rows (px) |
| `left_margin` | Horizontal space reserved for signal labels (px) |

### Waveform appearance

| Setting | Description |
|---|---|
| `default_amplitude` | Default signal height in pixels |
| `default_lwidth` | Default line width in pixels |
| `font.family` | Font used for signal names and annotations |
| `font.size` | Font size for signal names |

### Canvas dimensions

| Setting | Description |
|---|---|
| `canvas_width` | Total width of the waveform canvas (px) |
| `canvas_height` | Total height of the waveform canvas (px) |

> **TODO:** Verify all setting names against `classes/settingsdlg.py` and `classes/settings.py` and update the tables above.

## Applying settings via the TCL console

Settings can also be changed programmatically:

```tcl
# Example (confirm exact syntax):
settings set waveform.top_padding 20
settings set waveform.interslot 10
```

> **TODO:** Confirm the TCL `settings` command syntax.

## Tips

- Increase `interslot` to create more breathing room between signal rows, which is helpful when placing timing markers between adjacent signals.
- Changing `top_padding` while using anchored timing markers (see [Timing markers](05_timing_markers.md)) keeps markers aligned with their signals automatically.
- After changing layout settings, all signals are redrawn — there is no need to re-source the script.

---

*Previous: [How to modify a signal](13_modify_signal.md) | Next: [How to see command help notices](15_command_help.md)*
