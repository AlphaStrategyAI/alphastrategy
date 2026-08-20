# alphastrategy heartbeat live book holds until flatten or place

**Date:** 2026-08-20
**Status:** Requirements (improvement cycle on v1)
**Repo:** `AlphaStrategyAI/alphastrategy`
**Parent contract:** [`2026-08-19-alphastrategy-v1-requirements.md`](2026-08-19-alphastrategy-v1-requirements.md) §5–§8
**Related:** [`2026-08-20-alphastrategy-beat-book-requirements.md`](2026-08-20-alphastrategy-beat-book-requirements.md), [`2026-08-20-alphastrategy-live-glance-requirements.md`](2026-08-20-alphastrategy-live-glance-requirements.md)
**Technical design:** [`docs/plans/2026-08-20-alphastrategy-sticky-book-technical-design.md`](../plans/2026-08-20-alphastrategy-sticky-book-technical-design.md)

Paper only. Five screens. Quiet cockpit **tokens unchanged**. No sixth nav tab. No live. No WebSockets. No chart library. Do not revive `static/app.js`. `"Gross cap"` must not appear in assembled JS. `renderBanners` keeps a **single** `const reason`. Do not retry leftover orders. Resume does not catch up. Heartbeat still does **not** flatten. Keep `Next rebalance`. Keep live-limit banner, Clock `flatten ·`, Caps fail, spoken-policy digest cache, envelope digest cache, heartbeat seed + restamp. Idle overlays stay unpublished. GET `/api/status` and `/api/risk` must not flatten. Do not feed order sizing from the glance cache.

v1 §6: heartbeat every **20s** is health and reconciliation. v1 §8: the cockpit `refresh()` is **5s**. Live-glance coalesces one `Promise.all` with a **1s** TTL. Beat-book seeds that cache from the beat. After the beat, the next cockpit poll is 5s later, so the 1s TTL has already expired and GET fetches a **second** account/positions pair. Book NAV and heartbeat `last_got` split again. That is not 可靠 or 凭直觉交互.

## 1. Why this increment exists

Goal check against current main (`90cdfd7`):

| Goal slice | v1 / later contract | Current desk |
| --- | --- | --- |
| 可靠 | The beat’s book **is** the glance book until the next beat, flatten, or place. | Seed expires after 1s. Cockpit polls every 5s. Almost every poll refetches. |
| 稳定执行 | Poll must not hammer Alpaca between beats. Orders still see a fresh broker book. | Five screens × 5s × extra list_positions between 20s beats. |
| 凭直觉交互 | Book equity is the equity that produced `last_got` for the whole beat. | Marks from the beat; NAV from a GET 5s later. |
| 易于维护 | Heartbeat seed is sticky; glance-only fetch still has a short TTL. | One TTL for both sources. |
| 风险可控 | Kill then refresh is not the pre-kill book. Heartbeat still does not flatten. | Invalidate on flatten/place must still drop a sticky seed. |

Research applied:

- **Working blotter until the next snapshot.** EMS desks snapshot positions on the beat and let the UI read that blotter until the next beat or a trade. They do not list positions again 5s later “to be fresh” while marks stay on the previous beat.
- **Two lifetimes.** Glance-only fetch keeps the 1s TTL so `Promise.all` coalesces and a desk with no beat yet still refreshes. Heartbeat-seeded fetch ignores wall-clock TTL until `_invalidate_live_book()`.
- **Do not extend TTL to 20s globally.** That would hide a post-kill miss if invalidate were forgotten, and would stall a GET-only path for a full beat.
- **Do not slow the cockpit poll to 20s.** CLI `status` and overlapping GETs still need the same book as `last_got`.
- **Do not flatten on the beat.** Unchanged. Do not use `live_book()` inside `_enforce_live_book` / `_equity()`.

Out: heartbeat flatten; GET flatten; JS paint; merging HTTP routes; live; `app.js`; changing `LIVE_BOOK_TTL_SEC` for glance-only fetches.

## 2. Engine

`_live_book_cache` is `(monotonic, account, positions, sticky)`.

`live_book()` under `RLock`:

1. If cache is set and (`sticky` or age < `LIVE_BOOK_TTL_SEC`): return the pair.
2. Else `get_account` then `list_positions`, store with `sticky=False`.

Heartbeat `finally` stores the beat pair with `sticky=True`. `_touch_live_book_cache()` keeps the sticky bit. `_invalidate_live_book()` clears the cache (flatten / place).

GET status/risk still must not `close_all`. Order paths still hit the broker.

## 3. Help / README

- `A heartbeat live book holds until flatten or place`

Keep “Heartbeat seeds the live book glance”. Keep live-glance sentences. `"Gross cap"` in help labels only.

## 4. In / out

**In:** sticky bit on heartbeat seed; glance-only 1s TTL unchanged; help/README; tests that a beat holds past TTL and a glance fetch expires.

**Out:** heartbeat flatten; GET flatten; JS; live; `app.js`; 20s global TTL.

**Done when:**

1. After an idle heartbeat, advancing monotonic past `LIVE_BOOK_TTL_SEC` does not increment `get_account` / `list_positions` on `live_book()` or GET status/portfolio.
2. A glance-only `live_book()` (no heartbeat seed) still refetches after TTL.
3. Account kill then GET portfolio is not the pre-kill positions.
4. Heartbeat still writes `last_got` on a rally and does not flatten.
5. Help contains the new phrase. Five `#nav` screens. `"Gross cap"` not in `js_text`. No real broker.
