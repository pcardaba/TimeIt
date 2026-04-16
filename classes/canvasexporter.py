"""
CanvasExporter — rewritten from scratch.

Supported output formats:
  SVG   Hand-crafted XML; correct Tk arrowshape, all item types.
  PNG   Cairo ImageSurface + Pango text (no Ghostscript dependency).
  JPEG  PNG → Pillow JPEG conversion.
  PDF   Cairo PDFSurface.
  PS    Cairo PSSurface.
  EPS   Cairo PSSurface (EPS flag).
  EMF   SVG → LibreOffice headless conversion.
  VSDX  Generated directly from canvas items (MS Visio 2013+).

Key fixes over the previous version:
  * PNG uses Cairo directly — no EPS intermediate, no Ghostscript needed.
  * PS/EPS uses Cairo + Pango → correct font family AND size.
  * SVG arrows use userSpaceOnUse markers with correct Tk arrowshape geometry
    (concave arrowhead with proper neck/barb/tip positions).
  * All canvas item types handled: line, polygon, text, rectangle.
  * selection_bbox items are always skipped (they are UI artefacts).
"""
from __future__ import annotations

import math
import os
import subprocess
import tempfile
import contextlib
import zipfile
import xml.etree.ElementTree as ET
import tkinter as tk
from tkinter import filedialog
import tkinter.font as tkfont

# ── optional dependencies ──────────────────────────────────────────────────

try:
    from PIL import Image as _PilImage
    _PIL_OK = True
except ImportError:
    _PIL_OK = False

try:
    import cairo as _cairo
    _CAIRO_OK = True
except ImportError:
    _CAIRO_OK = False

try:
    import gi as _gi
    _gi.require_version("Pango", "1.0")
    _gi.require_version("PangoCairo", "1.0")
    from gi.repository import Pango as _Pango
    from gi.repository import PangoCairo as _PangoCairo
    _PANGO_OK = True
except Exception:
    _PANGO_OK = False


# ═══════════════════════════════════════════════════════════════════════════
# Shared helpers
# ═══════════════════════════════════════════════════════════════════════════

def _item_is_hidden(canvas: tk.Canvas, item: int) -> bool:
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


def _tk_rgb(canvas: tk.Canvas, c: str | None) -> tuple[float, float, float] | None:
    """Tk colour → (r,g,b) in [0,1], or None when colour is absent/none."""
    if not c:
        return None
    c = str(c).strip()
    if not c or c.lower() == "none":
        return None
    try:
        r16, g16, b16 = canvas.winfo_rgb(c)
        return r16 / 65535.0, g16 / 65535.0, b16 / 65535.0
    except Exception:
        return None


def _svg_color(canvas: tk.Canvas, c: str | None) -> str:
    """Tk colour → #rrggbb for SVG, or 'none'."""
    if not c:
        return "none"
    c = str(c).strip()
    if not c or c.lower() == "none":
        return "none"
    if c.startswith("#") and len(c) in (4, 7):
        return c
    try:
        r16, g16, b16 = canvas.winfo_rgb(c)
        return f"#{r16//257:02x}{g16//257:02x}{b16//257:02x}"
    except Exception:
        return c


def _svg_dash(dash) -> str | None:
    if not dash:
        return None
    if isinstance(dash, (tuple, list)):
        s = " ".join(str(x) for x in dash if x is not None)
        return s or None
    s = str(dash).strip()
    return s or None


def _parse_arrowshape(raw: str) -> tuple[float, float, float]:
    """
    Parse Tk arrowshape string → (a, b, c).

    Tk arrowshape semantics:
      a  distance neck → tip
      b  distance barb-tips → tip  (b >= a)
      c  half-width at the barb-tips
    """
    try:
        parts = [float(x) for x in str(raw).replace(",", " ").split() if x]
        if len(parts) >= 3:
            return parts[0], parts[1], parts[2]
    except Exception:
        pass
    return 10.0, 12.0, 4.0


def _arrow_polygon(x1: float, y1: float, x2: float, y2: float,
                   a: float, b: float, c: float
                   ) -> list[tuple[float, float]]:
    """
    Filled concave arrowhead polygon at (x2,y2) pointing from (x1,y1).
    Returns 4 points: tip, right-barb, neck, left-barb.
    """
    dx, dy = x2 - x1, y2 - y1
    L = math.hypot(dx, dy)
    if L < 1e-9:
        return []
    ux, uy = dx / L, dy / L   # unit along line
    px, py = -uy, ux           # unit perpendicular

    tip    = (x2,               y2)
    r_barb = (x2 - b*ux + c*px, y2 - b*uy + c*py)
    neck   = (x2 - a*ux,        y2 - a*uy)
    l_barb = (x2 - b*ux - c*px, y2 - b*uy - c*py)
    return [tip, r_barb, neck, l_barb]


def _parse_tk_font(font_str: str) -> tuple[str, float, bool, bool]:
    """Return (family, size_px, bold, italic)."""
    try:
        f = (tkfont.Font(font=font_str) if font_str
             else tkfont.nametofont("TkDefaultFont"))
        size = int(f.actual("size"))
        # Tk: positive = points, negative = pixels
        size_px = abs(size) if size < 0 else int(round(size * 96.0 / 72.0))
        return (
            f.actual("family") or "sans-serif",
            float(size_px),
            f.actual("weight") == "bold",
            f.actual("slant") == "italic",
        )
    except Exception:
        return "sans-serif", 12.0, False, False


# ═══════════════════════════════════════════════════════════════════════════
# VSDX colour helper
# ═══════════════════════════════════════════════════════════════════════════

