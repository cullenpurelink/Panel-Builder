# PureLink Product Icon Library

Small isometric "cartoon box" icons for individual products, generated directly from
Panel Builder's own layout data (`data/library/*.json`) rather than hand-drawn.

## The golden rule

**Files in this folder are never hand-edited.** Every icon is produced by
[`../product-icon-generator.html`](../product-icon-generator.html) reading the product's
layout JSON. To change an icon, change the generator (or the underlying product data) and
re-run it — never touch the PNG/SVG directly.

## Generating icons for a finished panel

Once a panel design in Panel Builder (`index.html`) is in `data/library/` (exported as a
"Layout file" and listed in `data/library/manifest.json` — see that file's own workflow), its
icons are available with **no code change**: the generator reads `manifest.json` dynamically
and lists every product in it.

1. Open [`../product-icon-generator.html`](../product-icon-generator.html) through the dev
   server — `start.bat`, or `http://localhost:8743/system-diagrams/product-icon-generator.html`
   — not as a `file://` page (it needs the server both to fetch `data/library/*.json` and to
   save files back).
2. Find the product's card and check all 4 views look right.
3. Click that card's **"Save to library"** button — it writes the 4 SVG + 4 PNG files straight
   into this folder via `tools/dev_server.py`'s `/api/save-product-icon` route (the same pattern
   as the Hub's existing "Push to GitHub" button). No manual download-and-move.
4. **"Save all to library"** (top of the page, once generation finishes) re-saves every product
   in the manifest in one go — use this after a change to the generator itself (a shape, colour,
   or geometry fix) so every icon picks it up, not just the one you were working on.

The per-view **SVG / PNG buttons** still trigger a normal browser download instead — useful for
a one-off copy, or if you're previewing the page without the dev server running.

## Technique

Same visual language as `assets/rooms/` and `assets/classroom_system/` (see
`../assets/README.md` for the full style guide), applied per-product instead of per-scene:

- The front/rear **panel face is drawn completely flat**, in ordinary top-left-origin 2D
  coordinates (a square-cornered chassis bar plus realistic port-shape approximations at
  their real relative X positions from the layout JSON — no inset bezel, no brand mark on
  this face) — exactly like a normal panel elevation. It is then mapped onto the isometric
  face with a single SVG `matrix(a,b,c,d,e,f)` affine transform, not by projecting each
  element in 3D. This is the same trick the classroom masters use (confirmed by inspecting
  their SVG source directly).
- The **"PureLink" wordmark sits centred on the top face**, sheared with its own affine map (same
  idea as the front content, not a flat/horizontal label and not a pure rotation — a rigid
  rotation is literally what italic text is, and reads as a sticker rather than paint lying on
  the surface). Right-facing and left-facing each use their own hand-tuned basis-vector pair,
  not mirror images of each other — see "Why the top wordmark isn't computed from a mirror"
  below. Rear views negate both basis vectors (a 180° flip): it's a fixed label on the real top
  surface, so viewing the unit from its rear genuinely shows that same label upside-down.
- The top and side faces are plain flat-shaded polygons behind it, using the exact three
  greys from the style guide: front `#3F4145`, side `#4A4C50`, top `#5A5C60`. No gradients,
  no stroke outlines.
- 30° isometric, 1.8× scale — the same `SCALE = 1.78` constant as the rest of the library.
- **Housing depth**: used directly from `housing.depth` in the product JSON when known
  (e.g. PT-PSW-21HC-KVM, 122mm). When `null`, assumed as `clamp(width × 0.46, 50, 110)` mm —
  the 46% ratio comes from the one product where real depth is known, as a better-than-nothing
  default. Real depths from a spec sheet, when available, are always preferable — pass them
  in `housing.depth` instead of relying on the guess.
- **Left-facing is a true mirror, not a second 3D configuration.** In 30° isometric, once the
  front face's orientation is fixed there is exactly one depth direction that reads right-side
  up — the other mathematically-available option reads as viewed-from-below (confirmed by
  trying it). So left-facing is built by literally mirroring the whole right-facing box
  (flips left/right only, never up/down, so it can never look upside-down). The front content's
  own affine map is independently rebuilt (swapped corner-correspondence) on the mirror side so
  its text comes out right-reading rather than mirrored.

### Why the top wordmark isn't computed from a mirror

This went through several wrong attempts worth recording so they aren't retried:

1. **Mapped through the top face's own corner correspondence**, same as the front content —
   came out backwards (the correspondence's natural handedness is reflective here, unlike the
   front face's). Swapping the corners to fix the reflection just rotates it 180° instead (both
   have positive determinant; "not mirrored" doesn't mean "right-side up") — came out upside-down.
2. **Drawn flat/horizontal, no shear at all** — reads as a sticker pasted on top rather than
   paint on the surface; nothing in a true isometric drawing sits at a flat 0°, every real edge
   runs along the ±30° grid.
3. **A pure rotation by 30°/-30°** (rigid, undistorted letters) — this is, by definition, what
   italic text is. It got the angle right but not the "lying flat on a tilted plane" look.
4. **A genuine shear, but using the same basis pattern for both sides** (mirroring or negating
   right-facing's basis to get left-facing's) — always either reflects the text or reproduces
   the italic look on one side, because the two sides' basis vectors are not simple mirrors of
   each other mathematically.

The working version (current code) gives right-facing and left-facing **independent, hand-tuned
basis-vector pairs**, confirmed by direct visual comparison against reference images rather than
derived algebraically from one another:
- Right-facing: `bx = STEP_RIGHT`, `by = -STEP_BACK`
- Left-facing: `bx = STEP_BACK`, `by = STEP_RIGHT`
- Rear views: negate both `bx` and `by` (keeps the determinant sign, flips 180°)

If either side's wordmark ever needs revisiting, change only that side's basis pair and
re-confirm both sides visually — they are not derivable from each other.

## Port shapes

Real connector-family silhouettes sized after the actual connectors (e.g. USB-C and USB-A are
wide and flat, not tall — a tall "pill" reads as a circle; HDMI is short and wide with its
wider edge on top), **not** colour-coded by cable type — every port is the same dark "recessed"
shade (`#202124`) with a thin lighter rim for definition, so the icon reads as a product, not
a legend. LEDs keep their own real lit colour with a soft glow, and sit in their own row near
the bottom edge, separate from and smaller than the connector row above them, so the panel
doesn't read as one uniform strip of same-sized dots:

| Shape | Used for |
|---|---|
| Circle, small, thin rim | 3.5mm jack |
| Circle, larger, inner dark dot | DC/barrel power (dc21, din4, dcnut, dclock) |
| Rectangle, squarish | RJ45 / RJ45 low-profile / SFP |
| Rectangle, wide and flat | USB-A / USB-B |
| Rounded capsule, wide and flat | USB-C |
| Trapezoid, wide and short, wider on top | HDMI |
| Rectangle + screw dots | Euroblock/terminal (eb35 family), dot count from `pins` |
| Square, raised fill, **blue edge** (`#A9E3FF`) | Buttons — matches the real button style |
| Raised circle/square (lighter `#6b6e73`, darker rim) | DIP, reset, pinhole, ground, slide — raised, not recessed, no blue edge |
| Small glowing dot, near the bottom edge | LED, using its real `color` field (red/green/amber/blue) when present |

Any future port `type` not listed above falls back to a plain raised nub rather than erroring.

## Register

The product list is **not** hardcoded here or in the generator — it's always whatever
`data/library/manifest.json` currently lists, fetched at page load. As of this writing that's
10 products (`HDP-EUB40CD-TX-DE0012`, `PT-PSW-21HC-KVM`, `PT-POE-4AV`, `PT-POE-8AV`,
`8 port Switch V1`, `IPAV - 3x1 Tranceiver V0.2`, `PT-HDBT-150`, `PT-CON-PEX-110`,
`PT-PSW-21KVM-40G RX`, `PT-PSW-21KVM-40G TX`) — treat that list as a snapshot, not a source of
truth; `manifest.json` always has the current count.

Some SKUs aren't filename-safe as written (spaces, mixed case, punctuation — e.g.
`8 port Switch V1`, `IPAV - 3x1 Tranceiver V0.2`), so the generator slugs the SKU for filenames
via `slug()` (e.g. `8-port-Switch-V1`) — the on-screen card title and the SVG's own content
still show the real `sku` field unchanged.

Each product has 4 files × 2 formats: `Product_<slug>_Front-Right`, `_Front-Left`,
`_Rear-Right`, `_Rear-Left`, as `.svg` and `.png` (PNG rasterised at 3× for crispness when
scaled down).

## Next steps (not built yet, on purpose)

A declarative scene-description file (room + placed devices + connections) is the real
answer to reliably reproducing a full room diagram from a text description — see the
roadmap in `../assets/README.md`. These icons are the vocabulary that step needs; building
the scene format itself is a separate next task.
