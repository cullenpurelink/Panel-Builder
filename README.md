# PureLink Panel Builder

Module 1 of the PureLink browser-based design/production tool suite.

A single-page tool for laying out AV device front and rear panels: a
draggable port/part library, panel canvas with grid/snap/alignment,
dimension guides, housing and 3D views, silkscreen rules, a validation
"Checks" panel, and a revision/approval workflow (Draft → Approved →
Released).

For contributors (human or AI): see [CLAUDE.md](CLAUDE.md) for the
full architecture/conventions reference this README summarizes.

## Repo layout

This repo's root **is** the Panel Builder app (`index.html` here is
Module 1). More modules live as subfolders:

- [`modules-hub/`](modules-hub/index.html) — the launcher shell
  (collapsible sidebar, embeds whichever module is selected, has the
  "Push to GitHub" button)
- [`content-builder/`](content-builder/index.html) — builds PIM/label/
  sales copy (Feature Title, Features, Use Case, Label Text, Concept
  Document) for a product, optionally AI-drafted from its linked Panel
  Builder panels' real ports; exports to `.xlsx` and `.docx`
- [`system-diagrams/`](system-diagrams/index.html) — Module 2, a
  viewer for the real PureLink System Diagram Library
- [`shared/local-db.js`](shared/local-db.js) — the local persistence
  shim every module includes
- [`tools/dev_server.py`](tools/dev_server.py) — the static server
  (`start.bat`/`stop.bat` run it) plus the JSON API routes the modules'
  export/publish/AI-draft/push-to-GitHub buttons call
- [`data/library/`](data/library/) — the shared panel-layout library
  (see [Bringing panels over from claude.ai](#bringing-panels-over-from-claudeai))
- `reference/` — internal PureLink styleguides/CAD, gitignored on
  purpose (only `reference/INDEX.md` is tracked)

## How to open this

The normal way in: run [`start.bat`](start.bat) (or double-click
[`modules-hub/index.html`](modules-hub/index.html) once a server is
running — `start.bat` does both). **The collapsible sidebar/menu lives
in the Hub, not in this file** — the Hub is a shell that embeds each
module.

You can also open [`index.html`](index.html) (this folder's root)
directly — it still works standalone, no install/server/build step
needed — but since the menu belongs to the Hub, you'll only see a
small "← Modules" link top-left instead of the full sidebar. Click it
to get back to the Hub.

## Where this came from

This is the user's "PureLink Panel Builder" Claude artifact (from the
*AV panel port layout builder tool* conversation), exported as a
standalone HTML page and adapted to run outside claude.ai.

## Local persistence — read this

The original artifact saves its data (the shared layout library,
approvals, the approver list) through Claude's hosted `db`/`user`
capabilities. A plain exported HTML file doesn't have that backend, so
`index.html` loads [`shared/local-db.js`](shared/local-db.js) as
its first `<script>` tag — a shim shared by every module in this suite
that reimplements the exact same `db`/`user`/`downloads` calls on top
of the browser's **IndexedDB** instead (replaced the original
localStorage-only version once the suite grew past one module).

What this means in practice:

- **Save, Library, Approve/Release/Return to draft all work fully
  offline** — nothing is disabled.
- Data lives **only in the browser you used it in, on this machine**.
  It will not show up in another browser, another computer, or back
  on claude.ai. There's no "team" to share with locally — you are
  always treated as the owner and sole approver.
- **Saving, deleting or changing the approval status of a library
  item now shows a small "Undo" pill** in the bottom-right corner for
  about 8 seconds — click it to revert that one action (click the
  resulting "Redo" to put it back). This is separate from the
  canvas's own Ctrl+Z/Ctrl+Shift+Z, which still undoes panel-editing
  moves as before.
- Clearing that browser's site data for this file will erase the
  saved library/approvals (the IndexedDB database is named
  `purelink-local-db`). The Undo pill above is the only short-term
  safety net — there's no long-term undo for that.
- The draft you're actively editing (even before saving to the
  library) still persists via plain `localStorage` under its own key
  (`purelink-panel-builder:draft`), unchanged from before — a page
  reload won't lose in-progress work.

If you want this to sync across machines or between people again,
that needs a small real backend (or re-adopting Claude's hosted
capabilities) — not in scope for this local copy.

## Bringing panels over from claude.ai

For each panel in your hosted claude.ai library you want available
locally:

1. In the **claude.ai version**: Library → open the panel (Reopen)
2. **Export** → scroll to the bottom → **Layout file** (the only export
   with the full editable model — not the PNG/SVG/PDF drawing exports)
   → download the `<name>-layout.json`
3. Drop it into [`data/library/`](data/library/)
4. Add its filename to [`data/library/manifest.json`](data/library/manifest.json)
5. Reload the app — anything listed there that isn't already in the
   local library gets loaded in automatically (silently, no undo pill,
   and only once per item — a seed already present is left alone, so
   it's safe to reload as often as you like)

This is how the panels currently in `data/library/` got there — they
load into the Library automatically the first time you open the app.

## Files

- `index.html` — the app (loads `shared/local-db.js`, otherwise the original export untouched)
- `start.bat` / `stop.bat` — start/stop the shared local server for the whole suite
- `data/library/` — exported layout JSONs + `manifest.json`, auto-loaded into the local Library on first run (see above)
- `index.html.bak` — untouched copy of the original export, kept as a safety copy; safe to delete whenever you're satisfied
- `shared/`, `modules-hub/`, `content-builder/`, `system-diagrams/`, `tools/` — see [Repo layout](#repo-layout) above
- `CLAUDE.md` — architecture/conventions reference for anyone (human or AI) working on this repo
