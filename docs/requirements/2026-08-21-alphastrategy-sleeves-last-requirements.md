# alphastrategy Sleeves Contribution names last against next

**Date:** 2026-08-21
**Status:** Requirements (improvement cycle on v1)
**Repo:** `AlphaStrategyAI/alphastrategy`
**Parent contract:** [`2026-08-19-alphastrategy-v1-requirements.md`](2026-08-19-alphastrategy-v1-requirements.md) §5, §8
**Related:** [`2026-08-21-alphastrategy-target-cash-requirements.md`](2026-08-21-alphastrategy-target-cash-requirements.md), [`2026-08-21-alphastrategy-next-glance-requirements.md`](2026-08-21-alphastrategy-next-glance-requirements.md)
**Technical design:** [`docs/plans/2026-08-21-alphastrategy-sleeves-last-technical-design.md`](../plans/2026-08-21-alphastrategy-sleeves-last-technical-design.md)

Paper only. Five screens. Quiet cockpit **tokens unchanged**. No sixth nav tab. No live. No WebSockets. No chart library. Do not revive `static/app.js`. `"Gross cap"` must not appear in assembled JS. `renderBanners` keeps a **single** `const reason`. Do not retry leftover orders. Resume does not catch up. Heartbeat still does **not** flatten. GET must not flatten. Keep `Next rebalance`. Keep Caps **four tiles**. Keep Headroom **four tiles**. Keep Positions glance **Rows / Wanted / Got / At cap**. Keep Sleeves glance **chrome only** (no Run tiles). Keep `live_limit.kind` book / send / unknown. Keep Book LIMIT rail. Do **not** overwrite Cash composition labels. Each JS part stays ≤ 400 lines. **Do not evaluate DSL on GET.** **Do not feed `_place_batch` from `live_book()`.** Positions **Wanted stays last combined**. Book Drift still last wanted vs last fill. Keep `colspan='9'` on Positions. Keep Sleeves table **Bundle / Allocation / Contribution**. Stopped sleeves keep last contribution.

v1 §8 Portfolio is combined positions plus sleeve contribution. `sleeve_contribution` already overlays `allocation × last sleeve weights` for positive sleeves. After raising a sleeve from 0.10 to 0.18, Headroom Target cash keeps `last 90%` under the next residual, and Positions keep Wanted 10% beside Next 18%. Sleeves Contribution silently becomes `AAPL 18%` with no last send. Rebalance dashboards keep **policy target** beside last execution. Dropping last contribution on the home Sleeves table is not 凭直觉交互 or 组合管理.

## 1. Why this increment exists

Goal check against current main (`a7aa182`):

| Goal slice | v1 / later contract | Current desk |
| --- | --- | --- |
| 组合管理 | §8 sleeve contribution on Portfolio | Glance contribution is next send; last send is gone. |
| 凭直觉交互 | Headroom last sub; Positions Wanted vs Next | Sleeves has only one number after an allocation change. |
| 易于使用 | Help: Sleeves Contribution names last against next. | Help says contribution follows current allocations; no last. |

Research applied:

- **Policy target ≠ last execution.** Contribution **number** stays the next-send overlay (same as Headroom Target cash number). **Last** is a muted `metric-sub` when it differs, same pattern as `#risk-head-target-sub`. Do not warn-color that sub (it is context, not LIMIT).
- **Fail closed.** If `_next_send_ready` is false, glance contribution is already last, so the sub is `—`. Stopped (`alloc <= 0`) keep last in the number; sub is `—`.
- **Do not add Sleeves glance tiles.** Table cell only.

Out: GET flatten; DSL on GET; fifth Positions tile; Sleeves tiles; changing overlay math; live; sixth screen.

## 2. Engine / API

`last_sleeve_contribution_glance(snapshot)` copies persisted `last_sleeve_contribution`.

GET `/api/portfolio` adds `"last_sleeve_contribution"` beside `"sleeve_contribution"`. Overlay math unchanged.

Fixture (do **not** use 0.40 name weight for LIMIT):

- last combined AAPL **0.10**, last sleeve weights `asb_x: {AAPL: 1.0}`, last contribution AAPL **0.10**, current sleeve **0.18**
- `sleeve_contribution.asb_x.AAPL == 0.18`
- `last_sleeve_contribution.asb_x.AAPL == 0.10`
- Positions `wanted == 0.10`, `next == 0.18`
- GET `close_all` unchanged

Keep `test_portfolio_contribution_follows_current_allocation`. Keep e2e stop: glance contribution equals pre-stop.

## 3. Cockpit

`formatContributionCell(nextMap, lastMap)` in `js/core.js` next to `fmtContribution`. Contribution `<td>` shows glance text; when last is a non-empty map and `fmtContribution` differs, append `<div class="metric-sub nums">last {lastText}</div>`. No warn class. `paint-portfolio.js` passes `portfolio.last_sleeve_contribution`. File ≤ 400 lines.

Do not put `Order size` / `Gross cap` in JS.

## 4. Help / README

Phrase (exact): `Sleeves Contribution names last against next`

Add to `cockpit` (after Positions Book names Next against Wanted), `how_portfolio` (after Sleeves contribution follows current allocations). README Operator after Sleeves contribution follows current allocations. Keep `Next rebalance`. Keep `Rows / Wanted / Got / At cap`. Keep `Sleeves contribution follows current allocations on last sleeve weights`. Keep Wanted is last combined.

## 5. In / out

**In:** `last_sleeve_contribution` on GET `/api/portfolio`; Contribution last sub; help/README; API + HTML/JS tests.

**Out:** GET flatten; DSL on GET; Sleeves tiles; changing overlay / stop semantics; live; sixth nav.

**Done when:**

1. GET `/api/portfolio` last contribution 0.10, current alloc 0.18 → glance 0.18 and last 0.10; `close_all` unchanged.
2. Assembled JS has `formatContributionCell` and `last ${` or `"last "`. Five `#nav` screens. `"Gross cap"` not in assembled JS. No real broker.
3. Help contains the phrase.
