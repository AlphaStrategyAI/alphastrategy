# alphastrategy Positions Next follows current allocations on last sleeve weights

**Date:** 2026-08-21
**Status:** Requirements (improvement cycle on v1)
**Repo:** `AlphaStrategyAI/alphastrategy`
**Parent contract:** [`2026-08-19-alphastrategy-v1-requirements.md`](2026-08-19-alphastrategy-v1-requirements.md) §5, §8
**Related:** [`2026-08-21-alphastrategy-target-cash-requirements.md`](2026-08-21-alphastrategy-target-cash-requirements.md)
**Technical design:** [`docs/plans/2026-08-21-alphastrategy-positions-next-technical-design.md`](../plans/2026-08-21-alphastrategy-positions-next-technical-design.md)

Paper only. Five screens. Quiet cockpit **tokens unchanged**. No sixth nav tab. No live. No WebSockets. No chart library. Do not revive `static/app.js`. `"Gross cap"` must not appear in assembled JS. `renderBanners` keeps a **single** `const reason`. Do not retry leftover orders. Resume does not catch up. Heartbeat still does **not** flatten. GET must not flatten. Keep `Next rebalance`. Keep Caps **four tiles**. Keep Headroom **four tiles**. Keep Positions glance **Rows / Wanted / Got / At cap**. Keep `live_limit.kind` book / send / unknown. Keep Book LIMIT rail. Do **not** overwrite Cash composition labels. Each JS part stays ≤ 400 lines. **Do not evaluate DSL on GET.** **Do not feed `_place_batch` from `live_book()`.** Positions **Wanted stays last combined**. Book Drift still last wanted vs last fill. Do not change Activity blotter Wanted / Got.

v1 §8 Portfolio is combined positions plus sleeve contribution. Caps LIMIT, Headroom Target cash, and Sleeves contribution already follow `combine(current allocations, last sleeve weights)` when every paper sleeve has last weights. Positions still show only last **Wanted**. After raising a sleeve from 0.10 to 0.18, Headroom says target cash 82% and Contribution 18%, but the holdings table still reads Wanted 10% with no next-send column. Rebalance dashboards show **policy target** beside last execution. That split on the home screen is not 凭直觉交互 or 组合管理.

## 1. Why this increment exists

Goal check against current main (`6b82a20`):

| Goal slice | v1 / later contract | Current desk |
| --- | --- | --- |
| 组合管理 | §5 next combined; §8 Portfolio combined positions | Wanted is last send. Next send names can be missing. |
| 凭直觉交互 | Same next book as Caps / Headroom / Sleeves | Operator must leave Positions to learn the send. |
| 界面令人眼前一亮 | Dense numbers, sparse chrome; halt/warn cannot be quiet | Next that differs from Wanted is the same muted numeral. |
| 易于使用 | Help: Positions Next follows current allocations on last sleeve weights. | Help says Wanted is last combined; no Next column. |

Research applied:

- **Policy target ≠ last execution.** Wanted / Got / Drift stay last send vs fill (TCA). **Next** is the next-send combined Caps already dry-runs.
- **Fail closed.** If `_next_send_ready` is false, omit `next` (em dash). Do not invent DSL / conformance weights. Do not seed demo names.
- **Union next-only names.** A name in next combined with no last wanted still appears (qty 0), same as wanted-only rows.
- **Warn token** `#f59e0b` on the Next cell when it differs from Wanted. Do not fail the row. Do not change Book bar (still wanted vs got).

Out: GET flatten; DSL on GET; fifth glance tile; changing Wanted; live; sixth screen.

## 2. Engine / API

Public `next_send_combined_glance(snapshot) -> dict | None`: None when not ready; else `_next_send_combined`.

`_enrich_positions(..., next_combined=None)`:

- If `symbol in next_combined`, set `next` to that weight.
- After wanted-only rows, union remaining next keys with non-zero weight as qty 0 rows (`wanted` omitted).

`handle_get_portfolio` passes `next_send_combined_glance(snapshot)`. GET does not flatten.

Fixture (do **not** use 0.40 name weight for LIMIT):

- last combined AAPL **0.10**, last sleeve weights `asb_x: {AAPL: 1.0}`, current sleeve **0.18**, empty qty
- `wanted == 0.10`, `next == 0.18`
- `close_all` unchanged

Second: paper sleeve without last weights → no `next` key (or null). Wanted still last combined.

Third: last combined AAPL 0.10; weights `{AAPL: 0.5, MSFT: 0.5}` at alloc **0.20** → MSFT row `next == 0.10`, no wanted (or wanted omitted).

Keep `test_portfolio_includes_wanted_name_with_no_fill`.
Keep `test_portfolio_contribution_follows_current_allocation` (Wanted 0.10).

## 3. Cockpit

Table head:

`Symbol / Qty / Notional / Day / Wanted / Next / Got / Book / Cap`

Empty `colspan='9'`. `formatNextCell` in `paint-rails.js`. Next cell warn `#f59e0b` when `|next − wanted| > 1e-9`. Glance tiles stay four. `paint-portfolio.js` ≤ 400 lines.

## 4. Help / README

Phrase (exact): `Positions Next follows current allocations on last sleeve weights`

Add to `execution` (after Sleeves contribution), `cockpit` (after Wanted is last combined), `how_portfolio` (after Positions Book column), `task_wanted`. README Portfolio after Wanted versus Got. Keep `Next rebalance`. Keep `Rows / Wanted / Got / At cap`. Keep Wanted is last combined.

## 5. In / out

**In:** `next_send_combined_glance`; Positions `next`; Next column; warn token; help/README; API + HTML/JS/CSS tests.

**Out:** GET flatten; DSL on GET; fifth glance tile; changing Wanted / Drift / blotter; live; sixth nav.

**Done when:**

1. GET `/api/portfolio` last combined 0.10, last weights AAPL 1.0, allocation 0.18 → `wanted == 0.10` and `next == 0.18`; `close_all` unchanged.
2. Missing last weights → no next on the row.
3. Next-only name appears with qty 0.
4. HTML has `<th>Next</th>` after Wanted. Empty colspan 9. Help contains the phrase. Five `#nav` screens. `"Gross cap"` not in assembled JS. No real broker.
