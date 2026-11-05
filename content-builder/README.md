# PureLink Content Builder

Builds PIM/label/sales copy for a product record: Feature Title, the 5
Features, Use Case, Label Text, and a PRD-style Concept Document —
optionally AI-drafted, grounded in a product's real, linked Panel Builder
panels rather than invented specs.

## What this is

A record has a **Seed** (a rough intro/bullets/use-case you type), can be
**linked to one or more Panel Builder layouts** (so Feature-drafting and
exports can cite real ports instead of guessing), and moves through two
stages:

- **Concept** — fields are editable, nothing is final yet.
- **Committed** — PIM fields, Label Text and feature images lock; this is
  the package handed to PIM/ERP/Graphics. Returning to Concept needs a
  note, same pattern as Panel Builder's approval workflow.

"**Draft with AI →**" fills Feature Title, the 5 Features, Use Case and
Label Text from the Seed plus the real ports on any linked panel(s), via
`POST /api/draft-content` (see
[`../tools/dev_server.py`](../tools/dev_server.py)). **As of 2026-11 the
Anthropic org used here has $0 credits, so that route errors in
practice** — the `content-draft-stopgap` skill
(`.claude/skills/content-draft-stopgap/`) is the standing manual
workaround; drop it once credits are restored and prefer the real button
again.

A fixed strip above the form always shows the linked panel(s)' real
front/rear silkscreen, borrowed live from Panel Builder's own
`exportSVG()` through a hidden iframe (`../panel-builder/index.html`) so
it can never drift out of sync with the actual layout.

## Exports

- **Export to Excel** (`exportBtn`) → `POST /api/export-content-xlsx` —
  opens PureLink's real product masterfile template and overwrites only
  this record's own cells; every formula and every other product's
  example row passes through unchanged. **Needs the `I:\` network drive
  mounted** (see the server's own docstring for exactly which cells).
- **Export to Word** (`exportPrdBtn`) → `POST /api/export-content-prd-docx`
  — a PRD-style Concept Document; the client renders the linked panel(s)
  live (front/rear PNGs via Panel Builder's `panelPNG()`) and posts them
  alongside the record, embedded under the PRD's Silkscreen and Interface
  Layout sections.

## Opening it

Via the [Modules Hub](../modules-hub/index.html) (normal way in), or
directly at [`index.html`](index.html) — same local-only, no-build-step
model as every other module (see
[`../panel-builder/README.md`](../panel-builder/README.md#local-persistence--read-this)
for how the shared local-persistence shim works).

## Files

- `index.html` — the app
- `feature-images.json` — the stock feature-image picker's catalog,
  fetched same-folder at runtime
