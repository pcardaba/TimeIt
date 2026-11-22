# How to modify a signal

There are two ways to modify an existing signal: the graphical edit dialog and re-issuing the create command from the TCL console.

---

## Method 1 — Edit dialog (GUI)

![TimeIt edit signal](screenshots/edit_signal.png)

1. <kbd>Double-click</kbd> the signal label on the left side of the canvas, or <kbd>Right-click</kbd> it and pick **Edit Signal**.  
   The signal edit dialog opens, pre-populated with the current signal parameters.
2. Update the fields you want to change.
3. Click **Ok** (or **Apply**) to redraw the signal with the new values.

Changing the **Name** in the dialog does not rename the signal: it creates a copy under the new name (see [How to copy a signal](10_copy_signal.md)).

---

## Method 2 — Re-issue the create command (TCL console)

Re-running `create_clock`, `create_input`, `create_output`, `create_inout`, `create_pwl`, `create_logic` or `create_sampled` with the **same** `-name` updates the signal in place. For a logic or sampled signal, `set_attribute` also accepts the operator, the inputs, the source, the clock and the timings (see `set_attribute -help`).

```tcl
# Change the clock colour and amplitude
create_clock -name clk \
             -period {10} \
             -color green \
             -amplitude 50 \
             -visible

# Change input delays
create_input -name data_i \
             -launch_clock clk \
             -specify internal \
             -rclk_inputdly_max {4.0} \
             -rclk_inputdly_min {1.5} \
             -data_edges {1P 2P} \
             -visible
```

---

## Visibility toggle

To show or hide a signal without deleting it:

- **GUI:** Open the signal dialog (<kbd>Double-click</kbd> the signal label on the left side of the canvas, or <kbd>Right-click</kbd> it and pick **Edit Signal**) and uncheck **Visible** in its **Signal** frame.
- **Console:** Re-issue the create command with or without the `-visible` flag.

To show hidden signals in the canvas again:

![TimeIt hidden signal](screenshots/hidden_signals.png)

1. <kbd>Right-click</kbd> anywhere in the canvas.
2. Open the cascade menu **Hidden Signals**: it lists the hidden signals (it is greyed out when there is none).
3. Click on the signal name to make it visible again.

---

## Common modifications

| Goal | How |
|---|---|
| Change colour | `-color green` (or other colour) in the create command |
| Change amplitude | `-amplitude 60` in the create command |
| Change line width | `-lwidth 3` in the create command |
| Change period (clock) | `-period {new_expr}` in the create command |
| Change edge list (input/output) | Update `-data_edges`, `-hiz_edges`, etc. |
| Rename a signal | Delete it and re-create with the new name (rename-in-place is not currently supported) |

---

*Previous: [How to delete a signal](12_delete_signal.md) | Next: [How to lay out signals in the canvas](14_layout.md)*
