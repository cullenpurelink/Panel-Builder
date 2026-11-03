# Layout JSON & PORTS catalog cheat-sheet

Snapshot taken 2026-10-28 from `index.html`'s `const PORTS = {` block and the
example files in `data/library/`. This is a shortcut to avoid re-reading the
whole (huge) `index.html` every time — but it's a snapshot, not a contract.
If a type you need isn't here, or a field doesn't behave as described, grep
`index.html` for the real thing (`grep -n "type: 'yourtype'"` or just
`PORTS = {`) rather than guessing. Hand-authored JSON gets loaded as-is: none
of the catalog's `def` (defaults) are applied automatically the way they are
when a part is dragged in through the UI, so **every field a part needs has
to be in the JSON explicitly** (rotation, lock, colorBox, pins, etc.) — don't
assume a default will kick in.

## File shape

```jsonc
{
  "format": "purelink-panel-layout",
  "version": 3,
  "sku": "...",
  "name": "...",
  "logoSvg": "",
  "chassis": { "form": "std", "height": 30, "width": 160 },
  "housing": { "depth": 110 },
  "panels": { "front": [ /* items */ ], "rear": [ /* items */ ] },
  "rules": {
    "fontWeight": 400, "edgeClearance": 3, "minGap": 1, "labelGap": 1,
    "autoNumber": false, "upper": false, "fontPt": 0,
    "alignLabels": true, "alignRange": 4
  },
  "render": {},
  "validation": { "cutouts": [ /* strings */ ], "silkscreen": [ /* strings */ ] }
}
```

- `chassis.width` = the panel's **left-right** extent as you look at the
  front or rear face (the long dimension on a typical slim extender).
  `chassis.height` = the panel's **vertical** extent. Both panels share the
  same size — it's one enclosure's two end-caps.
- `housing.depth` is the enclosure's front-to-back depth; it's informational
  (shown in the Housing tab), not the panel's own width/height.
- Every item needs a unique `id` (any string). Frames reference items by id
  in `members`.

## Item kinds

| kind | purpose | key fields |
|---|---|---|
| `logo` | the PureLink wordmark + category badge | `cat` (badge text, e.g. `"LX"`, `"SWITCH"`, `"HDBT"`), `showBox`, `scale`, `style` (`"inline"` normal, `"stacked"` for 1U rack), `x`,`y` (centre) |
| `port` | any connector/LED/switch/hole | `type` (key into `PORTS`, see table below), `func` (its own label text), `label` (override text), `sub` (small label above), `x`,`y`, `rot`, plus type-specific fields |
| `frame` | a bracket/box grouping several ports with a shared title | `members` (array of item ids), `title`, `titlePos` (`"top"` or `"bottom"`), `pad`, `padTop`, `padBottom` |
| `text` | free-standing text | `text`, `pt` (size), `weight`, `x`,`y`, `rot` |
| `dash` | a short dash between two ports (visual separator) | `members: [idA, idB]` |

### Logo badge

The badge box is **always the tool's fixed blue**, with the badge text drawn
in the panel's own dark face colour (a "knockout" look) — this is the house
style, not something to override to match a supplier drawing that shows the
badge text in white; trust the tool's own convention here. The wordmark and
badge sizing (18.4×3.5mm vs 21×4mm, badge padding, etc.) come straight from
the PureTools Silkprint style guide and depend only on `chassis.height` (a
`<27` vs `>=27` threshold) — you don't need to compute pixel sizes for this,
just set `cat` and a reasonable `x`/`y` and look at the render.

### Frames — the part that's easy to get backwards

`titlePos` controls **which side gets the frame's own title, and (just as
important) which side each member's own label ends up on**:

- `titlePos: "bottom"` → title at the bottom; each member's own `func` label
  renders **above** the member, same as if there were no frame at all.
- `titlePos: "top"` → title at the top; each member's own `func` label
  renders as a **line label** — breaking the frame's *bottom* border line,
  so the port's name sits right on the box edge (e.g. "OUTPUT" title on top,
  "VCX" written into the bottom border of the same box).

Read the source drawing's actual pixel layout to tell which of these you
need — don't assume "DEVICE"-style groupings always use one or the other;
different products (and, after a rotation fix, the same product) can use
either.

### The 180°-rotation trap

