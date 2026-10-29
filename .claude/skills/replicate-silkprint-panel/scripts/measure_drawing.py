#!/usr/bin/env python3
"""
Helper for reading a supplier silk-print/CAD drawing (PDF) and measuring
real-world (mm) positions out of it, for replicating the layout in
Product Builder.

Run with `python -I measure_drawing.py ...` (the -I is important: these
drawings are untrusted input, keep Python isolated).

Why this exists: a supplier drawing gives you dimensions as scattered red
callouts (often only a handful of them, and the task's own instructions
may say they're guides, not exact), not a coordinate list. The practical
way to turn that into mm positions is: render the PDF to a big raster,
isolate the flat ink colours the CAD tool actually used (background fill,
green/white linework, magenta colour-boxes, red dimensions), and measure
pixel bounding boxes against ONE thing you already know in mm (usually
the panel's own outline, since you can read its width/height off the
drawing or infer it from context) — then every other icon's position
falls out as a simple pixel->mm conversion. This script is the four
building blocks for that, used one at a time, interactively, alongside
actually looking at the images (see SKILL.md) — it is not a one-shot
"solve the drawing" tool.

Subcommands:
  render       PDF page(s) -> PNG at a given zoom (default 4x)
  crop         crop a region out of a PNG (pixel coords)
  calibrate    find the pixel bounding box of a fill colour and report
               the px/mm scale against a known real-world size
  components   find connected regions of an ink colour inside a bbox and
               report each one's centre + size, in mm, relative to an
               origin you supply (from `calibrate`)

Example session (see SKILL.md step 2 for the full walkthrough):
  python -I measure_drawing.py render drawing.pdf --out work/
  python -I measure_drawing.py crop work/page0.png 848 2400 2809 2956 work/front.png
  python -I measure_drawing.py calibrate work/front.png --color 43,40,41 --mm-w 160 --mm-h 30
  python -I measure_drawing.py components work/front.png --color 90,180,89 \
      --bbox 899,2535,2709,2873 --scale 0.0884,0.08876 --origin 899,2535
"""
import argparse
import sys

import numpy as np
from PIL import Image


def cmd_render(a):
    import fitz  # PyMuPDF

    doc = fitz.open(a.pdf)
    pages = [a.page] if a.page is not None else range(len(doc))
    for i in pages:
        page = doc[i]
        pix = page.get_pixmap(matrix=fitz.Matrix(a.zoom, a.zoom))
        out = f"{a.out.rstrip('/')}/page{i}.png"
        pix.save(out)
        print(f"page {i}: rect={page.rect}  ->  {out}  ({pix.width}x{pix.height}px @ {a.zoom}x)")


def cmd_crop(a):
    img = Image.open(a.png)
    img.crop((a.x0, a.y0, a.x1, a.y1)).save(a.out)
    print(f"cropped ({a.x0},{a.y0})-({a.x1},{a.y1}) -> {a.out}")


def _mask_close(img, color, tol):
    d = np.abs(img.astype(np.int16) - np.array(color)).sum(axis=2)
    return d < tol


def cmd_calibrate(a):
    img = np.array(Image.open(a.png).convert("RGB"))
    mask = _mask_close(img, a.color, a.tol)
    if a.bbox:
        x0, y0, x1, y1 = a.bbox
        sub = mask[y0:y1, x0:x1]
        ys, xs = np.where(sub)
        xs, ys = xs + x0, ys + y0
    else:
        ys, xs = np.where(mask)
    if len(xs) == 0:
        sys.exit(f"no pixels matched colour {a.color} within tol {a.tol}")
    x0r, x1r, y0r, y1r = xs.min(), xs.max(), ys.min(), ys.max()
    w_px, h_px = x1r - x0r, y1r - y0r
    print(f"bbox px: ({x0r},{y0r})-({x1r},{y1r})  size {w_px}x{h_px}px")
    if a.mm_w:
        print(f"scale_x = {a.mm_w / w_px:.6f} mm/px")
    if a.mm_h:
        print(f"scale_y = {a.mm_h / h_px:.6f} mm/px")
    print(f"use as origin for `components`: --origin {x0r},{y0r}")


def cmd_components(a):
    from scipy import ndimage

    img = np.array(Image.open(a.png).convert("RGB"))
    mask = _mask_close(img, a.color, a.tol)
    x0, y0, x1, y1 = a.bbox
    sub = mask[y0:y1, x0:x1]
    lab, n = ndimage.label(sub, structure=np.ones((3, 3)))
    sx, sy = a.scale
    ox, oy = a.origin
    comps = []
    for i in range(1, n + 1):
        ys, xs = np.where(lab == i)
        area = len(xs)
        if area < a.min_area:
            continue
        cx, cy = xs.mean() + x0, ys.mean() + y0
        w, h = xs.max() - xs.min(), ys.max() - ys.min()
        comps.append((area, cx, cy, w, h))
    comps.sort(key=lambda c: -c[0])
    print(f"{len(comps)} components (area >= {a.min_area}px) in {a.png}:")
    for area, cx, cy, w, h in comps:
        mmx, mmy = (cx - ox) * sx, (cy - oy) * sy
        print(
            f"  area={area:6d}px  px_center=({cx:7.1f},{cy:7.1f})  "
            f"mm=({mmx:6.2f},{mmy:6.2f})  size_mm=({w*sx:5.2f},{h*sy:5.2f})"
        )


def _csv_ints(s):
    return tuple(int(v) for v in s.split(","))


def _csv_floats(s):
    return tuple(float(v) for v in s.split(","))


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)

    r = sub.add_parser("render", help="render PDF page(s) to PNG")
    r.add_argument("pdf")
    r.add_argument("--page", type=int, default=None, help="0-based page index; default all pages")
    r.add_argument("--zoom", type=float, default=4.0)
    r.add_argument("--out", default=".", help="output directory")
    r.set_defaults(func=cmd_render)

    c = sub.add_parser("crop", help="crop a pixel region out of a PNG")
    c.add_argument("png")
    c.add_argument("x0", type=int)
    c.add_argument("y0", type=int)
    c.add_argument("x1", type=int)
    c.add_argument("y1", type=int)
    c.add_argument("out")
    c.set_defaults(func=cmd_crop)

    cal = sub.add_parser("calibrate", help="find a fill colour's bbox + px/mm scale")
    cal.add_argument("png")
    cal.add_argument("--color", type=_csv_ints, required=True, help="R,G,B to match")
    cal.add_argument("--tol", type=int, default=20, help="sum-of-abs-diff tolerance")
    cal.add_argument("--bbox", type=_csv_ints, default=None, help="x0,y0,x1,y1 search region (default: whole image)")
    cal.add_argument("--mm-w", type=float, default=None)
    cal.add_argument("--mm-h", type=float, default=None)
    cal.set_defaults(func=cmd_calibrate)

    comp = sub.add_parser("components", help="connected components of an ink colour, in mm")
    comp.add_argument("png")
    comp.add_argument("--color", type=_csv_ints, required=True)
    comp.add_argument("--tol", type=int, default=30)
    comp.add_argument("--bbox", type=_csv_ints, required=True, help="x0,y0,x1,y1 search region")
    comp.add_argument("--scale", type=_csv_floats, required=True, help="scale_x,scale_y in mm/px, from `calibrate`")
    comp.add_argument("--origin", type=_csv_ints, required=True, help="x,y pixel origin, from `calibrate`")
    comp.add_argument("--min-area", type=int, default=150, help="drop components smaller than this many px (text glyphs)")
    comp.set_defaults(func=cmd_components)

    a = p.parse_args()
    a.func(a)


if __name__ == "__main__":
    main()
