# alphastrategy LIMIT names a next send through Order size

**Date:** 2026-08-20
**Status:** Requirements (improvement cycle on v1)
**Repo:** `AlphaStrategyAI/alphastrategy`
**Parent contract:** [`2026-08-19-alphastrategy-v1-requirements.md`](2026-08-19-alphastrategy-v1-requirements.md) §7–§8
**Related:** [`2026-08-20-alphastrategy-send-limit-requirements.md`](2026-08-20-alphastrategy-send-limit-requirements.md), [`2026-08-20-alphastrategy-caps-limit-requirements.md`](2026-08-20-alphastrategy-caps-limit-requirements.md)
**Technical design:** [`docs/plans/2026-08-20-alphastrategy-limit-send-technical-design.md`](../plans/2026-08-20-alphastrategy-limit-send-technical-design.md)

Paper only. Five screens. Quiet cockpit **tokens unchanged**. No sixth nav tab. No live. No WebSockets. No chart library. Do not revive `static/app.js`. `"Gross cap"` must not appear in assembled JS. `renderBanners` keeps a **single** `const reason`. Do not retry leftover orders. Resume does not catch up. Heartbeat still does **not** flatten. GET `/api/status`, `/api/portfolio`, and `/api/risk` must not flatten. Keep `Next rebalance`. Keep sticky heartbeat live book, Book flatten-now, PUT `apply_risk`, Caps LIMIT priced book, next-send Order size dry-run, Book/Beat/Headroom source labels, LIMIT/BOOK/PNL stderr. Keep Caps **four tiles**. Keep `#risk-cap-order`. Idle overlays stay unpublished. **Do not feed `_place_batch` from the glance cache.** Each JS part stays ≤ 400 lines. Do **not** overwrite Cash composition subs. Do **not** hardcode `Order size` in JS.

v1 §7: a limit breach at the next legal send is account flatten. After send-limit, `live_limit.reason` can be a **book** cap (`check_book`) or a **next send** cap (`plan_orders` dry-run of last combined). The LIMIT banner and CLI still always say `LIMIT: live book through {label}`. Empty qty, last combined AAPL 0.18, Order size 10% is not a live-book breach. Saying “live book through Order size” is not 可靠 or 凭直觉交互.

## 1. Why this increment exists

Goal check against current main (`674a888`):

| Goal slice | v1 / later contract | Current desk |
| --- | --- | --- |
| 可靠 | LIMIT words match the check that fired. | Send LIMIT reuses book copy. |
| 凭直觉交互 | Operator can tell blotter vs next ticket. | Same banner for both. |
| 风险可控 | Warn before the send that will flatten, named honestly. | Caps fail-color is right; the sentence is wrong. |
| 易于使用 | Help: LIMIT names a next send through Order size. | Help only names the dry-run, not the spoken line. |

Research applied:

- **Tag the source, do not infer from the key alone.** `max_orders_per_day` can be book-adjacent (Orders today tile) and also a `plan_orders` send flatten. `kind: "book" | "send"` is the honest split. Missing `kind` on a payload still paints as book (old CLI fixtures).
- **Do not re-evaluate DSL on GET.** Keep last-combined replay. Book LIMIT still wins.
- **Do not flatten on GET.** Copy only.

Out: heartbeat flatten; GET flatten; placing from the dry-run; fifth Caps tile; changing the book LIMIT sentence; live; sixth screen.

## 2. Engine / API

`summarize` `check_book` LIMIT:

```python
live_limit = {"reason": str(exc.reason or "limit"), "kind": "book"}
```

`_next_send_limit` on `FlattenRequested`:

```python
return {"reason": str(exc.reason or "limit"), "kind": "send"}
```

Keep `reason` as today. Existing tests that only read `reason` stay valid. Book LIMIT still wins (no send overlay).

## 3. Cockpit / CLI

`renderLiveLimitBanner`: if `limit.kind === "send"`, paint `LIMIT: next send through ` + `policyLabel(reason)` + ` — next rebalance will flatten`. Else keep `LIMIT: live book through …`. Do not put `Order size` or `Gross cap` in JS.

CLI `_status_limit_line`: same two sentences via `kind`. Default missing/`book` to the live-book sentence so `test_status_prints_pnl_on_stderr` stays:

`LIMIT: live book through Name cap — next rebalance will flatten`

Send payload:

`LIMIT: next send through Order size — next rebalance will flatten`

Clock Next `flatten ·` stays for both kinds. Caps `markLimit` still keys on `reason`.

## 4. Help / README

Phrase (exact): `LIMIT names a next send through Order size`

Add it to `halt_flatten`, `how_risk`, `cli`, README Operator. Keep `Caps LIMIT follows a next send through Order size`. Keep `A live book through the spoken cap warns before the next rebalance flattens`. Keep `status names LIMIT while the live book is through the spoken cap`. Keep `Next rebalance`.

## 5. In / out

**In:** `live_limit.kind`; banner/CLI send sentence; help/README; API + unit + CLI + JS tests.

**Out:** GET flatten; placing; inferring kind only from the reason key; rewriting the book LIMIT sentence; fifth Caps tile; live; sixth nav.

**Done when:**

1. GET `/api/status` Order-size fixture → `live_limit.kind == "send"` and `reason == max_order_notional_frac`; `close_all` unchanged.
2. Priced name-cap book LIMIT → `kind == "book"`.
3. Banner/JS contains `next send through`. Book CLI line unchanged.
4. CLI send LIMIT stderr is `LIMIT: next send through Order size — next rebalance will flatten`.
5. Help contains the new phrase. Five `#nav` screens. `"Gross cap"` not in assembled JS. No real broker.
