# alphastrategy Positions Day is that name since last close

**Date:** 2026-08-20
**Status:** Requirements (improvement cycle on v1)
**Repo:** `AlphaStrategyAI/alphastrategy`
**Parent contract:** [`2026-08-19-alphastrategy-v1-requirements.md`](2026-08-19-alphastrategy-v1-requirements.md) §8
**Related:** [`2026-08-20-alphastrategy-day-pnl-requirements.md`](2026-08-20-alphastrategy-day-pnl-requirements.md), [`2026-08-20-alphastrategy-fill-drift-requirements.md`](2026-08-20-alphastrategy-fill-drift-requirements.md)
**Technical design:** [`docs/plans/2026-08-20-alphastrategy-positions-day-technical-design.md`](../plans/2026-08-20-alphastrategy-positions-day-technical-design.md)

Paper only. Five screens. Quiet cockpit **tokens unchanged**. No sixth nav tab. No live. No WebSockets. No chart library. Do not revive `static/app.js`. `"Gross cap"` must not appear in assembled JS. `renderBanners` keeps a **single** `const reason`. Do not retry leftover orders. Resume does not catch up. Heartbeat still does **not** flatten. GET `/api/status`, `/api/portfolio`, and `/api/risk` must not flatten. Keep `Next rebalance`. Keep sticky heartbeat live book, Book flatten-now, PUT `apply_risk`, Caps LIMIT priced book, Book/Beat/Headroom source labels, LIMIT/BOOK/PNL stderr. Keep Book Day PnL as equity minus last close. Keep Positions glance **Rows / Wanted / Got / At cap**. Idle overlays stay unpublished. **Do not feed order sizing from the glance cache.** Each JS part stays ≤ 400 lines. Do **not** overwrite Cash / Headroom cash composition subs. Do **not** paint Beat/Glance on Day PnL or Positions Day. Do **not** relabel `unrealized_pl` as Day.

v1 §8 Portfolio is combined positions plus day PnL. Book Day PnL is now honest (`equity - last_equity`, else `—`). Positions rows still show Symbol / Qty / Notional / Wanted / Got / Book / Cap with **no name-level session change**. Alpaca `GET /v2/positions` sends `unrealized_intraday_pl` and `lastday_price`; FakeBroker sends only `{symbol, qty}`. The desk cannot answer “which name moved Day PnL.” Using lifetime `unrealized_pl` under a Day header would repeat the fake-zero class of lie. That is not 凭直觉交互 or 可靠.

## 1. Why this increment exists

Goal check against current main (`2f9bd90`):

| Goal slice | v1 / later contract | Current desk |
| --- | --- | --- |
| 凭直觉交互 | Book Day PnL is auditable by name. | Total only; rows have no Day. |
| 可靠 | Unknown is `—`, not `0.00`. Lifetime P/L is not Day. | No field; FakeBroker would paint 0 if coerced. |
| 易于使用 | Help names Positions Day. | Help never mentions it. |
| 稳定执行 | GET still does not flatten. | Must keep that. |

Research applied:

- **Alpaca day change on a position is `unrealized_intraday_pl`, not `unrealized_pl`.** Fallback: `qty * (mark - lastday_price)` using desk `last_prices` (same mark as Notional/Got), else position `current_price`.
- **Do not sum rows into Book Day PnL.** Account day change includes cash/deposits; the tile stays `equity - last_equity`.
- **Wanted-only rows stay `null`.** Qty 0 and no intraday field → em dash.

Out: heartbeat flatten; GET flatten; glance-fed orders; replacing Book Day PnL with a sum of rows; `unrealized_pl` as Day; Cash/PnL Beat labels; live; sixth screen; fifth Positions glance tile.

## 2. Engine / API

`_enrich_positions` sets `day_pnl` on every row via `_position_day_pnl`:

1. If `unrealized_intraday_pl` is present and parseable (including `0`) → that number.
2. Else if `day_pnl` is present and parseable → that number.
3. Else if `qty != 0` and `lastday_price` parseable and a mark exists (`last_prices[symbol]` else `current_price`) → `qty * (mark - lastday_price)`.
4. Else → `None`.

Do **not** read `unrealized_pl` for this field. Wanted-only synthetic rows get `day_pnl: null`. GET `/api/portfolio` must not flatten. Do not persist. Do not add Positions Day to `/api/status`.

## 3. Cockpit

Positions table becomes eight columns:

`Symbol / Qty / Notional / Day / Wanted / Got / Book / Cap`

Empty row `colspan='8'`. Day cell: JSON null → `—`; number → `fmtNum(..., 2)` with `#10b981` / `#ef4444` on that `td` (not `.metric-value`). Keep glance tiles at four. Keep Equity Beat/Glance. Keep Cash composition.

`formatDayPnlCell` lives in `paint-rails.js` so `paint-portfolio.js` stays ≤ 400 lines.

## 4. Help / README

Phrase (exact): `Positions Day is that name since last close`

Add it to `cockpit`, `how_portfolio`, `task_wanted`, README Portfolio. Keep `Day PnL is equity minus last close`. Keep `Next rebalance`. Keep `Rows / Wanted / Got / At cap`.

## 5. In / out

**In:** `_position_day_pnl`; row `day_pnl`; Day column; signed table colors; help/README; API + HTML/JS/CSS tests.

**Out:** summing rows to Book Day PnL; `unrealized_pl` as Day; GET flatten; fifth glance tile; status JSON change; live; sixth nav.

**Done when:**

1. Live qty with no intraday field and no `lastday_price` → `day_pnl` is JSON `null` (not `0.0`); `close_all` unchanged.
2. `unrealized_intraday_pl` 12.5 wins. `unrealized_pl` 999 alone does **not** set `day_pnl`.
3. 15 AAPL, `lastday_price` 100, `last_prices` 110 → `day_pnl == 150`. Explicit `0` is `0.0`.
4. HTML has Positions `<th>Day</th>` after Notional. Empty rowspan uses `colspan='8'`. JS paints `pos.day_pnl`. CSS uses `#10b981` / `#ef4444` on `#positions-table` signed cells.
5. Help contains the new phrase and `Next rebalance`. Five `#nav` screens. `"Gross cap"` not in assembled JS. Each JS part ≤ 400 newlines. No real broker.
