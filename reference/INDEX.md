# Reference docs (local only — not pushed to GitHub)

Internal PureLink standards worth keeping on hand for every Panel Builder
session. This folder is gitignored on purpose: these are company-internal
documents, not something that belongs in the public-ish git history.

## What's here

- **`Styleguide PureTools_Enclosure_V1.1.pdf`** — housing dimensions by
  size class (small/medium/large), side cooling-fin cut-out formula,
  heat sink (`XXSUB-PT-ACC-MSINK`) and mounting-foot (`XXSUB-PT-ACC-
  SMOUNT`/`-MMOUNT`) specs, 1U rack ventilation-hole pattern.
- **`Styleguide PureTools_Silkprint_V1.4.pdf`** — frame/label layout
  rules, logo sizing table by housing type (bent housing by width band
  vs. housing-with-heatsink, independent of width), cable/port colour
  coding, and the underside "function coding" block layout (generic: it
  mirrors the same OUTPUT/INPUT/etc. frame groupings already on the
  front/rear panels, plus fixed MAC-address/rating-label/QR/NOTES
  elements — not bespoke per-product art). V1.4 (read in full
  2026-10-26) added: dedicated 23/25mm front-logo dimensions (18.4 x
  3.5mm, 5.1mm badge), bumped the 30mm badge font 3.8→4mm (badge cap
  height always equals the wordmark's own height — p.14/15), a ½U rack
  row on the top-logo table sharing the heat-sink tier's size (p.17,
  confirmed explicitly on the new p.20), and official fixed MAC-
  address/rating-label sticker sizes (39.5x9.6mm / 52.3x21.8mm, p.23).
  `topFace()`/`logoGeom()`/`logoDefault()`/`topBadgeTier()` and the
  Housing tab's MAC/rating box styles now match it. The superseded
  V1.2/V1.3 are kept at `archiv/` for reference, not read.
- **`Image creation styleguide for suppliers_V1.3.pdf`** — not yet read
  in a Panel Builder session; covers product-photo/render creation
  conventions for suppliers. **Earmarked for the 3D tab**: once that's
  built (still a "comes in phase 3" placeholder as of this writing),
  this guide governs how the generated product pictures/renders should
  look — read it before building any image-generation part of 3D.

- **`3D drawings/`** — real chassis STEP files added 2026-10-14 to
  check the Housing net view's vent/heat-sink cut-out against actual
  geometry instead of angled product photos: `PT-HDBT-150-RX S size at
  25mm.stp`, `PT-MA-HD44 L size chassis no heat sink.STEP`,
  `PT-VCX25-25-RX M size chassis no heat sink.stp`, and the real
  `PT-PSW-21HC-KVM V2 M size chassis with heat sink.step` (the exact
  product this app's test draft models). Confirmed: every housing's
  bottom shell has the same moulded rib-tab structure visible through
  the top cover's cut-out (fewer/wider tabs on S, more/finer on L); on
  the heat-sink variant that tab structure is absent and a real
  aluminium heat-sink insert sits there instead, same orientation/
  pitch. Mounting-ear hole count also varies by size (2 holes/ear on
  S/M, 5 holes/ear on L).

## What's deliberately *not* here

One-off silkprint PDFs or CAD for a single product beyond the
reference chassis above — those live on the network drive as the
single source of truth and change over time. Point me at the `I:\...`
path when a task needs one rather than copying it in here.

## Where this is used

`Panel Builder/index.html` — `netSVG()`, `sideFace()`/`ventSlot()`/
`ventRibs()`/`heatsinkRibs()`, `topFace()`, `bottomFace()`,
`heatsinkAllowed()`, `logoGeom()`/`logoDefault()` — built from the
Enclosure guide's measured rules, the Silkprint guide's logo/badge
tables, plus the real CAD in `3D drawings/` (cap-zone size and rib
pitch) and `PLK-M-1-04 Heat Sink V0.2.step`.

The bottom face's "function coding" block system (Silkprint p.21-22) is
built: `buildFuncBlockGroups()`/`funcBlockRows()`/
`insertFuncCodingNotes()` reuse the front/rear panels' own frame
groupings and per-port spec/LED-legend fields, laid out as draggable
Housing-tab notes at the guide's 4mm margin / 4mm header / 3mm
header-gap, with one shared gap constant between blocks so their
spacing is always even (p.22's explicit rule).
