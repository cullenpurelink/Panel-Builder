# CLAUDE.md

Guidance for Claude Code (or any future AI assistant) working in this
repository. See [README.md](README.md) for the user-facing overview.

**Keep this file (and README.md) current.** When a change you make adds,
removes, or materially reshapes a module, an API route, a data format, a
skill, or a dev workflow described below, update the relevant section in
the same session — don't leave it to a later pass. Small internal
refactors that don't change any of the below don't need a doc update.

## What this is

The **PureLink module suite**: a set of standalone, browser-based tools
for PureLink's AV-hardware product team, served from one small Python
static server. No build step, no framework, no package.json — each
module is a single self-contained `index.html` (inline CSS/JS). Started
as a Claude.ai artifact ("PureLink Panel Builder") and grown from there.

## Modules

| Module | Entry point | Purpose |
|---|---|---|
| **Panel Builder** (Module 1) | [`index.html`](index.html) | Design AV device front/rear panels: draggable port library, canvas with grid/snap/alignment, dimension guides, Housing (enclosure) and 3D views, silkscreen rules, a validation "Checks" panel, Draft → Approved → Released workflow. This is the oldest and largest module (~4,500 lines) and the source of truth for a product's physical port layout. |
| **Content Builder** | [`content-builder/index.html`](content-builder/index.html) | Builds PIM/label/sales copy for a product (Feature Title, 5 Features, Use Case, Label Text, Concept Document), optionally AI-drafted from a product's linked Panel Builder panels' real ports. Exports to `.xlsx` (matching the real PureTools product masterfile tabs) and `.docx` (PRD-style Concept Document). |
| **System Diagrams** (Module 2) | [`system-diagrams/index.html`](system-diagrams/index.html) | Viewer onto the `PureLink_Diagram_Library_v1.0` master register (room/system diagrams). **Not** an editor — masters are produced by a separate Python pipeline in a different Claude Project; see [`system-diagrams/README.md`](system-diagrams/README.md). |
| **Modules Hub** | [`modules-hub/index.html`](modules-hub/index.html) | Launcher shell: collapsible sidebar, embeds whichever module is selected via `<iframe>`, has the "Push to GitHub" button. This is the normal entry point — `start.bat` opens it. |

`shared/local-db.js` is loaded by every module as its first `<script>`
tag — see "Local persistence" below.

## How to run it

```
start.bat
```

Starts `tools/dev_server.py` on port 8743 and opens the Modules Hub.
`stop.bat` kills it. The script is idempotent (it stops any existing
instance on the port first), so re-running `start.bat` after edits is
the normal way to pick up server-side (`dev_server.py`) changes — static
HTML/JS/CSS changes just need a browser reload, no restart.

Each module also has its own `start.bat`/`stop.bat` under its folder,
and a `.claude/launch.json` config (`modules-static-server`) for driving
it via the Claude Code browser-preview tools.

## `tools/dev_server.py`

A plain static file server plus six JSON API routes the static pages
call via `fetch()`. Read the module's own top-of-file docstring before
changing it — each route's contract is documented there. Routes, in
brief:

