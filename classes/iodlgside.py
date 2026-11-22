# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2024 Pablo Cardaba

"""The left column of the input, output and bidir signal dialogs.

These dialogs read in the order they are filled in. The left column holds
what belongs to the signal itself: its name and style ("Signal"), then how
its delays are specified, with the illustration of the choice. The right
column holds the clocks, the delays and the launch edge lists. With the
illustration beside the form rather than above it, the dialogs stay short
enough for a laptop screen at 125 or 150 %.
"""

from tkinter import ttk

COLORS = ("black", "green", "red", "blue", "orange", "purple")


def build_side(dlg, checks, delay_text, images, image, choices):
    """Build the left column of `dlg` in its grid (row 1, column 0).

    Uses the tkvars of the dialog: `name_tkvar`, `color_tkvar`,
    `lwidth_tkvar`, `amplitude_tkvar` and `topology_tkvar`, and calls
    `dlg._update_topology` when the delay choice changes.

    checks      (text, BooleanVar) of the check buttons of the Signal frame.
    delay_text  title of the delay choice frame.
    images      every figure the illustration may show.
    image       the figure shown first.
    choices     (text, value) of the radio buttons of the delay choice.

    Returns the label of the illustration, the dialog changes its image.
    """
    side = ttk.Frame(dlg)
    side.grid(row=1, column=0, sticky="nwe", padx=(2, 6), pady=2)
    side.columnconfigure(0, weight=1)
    _build_signal(dlg, side, checks).grid(row=0, column=0, sticky="ew")
    lf_delays, label = _build_delay_choice(dlg, side, delay_text,
                                           images, image, choices)
    lf_delays.grid(row=1, column=0, sticky="ew", pady=(8, 0))
    return label


def _build_signal(dlg, parent, checks):
    """The Signal frame: name and color, line width and amplitude, checks."""
    lf = ttk.Labelframe(parent, text="Signal")
    lf.columnconfigure(1, weight=1)
    lf.columnconfigure(3, weight=1)
    ## -> Row : Name, Color
    ttk.Label(lf, text="Name").grid(row=0, column=0, sticky="e", padx=2)
    ttk.Entry(lf, textvariable=dlg.name_tkvar, width=16).grid(
        row=0, column=1, sticky="w", padx=2, pady=2)
    ttk.Label(lf, text="Color").grid(row=0, column=2, sticky="e", padx=2)
    ttk.Combobox(lf, textvariable=dlg.color_tkvar, values=COLORS,
                 width=10, state="readonly").grid(
        row=0, column=3, sticky="w", padx=2, pady=2)
    ## -> Row : Line width, Amplitude
    ttk.Label(lf, text="Line width").grid(row=1, column=0, sticky="e", padx=2)
    ttk.Spinbox(lf, from_=1, to=20, textvariable=dlg.lwidth_tkvar,
                width=2).grid(row=1, column=1, sticky="w", padx=2, pady=2)
    ttk.Label(lf, text="Amplitude").grid(row=1, column=2, sticky="e", padx=2)
    ttk.Spinbox(lf, from_=10, to=300, textvariable=dlg.amplitude_tkvar,
                width=3).grid(row=1, column=3, sticky="w", padx=2, pady=2)
    ## -> Row : the check buttons, spread over the width.
    row = ttk.Frame(lf)
    row.grid(row=2, column=0, columnspan=4, sticky="ew")
    for column, (text, tkvar) in enumerate(checks):
        row.columnconfigure(column, weight=1)
        ttk.Checkbutton(row, text=text, variable=tkvar).grid(
            row=0, column=column, sticky="w", padx=2, pady=2)
    return lf


def _build_delay_choice(dlg, parent, text, images, image, choices):
    """The illustration of the delay specification over its radio buttons."""
    lf = ttk.Labelframe(parent, text=text)
    ## The figures differ in size: their area is the largest of them, so
    ## that the dialog keeps its size whichever is shown. Image sizes are
    ## device pixels already (uiscale.load_image).
    holder = ttk.Frame(lf,
                       width=max(img.width() for img in images),
                       height=max(img.height() for img in images))
    holder.grid(row=0, column=0, columnspan=len(choices), padx=2, pady=2)
    label = ttk.Label(holder, image=image)
    ## To the west: the device box stays where it is from a figure to the
    ## other (when the figures are drawn so).
    label.place(x=0, rely=0.5, anchor="w")
    for column, (choice, value) in enumerate(choices):
        lf.columnconfigure(column, weight=1)
        ttk.Radiobutton(lf, text=choice, value=value,
                        variable=dlg.topology_tkvar,
                        command=dlg._update_topology).grid(
            row=1, column=column, padx=5, pady=4)
    return lf, label
