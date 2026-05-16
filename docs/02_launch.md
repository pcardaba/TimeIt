# How to launch TimeIt

## Running from the command line

From the TimeIt root directory, run:

```bash
python main.py
```

This opens the main application window containing the waveform canvas and the TCL console.

## Application layout overview

> **TODO:** Add annotated screenshot of the main window identifying the following areas:
> 1. Waveform canvas (top area)
> 2. TCL console / command entry (bottom area)
> 3. Signal list / labels (left column)
> 4. Menu bar

## Loading a script at startup

You can pass a TCL script file as an argument to pre-populate the canvas:

```bash
python main.py my_diagram.tcl
```

> **TODO:** Confirm startup argument syntax with the actual `main.py` argument parser.

---

*Previous: [Installation](01_install.md) | Next: [How to create clock signal(s)](03_clock_signal.md)*
