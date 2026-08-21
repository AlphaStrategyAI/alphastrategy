# alphastrategy Headroom Target cash follows current allocations on last sleeve weights

**Date:** 2026-08-21
**Status:** Requirements (improvement cycle on v1)
**Repo:** `AlphaStrategyAI/alphastrategy`
**Parent contract:** [`2026-08-19-alphastrategy-v1-requirements.md`](2026-08-19-alphastrategy-v1-requirements.md) §5, §8
**Related:** [`2026-08-21-alphastrategy-alloc-limit-requirements.md`](2026-08-21-alphastrategy-alloc-limit-requirements.md)
**Technical design:** [`docs/plans/2026-08-21-alphastrategy-target-cash-technical-design.md`](../plans/2026-08-21-alphastrategy-target-cash-technical-design.md)

Paper only. Five screens. Quiet cockpit **tokens unchanged**. No sixth nav tab. No live. No WebSockets. No chart library. Do not revive `static/app.js`. `"Gross cap"` must not appear in assembled JS. `renderBanners` keeps a **single** `const reason`. Do not retry leftover orders. Resume does not catch up. Heartbeat still does **not** flatten. GET must not flatten. Keep `Next rebalance`. Keep Caps **four tiles**. Keep Headroom **four tiles** Names / Orders today / Cash / Target cash. Keep `live_limit.kind` book / send / unknown. Keep Book LIMIT rail. Do **not** overwrite Cash composition **labels** (`invested … · cash … · target cash …`). Each JS part stays ≤ 400 lines. **Do not evaluate DSL on GET.** **Do not feed `_place_batch` from `live_book()`.** Positions **Wanted stays last combined**. Keep `colspan='8'`.

v1 §5: `combined[asset] = Σ allocation_i * weight_i[asset]`. Residual is cash. Caps LIMIT already dry-runs that next send when last sleeve weights cover every paper sleeve. Headroom Target cash and Book’s cash-composition target still use frozen `last_combined`. After a rebalance at allocation 0.10 (AAPL last combined 0.10, target cash 90%), the operator raises the sleeve to 0.18. Caps LIMIT can warn. Headroom still says target cash 90%. Portfolio Sleeves Contribution still shows 0.10. Rebalance dashboards treat **policy target** (next book) as distinct from last executed weights. Showing last residual as the live target is not 凭直觉交互 or 组合管理.

## 1. Why this increment exists

Goal check against current main (`e61a9ca`):

| Goal slice | v1 / later contract | Current desk |
| --- | --- | --- |
| 组合管理 | §5 residual cash; §8 combined positions + sleeve contribution | Target cash and contribution are last send. Run already shows the new allocation. |
| 风险可控 | Caps LIMIT follows current allocations × last weights | Headroom cash marker still aims at the old residual. |
| 凭直觉交互 | Cash / Headroom / Sleeves should match the next send Caps is scoring | LIMIT flatten-send vs Target cash 90% vs Contribution 10%. |
| 易于使用 | Help: Headroom Target cash follows current allocations on last sleeve weights. | Help only names Caps LIMIT / wait-weights. |

Research applied:

- **Policy target ≠ last execution.** Rebalance dashboards show current weight vs **policy** target; cash has its own target residual. Do not overwrite Positions Wanted (last intent vs fill / TCA).
- **Same next-send combined as Caps LIMIT.** `_next_send_ready` + `_next_send_combined`. When not ready, keep last combined residual and last contribution (fail closed, same as unknown LIMIT).
- **Stopped sleeves keep last contribution** until the next rebalance (e2e: stop does not rewrite contribution).
- **Headroom Target cash sub names last** when last residual differs, so the last send is still readable.

Out: GET flatten; placing; DSL on GET; Positions Next column; changing Wanted; fifth Headroom tile; live; sixth screen.

## 2. Engine / API

`from_supervisor`: after `summarize` (which still keys target cash on `last_combined`):

1. `last_target_cash_weight` = that last residual (or null).
2. If `_next_send_ready(snapshot)` and `_next_send_combined(snapshot)` is a dict, set `target_cash_weight` to `max(0, 1 - sum(next values))`.

GET `/api/portfolio` `sleeve_contribution`:

1. Start from persisted `last_sleeve_contribution`.
2. If ready, for each positive sleeve overwrite that id with `{asset: allocation * last_sleeve_weights[id][asset]}`.
3. Allocation `<= 0` (stopped) keeps last contribution.

Fixture (do **not** use 0.40 name weight for LIMIT):

- last combined AAPL **0.10**, last sleeve weights `asb_x: {AAPL: 1.0}`, current sleeve **0.18**, last contribution AAPL **0.10**
- `target_cash_weight == 0.82`, `last_target_cash_weight == 0.90`
- portfolio `sleeve_contribution.asb_x.AAPL == 0.18`
- Positions `wanted` still **0.10**
- GET `close_all` unchanged

Keep `test_summarize_*` last_combined residual.
Keep `test_portfolio_includes_contribution_and_position_weight` (no sleeves / no weights → last 0.4).
Keep empty-prices last_combined 0.40 → `live_limit` null.
Keep wait-weights unknown (no overlay of next cash).

## 3. Cockpit

`#risk-head-target-sub`: `last {fmtPct}` when last and next residuals differ by more than `1e-9`; else `—`.

Book `#metric-cash-sub` still `invested … · cash … · target cash …` with the **next** residual as the target number. Cash bar marker follows that next residual.

Do not fail the Target cash tile. Do not put `Order size` / `Gross cap` in JS.

## 4. Help / README

Phrases (exact):

- `Headroom Target cash follows current allocations on last sleeve weights`
- `Sleeves contribution follows current allocations on last sleeve weights`

Add to `execution` (after Caps LIMIT current allocations), `how_risk` (after Headroom four tiles), `how_portfolio` (after Positions Book column). README Operator after Caps LIMIT current allocations. Keep `Next rebalance`. Keep four Headroom tiles. Keep Wanted is last combined.

## 5. In / out

**In:** overlay next-send residual on `target_cash_weight`; `last_target_cash_weight`; glance contribution; Headroom last sub; help/README; API + unit + HTML/JS tests.

**Out:** GET flatten; DSL on GET; Positions Next column; changing Wanted; fifth tile; live; sixth nav.

**Done when:**

1. GET `/api/status` with last combined 0.10, last weights AAPL 1.0, allocation 0.18 → `target_cash_weight == 0.82` and `last_target_cash_weight == 0.90`; `close_all` unchanged.
2. GET `/api/portfolio` same fixture → contribution AAPL 0.18; Wanted 0.10.
3. No sleeves / last contribution 0.4 still 0.4.
4. HTML has `#risk-head-target-sub`. Help contains both phrases. Five `#nav` screens. `"Gross cap"` not in assembled JS. No real broker.
