# alphastrategy deviation banner follows live Book Drift

**Date:** 2026-08-20
**Status:** Requirements (improvement cycle on v1)
**Repo:** `AlphaStrategyAI/alphastrategy`
**Parent contract:** [`2026-08-19-alphastrategy-v1-requirements.md`](2026-08-19-alphastrategy-v1-requirements.md) §6–§8
**Related:** [`2026-08-20-alphastrategy-spent-window-requirements.md`](2026-08-20-alphastrategy-spent-window-requirements.md), [`2026-08-20-alphastrategy-book-honesty-requirements.md`](2026-08-20-alphastrategy-book-honesty-requirements.md)
**Technical design:** [`docs/plans/2026-08-20-alphastrategy-drift-banner-technical-design.md`](../plans/2026-08-20-alphastrategy-drift-banner-technical-design.md)

Paper only. Five screens. Quiet cockpit **tokens unchanged**. No sixth nav tab. No live. No WebSockets. No chart library. Do not revive `static/app.js`. Do not retry leftover orders. Do not un-consume `last_rebalance_event`. `"Gross cap"` must not appear in assembled JS. `renderBanners` keeps a **single** `const reason`.

Spent-window recovery writes `execution_deviation` then a `rebalance` with `complete: false`, then halt. The cockpit walks that tape and **turns the DEVIATION banner off** on any `rebalance` or `resume`. Book Drift can be red while the banner is hidden. v1 §8 says halt/deviation banners cannot be visually quiet. This cycle drives the banner from **live Book Drift** (and a spent window with a last combined book), not from the last audit event name.

## 1. Why this increment exists

Goal check against current main (`597650a`):

| Goal slice | v1 / later contract | Current desk |
| --- | --- | --- |
| 凭直觉交互 | §8 halt/deviation banners cannot be quiet. Book Drift already counts names off last combined. | `detectDeviation` sets active on `execution_deviation`, then clears on `resume` / `flatten` / **any** `rebalance`. Spent recovery order is deviation → incomplete rebalance → halt, so the banner goes quiet. |
| 稳定执行 | Persist-before-send can spend a window with 0 fills. Wanted names with no fill are still book rows. | Clock Last says spent. Tape says spent. DEVIATION hides. Operator can think the miss was acknowledged and cleared. |
| 组合管理 | Combined target vs live book is the truth. | Drift tile uses live rows. The banner uses a trailing audit walk that a spent line can silence. Two truths. |
| 易于使用 | Help names Book Drift. | It never says the deviation banner follows that tile. |
| 可靠 | Flatten still clears last combined. | Flatten should still hide the banner (empty book). Do not change flatten math. |

Research applied:

- **One number, one alarm.** OMS drift alerts follow the live book, not the last fill-ack. A spent or incomplete batch is not a successful mark-to-target.
- **Resume is not a fill.** v1 resume does not catch up; it must not look like it healed drift.
- **Flatten is a real empty book.** Flatten remains the clear.

## 2. Live drift function

Extract `bookDrift(positions, equity)` next to `renderBookDrift`. Same gap as today and as `deviations_after`: `|wanted − got| * equity ≥ max($1, 0.1% equity)`. Return `{ off, maxGap }`. Empty or unknown book: `off = 0`.

`renderBookDrift` calls it. No second formula.

## 3. When the banner is on

`refresh` sets `state.deviationActive` true when **either**:

1. `bookDrift(portfolio.positions, portfolio.equity).off > 0`, or
2. `status.last_rebalance_complete === false` and `portfolio.last_combined` has at least one key (spent window with a last book, even if enrich lagged).

Do **not** walk `resume` / `rebalance` to clear. Do **not** require `portfolio.deviation`. Flatten already empties last combined and positions, so both clauses go false.

Banner copy stays `DEVIATION: execution drift exceeds tolerance`. Keep a single halt `const reason`.

## 4. Spent recovery still has a last book

A 0-fill interrupt still persists `last_combined` before the first place. Recovery must not clear it. Restart after `crash_after_place=0` keeps those names; the incomplete audit may include `execution_deviation`.

## 5. Help / README

`how_portfolio` / cockpit: the deviation banner follows Book Drift and cannot go quiet while Drift is above zero. A spent window keeps it.

README Operator: same sentence.

## 6. In / out

**In:** `bookDrift`; banner from live drift + spent last book; 0-fill last_combined assertion; help/README; JS tests.

**Out:** retrying orders; un-consuming the event; changing Drift math; a new banner id; live; sixth screen; `app.js`; WebSockets; `"Gross cap"` in JS.

## 7. Verification

- 0-fill interrupt restart: `last_combined` still has the sleeve names; audit may contain `execution_deviation`; `last_rebalance_complete is False`.
- JS: `function bookDrift`; `detectDeviation` calls `bookDrift` and reads `last_rebalance_complete`; does not clear on `resume` or every `rebalance`. `renderBanners` still uses `deviationActive`. One `const reason`. `"Gross cap"` not in `js_text`.
- Help contains `deviation banner follows Book Drift`.
- Five `#nav` screens. No real broker.
