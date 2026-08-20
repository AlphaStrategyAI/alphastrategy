# alphastrategy Tighten and Start paper flatten the same live book as Book

**Date:** 2026-08-20
**Status:** Requirements (improvement cycle on v1)
**Repo:** `AlphaStrategyAI/alphastrategy`
**Parent contract:** [`2026-08-19-alphastrategy-v1-requirements.md`](2026-08-19-alphastrategy-v1-requirements.md) §5–§8
**Related:** [`2026-08-20-alphastrategy-named-book-requirements.md`](2026-08-20-alphastrategy-named-book-requirements.md), [`2026-08-20-alphastrategy-sticky-book-requirements.md`](2026-08-20-alphastrategy-sticky-book-requirements.md), [`2026-08-20-alphastrategy-overlay-start-requirements.md`](2026-08-20-alphastrategy-overlay-start-requirements.md), [`2026-08-20-alphastrategy-tighten-now-requirements.md`](2026-08-20-alphastrategy-tighten-now-requirements.md)
**Technical design:** [`docs/plans/2026-08-20-alphastrategy-book-enforce-technical-design.md`](../plans/2026-08-20-alphastrategy-book-enforce-technical-design.md)

Paper only. Five screens. Quiet cockpit **tokens unchanged**. No sixth nav tab. No live. No WebSockets. No chart library. Do not revive `static/app.js`. `"Gross cap"` must not appear in assembled JS. `renderBanners` keeps a **single** `const reason`. Do not retry leftover orders. Resume does not catch up. Heartbeat still does **not** flatten. GET `/api/status` and `/api/risk` must not flatten. Keep `Next rebalance`. Keep sticky heartbeat live book, runtime/envelope digest, Book/Beat/Headroom source labels, LIMIT/BOOK stderr. Idle overlays stay unpublished. **Do not feed order sizing from the glance cache.** Each JS part stays ≤ 400 lines.

v1 §7: a limit breach of spoken policy is the same as account kill if the broker is reachable. Tighten-now and overlay-start already `check_book` after `set_policy` / `start_sleeve` / allocated overlay PUT. Caps, Clock Next flatten, and Book NAV already read `live_book()` (heartbeat sticky or a 1s glance). `_enforce_live_book` still calls `_equity()` + `list_positions()` — a **second** account/positions pair. After a heartbeat, the operator sees Beat 15% AAPL; a broker mutation the desk has not glanced can make Tighten flatten a book Caps never showed, or skip a flatten Caps would have fired. That is not 风险可控, 可靠, or 凭直觉交互.

## 1. Why this increment exists

Goal check against current main (`6cb81bf`):

| Goal slice | v1 / later contract | Current desk |
| --- | --- | --- |
| 风险可控 | Flatten-now is the spoken cap against the **working blotter**. | Caps/LIMIT use `live_book` + `last_got`. Tighten/Start fetch again. |
| 凭直觉交互 | What Book names Beat or Glance is what Tighten/Start flatten. | Book can be sticky; flatten-now is a silent second snapshot. |
| 可靠 | One pair until flatten/place (heartbeat) or 1s (glance). | Extra Alpaca round-trip on every Tighten/Start can disagree. |
| 稳定执行 | Rebalance still sizes orders from **this** event's fetch. | Rebalance also double-fetches inside `_enforce_live_book`. |
| 易于维护 | One unlocked live-book helper. | `_equity` + `_live_book_weights` + `live_book` are three paths. |
| 易于使用 | Help says flatten-now uses Book. | Help names flatten now, not which blotter. |

Research applied:

- **OMS flatten-now uses the blotter the operator is looking at**, not a second private snapshot. Risk overlay and start-paper are explicit human actions; they should flatten the Beat/Glance book already on the desk.
- **Session rebalance is a new working copy.** Order sizing must not read the glance cache (locked). The live-cap check for **this** open/close must use the account/positions **this** rebalance already fetched, even if a sticky heartbeat book would disagree.
- **Do not flatten on the 20s heartbeat.** GET still does not flatten.

Out: heartbeat flatten; GET flatten; feeding `_place_batch` / `plan_orders` from `live_book()`; unifying PUT `/api/risk` onto the digest cache (next cycle); overwriting Cash/PnL composition subs; live; sixth screen; `app.js`.

## 2. Engine

Extract the cache lookup/miss currently inside `live_book()` to an unlocked helper (the Supervisor lock is already an `RLock`; `_enforce_live_book` runs under it). `live_book()` stays the public wrapper.

`_enforce_live_book(account=None, positions=None)`:

1. Broker `None` → return (CLI offline persist; do not halt).
2. State `flattening` or `stopped` → return.
3. If `account` or `positions` is omitted, load them from the unlocked live-book helper (heartbeat sticky **or** glance miss/hit). Do **not** call `_equity()` or `list_positions()` on this path.
4. `_live_book_weights(equity, raw_positions)` prices `qty * last_prices / equity` when possible, else `last_got`, else `last_combined` (same fallback order as today).
5. `check_book` against `_rebalance_policy()`. Broker failure → `_halt("tighten live book: …")`. `FlattenRequested` → `_flatten_account` then `_record_kill`.

`set_policy`, `start_sleeve`, and public `enforce_live_book()` (allocated overlay PUT) omit the pair → desk live book.

`_rebalance` keeps its own `get_account` + `list_positions` for `plan_orders`. After `last_prices = prices`, call `_enforce_live_book(account, raw_positions)` with **that** pair. Do **not** pass the sticky glance. If flattening/stopped after enforce, return before persist-before-send / place.

Flatten/place still `_invalidate_live_book`. Heartbeat still seeds sticky and does not flatten.

Fixture: 15 AAPL × $100 / $10k = 0.15 (under default 20% name cap, over a 10% tighten). 5 shares = 0.05. Do not use 40 shares against the default 20% cap.

## 3. Help / README

Phrase (exact): `Tighten and Start paper flatten the same live book as Book`

Add it to `execution`, `halt_flatten`, `how_risk`, `task_tighten`, `task_start`, README Operator. Keep `A heartbeat live book holds until flatten or place`. Keep `Next rebalance`. Keep `Rebalance flattens a live book that already breaches the spoken cap`.

## 4. In / out

**In:** unlocked live-book helper; operator flatten-now uses it; rebalance live-cap check uses this event's fetch; `_live_book_weights` takes the positions list; help/README; supervisor tests (sticky vs mutated broker, no extra fetch, rebalance fetch wins); lock start-while-halted with a breaching overlay (flatten wins over HALTED).

**Out:** heartbeat flatten; GET flatten; glance-fed orders; PUT risk parser merge; Cash/PnL source subs; JS paint changes; live; sixth nav.

**Done when:**

1. After a heartbeat sticky book of 15 AAPL (0.15), mutating the broker to 5 AAPL and tightening Name cap to 10% **flattens** (sticky 0.15). Mutating the broker to 15 AAPL after a sticky 5 AAPL book and tightening to 10% **does not flatten**.
2. After that heartbeat, `set_policy` that only changes `min_delta_*` does not call `get_account` / `list_positions` again.
3. `start_sleeve` that publishes a 10% overlay uses the sticky 15 AAPL book, not a mutated 5 AAPL broker.
4. Open/close rebalance live-cap flatten uses **this** rebalance's positions, not a sticky heartbeat book that would hide a larger live name.
5. Start paper while halted with a 5% overlay and a 15% live name flattens (`STOPPED`), not stay `HALTED`.
6. Help contains the new phrase and still contains `Next rebalance`. Five `#nav` screens. `"Gross cap"` not in assembled JS. No real broker.
