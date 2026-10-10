# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2024 Pablo Cardaba

import tkinter as tk
from tkinter import ttk
from .classes import uiscale
from .classes.timeitapp import TimeItApp


def main():
    ## HiDPI: the scale factor is settled before any widget exists.
    uiscale.enable_dpi_awareness()
    root = tk.Tk()
    uiscale.setup(root)
    app = TimeItApp(root)
    ## Set widgeds style...

    style = ttk.Style(root)
    try:
        style.theme_use("clam")
    except tk.TclError:
        pass
    uiscale.apply_ttk_style(style)
    
    root.mainloop()


if __name__ == "__main__":
    main()
