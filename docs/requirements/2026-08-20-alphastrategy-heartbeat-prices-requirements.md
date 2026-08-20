# alphastrategy heartbeat marks; rebalance flattens a live breach

**Date:** 2026-08-20
**Status:** Requirements (improvement cycle on v1)
**Repo:** `AlphaStrategyAI/alphastrategy`
**Parent contract:** [`2026-08-19-alphastrategy-v1-requirements.md`](2026-08-19-alphastrategy-v1-requirements.md) §6–§8
**Related:** [`2026-08-20-alphastrategy-spoken-caps-requirements.md`](2026-08-20-alphastrategy-spoken-caps-requirements.md), [`2026-08-20-alphastrategy-tighten-now-requirements.md`](2026-08-20-alphastrategy-tighten-now-requirements.md), [`2026-08-20-alphastrategy-overlay-start-requirements.md`](2026-08-20-alphastrategy-overlay-start-requirements.md)
**Technical design:** [`docs/plans/2026-08-20-alphastrategy-heartbeat-prices-technical-design.md`](../plans/2026-08-20-alphastrategy-heartbeat-prices-technical-design.md)

Paper only. Five screens. Quiet cockpit **tokens unchanged**. No sixth nav tab. No live. No WebSockets. No chart library. Do not revive `static/app.js`. `"Gross cap"` must not appear in assembled JS. `renderBanners` keeps a **single** `const reason`. Do not retry leftover orders. Resume does not catch up. Heartbeat still does **not** flatten. Keep `Next rebalance`. Keep overlay-on-start flatten. Keep spoken Caps. Keep idle overlays unpublished.

v1 §6: heartbeat every 20s is **health, reconciliation, audit**. It does not rebalance and does not place orders. Today the beat fetches sleeve-universe bars for staleness and **discards** the price map. `last_prices` / `last_got` are written only inside `_rebalance`. Between legal windows, Portfolio notionals and Got weights stay on the last rebalance print. A name can rally through the spoken Name cap while the desk still paints 15%.

v1 §7: a limit breach is account flatten if the broker is reachable. Today `_rebalance` `check_book`s the **combined wanted** book, then places toward that target. After a rally, wanted can still sit inside the cap while live qty × mark is over it. The close batch may even **trade**. Tighten / overlay / start already call `_enforce_live_book`. The legal order window does not. That is not 风险可控.

## 1. Why this increment exists

Goal check against current main (`975f63f`):

| Goal slice | v1 / later contract | Current desk |
| --- | --- | --- |
| 风险可控 | §7 flatten on a live limit breach. Spoken policy is the flatten book. | Heartbeat never marks. Rebalance `check_book`s wanted only. A 15-share AAPL book at $150 / $10k (0.225) stays live through close if wanted is still 15%. |
| 稳定执行 | §6 heartbeat reconciliation. Marks between the two RTH windows. | `_heartbeat_health_check` throws away `get_bars`. Glance uses stale `last_prices`. |
| 凭直觉交互 | Positions Got / Cap / Gross follow the same marks the kill-switch will use. | After a rally, Caps still looks honest (spoken 20%) while Got is a stale 15% until the next rebalance print. |
| 易于使用 | Help must say the beat marks and does not flatten; the legal window flattens a live breach. | Help says heartbeat does not place orders. It does not say marks vs flatten. |

Research applied:

- **Mark-to-market on the heartbeat, flatten on the order window.** Prime brokers and EMS blotters refresh last on a timer. They do not flatten every quote. Risk kill still fires at the next legal send if the live book is already through the working cap. That matches v1 §6 (heartbeat does not place) and §7 (limit breach = account kill) without turning a 20s beat into a kill loop.
- **Do not audit execution_deviation every beat.** Deviation is a rebalance completeness signal (wanted vs fill). Recomputing it on every mark vs last combined would flood JSONL whenever prices move. Reconciliation writes `last_prices` / `last_got` only.
- **Pre-trade: do not send a target batch while live already breaches spoken.** Selling down toward a still-legal wanted book would “cure” the name, but v1 §7 does not make an exception for “the next target is inside.” `_enforce_live_book` after fresh marks, before persist-before-send.

Out of this increment: flatten on heartbeat; 409 start; changing Tighten; idle overlays in spoken; JS `"Gross cap"`; `Number(x) \|\| fallback` zero-cap paint; Run Start ignoring POST `flattened`; crash-recovery changes; spending a session event because a heartbeat ran.

## 2. Engine

### 2.1 Heartbeat reconciliation (no flatten)

`_heartbeat_health_check` after a successful bar fetch:

1. Symbol universe = allocated sleeve weight keys ∪ live position symbols ∪ `last_combined` keys. Empty universe still returns without a fetch (same as today).
2. `_fetch_prices` for that universe (staleness / missing / broker failure still **health-halt**, no flatten).
3. Merge fetched closes into `snapshot.last_prices` (update fetched keys; keep others).
4. Recompute `snapshot.last_got` from live qty × fetched price / equity for priced live names. Do **not** call `_snapshot_got` (no `execution_deviation` audit on this path).
5. Do **not** call `_enforce_live_book`. Do **not** place. Do **not** consume a session event.

Idle `tick` already `_persist()`s after health check when `event is None`. Heartbeat `list_positions` / `get_account` failure is a health halt, not flatten.

### 2.2 Rebalance live-book flatten

`_rebalance` keeps `check_book(combined wanted, spoken policy)` first (illegal wanted still flattens without trading).

After a successful price fetch and `last_prices = prices`, call `_enforce_live_book()` **before** `plan_orders` and **before** persist-before-send.

If state is `flattening` or `stopped` after that call, return. Do not place. Do not spend the session event. Do not write a rebalance audit for a batch that did not start.

Heartbeat still does not flatten. Broker failure inside `_enforce_live_book` still health-halts (existing).

Example (default 20% name cap, $10k equity): 15 AAPL. Mark $100 → weight 0.15 (legal). Mark $150 → weight 0.225 (breach). A mid-session heartbeat writes 150 / 0.225 and stays running. Close (or the next legal window) flattens `max_name_weight`, `STOPPED`.

## 3. Help / README

`how_execution` / halt-flatten / how_risk / README heartbeat bullets:

- Heartbeat refreshes last prices and does not flatten.
- Rebalance flattens a live book that already breaches the spoken cap.

`REQUIRED_PHRASES` adds both sentences. Keep `Next rebalance`. Keep overlay / tighten / Caps phrases. `"Gross cap"` stays in help (Risk labels), not in assembled JS.

## 4. In / out

**In:** heartbeat mark universe; persist `last_prices` / `last_got` on the beat; rebalance `_enforce_live_book` after marks; help/README; tests.

**Out:** heartbeat flatten; spending open/close because a beat ran; `execution_deviation` on the beat; 409; live; sixth screen; `app.js`; crash-recovery rewrite.

**Done when:**

1. After an open fill of 15 AAPL at $100, a mid-session heartbeat with AAPL $150 writes `last_prices["AAPL"] == 150` and `last_got["AAPL"] == 0.225`, does not `close_all`, leaves state running, does not add `execution_deviation`, leaves `last_rebalance_event` as the open stamp.
2. Same book after stop (allocation 0, position still held): heartbeat still refreshes AAPL’s last price (universe includes live names / last combined, not only allocated sleeves).
3. Close window after that rally: flatten now, `last_kill.reason == max_name_weight`, no additional target orders, session close event not spent.
4. Heartbeat with live name 0.225 still does **not** flatten (lock).
5. Help contains both new phrases. Five `#nav` screens. `"Gross cap"` not in `js_text`. No real broker.
