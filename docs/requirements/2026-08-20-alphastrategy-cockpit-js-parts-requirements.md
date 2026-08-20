# alphastrategy Quiet cockpit JS parts

**Date:** 2026-08-20
**Status:** Requirements (improvement cycle on v1)
**Repo:** `AlphaStrategyAI/alphastrategy`
**Parent contract:** [`2026-08-19-alphastrategy-v1-requirements.md`](2026-08-19-alphastrategy-v1-requirements.md)
**Technical design:** [`docs/plans/2026-08-20-alphastrategy-cockpit-js-parts-technical-design.md`](../plans/2026-08-20-alphastrategy-cockpit-js-parts-technical-design.md)

Paper only. Five screens. Tokens unchanged. No sixth nav tab. No live. No bundler, no npm, no WebSockets. Browser still loads **one** `/app.js`. Behavior of painters, ids, and `window.confirm` ban stay.

This cycle makes the cockpit **maintainable**: the 1200-line IIFE is assembled from named parts that match the five screens, instead of one file that every increment has to touch.

## 1. Why this increment exists

Goal check against current main (`490d99b`):

| Goal slice | Contract | Current desk |
| --- | --- | --- |
| 易于维护 | §11 repository shape; Quiet cockpit is static HTML/JS | `app.js` is 1227 lines, one IIFE. Glance bands, labels, help, Run zones, and band errors all land in the same file. |
| 架构 | One Supervisor; small files that change together | Python is already split (`risk/labels.py`, `supervisor/heartbeat.py`). The cockpit is not. |
| 界面 / 交互 | Do not change what the operator sees | Split must be **source layout only**. One script URL. Same IIFE wrap so `const state` stays private. |
| 帮助文档 | Canonical helptext | One sentence: cockpit JS is assembled from `web/static/js/` parts. |

Research applied:

- **Screaming architecture / screen-shaped modules:** files named after the five screens plus `core` and `boot`, not after MVC layers.
- **No bundler in v1:** concatenate at serve time (stdlib HTTP). Tests consume the same `cockpit_js()` the server sends. Do not add webpack/esbuild.
- **IIFE privacy:** keep one wrap so `state` is not a `window` global (secrets still never appear; this is still paper desk state).
- **File size:** each part ≤ 400 lines so a later increment fits in one review.

## 2. Source of truth

Add `alphastrategy.web.cockpit`:

- `STATIC_DIR`
- `JS_PARTS` ordered tuple:
  1. `js/core.js` — caps, state, fmt, api, screen, errors, import helpers, labels
  2. `js/paint-portfolio.js`
  3. `js/paint-strategies.js`
  4. `js/paint-run.js`
  5. `js/paint-activity.js`
  6. `js/paint-risk.js`
  7. `js/boot.js` — refresh, form handlers, help, keys, interval
- `cockpit_js() -> str` wraps those files in `(function () { "use strict"; ... })();`

There is **no** `web/static/app.js` on disk. `GET /app.js` and `GET /static/app.js` return `cockpit_js()` bytes. `index.html` still has `<script src="app.js">`.

## 3. Tests

Pytest `js_text` fixture reads `cockpit_js()`, not a file named `app.js`. Existing substring tests stay. `GET /app.js` body equals `cockpit_js().encode()`.

## 4. Help / README

Architecture tree lists `web/static/js/`. Help walls or cockpit: Quiet cockpit JS is assembled from `js/` parts; the browser still loads `/app.js`.

## 5. In / out

**In:** `cockpit.py`, seven parts, serve-time assemble, tests, README/help. No operator-visible change.

**Out:** npm bundler; ES modules in the browser; exposing `state` on `window`; sixth screen; changing painters; live.

## 6. Verification

- `JS_PARTS` as listed; each file exists; each ≤ 400 lines; `app.js` absent from `static/`.
- `cockpit_js()` starts with `(function () {` and ends with `})();`, contains `function setRunError` and `function renderPortfolio`, no `window.confirm`.
- GET `/app.js` == GET `/static/app.js` == `cockpit_js()` bytes.
- Five `#nav` screens. No real broker orders.
