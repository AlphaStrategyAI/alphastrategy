# alphastrategy live spoken-cap breach warns before flatten

**Date:** 2026-08-20
**Status:** Requirements (improvement cycle on v1)
**Repo:** `AlphaStrategyAI/alphastrategy`
**Parent contract:** [`2026-08-19-alphastrategy-v1-requirements.md`](2026-08-19-alphastrategy-v1-requirements.md) §7–§8
**Related:** [`2026-08-20-alphastrategy-heartbeat-prices-requirements.md`](2026-08-20-alphastrategy-heartbeat-prices-requirements.md), [`2026-08-20-alphastrategy-fill-drift-requirements.md`](2026-08-20-alphastrategy-fill-drift-requirements.md), [`2026-08-20-alphastrategy-spoken-caps-requirements.md`](2026-08-20-alphastrategy-spoken-caps-requirements.md)
**Technical design:** [`docs/plans/2026-08-20-alphastrategy-live-limit-technical-design.md`](../plans/2026-08-20-alphastrategy-live-limit-technical-design.md)

Paper only. Five screens. Quiet cockpit **tokens unchanged**. No sixth nav tab. No live. No WebSockets. No chart library. Do not revive `static/app.js`. `"Gross cap"` must not appear in assembled JS. `renderBanners` keeps a **single** `const reason`. Do not retry leftover orders. Resume does not catch up. Heartbeat still does **not** flatten. Keep `Next rebalance`. Keep heartbeat marks. Keep Book Drift on last fill. Keep overlay-on-start flatten. Keep spoken Caps. Idle overlays stay unpublished.

v1 §7: a live limit breach is account flatten at the next legal send. Heartbeat-prices marks `last_got` between windows and close flattens. v1 §8: halt/deviation banners **cannot be visually quiet**. After a name rally (15 AAPL × $150 / $10k = 0.225 vs spoken Name 20%), Got and At cap can move, Book Drift stays quiet (fill matched), and there is **no** banner that the next rebalance will flatten. The desk looks too calm for 风险可控.

Separately, overlay/account `max_name_weight: 0` is a legal tighten (finite, non-negative). Glance paint uses `Number(x) || 0.2` and `Number(cap) > 0 ? cap : 0.2`, so a zero Name cap **paints as 20%**. That is not 凭直觉.

## 1. Why this increment exists

Goal check against current main (`e0a9c7a`):

| Goal slice | v1 / later contract | Current desk |
| --- | --- | --- |
| 风险可控 | Live marks already through spoken cap → flatten at next legal rebalance. Operator must see it now. | No desk banner. GET status does not name the live limit. Heartbeat still correctly does not flatten. |
| 凭直觉交互 | Banners that cannot go quiet. Caps 0 means 0. | Deviation is fill-only (correct). Flatten banner waits for STOPPED. Zero Name cap looks like 20%. |
| 易于使用 | Help: live book through the spoken cap warns before the next rebalance flattens. | Help says rebalance flattens; not that glance warns first. |
| 易于维护 | Same `check_book` as flatten, on `last_got`, read-only. | Paint duplicates cap math with `\|\|` fallbacks. |

Research applied:

- **Pre-breach vs post-kill.** Risk desks show a working-limit warning while the book is still open, then a kill/flat state after the flatten. Warn token `#f59e0b` for pending; fail `#ef4444` stays on the flatten banner.
- **Zero is a cap.** EMS remaining-limit widgets treat 0 as “no headroom,” not “missing.” `Number(x) \|\| fallback` is a JS footgun.
- **Do not flatten on poll.** GET `/api/status` / paint must not call `_enforce_live_book`. Heartbeat still marks only.

Out of this increment: heartbeat flatten; Run Start POST `flattened` copy; 409; live; sixth screen; `app.js`; changing Book Drift back to marks.

## 2. Engine / API

`summarize` / `from_supervisor` add:

```text
"live_limit": {"reason": "<check_book reason>"} | null
```

Compute by `check_book(last_got, 0, spoken policy)` (same FlattenRequested reasons: `long_only`, `max_gross`, `max_name_weight`, `max_names`). Empty `last_got` → `null`. Do **not** flatten. Do **not** use `last_combined` or `last_fill_got` (those are target / fill).

`GET /api/status` and `GET /api/risk` already return `utilization`; they inherit `live_limit`. GET must not `close_all`.

## 3. Paint

Desk banners (outside Portfolio, same family as halt/flatten): `#live-limit-banner` class `banner halt`. Copy:

`LIMIT: live book through <policyLabel(reason)> — next rebalance will flatten`

Hide when flattened/flattening/stopped (FLAT banner owns that state) or when `live_limit` is null.

Spoken Name / Gross glance caps: `Number.isFinite` — **0 is a real cap**. `nameCapBar`, Positions At cap, Gross rail, Headroom used/cap fail when used **>** cap (matches `check_book`). `wantedGotBar` scale may still use `max(cap, weights, 0.01)` so a 0 cap remains drawable.

Do not put `"Gross cap"` in JS. Each `js/` part ≤ 400 lines. One `const reason` in `renderBanners`.

## 4. Help / README

`REQUIRED_PHRASES`: `A live book through the spoken cap warns before the next rebalance flattens`.

Keep heartbeat / fill-drift / Caps / overlay sentences. `"Gross cap"` stays in help labels, not JS.

## 5. In / out

**In:** `utilization.live_limit`; live-limit banner; finite 0 caps on glance; help/README; tests.

**Out:** heartbeat flatten; GET flatten; 409; live; `app.js`.

**Done when:**

1. `last_got` AAPL 0.225 vs default spoken Name 0.20 → `utilization.live_limit.reason == max_name_weight`. GET status does not flatten.
2. `last_got` AAPL 0.15 → `live_limit` is null.
3. Spoken Name cap 0 with nonzero `last_got` → `live_limit.reason == max_name_weight`. Overlay 0 is accepted.
4. HTML has `#live-limit-banner` in desk banners. JS paints LIMIT copy from `live_limit` and hides it while flattened. Name/Gross paint uses `Number.isFinite`.
5. Help contains the new phrase. Five `#nav` screens. `"Gross cap"` not in `js_text`. No real broker.
