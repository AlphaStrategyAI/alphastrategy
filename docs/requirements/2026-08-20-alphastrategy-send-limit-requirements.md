# alphastrategy Caps LIMIT follows a next send through Order size

**Date:** 2026-08-20
**Status:** Requirements (improvement cycle on v1)
**Repo:** `AlphaStrategyAI/alphastrategy`
**Parent contract:** [`2026-08-19-alphastrategy-v1-requirements.md`](2026-08-19-alphastrategy-v1-requirements.md) §7–§8
**Related:** [`2026-08-20-alphastrategy-caps-limit-book-requirements.md`](2026-08-20-alphastrategy-caps-limit-book-requirements.md), [`2026-08-20-alphastrategy-risk-caps-requirements.md`](2026-08-20-alphastrategy-risk-caps-requirements.md)
**Technical design:** [`docs/plans/2026-08-20-alphastrategy-send-limit-technical-design.md`](../plans/2026-08-20-alphastrategy-send-limit-technical-design.md)

Paper only. Five screens. Quiet cockpit **tokens unchanged**. No sixth nav tab. No live. No WebSockets. No chart library. Do not revive `static/app.js`. `"Gross cap"` must not appear in assembled JS. `renderBanners` keeps a **single** `const reason`. Do not retry leftover orders. Resume does not catch up. Heartbeat still does **not** flatten. GET `/api/status`, `/api/portfolio`, and `/api/risk` must not flatten. Keep `Next rebalance`. Keep sticky heartbeat live book, Book flatten-now, PUT `apply_risk`, Caps LIMIT priced book, Book/Beat/Headroom source labels, LIMIT/BOOK/PNL stderr. Keep Caps **four tiles** Gross cap / Name cap / Names / Orders today. Keep Order size on Tighten groups. Idle overlays stay unpublished. **Do not feed `_place_batch` from the glance cache.** Each JS part stays ≤ 400 lines. Do **not** overwrite Cash composition subs.

v1 §7: a limit breach at the next legal send is account flatten. Caps LIMIT / Clock Next flatten / CLI LIMIT already `check_book` the live blotter. `plan_orders` still flattens a **next send** through Order size (`max_order_notional_frac`), orders/rebalance, or the daily budget. After last combined AAPL 0.18, empty qty, mark $100, equity $10k, spoken Order size 10%: the buy is $1,800 against a $1,000 cap. Book caps stay quiet (0.18 < 20% name). Next rebalance still flattens. That is not 风险可控 or 凭直觉交互.

## 1. Why this increment exists

Goal check against current main (`68131cb`):

| Goal slice | v1 / later contract | Current desk |
| --- | --- | --- |
| 风险可控 | LIMIT warns before the send that will flatten. | LIMIT is book-only; Order size is send-only. |
| 凭直觉交互 | Caps fail color / Clock Next flatten / LIMIT banner name the cap. | Order size has no Caps home; banner would have nothing to paint fail on. |
| 可靠 | One dry-run of `plan_orders`. GET does not flatten. | Two code paths, no warning. |
| 易于使用 | Help: Caps LIMIT follows a next send through Order size. | Help only names the live book. |

Research applied:

- **Replay last combined, not a new DSL eval.** Next open/close still evaluates fresh weights. Dry-run `last_combined` vs live qty vs `last_prices` answers “if we traded back to the last target from here, would `plan_orders` flatten?” Missing prices → skip (same as `plan_orders`).
- **Book LIMIT wins.** If `check_book` already set `live_limit`, do not replace it with a send reason.
- **Caps stay four tiles.** Order size is a muted line beside Long only (`#risk-cap-order`), not a fifth tile. Signal-over-noise from the Caps glance contract stays.

Out: heartbeat flatten; GET flatten; placing from the dry-run; feeding `_place_batch` from `live_book()`; fifth Caps tile; using `last_combined` for **book** LIMIT (already forbidden); live; sixth screen.

## 2. Engine / API

`from_supervisor(live=True)` after `summarize`:

If `live_limit` is null, call `_next_send_limit(policy, last_combined, last_prices, positions, equity, orders_today)`:

1. Skip when `equity` missing/`<=0`, or combined empty, or prices empty.
2. Qty map from the live-book positions list (symbol → float qty).
3. `plan_orders(...)` with spoken policy and `orders_already_today`.
4. On `FlattenRequested` → `{"reason": <key>}`. Other exceptions → null (do not fail GET).
5. Do **not** flatten. Do **not** persist. Do **not** place.

`live=False` (offline CLI) does not dry-run.

Existing `test_from_supervisor_live_limit_ignores_last_combined` keeps `last_prices={}` so missing prices skip the send check.

Fixture: last combined AAPL **0.18**, mark **$100**, equity **$10k**, empty qty, spoken Order size **0.10** → notional $1,800 > $1,000 → `max_order_notional_frac`. GET `close_all` unchanged. Do **not** use 0.40 (that is already a name-cap book LIMIT).

## 3. Cockpit

Keep metrics-4 Caps tiles. Add `#risk-cap-order` under `#risk-cap-long`. Paint `policyLabel("max_order_notional_frac")` plus `fmtPct`. Warn when spoken is tighter than account. Fail when `live_limit.reason === "max_order_notional_frac"` (skip while flattened). Tokens `#f59e0b` / `#ef4444`. Do not hardcode `Order size` or `Gross cap` in JS.

LIMIT banner, Clock Next flatten, CLI LIMIT stderr follow `live_limit` unchanged.

## 4. Help / README

Phrase (exact): `Caps LIMIT follows a next send through Order size`

Add it to `halt_flatten`, `how_risk`, `task_tighten`, README Operator. Keep `Caps LIMIT follows the same live book as Tighten`. Keep `Gross cap / Name cap / Names / Orders today`. Keep `Next rebalance`.

## 5. In / out

**In:** `_next_send_limit`; status/risk `live_limit` from dry-run `plan_orders`; `#risk-cap-order`; help/README; API + unit + HTML/JS/CSS tests.

**Out:** GET flatten; placing; fifth Caps tile; book LIMIT from `last_combined`; glance-fed `_place_batch`; live; sixth nav.

**Done when:**

1. GET `/api/status` with empty qty, last combined AAPL 0.18, last price $100, Order size 0.10 → `live_limit.reason == max_order_notional_frac` and `close_all` unchanged.
2. Same book LIMIT (priced 0.225 name) still reports `max_name_weight`, not Order size.
3. `last_combined` 0.40 with **empty** `last_prices` still does **not** set `live_limit`.
4. HTML has `#risk-cap-order` inside Caps, not a fifth metrics tile. JS `markLimit`s it for `max_order_notional_frac`. CSS fail token `#ef4444`.
5. Help contains the new phrase and `Next rebalance`. Five `#nav` screens. `"Gross cap"` not in assembled JS. No real broker.
