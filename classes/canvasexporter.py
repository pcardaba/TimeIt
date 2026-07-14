"""
CanvasExporter — rewritten from scratch.

Supported output formats:
  SVG   Hand-crafted XML; correct Tk arrowshape, all item types.
  PNG   Cairo ImageSurface + Pango text (no Ghostscript dependency).
  JPEG  PNG → Pillow JPEG conversion.
  PDF   Cairo PDFSurface.
  PS    Cairo PSSurface.
  EPS   Cairo PSSurface (EPS flag).

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
import tempfile
import contextlib
import xml.etree.ElementTree as ET
import tkinter as tk
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

        text_anchor  = ("start" if anchor in ("w", "nw", "sw")
                        else ("end" if anchor in ("e", "ne", "se") else "middle"))
        dominant_bl  = ("hanging" if anchor in ("n", "nw", "ne")
                        else ("auto" if anchor in ("s", "sw", "se") else "middle"))

        font_str = c.itemcget(item, "font") or ""
        fam, sz_px, bold, italic = _parse_tk_font(font_str)

        # Tk anchor="s": y is bounding-box BOTTOM = alphabetic baseline + descent.
        # SVG dominant-baseline="auto": y is the alphabetic baseline.
        # Shift y up by the actual font descent so both renderers agree.
        if anchor in ("s", "sw", "se"):
            try:
                f = (tkfont.Font(font=font_str) if font_str
                     else tkfont.nametofont("TkDefaultFont"))
                y -= f.metrics("descent")
            except Exception:
                y -= sz_px * 0.2

        # Tk anchor="n": y is bounding-box TOP = alphabetic baseline - ascent.
        # SVG dominant-baseline="hanging" is close but not exact; convert to the
        # precise alphabetic baseline instead.
        if anchor in ("n", "nw", "ne"):
            try:
                f = (tkfont.Font(font=font_str) if font_str
                     else tkfont.nametofont("TkDefaultFont"))
                y += f.metrics("ascent")
                dominant_bl = "auto"
            except Exception:
                y += sz_px * 0.8

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
        if anchor in ("w", "nw", "sw"):
            tx = x
        elif anchor in ("e", "ne", "se"):
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
        if anchor in ("w", "nw", "sw"):
            tx = x
        elif anchor in ("e", "ne", "se"):
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