def _hex_to_vsdx(hex_color: str) -> str:
    """#rrggbb → 'RGB(r,g,b)' for Visio XML.  Falls back to black."""
    if not hex_color or hex_color == "none" or not hex_color.startswith("#"):
        return "RGB(0,0,0)"
    try:
        h = hex_color.lstrip("#")
        if len(h) == 3:
            h = h[0]*2 + h[1]*2 + h[2]*2
        r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
        return f"RGB({r},{g},{b})"
    except Exception:
        return "RGB(0,0,0)"


_VSDX_DPI = 96.0  # Tk canvas uses 96 dpi equivalent


def _px_to_in(px: float) -> float:
    return px / _VSDX_DPI


# ═══════════════════════════════════════════════════════════════════════════
# Main exporter
# ═══════════════════════════════════════════════════════════════════════════

class CanvasExporter:

    def __init__(self, canvas: tk.Canvas):
        self.canvas = canvas

    # ── geometry ────────────────────────────────────────────────────────────

    def _content_bbox(self, pad: int = 10) -> tuple[int, int, int, int]:
        """Return (x, y, w, h) covering all canvas items."""
        c = self.canvas
        c.update_idletasks()
        bbox = c.bbox("all")
        if bbox is None:
            raise ValueError("Canvas is empty; nothing to export.")
        x1, y1, x2, y2 = bbox
        x1 -= pad; y1 -= pad; x2 += pad; y2 += pad
        return (int(round(x1)), int(round(y1)),
                max(1, int(round(x2 - x1))), max(1, int(round(y2 - y1))))

    # ── hidden-item management ──────────────────────────────────────────────

    @contextlib.contextmanager
    def _suppress_hidden_tagged(self):
        """Temporarily hide items whose tag set contains 'hidden'."""
        c = self.canvas
        restored: list[tuple[int, str]] = []
        try:
            for item in c.find_all():
                try:
                    if "hidden" in set(c.gettags(item) or ()):
                        prev = (c.itemcget(item, "state") or "").strip() or "normal"
                        if prev != "hidden":
                            restored.append((item, prev))
                            c.itemconfigure(item, state="hidden")
                except Exception:
                    pass
            yield
        finally:
            for item, prev in restored:
                try:
                    c.itemconfigure(item, state=prev)
                except Exception:
                    pass

    # ── public API ──────────────────────────────────────────────────────────

    def export_dialog(self, *, default_name: str = "canvas_export"):
        filetypes = [
            ("PNG image",                "*.png"),
            ("JPEG image",               "*.jpg;*.jpeg"),
            ("SVG vector",               "*.svg"),
            ("PDF document",             "*.pdf"),
            ("PostScript",               "*.ps"),
            ("Encapsulated PostScript",  "*.eps"),
            ("Enhanced Metafile (EMF)",  "*.emf"),
            ("MS Visio Drawing (VSDX)",  "*.vsdx"),
        ]
        path = filedialog.asksaveasfilename(
            defaultextension=".png",
            initialfile=default_name,
            filetypes=filetypes,
        )
        if path:
            self.export(path)

    def export(self, path: str, *, bg: str = "white",
               dpi: int = 300, jpeg_quality: int = 95):
        ext = os.path.splitext(path)[1].lower()
        dispatch = {
            ".svg":  self.export_svg,
            ".pdf":  self.export_pdf,
            ".ps":   self.export_ps,
            ".eps":  self.export_eps,
            ".png":  lambda p: self.export_png(p, bg=bg, dpi=dpi),
            ".jpg":  lambda p: self.export_jpg(p, bg=bg, dpi=dpi,
                                               quality=jpeg_quality),
            ".jpeg": lambda p: self.export_jpg(p, bg=bg, dpi=dpi,
                                               quality=jpeg_quality),
            ".emf":  self.export_emf,
            ".vsdx": self.export_vsdx,
        }
        fn = dispatch.get(ext)
        if fn is None:
            raise ValueError(f"Unsupported format: {ext!r}")
        fn(path)

    # ════════════════════════════════════════════════════════════════════════
    # SVG export
    # ════════════════════════════════════════════════════════════════════════

    def export_svg(self, path: str):
        tree = self._build_svg_tree()
        ET.indent(tree, space="  ", level=0)
        with open(path, "wb") as fh:
            tree.write(fh, encoding="utf-8", xml_declaration=True)

    def _build_svg_tree(self) -> ET.ElementTree:
        c = self.canvas
        c.update_idletasks()
        ox, oy, w, h = self._content_bbox(pad=10)

        svg = ET.Element("svg", {
            "xmlns": "http://www.w3.org/2000/svg",
            "version": "1.1",
            "width": str(w), "height": str(h),
            "viewBox": f"0 0 {w} {h}",
        })
        defs = ET.SubElement(svg, "defs")
        ET.SubElement(svg, "rect", {          # white background
            "width": str(w), "height": str(h), "fill": "white",
        })
        g = ET.SubElement(svg, "g", {"transform": f"translate({-ox},{-oy})"})

        # cache keyed by (stroke_hex, a, b, c) → (start_id, end_id)
        arrow_cache: dict[tuple, tuple[str, str]] = {}

        for item in c.find_all():
            if _item_is_hidden(c, item):
                continue
            if "selection_bbox" in set(c.gettags(item)):
                continue
            t = c.type(item)
            if   t == "line":      self._svg_line(g, defs, item, arrow_cache)
            elif t == "polygon":   self._svg_polygon(g, item)
            elif t == "text":      self._svg_text(g, item)
            elif t == "rectangle": self._svg_rect(g, item)

        return ET.ElementTree(svg)

    # ── SVG: arrow markers ───────────────────────────────────────────────

    def _svg_arrow_markers(
        self, defs: ET.Element,
        stroke: str, a: float, b: float, c: float,
        cache: dict,
    ) -> tuple[str, str]:
        """
        Create and cache SVG <marker> elements for Tk arrowshape (a,b,c).

        End marker  : tip at (b,c), neck at (b-a,c), barbs at (0,0) and (0,2c).
                      refX = b-a  → neck aligns with the line endpoint so the
                      arrowhead extends naturally past the line end.

        Start marker: mirror geometry (tip at x=0, neck at x=a).
                      refX = a  → neck aligns with the line start point.
                      orient="auto" + leftward tip = arrow points back along line.
        """
        key = (stroke, a, b, c)
        if key in cache:
            return cache[key]

        idx  = len(cache) + 1
        eid  = f"arwe{idx}"   # end marker
        sid  = f"arws{idx}"   # start marker
        h2   = 2.0 * c        # total height

        common = {
            "markerUnits":  "userSpaceOnUse",
            "markerWidth":  f"{b:.4f}",
            "markerHeight": f"{h2:.4f}",
            "orient":       "auto",
        }

        # End marker — line flows left→right, tip at (b,c)
        me = ET.SubElement(defs, "marker", {
            **common, "id": eid,
            "refX": f"{b:.4f}",
            "refY": f"{c:.4f}",
            "viewBox": f"0 0 {b:.4f} {h2:.4f}",
        })
        ET.SubElement(me, "path", {
            "d": (f"M {b:.4f} {c:.4f} "
                  f"L 0 0 "
                  f"L {b-a:.4f} {c:.4f} "
                  f"L 0 {h2:.4f} Z"),
            "fill": stroke, "stroke": "none",
        })

        # Start marker — tip at x=0 (leftward), neck at x=a
        ms = ET.SubElement(defs, "marker", {
            **common, "id": sid,
            "refX": "0",
            "refY": f"{c:.4f}",
            "viewBox": f"0 0 {b:.4f} {h2:.4f}",
        })
        ET.SubElement(ms, "path", {
            "d": (f"M 0 {c:.4f} "
                  f"L {b:.4f} 0 "
                  f"L {a:.4f} {c:.4f} "
                  f"L {b:.4f} {h2:.4f} Z"),
            "fill": stroke, "stroke": "none",
        })

        cache[key] = (sid, eid)
        return sid, eid

    # ── SVG: primitives ──────────────────────────────────────────────────

    def _svg_line(self, parent, defs, item, cache):
        c = self.canvas
        coords = c.coords(item)
        if len(coords) < 4:
            return

        stroke = _svg_color(c, c.itemcget(item, "fill")) or "#000000"
        sw  = c.itemcget(item, "width") or "1"
        cap = c.itemcget(item, "capstyle") or "butt"
        join= c.itemcget(item, "joinstyle") or "miter"
        dash= _svg_dash(c.itemcget(item, "dash"))

        attrs: dict[str, str] = {
            "fill": "none", "stroke": stroke,
            "stroke-width": sw,
            "stroke-linecap": cap, "stroke-linejoin": join,
        }
        if dash:
            attrs["stroke-dasharray"] = dash

        arrow = (c.itemcget(item, "arrow") or "none").strip().lower()
        if arrow != "none":
            a, b, av_c = _parse_arrowshape(c.itemcget(item, "arrowshape") or "")
            s_id, e_id = self._svg_arrow_markers(defs, stroke, a, b, av_c, cache)
            if arrow in ("first", "both"):
                attrs["marker-start"] = f"url(#{s_id})"
            if arrow in ("last", "both"):
                attrs["marker-end"] = f"url(#{e_id})"

        if len(coords) == 4:
            attrs.update({
                "x1": str(coords[0]), "y1": str(coords[1]),
                "x2": str(coords[2]), "y2": str(coords[3]),
            })
            ET.SubElement(parent, "line", attrs)
        else:
            attrs["points"] = " ".join(
                f"{coords[i]},{coords[i+1]}" for i in range(0, len(coords), 2))
            ET.SubElement(parent, "polyline", attrs)

    def _svg_polygon(self, parent, item):
        c = self.canvas
        coords = c.coords(item)
        if len(coords) < 6:
            return
        fill   = _svg_color(c, c.itemcget(item, "fill"))
        stroke = _svg_color(c, c.itemcget(item, "outline"))
        sw     = c.itemcget(item, "width") or "1"
        stipple= (c.itemcget(item, "stipple") or "").strip()
        dash   = _svg_dash(c.itemcget(item, "dash"))

        attrs: dict[str, str] = {
            "points": " ".join(
                f"{coords[i]},{coords[i+1]}" for i in range(0, len(coords), 2)),
            "fill": fill, "stroke": stroke, "stroke-width": sw,
        }
        if dash:
            attrs["stroke-dasharray"] = dash
        op_map = {"gray12": "0.12", "gray25": "0.25",
                  "gray50": "0.50", "gray75": "0.75"}
        if stipple in op_map:
            attrs["fill-opacity"] = op_map[stipple]
        ET.SubElement(parent, "polygon", attrs)

    def _svg_text(self, parent, item):
        c = self.canvas
        coords = c.coords(item)
        if len(coords) < 2:
            return
        x, y = coords[0], coords[1]
        text = c.itemcget(item, "text") or ""
        fill = _svg_color(c, c.itemcget(item, "fill"))
        anchor = (c.itemcget(item, "anchor") or "center").lower()

        text_anchor  = "start" if "w" in anchor else ("end" if "e" in anchor else "middle")
        dominant_bl  = ("hanging" if anchor.startswith("n")
                        else ("auto" if anchor.startswith("s") else "middle"))

        font_str = c.itemcget(item, "font") or ""
        fam, sz_px, bold, italic = _parse_tk_font(font_str)

        attrs: dict[str, str] = {
            "x": str(x), "y": str(y),
            "fill": fill,
            "text-anchor": text_anchor,
            "dominant-baseline": dominant_bl,
            "font-family": fam,
            "font-size": f"{sz_px:.1f}px",
        }
        if bold:
            attrs["font-weight"] = "bold"
        if italic:
            attrs["font-style"] = "italic"

        el = ET.SubElement(parent, "text", attrs)
        lines = text.splitlines() or [""]
        if len(lines) == 1:
            el.text = lines[0]
        else:
            for i, line in enumerate(lines):
                ta: dict[str, str] = {"x": str(x)}
                if i > 0:
                    ta["dy"] = "1.2em"
                ET.SubElement(el, "tspan", ta).text = line

    def _svg_rect(self, parent, item):
        c = self.canvas
        coords = c.coords(item)
        if len(coords) < 4:
            return
        x1, y1, x2, y2 = coords[:4]
        fill   = _svg_color(c, c.itemcget(item, "fill"))
        stroke = _svg_color(c, c.itemcget(item, "outline"))
        sw     = c.itemcget(item, "width") or "1"
        dash   = _svg_dash(c.itemcget(item, "dash"))
        attrs: dict[str, str] = {
            "x": str(min(x1, x2)),   "y": str(min(y1, y2)),
            "width": str(abs(x2-x1)), "height": str(abs(y2-y1)),
            "fill": fill, "stroke": stroke, "stroke-width": sw,
        }
        if dash:
            attrs["stroke-dasharray"] = dash
        ET.SubElement(parent, "rect", attrs)

    # ════════════════════════════════════════════════════════════════════════
    # Cairo renderer (shared by PNG / PDF / PS / EPS)
    # ════════════════════════════════════════════════════════════════════════

    def _render_to_cairo(self, ctx, ox: float, oy: float) -> None:
        """Draw all visible canvas items into *ctx*, shifted by (-ox, -oy)."""
        if not _CAIRO_OK:
            raise RuntimeError("pycairo is not installed.")
        c = self.canvas
        ctx.translate(-ox, -oy)

        for item in c.find_all():
            if _item_is_hidden(c, item):
                continue
            if "selection_bbox" in set(c.gettags(item)):
                continue
            t = c.type(item)
            if   t == "line":      self._cr_line(ctx, item)
            elif t == "polygon":   self._cr_polygon(ctx, item)
            elif t == "text":      self._cr_text(ctx, item)
            elif t == "rectangle": self._cr_rect(ctx, item)

    # ── Cairo: line ─────────────────────────────────────────────────────

    def _cr_line(self, ctx, item: int) -> None:
        import cairo
        c = self.canvas
        coords = c.coords(item)
        if len(coords) < 4:
            return

        rgb = _tk_rgb(c, c.itemcget(item, "fill")) or (0.0, 0.0, 0.0)
        sw  = float(c.itemcget(item, "width") or 1)
        cap_str = (c.itemcget(item, "capstyle") or "butt").lower()
        cap_map = {"butt": cairo.LINE_CAP_BUTT,
                   "round": cairo.LINE_CAP_ROUND,
                   "projecting": cairo.LINE_CAP_SQUARE}
        ctx.set_line_cap(cap_map.get(cap_str, cairo.LINE_CAP_BUTT))
        ctx.set_line_width(sw)
        ctx.set_source_rgb(*rgb)

        dash_raw = c.itemcget(item, "dash") or ""
        ds = _svg_dash(dash_raw)
        if ds:
            try:
                ctx.set_dash([float(x) for x in ds.split()])
            except Exception:
                ctx.set_dash([])
        else:
            ctx.set_dash([])

        pts = [(coords[i], coords[i+1]) for i in range(0, len(coords), 2)]
        ctx.move_to(*pts[0])
        for pt in pts[1:]:
            ctx.line_to(*pt)
        ctx.stroke()

        # Arrows
        arrow = (c.itemcget(item, "arrow") or "none").strip().lower()
        if arrow != "none":
            a, b, av_c = _parse_arrowshape(c.itemcget(item, "arrowshape") or "")
            ctx.set_source_rgb(*rgb)
            ctx.set_dash([])
            if arrow in ("last", "both") and len(pts) >= 2:
                poly = _arrow_polygon(
                    pts[-2][0], pts[-2][1], pts[-1][0], pts[-1][1], a, b, av_c)
                self._cr_fill_poly(ctx, poly)
            if arrow in ("first", "both") and len(pts) >= 2:
                poly = _arrow_polygon(
                    pts[1][0], pts[1][1], pts[0][0], pts[0][1], a, b, av_c)
                self._cr_fill_poly(ctx, poly)

    @staticmethod
    def _cr_fill_poly(ctx, pts: list[tuple[float, float]]) -> None:
        if len(pts) < 3:
            return
        ctx.move_to(*pts[0])
        for p in pts[1:]:
            ctx.line_to(*p)
        ctx.close_path()
        ctx.fill()

    # ── Cairo: polygon ───────────────────────────────────────────────────

    def _cr_polygon(self, ctx, item: int) -> None:
        c = self.canvas
        coords = c.coords(item)
        if len(coords) < 6:
            return
        fill_rgb   = _tk_rgb(c, c.itemcget(item, "fill"))
        stroke_rgb = _tk_rgb(c, c.itemcget(item, "outline"))
        sw         = float(c.itemcget(item, "width") or 1)
        stipple    = (c.itemcget(item, "stipple") or "").strip()
        alpha_map  = {"gray12": 0.12, "gray25": 0.25,
                      "gray50": 0.50, "gray75": 0.75}
        alpha = alpha_map.get(stipple, 1.0)

        pts = [(coords[i], coords[i+1]) for i in range(0, len(coords), 2)]
        ctx.move_to(*pts[0])
        for pt in pts[1:]:
            ctx.line_to(*pt)
        ctx.close_path()

        if fill_rgb is not None:
            ctx.set_source_rgba(*fill_rgb, alpha)
            ctx.fill_preserve() if stroke_rgb is not None else ctx.fill()

        if stroke_rgb is not None:
            ctx.set_source_rgb(*stroke_rgb)
            ctx.set_line_width(sw)
            ctx.stroke()

    # ── Cairo: text ──────────────────────────────────────────────────────

    def _cr_text(self, ctx, item: int) -> None:
        c = self.canvas
        coords = c.coords(item)
        if len(coords) < 2:
            return
        text = c.itemcget(item, "text") or ""
        if not text:
            return
        x, y   = coords[0], coords[1]
        rgb    = _tk_rgb(c, c.itemcget(item, "fill")) or (0.0, 0.0, 0.0)
        anchor = (c.itemcget(item, "anchor") or "center").lower()
        font_str = c.itemcget(item, "font") or ""
        fam, sz_px, bold, italic = _parse_tk_font(font_str)

        ctx.set_source_rgb(*rgb)
        if _PANGO_OK:
            self._cr_text_pango(ctx, x, y, text, anchor,
                                fam, sz_px, bold, italic)
        else:
            self._cr_text_toy(ctx, x, y, text, anchor,
                              fam, sz_px, bold, italic)

    def _cr_text_pango(self, ctx, x, y, text, anchor,
                       fam, sz_px, bold, italic) -> None:
        layout = _PangoCairo.create_layout(ctx)
        desc = _Pango.FontDescription()
        desc.set_family(fam)
        desc.set_size(int(sz_px * _Pango.SCALE))
        desc.set_weight(_Pango.Weight.BOLD if bold else _Pango.Weight.NORMAL)
        desc.set_style(_Pango.Style.ITALIC if italic else _Pango.Style.NORMAL)
        layout.set_font_description(desc)
        layout.set_text(text, -1)

        _, lr = layout.get_pixel_extents()
        lw, lh = lr.width, lr.height

        tx = x - lw / 2.0
        if "w" in anchor:
            tx = x
        elif "e" in anchor:
            tx = x - lw

        ty = y - lh / 2.0
        if anchor.startswith("n"):
            ty = y
        elif anchor.startswith("s"):
            ty = y - lh

        ctx.move_to(tx, ty)
        _PangoCairo.show_layout(ctx, layout)

    def _cr_text_toy(self, ctx, x, y, text, anchor,
                     fam, sz_px, bold, italic) -> None:
        import cairo
        slant  = cairo.FONT_SLANT_ITALIC  if italic else cairo.FONT_SLANT_NORMAL
        weight = cairo.FONT_WEIGHT_BOLD   if bold   else cairo.FONT_WEIGHT_NORMAL
        ctx.select_font_face(fam, slant, weight)
        ctx.set_font_size(sz_px)
        ext = ctx.text_extents(text)
        tw, th = ext.width, ext.height

        tx = x - tw / 2.0
        if "w" in anchor:
            tx = x
        elif "e" in anchor:
            tx = x - tw

        # y_bearing is negative (ascent above baseline)
        base_off = -ext.y_bearing
        ty = y - th / 2.0 - ext.y_bearing
        if anchor.startswith("n"):
            ty = y + base_off
        elif anchor.startswith("s"):
            ty = y - th + base_off

        ctx.move_to(tx, ty)
        ctx.show_text(text)

    # ── Cairo: rectangle ─────────────────────────────────────────────────

    def _cr_rect(self, ctx, item: int) -> None:
        c = self.canvas
        coords = c.coords(item)
        if len(coords) < 4:
            return
        x1, y1, x2, y2 = coords[:4]
        fill_rgb   = _tk_rgb(c, c.itemcget(item, "fill"))
        stroke_rgb = _tk_rgb(c, c.itemcget(item, "outline"))
        sw  = float(c.itemcget(item, "width") or 1)
        dash= _svg_dash(c.itemcget(item, "dash") or "")

        rx, ry = min(x1, x2), min(y1, y2)
        rw, rh = abs(x2 - x1), abs(y2 - y1)
        ctx.rectangle(rx, ry, rw, rh)

        if fill_rgb is not None:
            ctx.set_source_rgb(*fill_rgb)
            ctx.fill_preserve() if stroke_rgb is not None else ctx.fill()

        if stroke_rgb is not None:
            ctx.set_source_rgb(*stroke_rgb)
            ctx.set_line_width(sw)
            if dash:
                try:
                    ctx.set_dash([float(v) for v in dash.split()])
                except Exception:
                    ctx.set_dash([])
            ctx.stroke()
            ctx.set_dash([])

    # ════════════════════════════════════════════════════════════════════════
    # PNG / JPEG
    # ════════════════════════════════════════════════════════════════════════

    def export_png(self, path: str, *, bg: str = "white", dpi: int = 300):
        if not _CAIRO_OK:
            raise RuntimeError("pycairo is required for PNG export.")
        import cairo

        ox, oy, w, h = self._content_bbox(pad=10)
        scale = max(1.0, dpi / 96.0)
        iw, ih = int(math.ceil(w * scale)), int(math.ceil(h * scale))

        surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, iw, ih)
        ctx = cairo.Context(surface)
        ctx.scale(scale, scale)

        bg_rgb = _tk_rgb(self.canvas, bg) or (1.0, 1.0, 1.0)
        ctx.set_source_rgb(*bg_rgb)
        ctx.paint()

        with self._suppress_hidden_tagged():
            self._render_to_cairo(ctx, ox, oy)

        surface.write_to_png(path)

    def export_jpg(self, path: str, *,
                   bg: str = "white", dpi: int = 300, quality: int = 95):
        if not _PIL_OK:
            raise RuntimeError("Pillow is required for JPEG export.")
        with tempfile.TemporaryDirectory() as td:
            png = os.path.join(td, "tmp.png")
            self.export_png(png, bg=bg, dpi=dpi)
            _PilImage.open(png).convert("RGB").save(
                path, "JPEG", quality=quality)

    # ════════════════════════════════════════════════════════════════════════
    # PDF / PS / EPS
    # ════════════════════════════════════════════════════════════════════════

    def export_pdf(self, path: str):
        if not _CAIRO_OK:
            raise RuntimeError("pycairo is required for PDF export.")
        import cairo
        ox, oy, w, h = self._content_bbox(pad=10)
        surf = cairo.PDFSurface(path, w, h)
        ctx  = cairo.Context(surf)
        ctx.set_source_rgb(1, 1, 1)
        ctx.paint()
        with self._suppress_hidden_tagged():
            self._render_to_cairo(ctx, ox, oy)
        surf.finish()

    def export_ps(self, path: str):
        self._cairo_ps(path, eps=False)

    def export_eps(self, path: str):
        self._cairo_ps(path, eps=True)

    def _cairo_ps(self, path: str, *, eps: bool):
        if not _CAIRO_OK:
            raise RuntimeError("pycairo is required for PS/EPS export.")
        import cairo
        ox, oy, w, h = self._content_bbox(pad=10)
        surf = cairo.PSSurface(path, w, h)
        if eps:
            surf.set_eps(True)
        ctx = cairo.Context(surf)
        ctx.set_source_rgb(1, 1, 1)
        ctx.paint()
        with self._suppress_hidden_tagged():
            self._render_to_cairo(ctx, ox, oy)
        surf.finish()

    # ════════════════════════════════════════════════════════════════════════
    # EMF (LibreOffice conversion)
    # ════════════════════════════════════════════════════════════════════════

    def export_emf(self, path: str):
        """Convert SVG → EMF via LibreOffice headless."""
        with tempfile.TemporaryDirectory() as td:
            svg_path = os.path.join(td, "export.svg")
            self.export_svg(svg_path)
            self._lo_convert(svg_path, "emf", path)

    @staticmethod
    def _find_libreoffice() -> str | None:
        for name in ("soffice", "libreoffice"):
            r = subprocess.run(["which", name],
                               capture_output=True, text=True)
            if r.returncode == 0 and r.stdout.strip():
                return r.stdout.strip()
        return None

    def _lo_convert(self, src: str, ext: str, dst: str) -> None:
        lo = self._find_libreoffice()
        if lo is None:
            raise RuntimeError(
                "LibreOffice not found. Install it to export this format.\n"
                "Alternatively export as SVG and convert manually."
            )
        with tempfile.TemporaryDirectory() as td:
            r = subprocess.run(
                [lo, "--headless", "--convert-to", ext, "--outdir", td, src],
                capture_output=True, timeout=60,
            )
            base = os.path.splitext(os.path.basename(src))[0]
            out  = os.path.join(td, f"{base}.{ext}")
            if not os.path.exists(out):
                raise RuntimeError(
                    f"LibreOffice conversion to {ext} failed.\n"
                    + r.stderr.decode(errors="replace")
                )
            import shutil
            shutil.move(out, dst)

    # ════════════════════════════════════════════════════════════════════════
    # VSDX (MS Visio 2013+)
    # ════════════════════════════════════════════════════════════════════════

    def export_vsdx(self, path: str):
        ox, oy, w, h = self._content_bbox(pad=10)
        shapes = self._vsdx_collect_shapes(ox, oy, h)
        self._vsdx_write(path, _px_to_in(w), _px_to_in(h), shapes)

    # ── VSDX coordinate helpers ───────────────────────────────────────────

    @staticmethod
    def _vsdx_x(x_px: float, ox: float) -> float:
        return _px_to_in(x_px - ox)

    @staticmethod
    def _vsdx_y(y_px: float, oy: float, h_px: float) -> float:
        """Tk y (top-down) → Visio y (bottom-up, inches)."""
        return _px_to_in(h_px - (y_px - oy))

    # ── VSDX shape collection ─────────────────────────────────────────────

    def _vsdx_collect_shapes(self, ox, oy, h_px) -> list[ET.Element]:
        c   = self.canvas
        out : list[ET.Element] = []
        sid = [1]          # mutable counter shared across helpers

        def next_id() -> int:
            v = sid[0]; sid[0] += 1; return v

        vx = lambda xp: self._vsdx_x(xp, ox)
        vy = lambda yp: self._vsdx_y(yp, oy, h_px)

        for item in c.find_all():
            if _item_is_hidden(c, item):
                continue
            if "selection_bbox" in set(c.gettags(item)):
                continue
            t = c.type(item)
            if t == "line":
                out.extend(self._vsdx_line(item, next_id, vx, vy))
            elif t == "polygon":
                el = self._vsdx_polygon(item, next_id(), vx, vy)
                if el is not None:
                    out.append(el)
            elif t == "text":
                el = self._vsdx_text(item, next_id(), vx, vy)
                if el is not None:
                    out.append(el)
            elif t == "rectangle":
                el = self._vsdx_rect(item, next_id(), vx, vy)
                if el is not None:
                    out.append(el)
        return out

    # ── VSDX: line ───────────────────────────────────────────────────────

    def _vsdx_line(self, item, next_id, vx, vy) -> list[ET.Element]:
        c = self.canvas
        coords = c.coords(item)
        if len(coords) < 4:
            return []

        stroke_hex = _svg_color(c, c.itemcget(item, "fill"))
        lw    = float(c.itemcget(item, "width") or 1)
        arrow = (c.itemcget(item, "arrow") or "none").lower()
        pts   = [(coords[i], coords[i+1]) for i in range(0, len(coords), 2)]
        n     = len(pts)
        out   = []

        for i in range(n - 1):
            x1i, y1i = vx(pts[i][0]),   vy(pts[i][1])
            x2i, y2i = vx(pts[i+1][0]), vy(pts[i+1][1])
            s = ET.Element("Shape", {"ID": str(next_id()), "Type": "Shape"})

            def cell(n_, v_): ET.SubElement(s, "Cell", {"N": n_, "V": str(v_)})

            cell("BeginX",      f"{x1i:.6f}")
            cell("BeginY",      f"{y1i:.6f}")
            cell("EndX",        f"{x2i:.6f}")
            cell("EndY",        f"{y2i:.6f}")
            cell("LineWeight",  f"{_px_to_in(lw):.6f}")
            cell("LineColor",   _hex_to_vsdx(stroke_hex))
            cell("FillPattern", "0")

            if i == 0 and arrow in ("first", "both"):
                cell("BeginArrow",     "4")
                cell("BeginArrowSize", "2")
            if i == n - 2 and arrow in ("last", "both"):
                cell("EndArrow",     "4")
                cell("EndArrowSize", "2")
            out.append(s)
        return out

    # ── VSDX: polygon ────────────────────────────────────────────────────

    def _vsdx_polygon(self, item, sid, vx, vy) -> ET.Element | None:
        c = self.canvas
        coords = c.coords(item)
        if len(coords) < 6:
            return None

        fill_hex   = _svg_color(c, c.itemcget(item, "fill"))
        stroke_hex = _svg_color(c, c.itemcget(item, "outline"))
        lw = float(c.itemcget(item, "width") or 0)
        pts_v = [(vx(coords[i]), vy(coords[i+1]))
                 for i in range(0, len(coords), 2)]

        # Bounding box in Visio space
        xs = [p[0] for p in pts_v]; ys = [p[1] for p in pts_v]
        bx, by = min(xs), min(ys)
        bw, bh = max(xs)-bx,  max(ys)-by

        s = ET.Element("Shape", {"ID": str(sid), "Type": "Shape"})
        def cell(n_, v_): ET.SubElement(s, "Cell", {"N": n_, "V": str(v_)})

        cell("PinX",    f"{bx:.6f}")
        cell("PinY",    f"{by:.6f}")
        cell("Width",   f"{max(bw, 1e-4):.6f}")
        cell("Height",  f"{max(bh, 1e-4):.6f}")
        cell("LocPinX", "0")
        cell("LocPinY", "0")

        if fill_hex != "none":
            cell("FillForegnd", _hex_to_vsdx(fill_hex))
        else:
            cell("FillPattern", "0")

        if stroke_hex != "none":
            cell("LineColor",  _hex_to_vsdx(stroke_hex))
            cell("LineWeight", f"{_px_to_in(lw):.6f}")
        else:
            cell("LinePattern", "0")

        geom = ET.SubElement(s, "Section", {"N": "Geometry", "IX": "0"})
        ET.SubElement(geom, "Cell", {"N": "NoFill",
                                     "V": "1" if fill_hex == "none" else "0"})
        for i, (px, py) in enumerate(pts_v):
            row_t = "MoveTo" if i == 0 else "LineTo"
            row = ET.SubElement(geom, "Row", {"IX": str(i), "T": row_t})
            ET.SubElement(row, "Cell", {"N": "X", "V": f"{px - bx:.6f}"})
            ET.SubElement(row, "Cell", {"N": "Y", "V": f"{py - by:.6f}"})
        # Close
        row = ET.SubElement(geom, "Row", {"IX": str(len(pts_v)), "T": "LineTo"})
        ET.SubElement(row, "Cell", {"N": "X", "V": f"{pts_v[0][0]-bx:.6f}"})
        ET.SubElement(row, "Cell", {"N": "Y", "V": f"{pts_v[0][1]-by:.6f}"})
        return s

    # ── VSDX: text ───────────────────────────────────────────────────────

    def _vsdx_text(self, item, sid, vx, vy) -> ET.Element | None:
        c = self.canvas
        coords = c.coords(item)
        if len(coords) < 2:
            return None
        text = c.itemcget(item, "text") or ""
        if not text:
            return None

        x, y   = coords[0], coords[1]
        fill_h = _svg_color(c, c.itemcget(item, "fill"))
        fam, sz_px, bold, _ = _parse_tk_font(c.itemcget(item, "font") or "")
        anchor = (c.itemcget(item, "anchor") or "center").lower()

        # Approximate bounding box
        est_w = len(text) * sz_px * 0.6
        est_h = sz_px * 1.5

        bx = vx(x - (0 if "w" in anchor else (est_w if "e" in anchor else est_w/2)))
        by = vy(y + (0 if anchor.startswith("n")
                     else (est_h if anchor.startswith("s") else est_h/2)))

        s = ET.Element("Shape", {"ID": str(sid), "Type": "Shape"})
        def cell(n_, v_): ET.SubElement(s, "Cell", {"N": n_, "V": str(v_)})

        cell("PinX",    f"{bx:.6f}")
        cell("PinY",    f"{by:.6f}")
        cell("Width",   f"{_px_to_in(est_w):.6f}")
        cell("Height",  f"{_px_to_in(est_h):.6f}")
        cell("LocPinX", "Width*0.5")
        cell("LocPinY", "Height*0.5")
        cell("FillPattern", "0")
        cell("LinePattern", "0")

        char = ET.SubElement(s, "Section", {"N": "Character", "IX": "0"})
        row0 = ET.SubElement(char, "Row", {"IX": "0"})
        ET.SubElement(row0, "Cell", {"N": "Color",
                                     "V": _hex_to_vsdx(fill_h)})
        ET.SubElement(row0, "Cell", {"N": "Size",
                                     "V": f"{_px_to_in(sz_px):.6f}"})
        if bold:
            ET.SubElement(row0, "Cell", {"N": "Style", "V": "17"})

        ET.SubElement(s, "Text").text = text
        return s

    # ── VSDX: rectangle ──────────────────────────────────────────────────

    def _vsdx_rect(self, item, sid, vx, vy) -> ET.Element | None:
        c = self.canvas
        coords = c.coords(item)
        if len(coords) < 4:
            return None
        x1, y1, x2, y2 = coords[:4]
        fill_h   = _svg_color(c, c.itemcget(item, "fill"))
        stroke_h = _svg_color(c, c.itemcget(item, "outline"))
        lw = float(c.itemcget(item, "width") or 1)

        vx1, vy1 = vx(min(x1,x2)), vy(max(y1,y2))  # bottom-left in Visio
        vw  = _px_to_in(abs(x2-x1))
        vh  = _px_to_in(abs(y2-y1))

        s = ET.Element("Shape", {"ID": str(sid), "Type": "Shape"})
        def cell(n_, v_): ET.SubElement(s, "Cell", {"N": n_, "V": str(v_)})

        cell("PinX",    f"{vx1:.6f}")
        cell("PinY",    f"{vy1:.6f}")
        cell("Width",   f"{vw:.6f}")
        cell("Height",  f"{vh:.6f}")
        cell("LocPinX", "0")
        cell("LocPinY", "0")

        if fill_h != "none":
            cell("FillForegnd", _hex_to_vsdx(fill_h))
        else:
            cell("FillPattern", "0")

        if stroke_h != "none":
            cell("LineColor",  _hex_to_vsdx(stroke_h))
            cell("LineWeight", f"{_px_to_in(lw):.6f}")
        else:
            cell("LinePattern", "0")
        return s

    # ── VSDX: ZIP assembly ────────────────────────────────────────────────

    def _vsdx_write(self, path: str,
                    pw_in: float, ph_in: float,
                    shapes: list[ET.Element]) -> None:

        NS_PKG  = "http://schemas.openxmlformats.org/package/2006/content-types"
        NS_REL  = "http://schemas.openxmlformats.org/package/2006/relationships"
        NS_VIS  = "http://schemas.microsoft.com/office/visio/2012/main"
        NS_R    = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
        REL_DOC = "http://schemas.microsoft.com/visio/2010/relationships/document"
        REL_PG  = "http://schemas.microsoft.com/visio/2010/relationships/page"

        # [Content_Types].xml
        ct = ET.Element("Types", {"xmlns": NS_PKG})
        ET.SubElement(ct, "Default", {"Extension": "rels",
            "ContentType": "application/vnd.openxmlformats-package.relationships+xml"})
        ET.SubElement(ct, "Default", {"Extension": "xml",
            "ContentType": "application/xml"})
        ET.SubElement(ct, "Override", {
            "PartName": "/visio/document.xml",
            "ContentType": "application/vnd.ms-visio.drawing.main+xml"})
        ET.SubElement(ct, "Override", {
            "PartName": "/visio/pages/page1.xml",
            "ContentType": "application/vnd.ms-visio.page+xml"})

        # _rels/.rels
        root_rels = ET.Element("Relationships", {"xmlns": NS_REL})
        ET.SubElement(root_rels, "Relationship", {
            "Id": "rId1", "Type": REL_DOC,
            "Target": "visio/document.xml"})

        # visio/_rels/document.xml.rels
        doc_rels = ET.Element("Relationships", {"xmlns": NS_REL})
        ET.SubElement(doc_rels, "Relationship", {
            "Id": "rId1", "Type": REL_PG,
            "Target": "pages/page1.xml"})

        # visio/pages/_rels/page1.xml.rels  (empty)
        pg_rels = ET.Element("Relationships", {"xmlns": NS_REL})

        # visio/document.xml
        doc = ET.Element("VisioDocument", {
            "xmlns":   NS_VIS,
            "xmlns:r": NS_R,
        })
        ET.SubElement(doc, "DocumentSheet")
        pages = ET.SubElement(doc, "Pages")
        pg    = ET.SubElement(pages, "Page", {"ID": "0", "NameU": "Page-1",
                                               "Name": "Page-1"})
        psheet = ET.SubElement(pg, "PageSheet")
        for n, v in [("PageWidth",  f"{pw_in:.6f}"),
                     ("PageHeight", f"{ph_in:.6f}"),
                     ("DrawingScale",    "1"),
                     ("DrawingSizeType", "0")]:
            ET.SubElement(psheet, "Cell", {"N": n, "V": v})
        ET.SubElement(pg, "Rel", {"{%s}id" % NS_R: "rId1"})

        # visio/pages/page1.xml
        pc = ET.Element("PageContents", {
            "xmlns":           NS_VIS,
            "xmlns:r":         NS_R,
            "xml:space":       "preserve",
        })
        sh_el = ET.SubElement(pc, "Shapes")
        for s in shapes:
            sh_el.append(s)
        ET.SubElement(pc, "Connects")

        def to_bytes(el: ET.Element) -> bytes:
            ET.indent(el, space="  ")
            return (b'<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
                    + ET.tostring(el, encoding="unicode").encode("utf-8"))

        with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as zf:
            zf.writestr("[Content_Types].xml", to_bytes(ct))
            zf.writestr("_rels/.rels",          to_bytes(root_rels))
            zf.writestr("visio/document.xml",   to_bytes(doc))
            zf.writestr("visio/_rels/document.xml.rels", to_bytes(doc_rels))
            zf.writestr("visio/pages/page1.xml",         to_bytes(pc))
            zf.writestr("visio/pages/_rels/page1.xml.rels", to_bytes(pg_rels))
