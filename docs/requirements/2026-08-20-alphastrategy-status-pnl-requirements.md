# alphastrategy status names Day PnL

**Date:** 2026-08-20
**Status:** Requirements (improvement cycle on v1)
**Repo:** `AlphaStrategyAI/alphastrategy`
**Parent contract:** [`2026-08-19-alphastrategy-v1-requirements.md`](2026-08-19-alphastrategy-v1-requirements.md) §8–§9
**Related:** [`2026-08-20-alphastrategy-day-pnl-requirements.md`](2026-08-20-alphastrategy-day-pnl-requirements.md), [`2026-08-20-alphastrategy-named-book-requirements.md`](2026-08-20-alphastrategy-named-book-requirements.md)
**Technical design:** [`docs/plans/2026-08-20-alphastrategy-status-pnl-technical-design.md`](../plans/2026-08-20-alphastrategy-status-pnl-technical-design.md)

Paper only. Five screens. Quiet cockpit **tokens unchanged**. No sixth nav tab. No live. No WebSockets. No chart library. Do not revive `static/app.js`. `"Gross cap"` must not appear in assembled JS. `renderBanners` keeps a **single** `const reason`. Do not retry leftover orders. Resume does not catch up. Heartbeat still does **not** flatten. GET `/api/status`, `/api/portfolio`, and `/api/risk` must not flatten. Keep `Next rebalance`. Keep sticky heartbeat live book, Book flatten-now, PUT `apply_risk`, Caps LIMIT priced book, Book/Beat/Headroom source labels, LIMIT/BOOK stderr. Keep Book Day PnL as equity minus last close. Idle overlays stay unpublished. **Do not feed order sizing from the glance cache.** Each JS part stays ≤ 400 lines. Do **not** overwrite Cash / Headroom cash composition subs. Do **not** paint Beat/Glance on Day PnL.

v1 §9: `alphastrategy status` is the required CLI glance. Portfolio GET now returns honest Day PnL from the live-book account (`pnl` / `pnl_source`). GET `/api/status` and CLI `status` still omit it. A terminal operator sees BOOK and LIMIT but not the session number Book just made honest. Offline CLI stays `live=False` and must not invent a PnL. That is not 可靠 or 易于使用.

## 1. Why this increment exists

Goal check against current main (`4899365`):

| Goal slice | v1 / later contract | Current desk |
| --- | --- | --- |
| 可靠 | Status and Book Day PnL are the same live-book number. | Only GET `/api/portfolio` has `pnl`. |
| 易于使用 | `alphastrategy status` names Day PnL like BOOK/LIMIT. | JSON and stderr have no PnL. |
| 凭直觉交互 | One formula: equity minus last close. | Web yes; CLI silent. |
| 稳定执行 | GET still does not flatten. Offline still does not hit the broker for PnL. | Must keep that. |

Research applied:

- **Reuse `_account_day_pnl`.** Do not a second formula. Do not persist `last_equity`.
- **Same glance cache.** After `from_supervisor(live=True)` the live book is warm. Status reads that account. Do not add a second uncached `get_account`.
- **Offline is unknown, not zero.** Control-plane-down status keeps `live=False`, `pnl` JSON `null`, no PNL stderr line.

Out: heartbeat flatten; GET flatten; glance-fed orders; Risk JSON PnL; JS paint changes; Cash/PnL Beat labels; inventing offline PnL from snapshot; live; sixth screen.

## 2. Engine / API / CLI

`handle_get_status` after `from_supervisor(..., live=True)`:

```text
try:
    account, _ = supervisor.live_book()
    pnl, pnl_source = _account_day_pnl(account)
except Exception:
    pnl, pnl_source = None, None
```

Payload keys (same contract as Portfolio): `"pnl"`, `"pnl_source"`.

Offline `_cmd_status` (control plane down): include `"pnl": null` and `"pnl_source": null`. Do **not** call `live_book()`. Keep `from_supervisor(..., live=False)`.

CLI stdout remains one JSON object. `_print_status` stderr order: BOOK (if heartbeat/glance), then PNL (if `pnl` is a finite number), then LIMIT (existing).

PNL line:

- `PNL: 100.00 vs last close` when `pnl_source == "last_close"`
- `PNL: 42.50` when `pnl_source == "account"` (or any other non-null number)
- Omit when `pnl` is missing or JSON `null`

Explicit `0` prints `PNL: 0.00`. GET `/api/status` must not flatten.

## 3. Help / README

Phrase (exact): `status names Day PnL`

Add it to `cli`, README Operator (next to `status names BOOK`). Keep `Day PnL is equity minus last close`. Keep `status names BOOK heartbeat or glance`. Keep `Next rebalance`.

## 4. In / out

**In:** status JSON `pnl` / `pnl_source`; CLI PNL stderr; offline null keys; help/README; API + CLI tests.

**Out:** JS; Risk PnL; persist last_equity; offline live_book; GET flatten; live; sixth nav.

**Done when:**

1. Default FakeBroker GET `/api/status` → `pnl` is JSON `null`, `pnl_source` is `null`, `close_all` unchanged.
2. Same glance with `last_equity` 9900 and equity 10000 → status `pnl == 100` and `pnl_source == "last_close"`.
3. CLI `status` with that JSON prints `PNL: 100.00 vs last close` on stderr after BOOK and before LIMIT. Missing/null `pnl` prints no PNL line.
4. Offline status JSON includes `pnl` null and does not print PNL. `patch_alpaca` unused on that path.
5. Help contains the new phrase and `Next rebalance`. Five `#nav` screens. `"Gross cap"` not in assembled JS. No real broker.
