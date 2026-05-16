# How to export the canvas

TimeIt can export the timing diagram canvas to several image and vector formats for use in documents and presentations.

## Supported formats

| Format | Extension | Notes |
|---|---|---|
| PNG | `.png` | Raster image, suitable for web and office documents |
| SVG | `.svg` | Scalable vector, ideal for technical documents |
| PDF | `.pdf` | Portable vector format |
| EPS | `.eps` | PostScript vector, common in LaTeX workflows |
| EMF | `.emf` | Windows Enhanced Metafile (vector, for Microsoft Office) |
| JPEG | `.jpg` | Raster image with lossy compression |

## Exporting via the menu

**File → Export…** opens an export dialog where you can choose the format and output path.

> **TODO:** Add screenshot of the Export dialog.

## Exporting via the TCL console

Use the `canvas_export` command (or equivalent) from the console:

> **TODO:** Confirm the exact TCL export command name and syntax against `classes/canvasexporter.py`.

```tcl
# Example (confirm exact command):
canvas_export -file "output.svg" -format svg
canvas_export -file "output.png" -format png
canvas_export -file "output.pdf" -format pdf
```

## Tips

- **SVG and PDF** preserve full vector quality at any zoom level — prefer these for documentation.
- **PNG** is the most universally compatible raster format; use a high DPI setting if available.
- **EMF** is useful when embedding the diagram into Microsoft Word or PowerPoint.
- The exported image captures the visible area of the canvas. Scroll or zoom to frame the desired portion before exporting.

> **TODO:** Add side-by-side screenshots showing example exports in different formats.

---

*Previous: [How to show the background grid](07_grid.md) | Next: [How to create timing annotations](09_annotations.md)*
