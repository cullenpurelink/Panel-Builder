# Reference docs (local only — not pushed to GitHub)

Internal PureLink standards worth keeping on hand for every Panel Builder
session. This folder is gitignored on purpose: these are company-internal
documents, not something that belongs in the public-ish git history.

## What's here

- **`Styleguide PureTools_Enclosure_V1.1.pdf`** — housing dimensions by
  size class (small/medium/large), side cooling-fin cut-out formula,
  heat sink (`XXSUB-PT-ACC-MSINK`) and mounting-foot (`XXSUB-PT-ACC-
  SMOUNT`/`-MMOUNT`) specs, 1U rack ventilation-hole pattern.
- **`Styleguide PureTools_Silkprint_V1.2.pdf`** — frame/label layout
  rules, logo sizing table by enclosure-width band, cable/port colour
  coding, underside "function coding" block layout.
  (Note: this is **V1.2** — I only read V1.1 from the I: drive this
  session; the housing-tab logic was built against V1.1. Worth a diff
  pass if anyone asks "does the net view still match the guide?")
- **`Image creation styleguide for suppliers_V1.3.pdf`** — not yet read
  in a Panel Builder session; covers product-photo/render creation
  conventions for suppliers. **Earmarked for the 3D tab**: once that's
  built (still a "comes in phase 3" placeholder as of this writing),
  this guide governs how the generated product pictures/renders should
  look — read it before building any image-generation part of 3D.

## What's deliberately *not* here

Product-specific CAD/engineering files (STEP assemblies, one-off
silkprint PDFs for a single product) — these live on the network drive
as the single source of truth and change over time. Point me at the
`I:\...` path when a task needs one rather than copying it in here.

## Where this is used

`Panel Builder/index.html` — `netSVG()`, `finStrip()`, `topFace()`,
`bottomFace()`, `heatsinkAllowed()`/`HEATSINK` — all built from the
Enclosure guide's measured rules plus the real
`PT-PSW-21HC-KVM V2 CHASSIS.STP` / `PLK-M-1-04 Heat Sink V0.2.step` CAD.
