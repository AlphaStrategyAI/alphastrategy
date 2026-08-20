# alphastrategy Caps LIMIT follows the same live book as Tighten

**Date:** 2026-08-20
**Status:** Requirements (improvement cycle on v1)
**Repo:** `AlphaStrategyAI/alphastrategy`
**Parent contract:** [`2026-08-19-alphastrategy-v1-requirements.md`](2026-08-19-alphastrategy-v1-requirements.md) §7–§8
**Related:** [`2026-08-20-alphastrategy-book-enforce-requirements.md`](2026-08-20-alphastrategy-book-enforce-requirements.md), [`2026-08-20-alphastrategy-live-limit-requirements.md`](2026-08-20-alphastrategy-live-limit-requirements.md)
**Technical design:** [`docs/plans/2026-08-20-alphastrategy-caps-limit-book-technical-design.md`](../plans/2026-08-20-alphastrategy-caps-limit-book-technical-design.md)

Paper only. Five screens. Quiet cockpit **tokens unchanged**. No sixth nav tab. No live. No WebSockets. No chart library. Do not revive `static/app.js`. `"Gross cap"` must not appear in assembled JS. `renderBanners` keeps a **single** `const reason`. Do not retry leftover orders. Resume does not catch up. Heartbeat still does **not** flatten. GET `/api/status` and `/api/risk` must not flatten. Keep `Next rebalance`. Keep sticky heartbeat live book, Book flatten-now, PUT `apply_risk`, Book/Beat/Headroom source labels, LIMIT/BOOK stderr. Idle overlays stay unpublished. **Do not feed order sizing from the glance cache.** Each JS part stays ≤ 400 lines. Do **not** overwrite Cash / Headroom cash composition subs.

v1 §7: a live limit breach is the same as account kill at the next legal send. Caps, Clock Next flatten, the LIMIT banner, and CLI LIMIT already warn from `utilization.live_limit`. That field still `check_book`s **`last_got` only**. Flatten-now (`set_policy`, `start_sleeve`, overlay PUT, rebalance live-cap) now prices the **Book glance** (`qty * last_prices / equity`). After a glance with 15 AAPL × $150 and an empty `last_got`, Tighten/Start flatten while Caps stay quiet. That is not 风险可控 or 凭直觉交互.

## 1. Why this increment exists

Goal check against current main (`a0a9ada`):

| Goal slice | v1 / later contract | Current desk |
| --- | --- | --- |
| 风险可控 | Caps LIMIT is the same spoken check flatten-now will fire. | Caps uses persisted `last_got`. Flatten-now uses the live blotter. |
| 凭直觉交互 | LIMIT banner / Clock Next flatten / Caps fail color match Tighten. | Empty `last_got` → no LIMIT; Start paper still flattens. |
| 可靠 | One priced-qty helper. | `_live_book_weights` vs `summarize(last_got=...)`. |
| 易于使用 | Help: Caps LIMIT follows Tighten’s book. | Help still says live book through the cap, not *which* book. |
| 稳定执行 | GET still does not flatten. Heartbeat still does not flatten. | Must keep that. |

Research applied:

- **Pre-breach uses the working blotter.** After book-enforce, the working blotter is Beat/Glance, not a leftover fill mark. Caps LIMIT must price the same qty × last_prices path flatten-now uses.
- **Do not LIMIT on last_combined.** That is the last *target*, not the live book (live-limit contract). Fallback after priced qty: `last_got` if non-empty, else `null`.
- **Do not flatten on GET.** `check_book` in `summarize` stays read-only.

Out: heartbeat flatten; GET flatten; glance-fed orders; Cash/PnL Beat labels; JS paint changes; live; sixth screen; using `last_combined` for LIMIT.

## 2. Engine / API

Extract `_priced_live_weights(equity, raw_positions) -> dict` (qty × `last_prices` / equity when that set is non-empty). `_live_book_weights` stays: priced, else `last_got`, else `last_combined`.

`Supervisor.live_cap_weights(equity, raw_positions) -> dict` under the lock: priced if non-empty, else `last_got`, else `{}`. Never `last_combined`.

`from_supervisor(live=True)` after `live_book()`:

```text
cap_weights = supervisor.live_cap_weights(equity, positions)
summarize(..., last_got=cap_weights or snapshot.last_got)
```

`live=False` (offline CLI) still passes snapshot `last_got` only. Do not hit the broker.

Empty cap book → `live_limit` null. GET / risk inherit. Clock Next flatten, `#live-limit-banner`, Caps fail, CLI LIMIT stderr follow `live_limit` unchanged.

Fixture: 15 AAPL × $150 / $10k = 0.225 vs default 20% name cap. Empty `last_got` must still LIMIT. GET must not `close_all`.

## 3. Help / README

Phrase (exact): `Caps LIMIT follows the same live book as Tighten`

Add it to `execution`, `halt_flatten`, `how_risk`, `task_tighten`, README Operator. Keep `A live book through the spoken cap warns before the next rebalance flattens`. Keep `Next rebalance`. Keep `Tighten and Start paper flatten the same live book as Book`.

## 4. In / out

**In:** priced-qty helper; `live_cap_weights`; utilization uses it when `live=True`; help/README; API + unit tests.

**Out:** heartbeat flatten; GET flatten; JS; Cash/PnL source subs; last_combined LIMIT; live; sixth nav.

**Done when:**

1. GET `/api/status` with empty `last_got`, `last_prices` AAPL $150, 15 shares, default name cap → `utilization.live_limit.reason == max_name_weight` and `close_all` unchanged.
2. Priced live book 0.225 wins over a stale `last_got` of 0.15 (LIMIT fires).
3. `last_combined` 0.40 with empty live qty and empty `last_got` does **not** set `live_limit`.
4. Offline `live=False` still LIMITs from snapshot `last_got` (existing CLI lock).
5. Help contains the new phrase and `Next rebalance`. Five `#nav` screens. `"Gross cap"` not in assembled JS. No real broker.
