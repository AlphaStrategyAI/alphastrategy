# alphastrategy Caps LIMIT follows current allocations on last sleeve weights

**Date:** 2026-08-21
**Status:** Requirements (improvement cycle on v1)
**Repo:** `AlphaStrategyAI/alphastrategy`
**Parent contract:** [`2026-08-19-alphastrategy-v1-requirements.md`](2026-08-19-alphastrategy-v1-requirements.md) §5, §7
**Related:** [`2026-08-20-alphastrategy-send-limit-requirements.md`](2026-08-20-alphastrategy-send-limit-requirements.md)
**Technical design:** [`docs/plans/2026-08-21-alphastrategy-alloc-limit-technical-design.md`](../plans/2026-08-21-alphastrategy-alloc-limit-technical-design.md)

Paper only. Five screens. Quiet cockpit **tokens unchanged**. No sixth nav tab. No live. No WebSockets. No chart library. Do not revive `static/app.js`. `"Gross cap"` must not appear in assembled JS. `renderBanners` keeps a **single** `const reason`. Do not retry leftover orders. Resume does not catch up. Heartbeat still does **not** flatten. GET must not flatten. Keep `Next rebalance`. Keep Caps **four tiles** and `#risk-cap-order` / `#risk-cap-rebalance`. Keep `live_limit.kind` book vs send. Keep Book LIMIT rail. Do **not** overwrite Cash composition subs. Each JS part stays ≤ 400 lines. **Do not evaluate DSL on GET.** **Do not feed `_place_batch` from `live_book()`.**

v1 §5: `combined[asset] = Σ allocation_i * weight_i[asset]`. Next legal send evaluates DSL then combines **current** paper allocations. Caps next-send LIMIT still dry-runs frozen `last_combined`. After a rebalance at allocation 0.10 (AAPL last combined 0.10), the operator raises the sleeve to 0.18. Last combined stays 0.10. Empty qty, mark $100, equity $10k, spoken Order size 10%: replay last combined buys $1,000 (not through). The next rebalance buys $1,800 and flattens. That is not 可靠 or 风险可控.

## 1. Why this increment exists

Goal check against current main (`1463df7`):

| Goal slice | v1 / later contract | Current desk |
| --- | --- | --- |
| 可靠 | Next send uses current allocations. | LIMIT replays last combined. |
| 风险可控 | Warn before the send that will flatten. | Allocation tighten looks quiet until the window. |
| 凭直觉交互 | Caps / Clock Next / LIMIT banner name the send. | They stay quiet while Run already shows the new allocation. |
| 易于使用 | Help: Caps LIMIT follows current allocations on last sleeve weights. | Help only names Order size / Orders / rebalance. |

Research applied:

- **Replay last sleeve DSL weights at current allocations.** `last_sleeve_weights` is already persisted (weights before allocation). `combine([(alloc, weights) …])` with `snapshot.sleeves`. Do not sandbox on GET. Do not invent weights for a sleeve that has never rebalanced.
- **If that set is empty, keep last_combined.** Existing Order size fixture (no sleeve weights) stays valid. Empty `last_prices` still skips.
- **Book LIMIT still wins.** `check_book` on the live blotter is unchanged. Target cash / Headroom still follow last combined.

Out: GET flatten; placing; DSL eval on glance; fifth Caps tile; live; sixth screen.

## 2. Engine / API

`from_supervisor(live=True)` dry-run combined:

1. For each `last_sleeve_weights[id]` whose `sleeves[id]` is finite and `> 0`, append `(alloc, weights)`.
2. If that list is non-empty, `combine(...)`. On `ValueError` (alloc sum > 1) → skip send LIMIT (null), do not fail GET.
3. Else use `last_combined` as today.

Fixture (do **not** use 0.40 name weight):

- last combined AAPL **0.10**, last sleeve weights `asb_x: {AAPL: 1.0}`, current sleeve **0.18**, mark **$100**, equity **$10k**, empty qty, spoken Order size **0.10**
- Replay last combined would not fire (`$1,000` is not `>` `$1,000`)
- Recombined 0.18 fires `max_order_notional_frac`, `kind == send`
- GET `close_all` unchanged

Keep `test_from_supervisor_live_limit_ignores_last_combined` (empty prices).
Keep `test_status_live_limit_next_send_order_size` (no sleeve weights → last combined 0.18 still fires).

## 3. Cockpit

No HTML tile change. Banner / Clock Next / Caps already follow `live_limit`.

## 4. Help / README

Phrase (exact): `Caps LIMIT follows current allocations on last sleeve weights`

Add to `execution`, `halt_flatten`, `how_risk`, README Operator. Keep `Caps LIMIT follows a next send through Order size`. Keep `Next rebalance`. Keep four Caps tiles.

## 5. In / out

**In:** `_next_send_combined`; dry-run uses current allocations × last sleeve weights; help/README; API + unit tests.

**Out:** GET flatten; DSL on GET; fifth tile; changing Headroom target cash; live; sixth nav.

**Done when:**

1. GET `/api/status` with last combined 0.10, last sleeve weights AAPL 1.0, allocation 0.18, Order size 0.10 → `live_limit.reason == max_order_notional_frac` and `kind == send`; `close_all` unchanged.
2. Same fixture with empty `last_prices` still has `live_limit` null.
3. Existing last-combined 0.18 Order size fixture still fires.
4. Help contains the new phrase. Five `#nav` screens. `"Gross cap"` not in assembled JS. No real broker.
