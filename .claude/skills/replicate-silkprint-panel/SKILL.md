---
name: replicate-silkprint-panel
description: >-
  Turns a supplier's silk-print / silkscreen CAD drawing (PDF, often named
  with "丝印" in it, or sent as a 1:1 panel layout for front/back/underside
  of an enclosure) into real front and rear panel layouts inside this
  repo's Product Builder (index.html). Use this whenever the user hands
  over a supplier drawing — from HDCVT, PureLink's own ID team, or any
  other vendor — and asks to replicate, rebuild, match, or "make the panel
  from" it, even if they don't say "Product Builder" by name. Also use it
  when a drawing has a view rotated 180° (upside-down relative to how the
  panel actually mounts) and the user needs it corrected, or when a drawing
  mixes real silkscreen content with red dimension-guide callouts that
  shouldn't be printed. Not for touching up an existing library layout with
  no new source drawing — that's just normal editing in the app.
---

# Replicate a supplier silk-print drawing as a Product Builder panel

A supplier sends a 1:1 CAD drawing of what gets silkscreened onto a
product's enclosure — usually a single PDF page with several views mixed
together (front panel, rear panel, top/lid, side views, and often a
separate "bottom face" legend), red dimension callouts, and sometimes a
view drawn rotated because of how it's printed or mounted. The job is to
turn that into a real `front`/`rear` layout in this app's own JSON format,
seeded into `data/library/`, and verified by actually opening it.

This is a **read-the-drawing-carefully** task before it's a data-entry
task. The steps below are the shape of the work, not a fill-in-the-blanks
form — the specifics (which view is which, which way something is
rotated, what each icon actually is) have to be worked out fresh from the
actual pixels every time. Two supplier drawings will not look alike.

## Step 0 — get the drawing on screen

The Read tool's built-in PDF rendering needs `pdftoppm` (poppler), which
often isn't installed. Don't stop there — check for PyMuPDF instead and
render with it:

```
python -I -c "import fitz; print('ok')"
```

If that works, use `scripts/measure_drawing.py render <pdf> --out <dir>`
to rasterise the page(s) at a high zoom (4x default — these drawings are
dense, you want to be able to zoom into a single connector and still read
it). Then use the Read tool on the resulting PNGs, and `scripts/
measure_drawing.py crop` to pull out tight regions — reading a crop of
just the one view you care about beats trying to parse a 5000px-wide page
in one glance.

If neither `pdftoppm` nor PyMuPDF is available, say so and ask how the
user wants the drawing turned into images rather than guessing blind from
raw PDF text extraction (these drawings are almost entirely vector
line-art + callouts, not text you can usefully parse without seeing it).

