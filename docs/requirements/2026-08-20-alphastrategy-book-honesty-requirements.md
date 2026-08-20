# alphastrategy book honesty after miss and flatten

**Date:** 2026-08-20
**Status:** Requirements (improvement cycle on v1)
**Repo:** `AlphaStrategyAI/alphastrategy`
**Parent contract:** [`2026-08-19-alphastrategy-v1-requirements.md`](2026-08-19-alphastrategy-v1-requirements.md)
**Technical design:** [`docs/plans/2026-08-20-alphastrategy-book-honesty-technical-design.md`](../plans/2026-08-20-alphastrategy-book-honesty-technical-design.md)

Paper only. Five screens. Quiet cockpit **tokens unchanged**. No sixth nav tab. No live. No demo/ghost fills. Do not revive `static/app.js`. Resume stays halt-only and still does not catch up.

This cycle makes the Positions book the truth of last combined target versus the live book, and makes flatten a real end of the session loop that Start paper can leave.

## 1. Why this increment exists

Goal check against current main (`943799c`):

| Goal slice | v1 / later contract | Current desk |
| --- | --- | --- |
| 组合管理 | Combined target is the book the operator is running. Activity already shows Wanted / Got. | `GET /api/portfolio` only annotates **broker positions**. A name in `last_combined` with qty 0 never appears. |
| 稳定执行 | Flatten is account kill; Start paper is the second explicit action to trade. | `_flatten_account` leaves `last_combined` / sleeve allocations. `tick` returns immediately while `STOPPED`, so Start paper after flatten writes an allocation that **never rebalances**. |
| 风险可控 | Flattened book must not look live. | FLAT banner exists, but leftover last combined would paint wanted names as if the desk still wanted them. |
| 凭直觉交互 | Book glance is Equity / Cash / Day PnL. | Operator must scan Positions (and miss absent rows) to see tracking error. |
| 帮助文档 | Halt ≠ flatten; Resume does not catch up. | Copy never says flatten stops the loop, or that Start paper is how you run again. |

Research applied:

- **Blotter / TCA (wanted vs got):** intent that did not fill is still a book row, qty 0, not omitted. Do not invent VWAP or arrival-price children.
- **Allocation dashboards:** a glance **Drift** count (names off the last combined target by the same `max($1, 0.1% equity)` gap as `execution_deviation`) is enough. No tracking-error volatility chart.
- **Kill-switch:** after flatten, last target and live sleeve allocations must be empty/zero so the red FLAT book is empty and not a hidden live overlay.
- **NN/g recognition:** Book Drift sits next to Equity so the operator does not have to remember to open Positions.

## 2. Positions include wanted names with no fill

`_enrich_positions` unions broker positions with `last_combined` keys whose weight is non-zero.

A name only in `last_combined`:

- `qty` 0, `notional` 0, `weight` 0 (got)
- `wanted` = last combined weight

Do **not** seed demo symbols. Empty first-run stays empty until there is a last combined book.

## 3. Flatten clears the last book and live sleeves

On successful account flatten (`STOPPED` after `close_all`):

- `last_combined`, `last_got`, `last_sleeve_weights`, `last_sleeve_contribution`, `last_prices` are `{}`
- Every sleeve allocation is 0 and the id is on `stopped` (same as `stop_sleeve`)

Keep `last_rebalance_event` (countdown math). Keep audit history.

Do not change halt (still hold the book, still last combined).

## 4. Start paper after flatten leaves STOPPED

`start_sleeve` when state is `STOPPED`:

1. Set `prime_clock_after_resume` (do **not** catch up).
2. Enter `idle_in_session` or `idle_out_of_session` from the clock, same as `resume` after halt.
3. Then apply the new allocation as today.

Do **not** leave `FLATTENING` via Start paper (mid-flatten is not a new session). Resume remains halt-only.

## 5. Book Drift glance

Book metrics become four tiles: Equity (hero), Cash, Day PnL, **Drift**.

- Value: count of positions where `|wanted − got| * equity ≥ max($1, 0.1% equity)` (em dash when unknown).
- Sub: `max {fmtPct}` of those weight gaps, or em dash.
- `#metric-drift-bar` uses the existing util track (fail when the count is > 0).

Keep `#glance-book`. No chart library.

## 6. Help / README

- `how_portfolio`: Positions include wanted names with no fill. Book Drift is names off the last combined target.
- Cockpit / halt_flatten / `task_start`: Flatten clears the last book and stops the session loop. Start paper after flatten starts the loop again and does not catch up. Resume is only after halt.
- README Operator: same.

## 7. In / out

**In:** wanted-only position rows; flatten clears last book and zeros sleeves; Start paper leaves STOPPED; Book Drift tile; help/README; tests (API, supervisor, HTML/JS, e2e).

**Out:** VWAP/TWAP; ghost fills; Resume-after-flatten; sixth screen; live; `app.js`; changing halt vs flatten triggers.

## 8. Verification

- Portfolio with `last_combined.MSFT` and no MSFT position includes `qty` 0 and `wanted`.
- After account flatten, `last_combined` is `{}` and paper allocations are 0.
- After flatten, `start_sleeve` leaves `stopped`; a later legal open rebalance can place orders.
- HTML has `#metric-drift` inside `#glance-book`. `#nav` still five screens.
- No real broker orders.
