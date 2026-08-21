# alphastrategy Caps LIMIT waits when a paper sleeve has no last weights

**Date:** 2026-08-21
**Status:** Requirements (improvement cycle on v1)
**Repo:** `AlphaStrategyAI/alphastrategy`
**Parent contract:** [`2026-08-19-alphastrategy-v1-requirements.md`](2026-08-19-alphastrategy-v1-requirements.md) §5, §7
**Related:** [`2026-08-21-alphastrategy-alloc-limit-requirements.md`](2026-08-21-alphastrategy-alloc-limit-requirements.md)
**Technical design:** [`docs/plans/2026-08-21-alphastrategy-wait-weights-technical-design.md`](../plans/2026-08-21-alphastrategy-wait-weights-technical-design.md)

Paper only. Five screens. Quiet cockpit **tokens unchanged**. No sixth nav tab. No live. No WebSockets. No chart library. Do not revive `static/app.js`. `"Gross cap"` must not appear in assembled JS. `renderBanners` keeps a **single** `const reason`. Do not retry leftover orders. Resume does not catch up. Heartbeat still does **not** flatten. GET must not flatten. Keep `Next rebalance`. Keep Caps **four tiles** and `#risk-cap-order` / `#risk-cap-rebalance`. Keep `live_limit.kind` book vs send. Keep Book LIMIT rail. Do **not** overwrite Cash composition subs. Each JS part stays ≤ 400 lines. **Do not evaluate DSL on GET.** **Do not feed `_place_batch` from `live_book()`.** Do not add `next_send_unknown` to `POLICY_LABELS`.

v1 §5: next legal send evaluates DSL then combines **current** paper allocations. Alloc-limit dry-runs `combine(current allocations, last sleeve weights)` and, when that pair list is empty, **falls back to frozen `last_combined`**. After flatten (empty weights) the operator Start-papers a new sleeve at 0.18. Last combined can still be a leftover 0.18 AAPL book from a prior sleeve, or the Order-size fixture book. Empty qty, mark $100, equity $10k, spoken Order size 10%: Caps LIMIT says the next send will flatten through Order size. The next rebalance evaluates the **new** sleeve’s DSL. That book is not last combined. Pre-trade research: if the gate cannot see complete state, it must fail closed rather than certify a stale book. Replaying last combined here is not 可靠 or 风险可控.

## 1. Why this increment exists

Goal check against current main (`aac0b2b`):

| Goal slice | v1 / later contract | Current desk |
| --- | --- | --- |
| 可靠 | Next send uses current paper sleeves. | A paper sleeve with no `last_sleeve_weights` still dry-runs last combined. |
| 风险可控 | Warn only when the dry-run is the next send. | False Order size LIMIT after Start paper; or quiet LIMIT when another sleeve is missing weights. |
| 凭直觉交互 | Clock Next flatten send means flatten. | Unknown next send still paints flatten / flatten send from the stale book. |
| 易于使用 | Help: Caps LIMIT waits when a paper sleeve has no last weights. | Help only names current allocations on last sleeve weights. |

Research applied:

- **Fail closed on incomplete coverage.** Pre-trade gates that cannot evaluate a rule (missing position/target state) refuse rather than clear against a stale book. Do not sandbox DSL on GET. Do not invent conformance weights as the next send.
- **Partial books are also incomplete.** If any positive paper sleeve lacks last weights, do not `combine` the others and pretend that is the next send.
- **Keep last_combined fallback when there are no positive sleeves.** The Order size fixture (no sleeves, last combined 0.18) stays valid.
- **Book `check_book` LIMIT still wins.** A live blotter through Name cap is still flatten-now at the window. Unknown is only when book LIMIT is null.
- **Unknown is not flatten.** Banner / CLI / Clock must not say the next rebalance will flatten. Book rail stays off. Caps tiles stay unfailed.

Out: GET flatten; placing; DSL eval on glance; fifth Caps tile; live; sixth screen; Headroom target cash change.

## 2. Engine / API

When `from_supervisor(live=True)` would dry-run send LIMIT (book `live_limit` is null):