- `POST /api/git-push` — commits everything with an auto message and
  pushes (used by the Hub's "Push to GitHub" button).
- `POST /api/save-product-icon` — writes a generated product icon into
  `system-diagrams/assets/products/`.
- `POST /api/publish-to-library` — writes a panel's layout JSON into
  `data/library/` and registers it in `data/library/manifest.json`
  (Panel Builder's "Publish to System Diagrams library" export).
- `POST /api/export-content-xlsx` — Content Builder's Export to Excel
  button. Opens PureLink's own real product masterfile template
  (`CONTENT_MASTERFILE_TEMPLATE`, a path onto the `I:\` network drive —
  **requires that drive to be mounted**) and overwrites only this
  record's own literal cells in it; every formula and every other
  product's example row is passed through unchanged. See
  `build_content_workbook()`'s docstring for exactly which cells that is.
- `POST /api/export-content-prd-docx` — Content Builder's Export to Word
  (PRD) button. The client renders the linked panel(s) live from Panel
  Builder (front/rear PNGs via its own `panelPNG()`) and posts them
  alongside the record; the server embeds those under the PRD's
  Silkscreen and Interface Layout sections.
- `POST /api/draft-content` — Content Builder's "Draft with AI" button;
  calls the real Anthropic API. Needs a key — see below. **As of
  2026-11, the Anthropic organisation used here has $0 credits, so this
  route returns an error in practice; the
  `content-draft-stopgap` skill is the standing workaround** (draft the
  same fields by hand, same style/length rules). Prefer the real button
  again once credits are restored.

All file-writing routes validate filenames against a strict regex
(`SAFE_ICON_NAME`, `SAFE_LIBRARY_NAME`) before touching disk — keep that
pattern for any new write route.

### Anthropic API key

`get_anthropic_key()` checks `ANTHROPIC_API_KEY` env var first, then
`tools/anthropic_key.txt` / `tools/anthropic key.txt` (both gitignored,
plain text, one key per file — never commit one of these files or paste
a real key into a tracked file).

## Local persistence (`shared/local-db.js`)

The original claude.ai artifact used Claude's hosted `db`/`user`
capabilities. `shared/local-db.js` reimplements the same `db`/`user`/
`downloads` call shapes on top of browser **IndexedDB** (database name
`purelink-local-db`) so every module works fully offline with no backend.
Consequences worth knowing before changing data-model code:

- Data lives only in the browser/machine it was saved in — there is no
  sync between browsers, machines, or back to claude.ai.
- There's no real multi-user concept locally — the current browser is
  always treated as owner and sole approver.
- Save/delete/approval-status changes show a themed "Undo" pill
  (~8s window) — a convention to preserve when adding new mutating
  actions.
- The in-progress draft (before it's saved to the library) persists via
  plain `localStorage` under a per-module key (e.g.
  `purelink-panel-builder:draft`) so a reload never loses unsaved work.

## Data: `data/library/`

Panel Builder layouts, exported from the app as `<sku>-layout.json`, are
the canonical format Content Builder and System Diagrams both read
(linked ports, generated panel icons). `data/library/manifest.json` is a
flat JSON array of filenames in that folder — **every new layout file
must be added to this array**, or the app won't auto-load it. See
[README.md](README.md#bringing-panels-over-from-claudeai) for the full
claude.ai → local workflow.

## `reference/` is gitignored on purpose

`reference/` holds PureLink's internal styleguides (enclosure dimensions,
silkprint rules, supplier image conventions) and real chassis CAD/STEP
files — company-internal, not meant for git history. Only
`reference/INDEX.md` is tracked (`.gitignore` has an explicit
`!reference/INDEX.md` exception) so a fresh clone still explains what's
supposed to live there. **If you add a new reference doc, update
`reference/INDEX.md` to describe it** (what it covers, which code in
`index.html` was built from it) — that index is the only trace of
`reference/`'s contents that survives in git.

## Skills (`.claude/skills/`)

- **`replicate-silkprint-panel`** — turns a supplier silk-print CAD PDF
  into a real Panel Builder front/rear layout. Use for any "replicate
  this drawing" request, including rotated views and red dimension-guide
  callouts that shouldn't be printed.
- **`content-draft-stopgap`** — manually produces what Content Builder's
  "Draft with AI" button would (Feature Title, 5 Features, Use Case,
  Label Text) while the Anthropic org has no API credits. Drop this once
  `/api/draft-content` works again and prefer the real button.

If you add a new skill, give it a specific trigger description (what
request shape should invoke it, and what it's *not* for) — see the two
existing ones for the expected style.

## Conventions to follow

- **No build step.** Every module is one `index.html` with inline
  `<style>`/`<script>`. Don't introduce a bundler, framework, or
  `node_modules` unless the user explicitly asks for that scale change.
- **British English** in any user-facing PureLink product copy (colour,
  optimise, licence as a noun, etc.) — see `DRAFT_SYSTEM_PROMPT` in
  `tools/dev_server.py` for the house style Content Builder enforces.
- **Ground product copy in real data.** Never invent a port, connector,
  spec, or count that isn't present in a linked panel or the user's seed
  notes — this is a hard rule baked into the AI draft prompt and should
  hold for manual drafting too.
- **`index.html.bak`** is an untouched copy of the original claude.ai
  export, kept as a safety copy and gitignored. Don't treat it as a file
  to edit or keep in sync — it's a historical reference, not live code.
- Before relying on a memory of "X exists" from a prior session or this
  file, check the file/function still exists — this repo changes fast
  session to session.
