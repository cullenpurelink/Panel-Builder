# PureLink Panel Builder

Module 1 of the PureLink browser-based design/production tool suite.

A single-page tool for laying out AV device front and rear panels: a
draggable port/part library, panel canvas with grid/snap/alignment,
dimension guides, housing and 3D views, silkscreen rules, a validation
"Checks" panel, and a revision/approval workflow (Draft → Approved →
Released).

## Repo layout

This repo's root **is** the Panel Builder app (`index.html` here is
Module 1). Two more modules live as subfolders:

- [`modules-hub/`](modules-hub/index.html) — the launcher shell
  (collapsible sidebar, embeds whichever module is selected)
- [`system-diagrams/`](system-diagrams/index.html) — Module 2, a
  viewer for the real PureLink System Diagram Library
- [`shared/local-db.js`](shared/local-db.js) — the local persistence
  shim every module includes

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

## Bringing in today's in-progress design

The in-progress `PT-PSW-21HC-KVM (rebuilt)` layout from claude.ai was
exported as a portable layout file: [data/sample-layout.json](data/sample-layout.json).
To load it here: open the tool → **Library** → **Import layout
file** → pick `data/sample-layout.json`.

## Files

- `index.html` — the app (loads `shared/local-db.js`, otherwise the original export untouched)
- `start.bat` / `stop.bat` — start/stop the shared local server for the whole suite
- `data/sample-layout.json` — today's exported layout, importable via the Library dialog
- `index.html.bak` — untouched copy of the original export, kept as a safety copy; safe to delete whenever you're satisfied
- `shared/`, `modules-hub/`, `system-diagrams/` — see [Repo layout](#repo-layout) above
