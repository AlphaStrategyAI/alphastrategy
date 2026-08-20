# alphastrategy Book Drift follows the last fill, not last prices

**Date:** 2026-08-20
**Status:** Requirements (improvement cycle on v1)
**Repo:** `AlphaStrategyAI/alphastrategy`
**Parent contract:** [`2026-08-19-alphastrategy-v1-requirements.md`](2026-08-19-alphastrategy-v1-requirements.md) §6–§8
**Related:** [`2026-08-20-alphastrategy-heartbeat-prices-requirements.md`](2026-08-20-alphastrategy-heartbeat-prices-requirements.md), [`2026-08-20-alphastrategy-drift-banner-requirements.md`](2026-08-20-alphastrategy-drift-banner-requirements.md), [`2026-08-20-alphastrategy-book-honesty-requirements.md`](2026-08-20-alphastrategy-book-honesty-requirements.md)
**Technical design:** [`docs/plans/2026-08-20-alphastrategy-fill-drift-technical-design.md`](../plans/2026-08-20-alphastrategy-fill-drift-technical-design.md)

Paper only. Five screens. Quiet cockpit **tokens unchanged**. No sixth nav tab. No live. No WebSockets. No chart library. Do not revive `static/app.js`. `"Gross cap"` must not appear in assembled JS. `renderBanners` keeps a **single** `const reason`. Do not retry leftover orders. Resume does not catch up. Heartbeat still does **not** flatten. Keep `Next rebalance`. Keep heartbeat marks. Keep overlay-on-start flatten. Keep spoken Caps.

v1 §6: if the combined target cannot be achieved, log `execution_deviation`. That is a **fill** miss at the legal rebalance, not a later mark. Heartbeat-prices now refreshes `last_prices` / `last_got` between windows. `GET /api/portfolio` already prices live qty × `last_prices`, so Positions **Got** is a current mark (honest). Book Drift still compares **wanted vs that mark**. After a name rally (15 AAPL $100 → $150 on $10k), Got is 22.5% vs wanted 15%, Drift goes off-zero, and the banner says **DEVIATION: execution drift exceeds tolerance**. No `execution_deviation` audit was written. That is not 凭直觉交互.

## 1. Why this increment exists

Goal check against current main (`2a0ce39`):

| Goal slice | v1 / later contract | Current desk |
| --- | --- | --- |
| 凭直觉交互 | Deviation banner is fill honesty. Got is current weight. At cap is live vs spoken. | One number (`pos.weight`) drives Got, Cap, **and** Book Drift. A mark rally looks like a missed fill. |
| 风险可控 | At cap / Gross must follow live marks so the operator sees the 0.225 name before close flatten. | Keep MTM Got / Cap. Do not revert heartbeat marks. |
| 易于使用 | Help must say Drift is last fill, Got is the mark. | Help still says Book Drift is names off the last combined target, with no fill vs mark split. |
| 稳定执行 | Heartbeat must not invent execution_deviation. | Audit path is clean. Glance path is not. |

Research applied:

- **Mark vs fill are different blotter columns.** EMS desks keep last fill / average vs last mark. Drift of fill vs target is completeness. Drift of mark vs target is P&L / risk, not “the broker missed.”
- **Do not stop marking.** v1 §6 reconciliation is the beat. The fix is a second snapshot (`last_fill_got`), not freezing `last_got`.
- **Banner copy stays execution language** only if the tile it follows is fill-based.

Out of this increment: flatten on heartbeat; changing Tighten; zero-cap `Number(x) \|\| fallback`; Run Start ignoring POST `flattened`; 409; live; sixth screen; `app.js`.

## 2. Engine / API

`SupervisorSnapshot.last_fill_got`: weights at the last `_snapshot_got` (rebalance completeness, including interrupted rebalance recovery). Persist next to `last_got`.

- `_snapshot_got` writes **both** `last_got` and `last_fill_got`.
- Heartbeat reconciliation writes **only** `last_got` (and `last_prices`).
- Flatten / account kill clears `last_fill_got` with the rest of the last book.

`_enrich_positions` sets `fill` from `last_fill_got[symbol]` when that key exists. `weight` stays live qty × `last_prices` / equity (mark). `wanted` stays `last_combined`.

## 3. Paint

`bookDrift` gaps **wanted vs fill** (fallback to `weight` when `fill` is omitted, so older snapshots still work).

Positions Got column and name Cap still use `weight` (mark). `wantedGotBar` still sizes the got fill from `weight`, but the `drift` CSS class follows fill vs wanted, not mark vs wanted.

Deviation banner still follows Book Drift. One `const reason`. `"Gross cap"` out of JS. Each `js/` part ≤ 400 lines.

## 4. Help / README

`REQUIRED_PHRASES`: `Book Drift follows the last fill, not last prices`.

Keep `Book Drift`, `deviation banner follows Book Drift`, heartbeat mark sentences, `Next rebalance`.

README Portfolio Book Drift line: same fill vs mark split. Got remains current weight.

## 5. In / out

**In:** `last_fill_got`; portfolio `fill`; Book Drift / bar `drift` class from fill; help/README; tests.

**Out:** heartbeat flatten; dropping MTM Got; 409; live; `app.js`.

**Done when:**

1. After open fill of 15 AAPL at $100, `last_fill_got["AAPL"] == last_got["AAPL"] == 0.15`. Mid-session heartbeat at $150: `last_got == 0.225`, `last_fill_got` stays `0.15`, no new `execution_deviation`.
2. `GET /api/portfolio` after that mark: `weight == 0.225`, `fill == 0.15`, `wanted == 0.15`.
3. Assembled JS `bookDrift` reads `pos.fill`. Partial fill still counts as Drift. Complete fill + rally does not.
4. Flatten clears `last_fill_got`. Help contains the new phrase. Five `#nav` screens. `"Gross cap"` not in `js_text`. No real broker.
