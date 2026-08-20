# alphastrategy Day PnL is equity minus last close

**Date:** 2026-08-20
**Status:** Requirements (improvement cycle on v1)
**Repo:** `AlphaStrategyAI/alphastrategy`
**Parent contract:** [`2026-08-19-alphastrategy-v1-requirements.md`](2026-08-19-alphastrategy-v1-requirements.md) §8, §10
**Related:** [`2026-08-20-alphastrategy-named-book-requirements.md`](2026-08-20-alphastrategy-named-book-requirements.md), [`2026-08-20-alphastrategy-live-glance-requirements.md`](2026-08-20-alphastrategy-live-glance-requirements.md)
**Technical design:** [`docs/plans/2026-08-20-alphastrategy-day-pnl-technical-design.md`](../plans/2026-08-20-alphastrategy-day-pnl-technical-design.md)

Paper only. Five screens. Quiet cockpit **tokens unchanged**. No sixth nav tab. No live. No WebSockets. No chart library. Do not revive `static/app.js`. `"Gross cap"` must not appear in assembled JS. `renderBanners` keeps a **single** `const reason`. Do not retry leftover orders. Resume does not catch up. Heartbeat still does **not** flatten. GET `/api/status`, `/api/portfolio`, and `/api/risk` must not flatten. Keep `Next rebalance`. Keep sticky heartbeat live book, Book flatten-now, PUT `apply_risk`, Caps LIMIT priced book, Book/Beat/Headroom source labels, LIMIT/BOOK stderr. Idle overlays stay unpublished. **Do not feed order sizing from the glance cache.** Each JS part stays ≤ 400 lines. Do **not** overwrite Cash / Headroom cash composition subs with Beat/Glance. Do **not** paint Beat/Glance on Day PnL.

v1 §8 Portfolio is equity, cash, **day PnL**. Book already paints a Day PnL tile from `GET /api/portfolio` `pnl`. Alpaca `GET /v2/account` (the live-book account dict) does **not** send `pnl` or `day_pnl`. It sends `equity` and `last_equity` (prior session close). The handler still does `float(account.get("pnl", account.get("day_pnl", 0)) or 0)`, so a paper glance with no such keys paints **`0.00` as if the day were flat**. FakeBroker only returns `{equity, cash}`, so every test and every first desk glance lies the same way. That is not 可靠, 凭直觉交互, or 易于使用.

## 1. Why this increment exists

Goal check against current main (`7f49302`):

| Goal slice | v1 / later contract | Current desk |
| --- | --- | --- |
| 可靠 | Day PnL is a session number from the same live book as Equity. | Missing Alpaca fields coerce to `0.0`. |
| 凭直觉交互 | Tile says Day PnL; empty last close is an em dash, not a fake flat. | `0.00` looks like a mark. |
| 易于使用 | Help names the formula operators can check against Alpaca. | Help never mentions Day PnL. |
| 稳定执行 | GET still does not flatten. Heartbeat still does not flatten. | Must keep that. |
| 眼前一亮 | Honest dash vs signed color when the number exists. | Fake zero is visually quiet. |

Research applied:

- **Alpaca day change is `equity - last_equity`.** Do not relabel `unrealized_pl` (position mark, not day PnL) while the tile says Day PnL.
- **Unknown is not zero.** JSON `null` + cockpit `—`. Explicit broker `pnl` / `day_pnl` of `0` stays `0.00` (a real posted flat).
- **Same glance as Equity.** Derive from the `live_book()` account dict. Do not add a second `get_account`. Do not persist `last_equity`.

Out: heartbeat flatten; GET flatten; glance-fed orders; Cash/Headroom Beat labels on composition subs; Day PnL Beat/Glance sub; `unrealized_pl` as Day PnL; status/CLI PnL; live; sixth screen.

## 2. Engine / API

`handle_get_portfolio` keeps `supervisor.live_book()` for equity, cash, and positions. Add `_account_day_pnl(account) -> (pnl, source)`:

1. If `pnl` is present and parseable as float (including `0`) → that number, source `"account"`.
2. Else if `day_pnl` is present and parseable → that number, source `"account"`.
3. Else if `last_equity` is present and parseable **and** `equity` is parseable → `equity - last_equity`, source `"last_close"`.
4. Else → `(None, None)`.

Unparseable values skip that step. Do not treat a missing key as `0`.

Payload:

```text
"pnl": <float or JSON null>
"pnl_source": "account" | "last_close" | null
```

GET `/api/portfolio` must not flatten. Do not add `pnl` to `/api/status`. Do not persist. Do not feed `plan_orders` from this field.

## 3. Cockpit

Book Day PnL tile gains `#metric-pnl-sub` (existing `.metric-sub`). `paintDayPnl` lives in `paint-rails.js` so `paint-portfolio.js` stays ≤ 400 lines.

- `pnl` JSON null / missing / non-finite → value `—`, no positive/negative class, sub `—`.
- Number → `fmtNum(pnl, 2)`, positive `#10b981` / negative `#ef4444` classes unchanged.
- `pnl_source === "last_close"` → sub `vs last close`. Otherwise sub `—`.
- Do **not** write Beat/Glance onto `#metric-pnl-sub` or overwrite Cash composition subs.

Keep Equity hero. Keep `#metric-equity-sub` as Beat/Glance.

## 4. Help / README

Phrase (exact): `Day PnL is equity minus last close`

Add it to `cockpit`, `how_portfolio`, README Portfolio/Operator. Keep `Book Equity names Beat or Glance`. Keep `Next rebalance`. Keep Cash composition copy. Keep `Caps LIMIT follows the same live book as Tighten`.

## 5. In / out

**In:** `_account_day_pnl`; portfolio `pnl` / `pnl_source`; `#metric-pnl-sub`; `paintDayPnl`; help/README; API + HTML/JS tests.

**Out:** heartbeat flatten; GET flatten; `unrealized_pl` as Day PnL; persist last_equity; status/CLI PnL; Cash/PnL Beat labels; live; sixth nav.

**Done when:**

1. Default FakeBroker GET `/api/portfolio` → `pnl` is JSON `null` (not `0.0`) and `pnl_source` is `null`.
2. Same glance with `last_equity` 9900 and equity 10000 → `pnl == 100` and `pnl_source == "last_close"`; `close_all` unchanged.
3. Explicit `pnl` wins over `last_equity`. Explicit `0` is `0.0`, not null.
4. HTML has `#metric-pnl-sub`. JS paints `vs last close` only for `pnl_source === "last_close"` and an em dash when `pnl` is null.
5. Help contains the new phrase and `Next rebalance`. Five `#nav` screens. `"Gross cap"` not in assembled JS. Each JS part ≤ 400 newlines. No real broker.
