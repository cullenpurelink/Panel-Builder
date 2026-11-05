# PureLink Modules Hub

The launcher shell — the normal entry point for the whole suite.
[`../start.bat`](../start.bat) opens this.

## What this is

A collapsible sidebar listing every module, with the selected one
embedded via `<iframe>` into the main area — each module is still its
own independent `index.html`, the Hub just frames them. It also has the
**"Push to GitHub"** button (`POST /api/git-push`, see
[`../tools/dev_server.py`](../tools/dev_server.py)): commits everything
with an auto message and pushes.

## Adding a module

Everything the Hub needs lives in one place: the `MODULES` array near the
top of [`index.html`](index.html)'s script, which already carries its own
comment on exactly this:

```js
/* Add the next module here: give it a folder next to "modules-hub" and
   "system-diagrams" (at the repo root), then add one entry below
   pointing at its index.html. */
var MODULES = [
  { id: 'panel-builder', name: 'Product Builder', icon: '▆',
    href: '../panel-builder/index.html', desc: '…' },
  // ...
];
```

A new module is: its own sibling folder at the repo root (ideally with
its own `README.md`, matching every existing module), an `index.html`
that loads [`../shared/local-db.js`](../shared/local-db.js) if it needs
local persistence, and one entry here. No other Hub code needs to
change — this is the intended drop-in point for the planned 3D-design
module integration.

## Opening it

Double-click [`index.html`](index.html), or just run
[`../start.bat`](../start.bat) (does both: starts the server and opens
this).