1. For each `snapshot.sleeves[id]` with finite allocation `> 0`, require `last_sleeve_weights[id]` to be a non-empty dict.
2. If any such sleeve is missing weights → `live_limit = {"reason": "next_send_unknown", "kind": "unknown"}`. Do **not** call `plan_orders`. Do **not** use last combined. Do **not** combine a subset.
3. Else keep `_next_send_combined` + `_next_send_limit` as today (including last_combined fallback when there are no positive sleeves).

Fixture (do **not** use 0.40 name weight):

- last combined AAPL **0.18**, empty last sleeve weights, current sleeve **asb_y 0.18**, mark **$100**, equity **$10k**, empty qty, spoken Order size **0.10**
- Today: fallback last combined fires `max_order_notional_frac` / `send`
- Desired: `reason == next_send_unknown`, `kind == unknown`
- GET `close_all` unchanged, state not `stopped`

Second fixture (partial): last combined AAPL 0.18, `asb_x` weights AAPL 1.0 at alloc 0.18, `asb_y` alloc 0.01 with **no** weights → unknown, not send.

Book still wins: last_got AAPL 0.225 (15 shares × $100 / $10k under a tighter name cap, or 0.225 vs default 0.20) plus a paper sleeve without weights → `kind == book`, Name cap.

Keep `test_from_supervisor_live_limit_ignores_last_combined` (empty prices, no sleeves → null).
Keep `test_status_live_limit_next_send_order_size` (no sleeves → last combined 0.18 still fires send).
Keep `test_status_live_limit_next_send_follows_current_allocation`.

## 3. Cockpit / CLI

`live_limit.kind === "unknown"`:

- Banner `#live-limit-banner`: `LIMIT: next send waits for last sleeve weights — Caps cannot dry-run` (do not append flatten; do not call `policyLabel` on `next_send_unknown`).
- Clock Next: `weights · ` + the rebalance kind, warn `#f59e0b`. Not `flatten ·` / `flatten send ·`.
- Book rail: do **not** add warn for unknown.
- Caps tiles / muted Order size: `markLimit` stays keyed on policy reasons, so unknown does not fail a tile.
- CLI stderr: the same banner sentence. Do not format `label_for("next_send_unknown")`. Missing `kind` still paints the book LIMIT line.

Keep `LIMIT: live book through Name cap — next rebalance will flatten`.
Keep `LIMIT: next send through Order size — next rebalance will flatten`.

JS must not contain `Gross cap`, `Order size`, or `Orders / rebalance`. `paint-portfolio.js` stays ≤ 400 lines.

## 4. Help / README

Phrases (exact):

- `Caps LIMIT waits when a paper sleeve has no last weights`
- `Clock Next is weights while a paper sleeve has no last weights`

Add to `execution` (after Caps LIMIT current allocations), `halt_flatten` (same), `how_risk` (same). Clock sentence in `halt_flatten` after Clock Next flatten send. README Operator after Caps LIMIT current allocations. Keep `Next rebalance`. Keep four Caps tiles. Keep `Caps LIMIT follows current allocations on last sleeve weights`.

## 5. In / out

**In:** `_next_send_ready`; unknown `live_limit`; banner / Clock / CLI / Book rail; help/README; API + unit + JS + CLI tests.

**Out:** GET flatten; DSL on GET; fifth tile; changing Headroom target cash; live; sixth nav; `POLICY_LABELS` entry.

**Done when:**

1. GET `/api/status` with last combined 0.18, empty last sleeve weights, paper sleeve 0.18, Order size 0.10 → `live_limit.reason == next_send_unknown` and `kind == unknown`; `close_all` unchanged.
2. Partial weights (one paper sleeve missing last weights) → unknown, not send.
3. Existing last-combined 0.18 Order size fixture (no sleeves) still fires send.
4. Empty `last_prices` / last combined 0.40 / no sleeves still has `live_limit` null.
5. Book Name cap still wins over unknown.
6. Help contains both new phrases. Five `#nav` screens. `"Gross cap"` not in assembled JS. No real broker.
