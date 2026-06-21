from __future__ import annotations

import tkinter as tk
from tkinter import ttk, colorchooser

from .waveformannotation import WaveformAnnotation


_COLOR_CHOICES = ("black", "white", "red", "green", "blue",
                  "orange", "purple", "cyan", "magenta", "yellow", "gray")


class WaveformAnnotationDlg(tk.Toplevel):
    """
    Modal dialog for creating or editing a waveform annotation.

    Parameters
    ----------
    parent      The TopLevel application window (topapp).
    wf_uid      The uidtag of the target waveform canvas item (e.g. "uid_2_11").
    annotation  Existing WaveformAnnotation to edit, or None to create one.
    """

    def __init__(self, parent, wf_uid: str,
                 annotation: WaveformAnnotation | None = None) -> None:
        super().__init__(parent, padx=10, pady=6)
        self.topapp = parent
        self.wf_uid = wf_uid
        self._annotation = annotation

        self.title("Waveform Annotation")
        self._build_dlg()
        self._align_bg_colors()

        self.resizable(False, False)
        self.protocol("WM_DELETE_WINDOW", self.dismiss)
        self.transient(parent)
        self.wait_visibility()
        self.grab_set()
        self.wait_window()

    # ------------------------------------------------------------------
    # Dialog construction
    # ------------------------------------------------------------------

    def _build_dlg(self) -> None:
        ann = self._annotation

        # ---- Tk variables (pre-populated when editing) ----------------
        self._text_tkvar       = tk.StringVar(value=ann.text if ann else "")
        default_font_size = str(self.topapp.settings.waveform["font"]["size"])
        self._font_size_tkvar  = tk.StringVar(
            value=str(ann.font_size) if (ann and ann.font_size) else default_font_size)
        self._font_slant_tkvar = tk.StringVar(
            value=ann.font_slant if ann else "normal")
        self._font_weight_tkvar = tk.StringVar(
            value=ann.font_weight if ann else "normal")
        self._font_color_tkvar = tk.StringVar(
            value=ann.font_color if ann else "black")
        self._fill_tkvar       = tk.StringVar(
            value=ann.fill if (ann and ann.fill) else "")
        self._line_tkvar       = tk.StringVar(
            value=ann.line if (ann and ann.line) else "")
        self._rel_x_tkvar      = tk.IntVar(value=ann.rel_x if ann else 0)
        self._rel_y_tkvar      = tk.IntVar(value=ann.rel_y if ann else 0)

        row = 0

        # ---- Waveform object reference (read-only info) ---------------
        ttk.Label(self, text="Waveform object:").grid(
            row=row, column=0, sticky="e", padx=(0, 4))
        ttk.Label(self, text=self.wf_uid, font=("TkFixedFont", 9)).grid(
            row=row, column=1, columnspan=5, sticky="w")
        row += 1
        ttk.Separator(self, orient="horizontal").grid(
            row=row, column=0, columnspan=6, sticky="ew", pady=6)
        row += 1

        # ---- Text -----------------------------------------------------
        lf_text = ttk.Labelframe(self, text="Text annotation")
        lf_text.grid(row=row, column=0, columnspan=6,
                     sticky="nsew", padx=2, pady=2)
        row += 1

        tr = 0  # local row inside labelframe

        ttk.Label(lf_text, text="Text:").grid(
            row=tr, column=0, sticky="e", padx=(4, 2), pady=3)
        ttk.Entry(lf_text, textvariable=self._text_tkvar, width=30).grid(
            row=tr, column=1, columnspan=5, sticky="ew", padx=(0, 4), pady=3)
        tr += 1

        # Font size | Font color
        ttk.Label(lf_text, text="Font size:").grid(
            row=tr, column=0, sticky="e", padx=(4, 2), pady=3)
        ttk.Spinbox(
            lf_text, from_=4, to=72,
            textvariable=self._font_size_tkvar, width=4,
        ).grid(row=tr, column=1, sticky="w", padx=(0, 8), pady=3)

        ttk.Label(lf_text, text="Font color:").grid(
            row=tr, column=2, sticky="e", padx=(0, 2))
        ttk.Combobox(
            lf_text, textvariable=self._font_color_tkvar,
            values=_COLOR_CHOICES, width=10,
        ).grid(row=tr, column=3, columnspan=2, sticky="w", padx=(0, 4), pady=3)
        tr += 1

        # Font weight | Font slant
        ttk.Label(lf_text, text="Weight:").grid(
            row=tr, column=0, sticky="e", padx=(4, 2), pady=3)
        fw_frame = ttk.Frame(lf_text)
        fw_frame.grid(row=tr, column=1, columnspan=2, sticky="w")
        ttk.Radiobutton(fw_frame, text="Normal", variable=self._font_weight_tkvar,
                        value="normal").pack(side="left")
        ttk.Radiobutton(fw_frame, text="Bold", variable=self._font_weight_tkvar,
                        value="bold").pack(side="left", padx=(6, 0))

        ttk.Label(lf_text, text="Slant:").grid(
            row=tr, column=3, sticky="e", padx=(0, 2))
        fs_frame = ttk.Frame(lf_text)
        fs_frame.grid(row=tr, column=4, columnspan=2, sticky="w")
        ttk.Radiobutton(fs_frame, text="Normal", variable=self._font_slant_tkvar,
                        value="normal").pack(side="left")
        ttk.Radiobutton(fs_frame, text="Italic", variable=self._font_slant_tkvar,
                        value="italic").pack(side="left", padx=(6, 0))
        tr += 1

        # Position offset
        ttk.Label(lf_text, text="Offset X:").grid(
            row=tr, column=0, sticky="e", padx=(4, 2), pady=3)
        ttk.Spinbox(
            lf_text, from_=-9999, to=9999,
            textvariable=self._rel_x_tkvar, width=6,
        ).grid(row=tr, column=1, sticky="w", padx=(0, 8), pady=3)
        ttk.Label(lf_text, text="Offset Y:").grid(
            row=tr, column=2, sticky="e", padx=(0, 2))
        ttk.Spinbox(
            lf_text, from_=-9999, to=9999,
            textvariable=self._rel_y_tkvar, width=6,
        ).grid(row=tr, column=3, sticky="w", padx=(0, 4), pady=3)

        # ---- Color overrides ------------------------------------------
        lf_color = ttk.Labelframe(self, text="Color overrides")
        lf_color.grid(row=row, column=0, columnspan=6,
                      sticky="nsew", padx=2, pady=(4, 2))
        row += 1

        cr = 0
        ttk.Label(lf_color, text="Fill color:").grid(
            row=cr, column=0, sticky="e", padx=(4, 2), pady=3)
        ttk.Entry(lf_color, textvariable=self._fill_tkvar, width=12).grid(
            row=cr, column=1, sticky="w", padx=(0, 2), pady=3)
        ttk.Button(
            lf_color, text="...", width=2,
            command=lambda: self._pick_color(self._fill_tkvar),
        ).grid(row=cr, column=2, sticky="w", padx=(0, 6), pady=3)
        ttk.Label(lf_color, text="(polygon items only)",
                  foreground="gray").grid(row=cr, column=3, sticky="w")
        cr += 1

        ttk.Label(lf_color, text="Line color:").grid(
            row=cr, column=0, sticky="e", padx=(4, 2), pady=3)
        ttk.Entry(lf_color, textvariable=self._line_tkvar, width=12).grid(
            row=cr, column=1, sticky="w", padx=(0, 2), pady=3)
        ttk.Button(
            lf_color, text="...", width=2,
            command=lambda: self._pick_color(self._line_tkvar),
        ).grid(row=cr, column=2, sticky="w", padx=(0, 6), pady=3)

        # ---- Buttons --------------------------------------------------
        b_frame = ttk.Frame(self)
        b_frame.grid(row=row, column=0, columnspan=6, sticky="ew", pady=(8, 2))
        b_frame.columnconfigure(0, weight=1)
        if ann is not None:
            ttk.Button(b_frame, text="Delete", command=self.delete).grid(
                row=0, column=1, padx=4)
        ttk.Button(b_frame, text="Cancel", command=self.dismiss).grid(
            row=0, column=2, padx=4)
        ttk.Button(b_frame, text="Apply", command=self.apply).grid(
            row=0, column=3, padx=4)
        ttk.Button(b_frame, text="OK", command=self.ok).grid(
            row=0, column=4, padx=4)

    def _pick_color(self, tkvar: tk.StringVar) -> None:
        """Open the system color-chooser and write the result into *tkvar*."""
        initial = tkvar.get().strip() or None
        result = colorchooser.askcolor(color=initial, parent=self,
                                       title="Choose color")
        hex_color = result[1]   # e.g. "#3a7bd5", or None if cancelled
        if hex_color:
            tkvar.set(hex_color)

    def _align_bg_colors(self) -> None:
        """Align dialog background with ttk frame colour (cross-platform)."""
        frame = ttk.Frame(self)
        style = ttk.Style()
        bg = style.lookup(frame.winfo_class(), "background")
        self.config(bg=bg)

    # ------------------------------------------------------------------
    # Command builder
    # ------------------------------------------------------------------

    def _build_command(self) -> str:
        cmd = f"create_waveform_annotation -on {self.wf_uid}"

        text = self._text_tkvar.get()
        if text:
            cmd += f" -text {{{text}}}"

            size_str = self._font_size_tkvar.get().strip()
            if size_str:
                try:
                    size = int(size_str)
                    if size > 0:
                        cmd += f" -font_size {size}"
                except ValueError:
                    pass

            slant = self._font_slant_tkvar.get()
            if slant != "normal":
                cmd += f" -font_slant {slant}"

            weight = self._font_weight_tkvar.get()
            if weight != "normal":
                cmd += f" -font_weight {weight}"

            color = self._font_color_tkvar.get().strip()
            if color and color != "black":
                cmd += f" -font_color {color}"

            rel_x = self._rel_x_tkvar.get()
            if rel_x:
                cmd += f" -rel_x {rel_x}"

            rel_y = self._rel_y_tkvar.get()
            if rel_y:
                cmd += f" -rel_y {rel_y}"

        fill = self._fill_tkvar.get().strip()
        if fill:
            cmd += f" -fill {fill}"

        line = self._line_tkvar.get().strip()
        if line:
            cmd += f" -line {line}"

        return cmd

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------

    def delete(self) -> None:
        """Remove the annotation from its parent signal and redraw."""
        ann = self._annotation
        if ann is not None:
            with self.topapp.undo.transaction():
                ann.signal.annotations.pop(ann.wf_uid, None)
                self.topapp.redraw()  # full redraw restores default item colors
        self.dismiss()

    def apply(self) -> None:
        cmd = self._build_command()
        with self.topapp.undo.transaction():
            self.topapp.console.execute(cmd)

    def ok(self) -> None:
        self.apply()
        self.dismiss()

    def dismiss(self) -> None:
        self.grab_release()
        self.destroy()
