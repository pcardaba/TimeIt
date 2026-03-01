from __future__ import annotations

import os
import tempfile
import contextlib
import tkinter as tk
from tkinter import filedialog
import tkinter.font as tkfont
import xml.etree.ElementTree as ET

try:
    from PIL import Image  # type: ignore
    _PIL_OK = True
except Exception:
    _PIL_OK = False


# ----------------------------
# Helpers
# ----------------------------

def _item_is_hidden(canvas: tk.Canvas, item: int) -> bool:
    """Hidden means: state='hidden' OR tag 'hidden'."""
    try:
        if (canvas.itemcget(item, "state") or "").strip() == "hidden":
            return True
    except Exception:
        pass
    try:
        if "hidden" in set(canvas.gettags(item) or ()):
            return True
    except Exception:
        pass
    return False


def _svg_color(canvas: tk.Canvas, c: str | None) -> str:
    """
    Convert Tk color (including names with spaces like 'light grey') into #RRGGBB.
    This avoids SVG viewers mis-parsing non-CSS Tk color names.
    """
    if c is None:
        return "none"
    c = str(c).strip()
    if not c or c.lower() == "none":
        return "none"
    if c.startswith("#") and len(c) in (4, 7):
        return c
    try:
        r16, g16, b16 = canvas.winfo_rgb(c)
        r = int(round(r16 / 257))
        g = int(round(g16 / 257))
        b = int(round(b16 / 257))
        return f"#{r:02x}{g:02x}{b:02x}"
    except Exception:
        return c


def _svg_dash(dash) -> str | None:
    if not dash:
        return None
    if isinstance(dash, (tuple, list)):
        s = " ".join(str(x) for x in dash if x is not None)
        return s if s.strip() else None
    s = str(dash).strip()
    return s if s else None


def _tk_font_to_svg(canvas: tk.Canvas, font_str: str) -> dict[str, str]:
    """
    Convert a Tk font (canvas item 'font') to SVG font attributes.

    Notes:
      - Tk: size > 0 => pixels, size < 0 => points.
      - SVG font-size defaults to px, so we convert points -> px assuming 96 DPI.
    """
    attrs: dict[str, str] = {}
    try:
        f = tkfont.Font(font=font_str) if font_str else tkfont.nametofont("TkDefaultFont")
        family = f.actual("family")
        size = int(f.actual("size"))
        weight = f.actual("weight")
        slant = f.actual("slant")

        if size < 0:
            px = int(round(abs(size) * 96 / 72))  # points -> px
        else:
            px = abs(size)

        if family:
            attrs["font-family"] = family
        if px:
            attrs["font-size"] = str(px+2)
        if weight and weight != "normal":
            attrs["font-weight"] = str(weight)
        if slant and slant != "roman":
            attrs["font-style"] = "italic"
    except Exception:
        pass
    return attrs


# ----------------------------
# Exporter
# ----------------------------

