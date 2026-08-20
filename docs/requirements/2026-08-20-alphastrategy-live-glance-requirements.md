# alphastrategy one live book per desk glance

**Date:** 2026-08-20
**Status:** Requirements (improvement cycle on v1)
**Repo:** `AlphaStrategyAI/alphastrategy`
**Parent contract:** [`2026-08-19-alphastrategy-v1-requirements.md`](2026-08-19-alphastrategy-v1-requirements.md) §5–§8
**Related:** [`2026-08-20-alphastrategy-spoken-cache-requirements.md`](2026-08-20-alphastrategy-spoken-cache-requirements.md), [`2026-08-20-alphastrategy-heartbeat-prices-requirements.md`](2026-08-20-alphastrategy-heartbeat-prices-requirements.md)
**Technical design:** [`docs/plans/2026-08-20-alphastrategy-live-glance-technical-design.md`](../plans/2026-08-20-alphastrategy-live-glance-technical-design.md)

Paper only. Five screens. Quiet cockpit **tokens unchanged**. No sixth nav tab. No live. No WebSockets. No chart library. Do not revive `static/app.js`. `"Gross cap"` must not appear in assembled JS. `renderBanners` keeps a **single** `const reason`. Do not retry leftover orders. Resume does not catch up. Heartbeat still does **not** flatten. Keep `Next rebalance`. Keep live-limit banner, Clock `flatten ·`, Caps fail on `live_limit`. Keep spoken-policy stamp cache. Idle overlays stay unpublished. GET `/api/status` and `/api/risk` must not flatten.

v1 §5: Supervisor is the sole holder of Alpaca keys and the sole order placer. v1 §8: the cockpit polls as one desk. `refresh()` fires **Promise.all** of GET status, portfolio, bundles, activity, and risk every 5s. Today that is three independent `get_account` + `list_positions` (status utilization `live=True`, portfolio, risk utilization `live=True`) plus GET risk calling `_load_runtime` **once per imported sleeve**. Book equity, Headroom cash, and Caps spoken can disagree inside one glance; Alpaca paper is hammered; a torn `runtime.yaml` mid-poll can disagree overlay cards vs spoken. That is not 可靠 or 凭直觉交互.

## 1. Why this increment exists

Goal check against current main (`6e74290`):

| Goal slice | v1 / later contract | Current desk |
| --- | --- | --- |
| 可靠 | One live book per glance. Overlay cards share one runtime parse. | Status + portfolio + risk each hit Alpaca. Risk yaml-parses per imported id. |
| 稳定执行 | Poll must not starve or race flatten. Flatten/orders see a fresh broker book. | Concurrent GET can read a book that flatten just emptied, or the reverse, without a shared snapshot. |
| 凭直觉交互 | Book equity and Headroom cash are the same glance. | Two `get_account` calls can split cash vs equity. |
| 易于维护 | Supervisor owns live-book and runtime-doc caches. Handlers do not re-merge overlays by hand. | Duplicate `_effective_sleeve_policy` in `handlers.py`. |
| 风险可控 | GET still does not flatten. Kill then refresh must not paint the pre-kill book. | Cache must invalidate on flatten and place. |

Research applied:

- **OMS glance coalescing.** Desk UIs snapshot the working book once per paint cycle, then fan the same positions into blotter, risk, and NAV. They do not issue three `list_positions` for one frame.
- **Short TTL + explicit invalidate.** 1s is enough for `Promise.all` (threaded control plane). Flatten, place, and live-book enforce drop the cache so kill → refresh is not stale.
- **Do not feed order sizing from the glance cache.** `_equity()` / `_live_book_weights` / rebalance keep hitting the broker. Only GET utilization and GET portfolio share `live_book()`.
- **Runtime dict stamp cache.** Spoken policy already caches the merge. Overlay cards still need the yaml. Cache `_read_runtime()` by mtime+size so spoken + `sleeve_policies` share one parse.

Out: heartbeat flatten; GET flatten; changing Caps/Clock paint; live; `app.js`; combining the five HTTP routes into one.

## 2. Engine / API

`Supervisor.LIVE_BOOK_TTL_SEC = 1.0`.

`Supervisor.live_book() -> (account, positions)` under the existing `RLock`: on hit (age < TTL) return the cached pair; on miss call `get_account` then `list_positions`, store, return. If `_broker is None`, raise (GET portfolio still fails closed).

`_invalidate_live_book()` at the start of `_flatten_account` and after `_place_batch` (any placed or error return). Do **not** use `live_book()` inside `_enforce_live_book` / rebalance.

`from_supervisor(..., live=True)` uses `supervisor.live_book()` instead of `broker.get_account` / `list_positions`. Still swallow broker errors (cash/names become None). Still does not flatten.

`handle_get_portfolio` uses `supervisor.live_book()` for account + positions.

`Supervisor.sleeve_policies(bundle_ids) -> dict[str, AccountPolicy]`: one `_read_runtime()`, then `_effective_sleeve_policy(id, runtime)` per id.

`handle_get_risk` builds `sleeves` from `supervisor.sleeve_policies(imported)`. PUT risk still uses `_load_runtime` / `_save_runtime` / `_bundle_envelope`.

`_read_runtime` caches the parsed dict by `_file_stamp(runtime.yaml)` (mtime_ns + size). Missing file → empty dict, stamp `(0, 0)`.

GET status/risk still must not `close_all`.

## 3. Help / README

- `Status, Portfolio, and Risk share one live book glance`
- `Risk overlays load runtime once per glance`

Keep spoken-policy reuse. Keep live-limit / Caps sentences. `"Gross cap"` in help labels only.

## 4. In / out

**In:** `live_book` TTL + invalidate; portfolio + live utilization share it; `_read_runtime` stamp cache; `sleeve_policies`; GET risk uses it; help/README; tests.

**Out:** heartbeat flatten; GET flatten; merging HTTP routes; JS paint; live; `app.js`.

**Done when:**

1. Sequential GET status + portfolio + risk in one test increment `get_account` / `list_positions` once each.
2. Account kill then GET portfolio is not the pre-kill positions (cache invalidated).
3. `sleeve_policies` for two ids calls `_read_runtime` once; GET risk with three imported dirs parses `runtime.yaml` at most twice (spoken miss + policies, or once if yaml cache shares).
4. GET status with `last_got` through Name cap still does not flatten.
5. Help contains both new phrases. Five `#nav` screens. `"Gross cap"` not in `js_text`. No real broker.
