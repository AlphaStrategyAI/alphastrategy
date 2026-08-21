# alphastrategy Positions Book names Next against Wanted

**Date:** 2026-08-21
**Status:** Requirements (improvement cycle on v1)
**Repo:** `AlphaStrategyAI/alphastrategy`
**Parent contract:** [`2026-08-19-alphastrategy-v1-requirements.md`](2026-08-19-alphastrategy-v1-requirements.md) §5, §8
**Related:** [`2026-08-21-alphastrategy-positions-next-requirements.md`](2026-08-21-alphastrategy-positions-next-requirements.md)
**Technical design:** [`docs/plans/2026-08-21-alphastrategy-next-glance-technical-design.md`](../plans/2026-08-21-alphastrategy-next-glance-technical-design.md)

Paper only. Five screens. Quiet cockpit **tokens unchanged**. No sixth nav tab. No live. No WebSockets. No chart library. Do not revive `static/app.js`. `"Gross cap"` must not appear in assembled JS. `renderBanners` keeps a **single** `const reason`. Do not retry leftover orders. Resume does not catch up. Heartbeat still does **not** flatten. GET must not flatten. Keep `Next rebalance`. Keep Caps **four tiles**. Keep Headroom **four tiles**. Keep Positions glance **Rows / Wanted / Got / At cap**. Keep `live_limit.kind` book / send / unknown. Keep Book LIMIT rail. Do **not** overwrite Cash composition labels. Each JS part stays ≤ 400 lines. **Do not evaluate DSL on GET.** **Do not feed `_place_batch` from `live_book()`.** Positions **Wanted stays last combined**. Book Drift still last wanted vs last fill. Do not change Activity blotter Wanted / Got. Keep `colspan='9'`. Keep `formatNextCell`. **Do not add a fifth glance tile.**

v1 §8 Portfolio is combined positions at a glance. Caps LIMIT, Headroom Target cash, Sleeves contribution, and the Positions **Next** column already follow `combine(current allocations, last sleeve weights)` when every paper sleeve has last weights. After raising a sleeve from 0.10 to 0.18, the table Next cell goes amber, but the Positions glance Wanted hero still only counts last-send names, and the Book bar still marks only Wanted and Got. The operator must read the table to see the send Caps already scores. Rebalance dashboards put **policy target** on the same sparkline as last execution. Hiding Next on glance and on the Book bar is not 凭直觉交互, 眼前一亮, or 组合管理.

## 1. Why this increment exists

Goal check against current main (`33ad87d`):

| Goal slice | v1 / later contract | Current desk |
| --- | --- | --- |
| 组合管理 | §8 combined positions at a glance | Glance Wanted is last-send count. Book bar is last wanted vs got. |
| 凭直觉交互 | Same next book as Caps / Headroom / Next column | Operator must scan the Next column to see the send. |
| 界面令人眼前一亮 | Halt/warn cannot be quiet; dense numbers, sparse chrome | Next that differs from Wanted is invisible above the fold. |
| 易于使用 | Help: Positions Book names Next against Wanted. | Help names the Next column, not glance or Book bar. |

Research applied:

- **Policy target ≠ last execution.** Wanted / Got / Drift stay last send vs fill (TCA). **Next** is the next-send combined Caps already dry-runs. Glance and Book bar must name that split without a fifth tile.
- **Fail closed.** If a row has no finite `next`, omit the bar marker and do not count that row as a next-diff. If no row has a finite next, Wanted sub is `—` (not `next 0`). Do not invent DSL / conformance weights.
- **Wanted hero sub.** `#pos-count-wanted-sub` is `next {n}` with warn `#f59e0b` when `n > 0` names have a finite Next that differs from Wanted (`|next − wanted| > 1e-9`, including next-only names). Else `—`. Do not change the Wanted count.
- **Book bar third mark.** `wantedGotBar` draws `.wg-next` when `pos.next` is finite. Scale includes next. `aria-label` includes `next` when present. Paint next **under** wanted so equal ticks stay the white last-send mark. Drift class still wanted vs fill.

Out: GET flatten; DSL on GET; fifth glance tile; changing Wanted / Drift / blotter; live; sixth screen; API shape change.

## 2. Engine / API

No change. GET `/api/portfolio` already stamps `next` via `next_send_combined_glance`. Keep `close_all` unchanged. Keep `test_portfolio_next_follows_current_allocation`. Keep `test_portfolio_omits_next_when_paper_sleeve_has_no_last_weights`. Keep `test_portfolio_includes_next_only_name`.

## 3. Cockpit

Wanted hero inside `#glance-positions` gains `#pos-count-wanted-sub` (`metric-sub`). Glance tiles stay four. `paintPositionsWantedNextSub` lives in `paint-rails.js` so `paint-portfolio.js` stays ≤ 400 lines. `renderPositionsGlance` calls it.

`wantedGotBar(wanted, got, cap, fill, next)`: third mark `.wg-next` `#f59e0b` when next is finite; scale `max(cap, wanted, got, next, 0.01)`; aria `wanted … got …` plus ` next …` when finite. Drift still `|wanted − fill| > 0.001` (fill falls back to got). Call site passes `pos.next`. Empty table still `colspan='9'`.

Do not put `Order size` / `Gross cap` in JS. Do not fail the Wanted tile.

## 4. Help / README

Phrase (exact): `Positions Book names Next against Wanted`

Add to `cockpit` (after Positions Book column), `how_portfolio` (after Positions Next follows current allocations), `task_wanted` (after Positions Next follows current allocations). README Portfolio after the Book bar (wanted vs got). Keep `Next rebalance`. Keep `Rows / Wanted / Got / At cap`. Keep `Positions Next follows current allocations on last sleeve weights`. Keep Wanted is last combined.

## 5. In / out

**In:** Wanted hero next-diff sub; Book bar next mark; help/README; HTML/CSS/JS tests.

**Out:** GET flatten; DSL on GET; fifth glance tile; changing Wanted / Drift / blotter / API; live; sixth nav.

**Done when:**

1. HTML has `#pos-count-wanted-sub` under the Wanted hero. Glance still four tiles. Empty colspan 9.
2. Assembled JS has `paintPositionsWantedNextSub` and `wg-next`; `wantedGotBar(..., pos.next)`; Next cell helper unchanged.
3. CSS `#pos-count-wanted-sub.warn` and `.wg-next` use `#f59e0b`.
4. Help contains the phrase. Five `#nav` screens. `"Gross cap"` not in assembled JS. No real broker.
