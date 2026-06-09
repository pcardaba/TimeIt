# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2024 Pablo Cardaba

import tkinter as tk
from tkinter import ttk
from .classes.timeitapp import TimeItApp


def main():
    root = tk.Tk()
    app = TimeItApp(root)
    ## Set widgeds style...

    style = ttk.Style(root)
    try:
        style.theme_use("clam")
    except tk.TclError:
        pass
    
    root.mainloop()


if __name__ == "__main__":
    main()
