from __future__ import annotations

from dataclasses import dataclass
from typing import Any, TextIO

import tkinter as tk


@dataclass(slots=True)
class _Style:
    """Visual style for drawing a signal."""

    amplitude: int = 40
    color: str = "black"
    lwidth: int = 2

    
class Signal:
    """Base class for all signals (clock/input/output).

    Notes
    -----
    `canvas` is a custom Canvas-like class (not a plain tk.Canvas):
    it provides attributes like `settings`, `scale_factor`, etc ...
    `console` provides `append_log(text, tag)` and `interp` (Tcl interpreter).
    """

    static_id: int = 0

    def __init__(self, name: str = "", sig_type: str = "clock") -> None:
        
        self.console: TclConsole | None = None

        self.type: str = sig_type  # "clock" | "input" | "output"
        self._related  = set()

        self.name: str = name
        self.visible: bool = False

        self.style = _Style()

        self.uid: int = Signal.static_id
        Signal.static_id += 1

        # Element unique id (for tags). Reset on each draw().
        self.elid: int = 0

        # Cached per-draw reference
        self.settings: Settings | None = None

    @property
    def amplitude(self):
        return self.style.amplitude
    
    @amplitude.setter
    def amplitude(self, value):
        self.style.amplitude = value
        
    @property
    def color(self):
        return self.style.color

    @color.setter
    def color(self, value):
        self.style.color = value
        
    @property
    def lwidth(self):
        return self.style.lwidth
    
    @lwidth.setter
    def lwidth(self, value):
        self.style.lwidth = value
        
    # ------------------------------------------------------------------
    # Protected methods
    # ------------------------------------------------------------------
    def _draw_label(self, canvas: tk.Canvas, top: int) -> None:
        """Draw the signal label at the left margin."""
        if self.settings is None:
            self.settings = getattr(canvas, "settings", None)

        slot_height = int(self.amplitude)
        canvas.create_text(
            self.settings.waveform["left_padding"],
            top + (slot_height / 2),
            text=self.name,
            font=self.settings.get_font(self.settings.waveform["font"]),
            anchor="w",
            tags=(self.uidtag(), "wf_labels", f"{self.name}_label"),
        )

    def _apply_hidden_state(self, canvas: tk.Canvas) -> bool:
        """Apply hidden state on non-virtual canvas;
           return True if hidden."""
        if getattr(canvas, "is_virtual", False):
            return False
        if self.visible:
            return False

        for tag in (f"{self.name}_waveform",
                    f"{self.name}_uncertainties",
                    f"{self.name}_label"):
            try:
                canvas.itemconfigure(tag, state="hidden")
            except tk.TclError:
                # Tag may not exist for some signal types; ignore.
                pass
        return True

    def _tcl_eval_float(self, expr: str, *, context: str) -> float:
        """Evaluate a Tcl expression and convert to float."""
        if self.console is None:
            raise RuntimeError("Tcl interpreter not set (call set_tcl_console).")
        try:
            interp = self.console.interp
            return float(interp.eval(f"expr {{{expr}}}"))
        except tk.TclError as exc:
            if self.console is not None:
                self.console.append_log(f"[{context}] Invalid expression: {expr}\n{exc}\n",
                                        "error")
            raise

    def _write_common_args(self, fileref: TextIO) -> None:
        for attr in ("color", "amplitude", "lwidth"):
            value = getattr(self, attr, None)
            if value is not None:
                fileref.write(f"   -{attr} {value}  \\\n")
            
        fileref.write(f"   -use_uid {self.uid}  ")
        if self.visible:
            fileref.write("   -visible ")
        fileref.write("\n")
        
    # ------------------------------------------------------------------
    # Public methods
    # ------------------------------------------------------------------
    
    def get_related_objs(self) -> set[Any]:
        return self._related

    def add_related_obj(self, obj: Signal | TimingMarker) -> None:
        self._related.add(obj)

    def remove_related_obj(self, obj: Signal | TimingMarker) -> None:
        self._related.discard(obj)

    def set_tcl_console(self, console: TclConsole) -> None:
        self.console = console

    def uidtag(self) -> str:
        tag = f"uid_{self.uid}_{self.elid}"
        self.elid += 1
        return tag

    def draw(self, canvas: tk.Canvas, top: int) -> None:
        """Prepare drawing: reset element-id and cache settings."""
        self.elid = 0
        if self.settings is None:
            self.settings = getattr(canvas, "settings", None)

    def write(self, fileref: TextIO) -> None:
        raise NotImplementedError