If the given path is on a mapped network drive (e.g. `I:\...`) and it's
unreachable, don't give up on the file — a mapped drive is a per-session
thing and isn't always available to a subagent's process even when it
works fine elsewhere. Check for an identical copy already synced
locally first (e.g. under `OneDrive - <company>\...\Teams Chat Files\`,
matching the same filename) before asking the user to resend it.

## Step 1 — work out what's actually on the page

Before measuring anything, identify:

1. **Which rectangle is the front panel, which is the rear panel.** There
   are usually other views too (top/lid, side profiles, a full enclosure
   render) — those aren't what you're building.
2. **Is either view rotated** relative to how it actually sits on the
   product? Suppliers sometimes draw the rear panel upside-down (e.g.
   because of print-feed orientation). The task or the drawing itself
   will usually tell you, or it'll be obvious from reading the mirrored
   text.
3. **Is there a large, separately-annotated rectangle with things like
   "Rating Label", "MAC address", "NOTES", a switch-settings table, or
   long multi-line spec text** (e.g. "DEVICE1: USB-A | USB 2.0 |
   480Mbps")? That's very likely the **bottom-face "function coding"
   legend**, not a third panel — this repo's silkprint style guide has a
   whole documented pattern for it (see `reference/INDEX.md` in the repo
   root, and `reference/Styleguide PureTools_Silkprint_V1.4.pdf`): it
   mirrors the same frame groupings as the front/rear panels plus fixed
   MAC/rating/NOTES elements, and the app can already generate it in the
   Housing tab. Don't try to build it as a `front`/`rear` panel — use it
   only as a legend for label *text*, and only build front/rear unless
   asked for more.
4. **Which marks are real silkscreen content vs. dimension guides?** CAD
   drawings commonly use one colour (often red) purely for construction
   dimensions — check the task and the drawing's own title block/legend
   for this. Guide dimensions tell you proportions and scale; they are
   not something to reproduce on the panel.

## Step 2 — measure

Use `scripts/measure_drawing.py` (`calibrate` then `components` — see its
own `--help` and docstring) to turn pixel positions into millimetres:
calibrate the px/mm scale against **something you already know in mm**
(the panel's own outline is usually the most reliable anchor — measure its
pixel bounding box against a width/height you can read off the drawing or
infer from context, rather than trusting every small dimension callout
individually). Then pull connector positions out as connected-component
centres.

Treat the script's output as a strong hint, not ground truth — merged or
touching shapes can produce misleading bounding boxes (two port outlines
that touch become one "component", or a component gets split by an
internal cavity detail). Cross-check anything that looks odd by reading a
tight `crop` of that exact spot with the Read tool. Precision only matters
to the extent the source drawing itself warrants it — getting the port
**types, left-to-right order, and grouping** right matters far more than
chasing a dimension to a tenth of a millimetre, especially when the task
tells you dimensions are guides.

## Step 3 — map to the Product Builder schema

Read `references/ports-cheatsheet.md` now — it has the JSON schema, the
`PORTS` catalog entries you'll need most often, the bracket glyph tokens
(`[power]`, `[gnd]`, `[bolt]`), and two easy-to-get-wrong details that bit
the first time this was done:

- **Frame `titlePos`** controls which side the frame's title lands on
  *and* which side each member's own label lands on — they're linked, not
  independent.
- **Correcting a 180°-rotated view flips both axes**, not just left-right
  — top and bottom swap too, which usually means the `titlePos` you need
  is the opposite of what the rotated image looks like it's showing. Work
  this out from the actual pixel layout each time.

If you need a `PORTS` type that isn't in the cheat-sheet, or a field
doesn't behave as documented there, grep the real thing in `index.html`
(`const PORTS = {`) — the cheat-sheet is a snapshot, not a substitute for
the source when something doesn't match.

## Step 4 — write the layout file

Author `data/library/<slug>-layout.json` by hand (the schema is simple
enough — see the cheat-sheet and any existing file in `data/library/` for
a worked example), then add its filename to `data/library/manifest.json`
(append to the existing array — don't remove or reorder the others).

## Step 5 — open it and actually look

1. Start the dev server if it isn't already running:
   `python tools/dev_server.py 8743` (or `start.bat`), then open
   `http://localhost:8743/index.html` in **Claude in Chrome** per the
   user's standing preference for that over the built-in browser pane.
2. **Hard-reload** (Ctrl+Shift+R) before opening the Library. The app
   fetches `data/library/manifest.json` on load, and a plain reload can
   serve a browser-cached copy from before you edited it — a new entry
   you just added can silently fail to show up in the Library list for
   this reason alone. If it's still missing after a hard reload, fetch
   the manifest with `cache:'no-store'` via the JS tool to rule out
   caching before assuming the file itself is wrong.
3. Open your new item from the Library (confirm "Open anyway" if it
   warns about discarding whatever draft was open).
4. Zoom into each region of the rendered panel and compare side-by-side
   against the crops you read in Step 0–2. Check specifically for: port
   left-to-right order, frame grouping/titles, colour boxes (magenta
   HDBaseT box, blue USB-C box) showing where expected, and lock holes
   (`"lock": true` draws a small circle *above* the port, a few mm off —
   easy to mistake for a stray grid dot at a glance, so actually zoom in
   rather than assuming it's missing). Before Step 3 even, read
   `references/ports-cheatsheet.md`'s lock-hole section — a small icon
   above an HDMI or USB-C jack in the source drawing is that jack's own
   lock hole in the overwhelming majority of cases, not a separate
   `ground` or `led` item; defaulting to a separate part there is the
   single most repeated mistake in every run of this skill so far.
5. **Scroll to the "Checks" panel and read it — don't skip this.** It's
   the app's own geometry/clearance validator, and it catches real
   placement bugs that are easy to miss by eye (a frame that runs off the
   panel face isn't always visibly wrong until you zoom to the exact
   pixel; a label crowding its neighbour by half a millimetre looks fine
   at a glance). Treat anything listed under "problems" as blocking and
   anything under "warnings" as worth fixing too, and don't call the
   layout done until it reads "every part clears the edges and its
   neighbours, and every label fits" — the one standing exception is a
   note like "the enclosure guide puts 30mm housings at 210–400mm wide,
   this one is Nmm", which just reflects the real product's actual size
   and isn't something to fix.
6. Iterate by editing the JSON + hard-reload + reopen, or by nudging
   directly in the canvas (drag, or the inspector's numeric x/y fields) —
   whichever is faster for the specific fix. If you edit live in the UI,
   you can pull the result back out with Export → Layout file if you want
   the JSON in `data/library/` to match exactly what's now open.

### Two things that actually went wrong the first few times

- **A ground screw (or any member) sitting too close to the panel's top
  edge breaks a `titlePos:"top"` frame**, not because of its own x/y so
  much as because that frame needs headroom *above* its topmost member
  for the title text itself (title height + label gap + `padTop`). A
  member center around y=9mm on a 30mm-tall panel is already too tight —
  the frame's computed top edge ends up above y=0, i.e. "off the panel
  face", even though every individual part looks fine sitting inside the
  panel. If you see that error, look at the topmost member's y before
  anything else; moving it down a couple of mm usually fixes it outright.
  (The opposite case — a `titlePos:"bottom"` frame whose bottom member
  sits too close to the panel's bottom edge — breaks the same way.)
- Fixing a label-collision warning by moving a ground screw's **x**
  can just as easily reintroduce the problem as an **icon-to-icon**
  overlap with a *different* neighbour a few mm further along, or leave
  too little vertical gap to the port it was originally paired with —
  moving something in a crowded row rarely has only one effect. After
  any such nudge, re-check the Checks panel rather than assuming the one
  warning you were chasing was the only thing that changed.

### Verifying a hand-edited JSON without the browser-cache trap

This app's own in-page code fetches each library file without
`cache:'no-store'`, so once a product's already been seeded into a
browser's local library, re-editing its file on disk and reloading can
silently keep showing the old version (the same trap as the manifest.json
one above, just one layer deeper — a plain hard-reload doesn't reliably
bust it either, since the fetch happens after the top-level navigation).
The reliable way to check a fix without fighting this: open the browser's
own JS console (the `javascript_tool`, if you're driving the app that
way) and run

```js
const m = await fetch('data/library/<file>.json', {cache:'no-store'}).then(r=>r.json());
loadModel(m); renderAll();
```

— this loads the file's *current, on-disk* content straight into the
editor as the active draft, so the Checks panel reflects exactly what
you just wrote. Only once it looks right should you click **Save** to
put it in the library for real. One side-effect to know: `Save` on a
model loaded this way creates a *new* library entry rather than updating
the one already there (it doesn't carry over the original entry's id) —
so if you were fixing something already in the library, delete the old
copy afterward to avoid leaving a stale duplicate sitting next to it.

## Worked examples

The first time this process was done was `HDP-EUB40CD-TX-DE0012` (a
PureLink VCX2 LX transmitter): `data/library/hdp-eub40cd-tx-de0012-
layout.json` is a real finished example of the output shape, and its
source drawing had a rotated rear-panel view plus a separate bottom-face
legend rectangle, i.e. it exercises most of what this skill is about.

This skill was then run independently (fresh sessions, no shared context)
against three related drawings from the same supplier/family —
`data/library/hdprx-eub40d-de0012-layout.json`, `hdp-eub40hcd-tx-de0012-
layout.json`, and `hdprx-eub40hcd-de0012-layout.json` — as a real test.
All three came out structurally sound on inspection and converged
independently on the same techniques now written into
`references/ports-cheatsheet.md` (checking a rotation correction against
a pin-order convention, telling lock holes from ground screws by offset,
skipping manufacturer reference text like "Amphenol"). They're good
further examples of the output shape, including the more complex
240mm-chassis product with push-buttons and a 2-row Phoenix block.

All three *did* need a follow-up pass, though — none of them had been
checked against the app's own "Checks" panel (that step was explicitly
out of scope for that test run), and all three turned out to have real
geometry problems once opened: ground screws placed too close to the
panel's top edge broke their `titlePos:"top"` frame (see "Two things
that actually went wrong" above), and one had two ports spaced too
close together for their shared text labels to fit. Step 5's Checks-panel
check above is written the way it is because of exactly this.

That same follow-up pass is also where the lock-hole-vs-ground-screw
mistake above got caught — all three test files (and the original
HDP-EUB40CD-TX-DE0012 build) had modelled a small icon above an HDMI or
USB-C jack as a separate `ground`/`led` item instead of that jack's own
`"lock": true`. All four were corrected afterward; if you're looking at
an older copy of any of them for reference, check it still shows
`"lock": true` on the port rather than a nearby `ground`/`led` item
before trusting it as an example.

`data/library/hdp-hub42u40-tx-layout.json` (a 4x2 HDMI/USB-C matrix
switcher) is a later, more cramped example: a 320mm-wide, originally
23mm-tall panel densely packed with switches, Phoenix terminal blocks,
and HDMI/USB-C jacks with real lock holes. Worth reading if you hit any
of these:

- **Raise the chassis height rather than fight the squeeze.** At 23mm,
  several lock holes, group frames, and labels had no valid position at
  all — not a placement mistake, a real structural shortfall (the
  numbers in "Two things that actually went wrong" show why). The fix
  the user asked for was simply a taller chassis (30mm, which also
  happened to match this width's actual housing-guide tier instead of
  falling outside it) — cheaper and more honest than dropping content to
  fit. If a product is this dense, don't assume the drawing's own stated
  height is the one to build at; flag the squeeze and suggest the next
  housing tier up before stripping detail to make a too-small panel work.
- **`rules.alignLabels` can cascade a single fix into many new breaks.**
  It snaps every "below"-positioned label within `alignRange` (default
  4mm) of each other onto one shared line. Moving one port down to clear
  a lock-hole conflict can drag every *other* label on that row down with
  it — including ones that were already fine — straight off the panel
  edge. If a small, local position change produces a wave of brand-new
  "label runs off the panel face" errors across unrelated parts, this is
  almost certainly why; either set `"alignLabels": false` for a dense
  panel where rows were never going to line up perfectly anyway, or make
  the fix in a way that doesn't move the shared row at all.
- **A multi-line text block is a height problem, not a clearance
  problem.** Stacking one label per switch position (e.g. 5 lines for a
  5-way DIP) costs roughly (line count) × (line height) of vertical
  space — for 5 lines that's 20mm+, which won't fit next to anything on
  most panel heights no matter how much you nudge it. Prefer a single
  compact line (`"IN1-4 / AUTO"` rather than one line per position) over
  a tall stacked block.

`data/library/pt-vcx25-46lx-layout.json` (a 42-port KVM TX switch,
HDP-PSB42H100P-DE0012) is the first build where the user explicitly asked
to go beyond front/rear and also (A) build the bottom-face panel for
real and (B) fill in each port's detailed spec text from the bottom-leg
legend — i.e. everything Step 1.3 above says to treat as reference-only
by default. Worth reading if the user asks for the same:

- **The bottom-face text is driven by fields on each port item, not
  hand-placed text.** Set `it.spec = { note: "..." }` for a normal
  connector (group other than 'Front panel' — see
  `references/ports-cheatsheet.md`), `it.ledLegend` (RJ45/RJ45LP only,
  `greenOff/greenOn/greenBlink/amberOff/amberOn/amberBlink`),
  `it.pinFuncs`/`it.pinFuncs2` (array, per Phoenix pin), or
  `it.bottomNote` (an extra freeform line any port can have). Then, live
  in the browser console, call `insertFuncCodingNotes()` (it reads those
  fields straight off `model`) and read the result back from
  `model.housing.notes` — don't hand-simulate the layout math yourself.
- **`it.spec.note` is silently dropped for `group: 'Front panel'` types**
  (`led`, `button`, `dip`, `reset`, `slide`, …) — `hasSpec()` only allows
  it for real connector groups. For a front-panel-style part, put
  everything you want on the bottom face into `bottomNote` instead; it
  always works, regardless of group.
- **Don't repeat the port's own catalog name at the start of
  `spec.note`.** The generator already prepends `PORTS[type].name` (e.g.
  "USB-A", "USB-C") before your note, so writing `spec.note: "USB-A | 2.0
  | 480Mbps"` renders as "USB-A | USB-A | 2.0 | 480Mbps". Write just the
  part after that first "|" (`"2.0 | 480Mbps"`) and let the generator add
  the type name once.
- **`insertFuncCodingNotes()` lays everything out in one single stacked
  column**, in panel-then-frame order, merging front and rear groups
  that share the same frame title (e.g. a front "AUDIO" selector group
  and a rear "AUDIO" port group become one combined column) — which is
  the right behaviour, but for a wide/dense product the column can run
  far past the housing's actual depth (390mm-wide, 6-group product here
  stacked to ~204mm of column height against a 130mm depth). Call the
  function, then **regroup the generated `housing.notes` into a grid by
  hand**: split on the `kind:'box', style:'header'` items to find each
  frame-title group's own lines, measure each group's natural height
  from its own item spread, then reassign `x`/`y` in columns/rows that
  fit the real depth (preserve each line's *relative* x-indent within
  its group when you shift the column, since sub-bullet lines like the
  LED-legend rows are indented further than the port lines). Add
  MAC/RATING/NOTES/Device-Info boxes afterward in the space below, at
  their style-guide fixed/minimum sizes (see the `addHousingBox`/
  `STICKER_SIZE`/`NOTES_MIN` constants in `index.html`).
- **The Housing tab's own UI can be gated behind a "Housing opens after
  panel approval" screen** (save to library + an approver signs off)
  that this skill's established workflow has no need to go through —
  `insertFuncCodingNotes()`, `addHousingBox()`, and `model.housing.notes`
  are plain functions/data on `window`, callable directly from the JS
  console regardless of that UI gate.
- **Getting a large JS value (e.g. the full `housing.notes` array) back
  out of the browser console can get silently truncated** by the tool
  output itself, even well under what `JSON.stringify` actually
  produced. The reliable way: trigger a real file download from the page
  (`new Blob([...]) → URL.createObjectURL → <a download> → .click()`)
  and then read it back with the Read tool from the Downloads folder —
  delete the scratch download afterward once you've copied what you
  need into the layout file.
