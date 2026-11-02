---
name: content-draft-stopgap
description: >-
  Manually produces Content Builder's AI-drafted fields (Feature Title, the
  5 Features, Use Case, Label Text) by hand, for use while the Anthropic
  organisation has no API credits and the real "Draft with AI" button in
  content-builder/index.html can't reach /api/draft-content. Use this
  whenever the user asks to draft, write, or fill in that content for a
  product record and either says the API/credits aren't working, says to
  do it manually or as a stopgap, or you already know from context that
  the account has $0 credits. Not for anything once the real endpoint is
  funded and working again — prefer the actual button then, since this
  skill is only a bridge.
---

# Draft Content Builder's AI fields by hand (stopgap)

This mirrors exactly what `tools/dev_server.py`'s `/api/draft-content`
route does, minus the actual API call — same inputs, same prompt, same
output schema, just produced by reading and reasoning instead of an
Anthropic API round trip. It exists only because the organisation's API
credits are at $0; once that's fixed, tell the user to use the real
"Draft with AI" button instead and treat this as superseded.

## Step 0 — re-read the real prompt and schema first, every time

**Don't draft from memory of how this worked last time.** Read
`tools/dev_server.py` fresh — specifically `DRAFT_SYSTEM_PROMPT`,
`build_draft_prompt()`, and `call_anthropic_draft()`'s post-processing
(the exactly-5-entries padding on `features`/`labelFeatures`). That file
is the single source of truth for the style, the grounding rules, and the
output shape. If it's changed since you last did this, your output should
change with it — copying the prompt text into this skill would let the
two drift apart, so this skill deliberately doesn't restate it.

Carry forward from the prompt, as of the last time this was written:

- British English throughout (colour, optimise, licence as a noun, etc.)
- Never invent a connector, spec, or capability that isn't in the seed
  notes or the real port list — and never guess a port count you weren't
  given
- Terse, feature-led style (`DRAFT_SYSTEM_PROMPT`'s own example: "2x1 5K
  HDBaseT Presentation Switch")
- Exactly 5 `features` and exactly 5 `labelFeatures`
- `labelFeatures` abbreviated to **24 characters or fewer each** — count
  every character, including spaces and punctuation, explicitly (write
  the string out and count it) rather than eyeballing it

## Step 1 — get the real product record open

Per the user's standing preference, drive this in **Claude in Chrome**,
not the built-in browser pane. Open `content-builder/index.html` on the
running dev server and get to the record in question (via Library, or
it's already open).

**Don't trust the open draft blindly.** The module keeps a single
`localStorage` draft slot (`purelink-content-builder:draft`) that holds
whatever record was last worked on in that browser — including by Claude
during earlier testing. It's entirely possible for the `seed` text to be
genuinely the user's real notes while `name`/`sku`/`featureTitle`/
`features`/`useCase` are stale placeholders from an unrelated test run (this
has already happened once). Before drafting, check that `name`, `sku`,
and `linkedPanels` in the open record actually match the product the user
asked about — read it via:

```js
JSON.parse(localStorage.getItem('purelink-content-builder:draft'))
```

and cross-check against the shared library (`db.collection('content')`,
via `onSnapshot` — it has no `.get()`) in case the real saved copy lives
there instead of in the single draft slot.

## Step 2 — gather the same inputs the real endpoint would get

1. **Seed notes**: the record's `seed` field, verbatim.
2. **Additional context**: the record's `additionalContext` field, if any.
3. **Real ports**: for every entry in the record's `linkedPanels`, read
   that panel's actual `data/library/<sku>-layout.json` and pull every
   `kind: "port"` item from both `panels.front` and `panels.rear` (type,
   func, label). Ground every feature in these — don't infer ports from
   the product name or from memory of similar products. If no panels are
   linked, don't invent specific port counts or connector types; keep
   features general to the seed notes, same as the real prompt instructs.
4. **Existing draft text**: if the record already has non-placeholder
   `featureTitle`/`features`/`useCase`, treat it as a starting point to
   improve rather than discard, same as the real prompt does.

## Step 3 — produce the output

Write `featureTitle`, 5 `features`, `useCase`, and 5 `labelFeatures`
following Step 0's rules. Treat this like writing the actual API response
the endpoint would have returned — same tone, same grounding discipline —
not like a looser chat answer.

## Step 4 — fill it in, don't just paste it in chat

Fill the fields directly into the open record in the browser
(`form_input` on the Feature Title / Feature 1–5 / Use Case / Short
feature 1–5 fields) so the user can review in place, unless they've asked
for the text in chat instead. **Never touch `Name` or `SKU`** — those are
compliance-relevant identity fields the user must confirm themselves, not
content to draft. If they're showing placeholder/test values, say so and
leave them for the user to fix before they hit Save.

## When this skill is done being needed

Once `/api/draft-content` works end-to-end (organisation has credits, a
real key is configured), stop using this skill — point the user at the
real "Draft with AI" button instead. If asked to run this again after
that point, mention the real button is available and confirm whether they
still want the manual version anyway.
