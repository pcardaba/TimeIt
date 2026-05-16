# How to copy a signal

Copying a signal lets you duplicate an existing waveform definition as the starting point for a similar signal, avoiding the need to retype all parameters.

## Via the canvas context menu

1. **Right-click** on the signal label or waveform row you want to copy.
2. Select **Copy** (or **Duplicate**) from the context menu.
3. The copied signal appears below the original with an auto-generated name.
4. Rename and modify it as needed (see [How to modify a signal](13_modify_signal.md)).

> **TODO:** Add annotated screenshot showing the right-click context menu with Copy highlighted.

## Via the TCL console

The most reliable way to copy a signal is to retrieve and re-issue its definition with a new name. You can read the current signal definition with:

> **TODO:** Confirm whether a `get_signal` or similar introspection command exists, and document it.

A manual copy workflow:

1. Open the saved `.tcl` file in a text editor.
2. Duplicate the relevant `create_clock` / `create_input` / `create_output` line.
3. Change the `-name` parameter.
4. Source the modified file or paste the new command into the console.

## Tips

- After copying, use the **Edit signal dialog** (double-click the signal label) or re-issue the create command with updated parameters to differentiate the copy.
- If you only want to change the colour or amplitude of a copy, the `-color` and `-amplitude` flags on the create command are the quickest path.

---

*Previous: [How to create timing annotations](09_annotations.md) | Next: [How to move a signal](11_move_signal.md)*
