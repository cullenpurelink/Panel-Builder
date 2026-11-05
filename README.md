# PureLink module suite

A set of standalone, browser-based tools for PureLink's AV-hardware
product team, served from one small Python static server. No build step,
no framework, no `package.json` — each module is a single self-contained
`index.html` (inline CSS/JS) in its own folder.

For contributors (human or AI): see [CLAUDE.md](CLAUDE.md) for the full
architecture/conventions reference this README summarizes.

## How to open this

Run [`start.bat`](start.bat): starts the shared server and opens the
[Modules Hub](modules-hub/index.html) — the collapsible sidebar that
embeds whichever module you pick. That's the normal way in for everyone.

Every module also still works opened directly (double-click its
`index.html`) — no install/server/build step needed — you'll just see a
small "← Modules" link instead of the full sidebar, since the sidebar
itself belongs to the Hub.

## Repo layout

Each module is its own folder, with its own `README.md`:

- [`panel-builder/`](panel-builder/README.md) — **Module 1**, and the
  oldest/largest. Lay out AV device front & rear panels: port library,
  canvas with grid/snap/alignment, housing & 3D views, silkscreen rules,
  a validation "Checks" panel, Draft → Approved → Released revision
  workflow. The source of truth for a product's physical port layout.
- [`system-diagrams/`](system-diagrams/README.md) — **Module 2**, a
  viewer for the real PureLink System Diagram Library (room masters,
  classroom touch-panel systems), plus two standalone helper pages
  (a product-icon generator and an early scene-builder prototype).
- [`content-builder/`](content-builder/README.md) — builds PIM/label/
  sales copy for a product, optionally AI-drafted from its linked Panel
  Builder panels' real ports; exports to `.xlsx` and `.docx`.
- [`modules-hub/`](modules-hub/README.md) — the launcher shell described
  above; also has the "Push to GitHub" button. **Adding a new module**
  (e.g. the planned 3D-design-program integration) means a new sibling
  folder here plus one entry in the Hub's `MODULES` array — see its
  README for the exact spot.

Shared, suite-wide pieces live at the root, not inside any one module:

- [`shared/`](shared/local-db.js) — `local-db.js` (the local-persistence
  shim every module loads) and the suite's favicon set
  (`favicon.svg`/`.ico`, `apple-touch-icon.png`), used by all four
  modules above
- [`tools/dev_server.py`](tools/dev_server.py) — the static server
  (`start.bat`/`stop.bat` run it) plus the JSON API routes the modules'
  export/publish/AI-draft/push-to-GitHub buttons call
- [`data/library/`](data/library/) — the shared panel-layout library
  (every layout `panel-builder/` exports, that `content-builder/` and
  `system-diagrams/` both also read); see
  [panel-builder/README.md](panel-builder/README.md#bringing-panels-over-from-claudeai)
  for how a layout gets in here
- `reference/` — internal PureLink styleguides/CAD, gitignored on
  purpose (only `reference/INDEX.md` is tracked)

## Local persistence, in short

No module here has a real backend — each saves through a shared
IndexedDB-based shim (`shared/local-db.js`) instead, so everything works
fully offline but data lives only in the browser/machine that saved it.
See [`panel-builder/README.md`](panel-builder/README.md#local-persistence--read-this)
for the full explanation (Undo pills, what survives a reload, what
doesn't) — it applies to every module, not just Panel Builder.
