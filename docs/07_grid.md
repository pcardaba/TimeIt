# How to show the background grid

The background grid helps align timing markers and visually read signal timing relationships.

## Enabling the grid

### Via the menu

**View → Grid** (or **View → Show Grid**) toggles grid visibility.

> **TODO:** Confirm exact menu path and add a screenshot showing the grid enabled on the canvas.

### Via the TCL console

> **TODO:** Confirm the exact settings key and document the command here.

```tcl
# Example (confirm exact setting name):
settings set canvas.grid.visible true
```

## Grid settings

Grid spacing and appearance are configurable through the Grid Settings dialog:

**View → Grid Settings…** (or **Edit → Grid Settings…**)

> **TODO:** Add screenshot of the Grid Settings dialog identifying each option.

Typical options include:

| Setting | Description |
|---|---|
| Spacing | Distance between grid lines in pixels or time units |
| Color | Grid line colour |
| Style | Solid, dashed, or dotted lines |

> **TODO:** Confirm available options against `classes/gridsettingsdlg.py` and update the table.

## Example

> **TODO:** Add a before/after screenshot pair showing the canvas without and with the grid enabled.

---

*Previous: [How to save and load](06_save_load.md) | Next: [How to export the canvas](08_export.md)*
