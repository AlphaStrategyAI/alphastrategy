# alphastrategy Sleeves names when a paper sleeve has no last weights

**Date:** 2026-08-21
**Status:** Requirements (improvement cycle on v1)
**Repo:** `AlphaStrategyAI/alphastrategy`
**Parent contract:** [`2026-08-19-alphastrategy-v1-requirements.md`](2026-08-19-alphastrategy-v1-requirements.md) §5, §8
**Related:** [`2026-08-21-alphastrategy-roster-weights-requirements.md`](2026-08-21-alphastrategy-roster-weights-requirements.md)
**Technical design:** [`docs/plans/2026-08-21-alphastrategy-sleeves-weights-technical-design.md`](../plans/2026-08-21-alphastrategy-sleeves-weights-technical-design.md)

Paper only. Five screens. Quiet cockpit **tokens unchanged**. No sixth nav tab. No live. No WebSockets. No chart library. Do not revive `static/app.js`. `"Gross cap"` must not appear in assembled JS. `renderBanners` keeps a **single** `const reason`. Do not retry leftover orders. Resume does not catch up. Resume does **not** seed. Heartbeat still does **not** flatten. GET must not flatten. GET must **not** evaluate DSL. Keep `Next rebalance`. Keep Caps **four tiles**. Keep Headroom **four tiles**. Keep Positions glance **Rows / Wanted / Got / At cap**. Keep After halt **Reason / Spent / Next / Resume**. Keep Strategies Inventory **Imported / Paper / Halted / Stopped**. Keep Roster columns **Bundle / State / Allocation / Risk**. Keep Sleeves columns **Bundle / Allocation / Contribution** (`colspan='3'`). Keep `live_limit.kind` book / send / unknown. Do **not** overwrite Cash composition labels. Each JS part stays ≤ 400 lines. **Do not feed `_place_batch` from `live_book()`.** Keep exact Start hint waits-for-resume and seed-hold sentences. Keep `formatHaltBanner` maps. Keep `sleeveState` four words. Keep GET `/api/portfolio` `last_sleeve_weight_ids` (presence only; no `"last_sleeve_weights"` key). Keep Roster `formatWeightsWaitSub` / allocation rail.

After #98, Strategies Roster and Run cards name `weights` when a paper sleeve has no last weights. Portfolio **Sleeves** (home) still paints Contribution as `—`. Inventory **Paper** stays `#10b981` whenever count > 0. Clock Next and Caps already wait. The management glance and the home contribution cell still look healthy. That is not 可靠, 凭直觉交互, or 界面令人眼前一亮.

## 1. Why this increment exists

Goal check against current main (`fe64d5a`):

| Goal slice | v1 / later contract | Current desk |
| --- | --- | --- |
| 可靠 | Missing last weights stay visible on every sleeve list. | Roster/Run wait; Portfolio Sleeves shows `—`. |
| 凭直觉交互 | Same desk word **weights**. Paper hero must not look running-green while Caps cannot dry-run. | Paper count is `status-running` whenever count > 0. |
| 易于使用 | Help names Roster wait. | Help never says Sleeves or Paper count name the wait. |
| 风险可控 | GET does not eval DSL; Resume does not seed. | Unchanged; glance + naming only. |

Research applied:

- **Same helper.** Reuse `formatWeightsWaitSub` / `sleeveHasLastWeights` / `last_sleeve_weight_ids`. Do not infer from contribution maps (same false-positive as #98).
- **Paper hero is an instrument.** Green means paper is send-ready. Warn `#f59e0b` when any paper allocation has no last weights. Do not keep `status-running` at the same time.
- **Do not grow `paint-portfolio.js` / `paint-rails.js` past 400.** Put wait rendering in `formatContributionCell` (core.js). Portfolio only passes `id` and allocation.

Out: GET flatten; DSL on GET; placing; seeding on resume; dumping weight maps; fifth sleeve state; fifth Inventory tile; extra Sleeves column; live; sixth nav; changing CLI exact BOOK/HALT/LIMIT splitlines.

## 2. Engine / API

No new endpoints. Keep `last_sleeve_weight_ids(snapshot)`. GET `/api/portfolio` already returns that list. Do not add `"last_sleeve_weights"`. GET still must not flatten.

## 3. Cockpit

`formatContributionCell(nextMap, lastMap, bundleId, alloc)` in `core.js`:

- If `formatWeightsWaitSub(bundleId, alloc)` is non-empty, return `<td class="nums">` + that sub + `</td>` (do not also paint last/next contribution).
- Else existing next + optional `last ` sub.

`renderPortfolio` Sleeves rows call `formatContributionCell(contrib[id], lastContrib[id], id, sleeves[id])`. Keep `colspan='3'`.

`renderStrategies` Paper tile: after counting, if any id has `Number(alloc) > 0` and not `sleeveHasLastWeights(id)`, `#strat-count-paper` uses class `warn` (not `status-running`). Otherwise keep `status-running` when count > 0.

CSS `#f59e0b` for `#sleeves-table .metric-sub.warn` and `#strat-count-paper.warn`.

No `window.confirm`. No `window.state`. `"Gross cap"` not in JS.

## 4. Help / README

Phrases (exact):

- `Sleeves names when a paper sleeve has no last weights`
- `Paper count warns when a paper sleeve has no last weights`

Add the first to `how_portfolio` after `Sleeves Contribution names last against next.` Add to `cockpit` after that same sentence.

Add the second to `how_strategies` after `Roster names when a paper sleeve has no last weights.`

README Operator after `Roster names when a paper sleeve has no last weights.`

Keep `Next rebalance`. Keep `Roster names when a paper sleeve has no last weights`. Keep waits-for-resume.

## 5. In / out

**In:** Contribution cell wait via `formatContributionCell`; Inventory Paper warn; CSS; help/README.

**Out:** GET flatten; DSL on GET; placing; seeding; weight maps in JSON; CLI splitline changes; live; sixth nav.

## 6. Verification

- JS: `formatContributionCell` calls `formatWeightsWaitSub`; Portfolio passes `id` and allocation; Paper tile toggles `warn` vs `status-running`; `"Gross cap"` not in JS.
- CSS warn `#f59e0b` on `#sleeves-table .metric-sub.warn` and `#strat-count-paper.warn`.
- Help contains both phrases. Five `#nav` screens. Sleeves `colspan='3'`.
- `PYTHONPATH=src python3 -m pytest tests/alphastrategy/ -q`