If part of the source drawing is rotated 180° (upside-down relative to how
the panel actually sits), correcting it is **not** just mirroring x. A
genuine 180° rotation flips **both** axes about the panel's centre:

```
real_x = chassis.width  - raw_x
real_y = chassis.height - raw_y
```

Flipping y means **top and bottom swap too** — so if, in the as-drawn
(rotated) image, a frame's title sits at the pixel-bottom and a port's own
label sits at the pixel-top, then in the real/corrected panel the title
belongs at the **top** and the port's label at the **bottom** (i.e. the
`titlePos` you pick is the *opposite* of what the rotated image looks like
it's showing). Work this out freshly from the actual pixels each time —
don't pattern-match to an unrelated example file that happens to use the
other convention.

Two ways to actually apply the correction, both fine — pick whichever is
less error-prone for the case in front of you:

1. Apply the `real_x`/`real_y` formula above to each measured point.
2. Or just rotate the working image/crop 180° first (flip it in Pillow,
   or re-render/re-crop upside down) and measure positions directly off
   the now-right-side-up picture. This avoids compounding a sign mistake
   across dozens of points, and reads more naturally since you're looking
   at text the right way up while you measure it.

Either way, **check your own correction** before trusting it: look for
something in the drawing with a known or sensible order — a Phoenix/
terminal-block pin sequence (e.g. `TX, [gnd], RX`, or `L+, L−, [gnd], R+,
R−`), or numbered ports that should read ascending left-to-right — and
confirm it comes out sensible (not reversed) after your correction, not
just mirrored. A pin order that still reads backwards after "correction"
means you only mirrored x and missed the y-flip.

### A small icon above a jack is a lock hole until proven otherwise

The single most common misreading in every run of this skill so far,
including the one that wrote the first version of this cheat-sheet: a
small icon sitting directly above an HDMI or USB-C connector is that
connector's own **locking-screw insert** (`"lock": true` on the port
item itself) — not a separate `ground` part, and not a separate unlabelled
`led`. Default to that reading for any such icon; treat a genuine
standalone ground screw or indicator LED at that position as the
exception, not the default, and only model one when something about the
drawing actively rules out a lock hole (wrong offset — see below — or a
func label that names a ground pin specifically, e.g. `[gnd]`, rather
than just sitting silently above the jack).

Mechanically: `"lock": true` draws a small retention-screw circle
**above** the port (not below — `lockY` is negative, i.e. up), a few mm
off at a fixed `dist` per type (`usbc` is 6.8mm, `hdmi` is 10.5mm — HDMI's
is drawn as a more detailed "insert" graphic, which is exactly the
hex/washer look that's easy to mistake for a `ground` part at a glance).
At a glance a lock hole can also look like a stray grid dot. Zoom into a
screenshot before concluding one didn't render, and before adding a
`ground` item to explain an icon you've spotted — check whether the
jack's own `lock` feature already accounts for it first (measure the
icon's offset from the port and compare to `PORTS[type].lock.dist`; a
real ground screw sits elsewhere, e.g. near a panel edge or seam, not
hugging a specific jack).

One practical consequence: because the lock hole is part of the port's
*own* geometry (not a separate item you place), it's included automatically
in that port's edge-clearance and overlap checks — you don't add a second
item or a frame member for it, you just set `"lock": true` and verify the
port's own position gives the hole enough room (see "Two things that
actually went wrong" in `SKILL.md` for what happens when it doesn't).

### What's drawn but isn't silkscreen

Supplier CAD art sometimes includes the **connector manufacturer's own
part art**, e.g. an "Amphenol" (or similar) wordmark moulded into an RJ45
or USB jack's outline — that's reference detail for the mechanical
drawing, not something printed on the panel. Leave it out of `func`/
`label`/`sub` entirely; it has no equivalent in the `PORTS` catalog's own
connector art either (that art is generic, not brand-specific).

## Common `PORTS` types

