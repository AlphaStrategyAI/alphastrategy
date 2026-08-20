# alphastrategy Portfolio glance bands

**Date:** 2026-08-20
**Status:** Requirements (improvement cycle on v1)
**Repo:** `AlphaStrategyAI/alphastrategy`
**Parent contract:** [`2026-08-19-alphastrategy-v1-requirements.md`](2026-08-19-alphastrategy-v1-requirements.md)
**Technical design:** [`docs/plans/2026-08-20-alphastrategy-glance-bands-technical-design.md`](../plans/2026-08-20-alphastrategy-glance-bands-technical-design.md)

Paper only. Five screens. Quiet cockpit **tokens unchanged**. No sixth nav tab. No live. No WebSockets. No chart libraries. No Supervisor math change. Existing metric **ids stay** so painters keep working.

This cycle makes Portfolio **first glance** match the goal: a personal investor sees book, flatten-capable risk, and session clock as three labeled bands, with Equity as the hero — not eight identical tiles.

## 1. Why this increment exists

Goal check against current main (`fc74b45`):

| Goal slice | v1 / later contract | Current desk |
| --- | --- | --- |
| 界面令人眼前一亮 | §8 Quiet cockpit: dense numbers, **sparse chrome**. Same tokens, different job from a research lab. | `.metrics` is `auto-fill minmax(140px)`. Equity, Gross, Session, Orders today are the same 1.15rem tile. Adding rails made first glance *worse*. |
| 凭直觉交互 | §8 Portfolio home: equity, cash, PnL, gross, positions, sleeves, countdown. | Book facts, flatten budgets, and RTH clock share one unlabeled soup. Session OPEN is easy to confuse with header LIVE (already documented); grouping Clock as its own band reduces that. |
| 组合管理 | Combined book vs residual cash. | Cash composition exists but sits equal to Orders today. |
| 风险可控 | Flatten budgets (gross, names, orders) must be readable before they fire. | Those tiles do not read as a risk strip. |
| 易于维护 | Markup without inline layout. | Four `style="margin-top: 0.75rem"` in `index.html`. `.grid` has no columns, so Positions and Sleeves **stack** on a wide desk. |

Research applied (not a new palette):

- **Tufte / Gestalt proximity:** group what is asked together. Three questions → three bands: What is the book? How close to flatten? When does it trade?
- **Trading desks:** hero NAV (equity) larger than secondary stats; risk utilization is a strip, not mixed with the clock.
- **Quiet cockpit:** raise type scale only on Equity. Headings are sparse chrome (`glance-heading`), not a sixth screen.

## 2. Three glance bands

Replace the single `.metrics` wrapper on Portfolio with:

| id | aria-label / heading | Tiles (existing ids) |
| --- | --- | --- |
| `#glance-book` | Book | Equity (**hero**), Cash, Day PnL |
| `#glance-risk` | Flatten budgets | Gross, Names, Orders today |
| `#glance-clock` | Clock | Session, Next rebalance |

Each band: `class="glance-band"`, child `h2.glance-heading`, child `.metrics.nums`.

Equity tile: add class `hero` on the metric (or on `#metric-equity`). Hero value `font-size: 1.85rem` (others stay 1.15rem).

Band metric grids are **explicit columns**, not `auto-fill minmax(140px)`:

- Book and Flatten budgets: `repeat(3, minmax(0, 1fr))`
- Clock: `repeat(2, minmax(0, 1fr))`

Below 640px: one column is allowed (`grid-template-columns: 1fr`).

`#clock-line` stays under the Clock band.

## 3. Book table pair

Positions + Sleeves wrapper: `class="grid book-grid stack"` (no inline style).

From `min-width: 800px`, `.book-grid` is two columns `1fr 1fr`. Below that, one column.

## 4. Stack utility

CSS `.stack { margin-top: 0.75rem; }`. Remove every `style="margin-top: 0.75rem"` from `index.html`.

## 5. Help / README

Portfolio home is three bands: **Book**, **Flatten budgets**, **Clock**. Equity is the hero number. Positions and Sleeves sit side by side on a wide desk.

## 6. In / out

**In:** glance bands + headings; hero Equity; explicit metric columns; book-grid two columns; `.stack`; help/README; HTML/CSS/e2e tests.

**Out:** new tokens; chart libraries; sixth screen; changing JS metric ids; Supervisor/API changes; splitting `app.js` (ids unchanged, painters stay).

## 7. Verification

- HTML ids `glance-book`, `glance-risk`, `glance-clock`. Headings `Book`, `Flatten budgets`, `Clock`.
- `#metric-equity` lives inside `#glance-book`. `#metric-orders` inside `#glance-risk`. `#metric-session` inside `#glance-clock`.
- `class="hero"` (or parent) on the Equity metric. CSS `.metric.hero .metric-value` includes `1.85rem`.
- `index.html` contains no `style="margin-top`.
- CSS `.book-grid`, `.glance-band`, `.stack`. `#nav` still five screens.
- GET `/` includes `glance-book`.
- No real broker orders.
