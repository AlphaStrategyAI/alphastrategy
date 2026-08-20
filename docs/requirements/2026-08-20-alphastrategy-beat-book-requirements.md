# alphastrategy heartbeat seeds the live book glance

**Date:** 2026-08-20
**Status:** Requirements (improvement cycle on v1)
**Repo:** `AlphaStrategyAI/alphastrategy`
**Parent contract:** [`2026-08-19-alphastrategy-v1-requirements.md`](2026-08-19-alphastrategy-v1-requirements.md) §5–§8
**Related:** [`2026-08-20-alphastrategy-live-glance-requirements.md`](2026-08-20-alphastrategy-live-glance-requirements.md), [`2026-08-20-alphastrategy-heartbeat-prices-requirements.md`](2026-08-20-alphastrategy-heartbeat-prices-requirements.md), [`2026-08-20-alphastrategy-spoken-cache-requirements.md`](2026-08-20-alphastrategy-spoken-cache-requirements.md)
**Technical design:** [`docs/plans/2026-08-20-alphastrategy-beat-book-technical-design.md`](../plans/2026-08-20-alphastrategy-beat-book-technical-design.md)

Paper only. Five screens. Quiet cockpit **tokens unchanged**. No sixth nav tab. No live. No WebSockets. No chart library. Do not revive `static/app.js`. `"Gross cap"` must not appear in assembled JS. `renderBanners` keeps a **single** `const reason`. Do not retry leftover orders. Resume does not catch up. Heartbeat still does **not** flatten. Keep `Next rebalance`. Keep live-limit banner, Clock `flatten ·`, Caps fail, spoken-policy cache, one live book per HTTP glance. Idle overlays stay unpublished. GET `/api/status` and `/api/risk` must not flatten. Do not feed order sizing from the glance cache.

v1 §6: heartbeat is health and reconciliation. Live-glance already coalesces GET status/portfolio/risk. The beat still does its own `list_positions` + `get_account` (`_equity`) and **throws that book away**, then the next cockpit poll fetches a second book. Headroom cash and `last_got` marks can be one heartbeat apart. Sleeve `risk-envelope.yaml` is still parsed on every `_effective_sleeve_policy` even when the file stamp is unchanged. That is not 可靠.

## 1. Why this increment exists

Goal check against current main (`dfb0c11`):

| Goal slice | v1 / later contract | Current desk |
| --- | --- | --- |
| 可靠 | The beat’s live account/positions **are** the glance book until TTL/invalidate. | Heartbeat reads the book, updates `last_got`, does not seed `live_book()`. Glance immediately refetches. |
| 稳定执行 | One Alpaca positions+account pair per beat, reused by GET. | Beat + glance = two pairs. Empty-universe beat skips `get_account` today, so cash on the next glance is a third code path. |
| 易于维护 | Envelope yaml stamp-cached like `runtime.yaml`. | `_bundle_envelope` `load_risk_envelope` every sleeve, every miss of the spoken merge. |
| 凭直觉交互 | After a beat, Book equity is the equity that produced `last_got`. | Marks from beat equity; NAV from a later `get_account`. |
| 风险可控 | Heartbeat still does not flatten. Envelope file change still tightens spoken. | Cache must miss when envelope mtime/size changes. |

Research applied:

- **Reconciliation writes the working blotter.** EMS heartbeats snapshot positions once and let the UI read that snapshot until the next beat or a trade. They do not list positions again 50ms later for NAV.
- **Stamp cache immutable research caps.** `risk-envelope.yaml` is import-time. Parse once per stamp. A byte change (tests, operator replace) must miss.
- **Do not flatten on the beat.** Unchanged. Do not use `live_book()` inside `_enforce_live_book` / `_equity()` for orders.

Out: heartbeat flatten; GET flatten; JS paint; merging HTTP routes; live; `app.js`.

## 2. Engine

`_heartbeat_health_check`:

1. `list_positions` then `get_account` in one try. Failure → existing `HaltRequested("heartbeat live book: …")`. Do not flatten.
2. Seed `_live_book_cache = (monotonic, account, raw_positions)` (same pair `live_book()` returns).
3. Build the price universe from the mapped positions. Empty universe **returns after the seed** (no bars). Non-empty: `_fetch_prices`, merge `last_prices`, recompute `last_got` from **this** account equity × live qty × fetched prices. Do not call `_snapshot_got`. Do not call `_equity()` again.

`live_book()` unchanged: TTL hit returns the seeded pair.

`_bundle_envelope`: cache `dict[bundle_id, (stamp, doc)]` via `_file_stamp`. Missing file → `{}` and stamp `(0, 0)`. File change misses. `sleeve_policies` / `_rebalance_policy` keep calling it; they must not re-parse unchanged bytes.

GET status/risk still must not `close_all`. Flatten/place still `_invalidate_live_book()`.

## 3. Help / README

- `Heartbeat seeds the live book glance`
- `Sleeve envelopes load once until the file changes`

Keep “Heartbeat refreshes last prices and does not flatten”. Keep live-glance sentences. `"Gross cap"` in help labels only.

## 4. In / out

**In:** heartbeat seeds `live_book`; empty universe still seeds; envelope stamp cache; help/README; tests.

**Out:** heartbeat flatten; GET flatten; JS; live; `app.js`.

**Done when:**

1. After an idle heartbeat, `live_book()` / GET portfolio+status do not increment `get_account` / `list_positions` beyond the beat.
2. Heartbeat still writes `last_got` on a rally and does not flatten.
3. Two `sleeve_policies` calls with unchanged envelope files do not call `load_risk_envelope` again.
4. Rewriting `risk-envelope.yaml` is visible on the next `spoken_policy()`.
5. Help contains both new phrases. Five `#nav` screens. `"Gross cap"` not in `js_text`. No real broker.