| `type` | what it is | notes |
|---|---|---|
| `usbc` | USB-C jack | `cbox:[12,6]` blue colour-box option (`colorBox:true`); `lock:{dist:6.8}`; default silkprint `rot:0` (horizontal) — set `rot:90` explicitly for a vertical one (e.g. a "SERVICE" port drawn standing up) |
| `usba` | USB-A jack | drawn **vertical by default in the real product** (`def.rot:90`) — set `"rot": 90` explicitly in hand-written JSON, it is not applied for you |
| `usbb` | USB-B jack | rarer, same idea |
| `rj45` | RJ45 jack | `cbox:[19.3,16]`, `cboxColor: MAGENTA` (≈ Pantone 240C) — this is the standard "HDBaseT colour box"; set `colorBox:true` to show it |
| `rj45lp` | RJ45, low-profile | smaller body (16.6×11.8mm vs 17×13.6mm) — use when the real part sits flush/shallow |
| `hdmi`, `dp`, `bnc`, `sfp`, `lc`, `sma` | video/network jacks | as named |
| `dc21`, `din4`, `eb508`, `dclock`, `dcnut` | power jacks | pick by the connector shape in the drawing |
| `eb35` / `eb35p2` / `eb35p5` / `eb35x2` | Phoenix/terminal block, 3/2/5-pin, 1 or 2 rows | `pins`, `pinLabels` (comma list, e.g. `"TX, [gnd], RX"`) |
| `iec` | IEC C14 power inlet | |
| `jack35`, `rca`, `toslink` | audio jacks | |
| `led` | status LED | **only for a genuinely separate indicator** (its own labelled bank, e.g. per-input signal/link lights) — don't reach for this to explain a small icon sitting directly above a jack; that's almost always the jack's own lock hole, see above. `color` (`red`/`green`/`blue`/`amber`/…), `size` (mm, `1.6`–`2` typical), `lit`. **`func` can be a bracket glyph token, not just text** — see below. There's also no plain circular pushbutton part in this catalog — an unlit `led` sized to match is the usual stand-in for a drawing's plain round button (IR window, power, reset-style buttons), not a reach for `button` (a backlit rounded-*square*, a different shape) |
| `button` | backlit push-button | |
| `reset` | small reset pinhole | |
| `pinhole` | plain unlabelled hole | |
| `dip` / `dip4` / `dip8` / `dip2` | DIP switch, 5/4/8/2-way | the photo-realistic art already bakes in the position numbers (1..n) and "ON" marking — don't add separate text items for switch numbers; only add `pinLabels`/`pinGroups` if you actually need per-switch *meaning* text next to it |
| `slide`, `slide3` | slide switch, 2 or 3-position | |
| `ground` | M4 ground screw | **only use this for an icon that fails the lock-hole check above** (wrong offset from any nearby jack, or its own `[gnd]`-style label). Fixed art at 8.4mm — a supplier drawing's own ground-screw icon is often drawn smaller (~5-6mm); if placing it at the drawing's exact spacing would make the tool's full-size art overlap a neighbour once rendered, nudge it a little further away rather than shrinking it (it isn't resizable) — note the nudge in `validation.cutouts` so it's not mistaken for a measurement error later |

### Bracket glyph tokens

`func`, `sub`, `label`, and `pinLabels` text can include these tokens; the
renderer swaps them for the matching symbol:

- `[power]` → ⏻
- `[gnd]` → ⏚
- `[bolt]` → ⚡ (e.g. a sub-label `"100W [bolt]"`)
- `\n` → line break

A `led` with `func: "[power]"` and nothing else is the normal way to draw an
unlabelled power indicator — it renders as an icon-only "label", not a word.

## Use sibling files as a second opinion

If this product has a relative already in `data/library/` (a TX/RX pair,
an earlier revision, a different variant of the same enclosure family),
skim it once you've got a first draft. It won't tell you what *this*
drawing says, but it's a real, previously-checked example of this app's
own conventions for the same hardware family — chassis size, logo
position, pin-label wording, ground-screw placement style — and it's a
good independent check on a rotation correction: if two siblings' pin
orders for the "same" connector type come out identical after each was
corrected separately, that's good evidence both corrections were done
right.

## Validating before you trust a number off the drawing

Supplier drawings routinely mark dimensions in a different colour (often
red) purely as construction guides, not as exact, final values — check the
task's own instructions or the drawing's title block for a note like this
before treating every red callout as gospel. When in doubt, prioritise
getting the **port types, left-to-right order, and grouping** right over
chasing a dimension to the tenth of a millimetre; `measure_drawing.py`
(see `SKILL.md`) gets you close enough, and the tool's own grid/alignment
tools make final nudging in the browser cheap.