class CanvasExporter:
    """
    Cleaned minimal exporter v2 for tk.Canvas.

    Supported formats:
      - SVG  : line (incl arrows), polygon (incl stipple approximation), text (incl fonts)
      - PS   : Tk postscript()
      - EPS  : same as PS (portable; avoids Tk '-eps' option and avoids manual EPS wrapping)
      - PNG/JPG : via PS/EPS rasterization with Pillow (Ghostscript usually required)

    Behavior:
      - Exports FULL CONTENT area enclosing objects: bbox('all') with padding.
      - Hidden items are not exported:
          * state='hidden' items are naturally not drawn by Tk postscript()
          * items tagged 'hidden' are temporarily hidden for PS/EPS/PNG/JPG
          * SVG skips state hidden OR 'hidden' tag
      - SVG color conversion handles Tk names like 'light grey'
      - SVG line arrows supported: arrow=first|last|both with correct start orientation
      - Stipple patterns (gray12/25/50/75) approximated via fill-opacity
      - Raster export: default 300 DPI (min 100)
    """

    def __init__(self, canvas: tk.Canvas):
        self.canvas = canvas

    # ---------- Region logic (FULL CONTENT, not viewport) ----------

    def _content_bbox(self, pad: int = 10) -> tuple[int, int, int, int]:
        """Return (x, y, w, h) in canvas coordinates covering ALL items."""
        c = self.canvas
        c.update_idletasks()
        bbox = c.bbox("all")
        if bbox is None:
            raise ValueError("Canvas is empty; nothing to export.")

        x1, y1, x2, y2 = bbox
        x1 -= pad
        y1 -= pad
        x2 += pad
        y2 += pad
        w = max(1, int(round(x2 - x1)))
        h = max(1, int(round(y2 - y1)))
        return int(round(x1)), int(round(y1)), w, h

    # ---------- Hidden-tag suppression for PS/EPS/raster ----------

    @contextlib.contextmanager
    def _suppress_hidden_tagged_items(self):
        """Temporarily hide items tagged 'hidden' for PS/EPS export."""
        c = self.canvas
        changed: list[tuple[int, str]] = []
        try:
            for item in c.find_all():
                try:
                    if "hidden" in set(c.gettags(item) or ()):
                        prev = (c.itemcget(item, "state") or "").strip() or "normal"
                        if prev != "hidden":
                            changed.append((item, prev))
                            c.itemconfigure(item, state="hidden")
                except Exception:
                    continue
            yield
        finally:
            for item, prev in changed:
                try:
                    c.itemconfigure(item, state=prev)
                except Exception:
                    pass

    # ---------- Public API ----------
    def export_dialog(self, *, default_name: str = "canvas_export"):
        filetypes = [
            ("PNG image", "*.png"),
            ("JPEG image", "*.jpg;*.jpeg"),
            ("PostScript", "*.ps"),
            ("Encapsulated PostScript", "*.eps"),
            ("SVG", "*.svg"),
        ]
        path = filedialog.asksaveasfilename(
            defaultextension=".png",
            initialfile=default_name,
            filetypes=filetypes,
        )
        if path:
            self.export(path)
    
    def export(self, path: str, *, bg: str = "white", dpi: int = 300, jpeg_quality: int = 95):
        ext = os.path.splitext(path)[1].lower()
        if ext == ".svg":
            self.export_svg(path)
        elif ext == ".ps":
            self.export_ps(path)
        elif ext == ".eps":
            self.export_eps(path)
        elif ext == ".png":
            self.export_png(path, bg=bg, dpi=dpi)
        elif ext in (".jpg", ".jpeg"):
            self.export_jpg(path, bg=bg, dpi=dpi, quality=jpeg_quality)
        else:
            raise ValueError(f"Unsupported format: {ext}")

    # ---------- PS / EPS ----------

    def export_ps(self, path: str):
        self._postscript(path)

    def export_eps(self, path: str):
        # Many Tk builds don't support the '-eps' flag, and manual EPS wrapping can
        # break Ghostscript/Pillow pipelines. We therefore write the same PS content.
        self._postscript(path)

    def _postscript(self, path: str):
        c = self.canvas
        x, y, w, h = self._content_bbox(pad=10)

        with self._suppress_hidden_tagged_items():
            ps = c.postscript(
                colormode="color",
                x=x, y=y,
                width=w, height=h,
                # Keep placement deterministic (prevents offsets that look like "wrong area exported")
                pagex=0, pagey=0,
                pagewidth=w, pageheight=h,
                rotate=False,
            )

        with open(path, "w", encoding="utf-8") as f:
            f.write(ps)

    # ---------- Raster via PS/EPS ----------

    def export_png(self, path: str, *, bg: str = "white", dpi: int = 300):
        self._export_raster(path, fmt="PNG", bg=bg, dpi=dpi)

    def export_jpg(self, path: str, *, bg: str = "white", dpi: int = 300, quality: int = 95):
        self._export_raster(path, fmt="JPEG", bg=bg, dpi=dpi, quality=quality)

    def _export_raster(self, path: str, *, fmt: str, bg: str, dpi: int, quality: int = 95):
        if not _PIL_OK:
            raise RuntimeError("Pillow not installed. Install with: pip install pillow")

        dpi = int(dpi)
        if dpi < 100:
            dpi = 100

        # Pillow/Ghostscript EPS rendering is ~72dpi base; upscale for sharp text.
        scale = max(1, int(round(dpi / 72.0)))

        with tempfile.TemporaryDirectory() as td:
            eps_path = os.path.join(td, "export.eps")
            self.export_eps(eps_path)

            im = Image.open(eps_path)
            try:
                # Newer Pillow:
                im.load(scale=scale)
            except TypeError:
                # Older Pillow:
                im.load()
                if scale != 1:
                    im = im.resize((im.size[0] * scale, im.size[1] * scale), Image.Resampling.LANCZOS)

            if fmt.upper() == "JPEG":
                im = im.convert("RGBA")
                bg_im = Image.new("RGBA", im.size, bg)
                bg_im.alpha_composite(im)
                out = bg_im.convert("RGB")
                out.save(path, "JPEG", quality=quality, dpi=(dpi, dpi))
            else:
                if im.mode not in ("RGB", "RGBA"):
                    im = im.convert("RGBA")
                im.save(path, "PNG", dpi=(dpi, dpi))

    # ---------- SVG ----------

    def export_svg(self, path: str):
        c = self.canvas
        c.update_idletasks()
        x, y, w, h = self._content_bbox(pad=10)

        svg = ET.Element(
            "svg",
            {
                "xmlns": "http://www.w3.org/2000/svg",
                "version": "1.1",
                "width": str(w),
                "height": str(h),
                "viewBox": f"0 0 {w} {h}",
            },
        )
        defs = ET.SubElement(svg, "defs")
        g = ET.SubElement(svg, "g", {"transform": f"translate({-x},{-y})"})

        marker_cache: dict[tuple[str, float, float, float], tuple[str, str]] = {}

        for item in c.find_all():
            if _item_is_hidden(c, item):
                continue
            t = c.type(item)
            if t == "line":
                self._svg_line(g, defs, item, marker_cache)
            elif t == "polygon":
                self._svg_polygon(g, item)
            elif t == "text":
                self._svg_text(g, item)
            # add more types as needed: rectangle, oval, image...

        tree = ET.ElementTree(svg)
        ET.indent(tree, space="  ", level=0)
        with open(path, "wb") as f:
            tree.write(f, encoding="utf-8", xml_declaration=True)

    # ---- SVG: arrows ----

    def _svg_markers(
        self,
        defs: ET.Element,
        stroke: str,
        arrowshape: tuple[float, float, float],
        cache: dict[tuple[str, float, float, float], tuple[str, str]],
    ) -> tuple[str, str]:
        """
        Create two markers: start + end.

        Fixes the 'start arrow points the wrong way' issue by mirroring geometry.
        Tk arrowshape: (length, width, inset) — we approximate with a triangle.
        """
        length, width, inset = arrowshape
        key = (stroke, float(length), float(width), float(inset))
        if key in cache:
            return cache[key]

        base = f"arrow_{len(cache) + 1}"
        start_id = f"{base}_start"
        end_id = f"{base}_end"

        # End marker: tip at x=length
        mend = ET.SubElement(
            defs,
            "marker",
            {
                "id": end_id,
                "markerWidth": str(length),
                "markerHeight": str(width),
                "refX": str(length),
                "refY": str(width / 2.0),
                "orient": "auto",
                "markerUnits": "strokeWidth",
                "viewBox": f"0 0 {length} {width}",
            },
        )
        ET.SubElement(
            mend,
            "path",
            {"d": f"M 0 0 L {length} {width/2.0} L 0 {width} z", "fill": stroke, "stroke": "none"},
        )

        # Start marker: mirrored, tip at x=0
        mstart = ET.SubElement(
            defs,
            "marker",
            {
                "id": start_id,
                "markerWidth": str(length),
                "markerHeight": str(width),
                "refX": "0",
                "refY": str(width / 2.0),
                "orient": "auto",
                "markerUnits": "strokeWidth",
                "viewBox": f"0 0 {length} {width}",
            },
        )
        ET.SubElement(
            mstart,
            "path",
            {"d": f"M {length} 0 L 0 {width/2.0} L {length} {width} z", "fill": stroke, "stroke": "none"},
        )

        cache[key] = (start_id, end_id)
        return start_id, end_id

    # ---- SVG: primitives ----

    def _svg_line(
        self,
        parent: ET.Element,
        defs: ET.Element,
        item: int,
        cache: dict[tuple[str, float, float, float], tuple[str, str]],
    ):
        c = self.canvas
        coords = c.coords(item)
        if len(coords) < 4:
            return

        stroke = _svg_color(c, c.itemcget(item, "fill"))
        sw = c.itemcget(item, "width") or "1"
        dash = _svg_dash(c.itemcget(item, "dash"))
        cap = c.itemcget(item, "capstyle") or "butt"
        join = c.itemcget(item, "joinstyle") or "miter"

        attrs = {
            "fill": "none",
            "stroke": stroke,
            "stroke-width": str(sw),
            "stroke-linecap": cap,
            "stroke-linejoin": join,
        }
        if dash:
            attrs["stroke-dasharray"] = dash

        arrow = (c.itemcget(item, "arrow") or "").strip().lower()
        if arrow and arrow != "none":
            ashape_raw = (c.itemcget(item, "arrowshape") or "").strip()
            try:
                parts = [float(x) for x in ashape_raw.replace(",", " ").split()]
                ashape = (parts[0], parts[1], parts[2]) if len(parts) >= 3 else (8.0, 10.0, 3.0)
            except Exception:
                ashape = (8.0, 10.0, 3.0)
            start_id, end_id = self._svg_markers(defs, stroke, ashape, cache)
            if arrow in ("first", "both"):
                attrs["marker-start"] = f"url(#{start_id})"
            if arrow in ("last", "both"):
                attrs["marker-end"] = f"url(#{end_id})"

        if len(coords) == 4:
            attrs.update({"x1": str(coords[0]), "y1": str(coords[1]),
                          "x2": str(coords[2]), "y2": str(coords[3])})
            ET.SubElement(parent, "line", attrs)
        else:
            attrs["points"] = " ".join(f"{coords[i]},{coords[i+1]}" for i in range(0, len(coords), 2))
            ET.SubElement(parent, "polyline", attrs)

    def _svg_polygon(self, parent: ET.Element, item: int):
        c = self.canvas
        coords = c.coords(item)
        if len(coords) < 6:
            return

        fill = _svg_color(c, c.itemcget(item, "fill"))
        stroke = _svg_color(c, c.itemcget(item, "outline"))
        sw = c.itemcget(item, "width") or "1"
        dash = _svg_dash(c.itemcget(item, "dash"))
        join = c.itemcget(item, "joinstyle") or "miter"
        stipple = (c.itemcget(item, "stipple") or "").strip()

        attrs = {
            "points": " ".join(f"{coords[i]},{coords[i+1]}" for i in range(0, len(coords), 2)),
            "fill": fill,
            "stroke": stroke,
            "stroke-width": str(sw),
            "stroke-linejoin": join,
        }
        if dash:
            attrs["stroke-dasharray"] = dash

        # Approximate common Tk bitmap stipples using opacity
        if stipple:
            op_map = {
                "gray12": 0.12,
                "gray25": 0.25,
                "gray50": 0.50,
                "gray75": 0.75,
            }
            if stipple in op_map:
                if fill == "none":
                    # Ensure opacity has something to apply to
                    attrs["fill"] = stroke if stroke != "none" else "#000000"
                attrs["fill-opacity"] = str(op_map[stipple])

        ET.SubElement(parent, "polygon", attrs)

    def _svg_text(self, parent: ET.Element, item: int):
        c = self.canvas
        coords = c.coords(item)
        if len(coords) < 2:
            return

        x, y = coords[0], coords[1]
        text = c.itemcget(item, "text") or ""
        fill = _svg_color(c, c.itemcget(item, "fill"))

        anchor = (c.itemcget(item, "anchor") or "center").lower()
        if "w" in anchor:
            text_anchor = "start"
        elif "e" in anchor:
            text_anchor = "end"
        else:
            text_anchor = "middle"

        if anchor.startswith("n"):
            baseline = "hanging"
        elif anchor.startswith("s"):
            baseline = "auto"
        else:
            baseline = "middle"

        attrs = {"x": str(x), "y": str(y),
                 "fill": fill, "text-anchor": text_anchor,
                 "dominant-baseline": baseline}

        font_str = c.itemcget(item, "font") or ""
        attrs.update(_tk_font_to_svg(c, font_str))

        el = ET.SubElement(parent, "text", attrs)

        # Preserve newlines with <tspan>
        lines = text.splitlines() or [""]
        if len(lines) == 1:
            el.text = lines[0]
        else:
            el.text = ""
            for i, line in enumerate(lines):
                tattrs = {"x": str(x)}
                if i > 0:
                    tattrs["dy"] = "1.2em"
                t = ET.SubElement(el, "tspan", tattrs)
                t.text = line

