# alphastrategy Caps LIMIT follows a next send through Orders / rebalance

**Date:** 2026-08-20
**Status:** Requirements (improvement cycle on v1)
**Repo:** `AlphaStrategyAI/alphastrategy`
**Parent contract:** [`2026-08-19-alphastrategy-v1-requirements.md`](2026-08-19-alphastrategy-v1-requirements.md) §7–§8
**Related:** [`2026-08-20-alphastrategy-send-limit-requirements.md`](2026-08-20-alphastrategy-send-limit-requirements.md), [`2026-08-20-alphastrategy-limit-send-requirements.md`](2026-08-20-alphastrategy-limit-send-requirements.md), [`2026-08-20-alphastrategy-flatten-next-requirements.md`](2026-08-20-alphastrategy-flatten-next-requirements.md)
**Technical design:** [`docs/plans/2026-08-20-alphastrategy-send-rebalance-technical-design.md`](../plans/2026-08-20-alphastrategy-send-rebalance-technical-design.md)

Paper only. Five screens. Quiet cockpit **tokens unchanged**. No sixth nav tab. No live. No WebSockets. No chart library. Do not revive `static/app.js`. `"Gross cap"` must not appear in assembled JS. `renderBanners` keeps a **single** `const reason`. Do not retry leftover orders. Resume does not catch up. Heartbeat still does **not** flatten. GET must not flatten. Keep `Next rebalance`. Keep Caps **four tiles**. Keep `#risk-cap-order`. Keep `live_limit.kind` book vs send. Keep Book LIMIT rail. Do **not** overwrite Cash composition subs. Each JS part stays ≤ 400 lines. Do not hardcode `Order size` or `Orders / rebalance` in JS.

v1 §7: `plan_orders` flattens when the next batch is over Orders / rebalance (default 100). `_next_send_limit` already dry-runs that. Caps fail-color has homes for book caps, Orders today, Long only, and Order size. Orders / rebalance has none. Clock Next still paints `flatten ·` for both book and send, while Help says flatten only while the live book is through the spoken cap. After last combined three 1% names, empty qty, mark $100, equity $10k, spoken Orders / rebalance **2**: three $100 buys pass Order size and name cap; next rebalance still flattens. That is not 风险可控 or 凭直觉交互.

## 1. Why this increment exists

Goal check against current main (`ba2c347`):

| Goal slice | v1 / later contract | Current desk |
| --- | --- | --- |
| 风险可控 | LIMIT warns and fail-colors the cap that will flatten. | Send LIMIT through Orders / rebalance has banner copy, no Caps home. |
| 凭直觉交互 | Clock Next already distinguishes held / flat / flatten. Send vs book is a different next action. | Both paints `flatten · open`. |
| 可靠 | One dry-run of `plan_orders`. GET does not flatten. | Engine already returns the reason; the desk does not house it. |
| 易于使用 | Help: Caps LIMIT follows a next send through Orders / rebalance. Clock Next is flatten send. | Help only names Order size and live-book flatten. |

Research applied:

- **Same muted-line pattern as Order size.** `#risk-cap-rebalance` beside `#risk-cap-order`, not a fifth Caps tile. Integer spoken cap via `policyLabel("max_orders_per_rebalance")`.
- **Clock Next uses `kind`, not the reason key.** `kind === "send"` → `flatten send · ` + next window. Else keep `flatten · `. Missing kind stays book (old payloads).
- **Do not re-evaluate DSL on GET.** Keep last-combined replay. Book LIMIT still wins. Missing prices skip.

Out: GET flatten; placing; fifth Caps tile; using last_combined for book LIMIT; live; sixth screen.

## 2. Engine / API

No new dry-run. Fixture (do **not** use 0.40 name weight):

- last combined AAA/BBB/CCC **0.01** each, last prices **$100**, equity **$10k**, empty qty
- spoken `max_orders_per_rebalance` **2**
- each buy is $100 < Order size 20%; 3 plans > 2 → `reason == max_orders_per_rebalance`, `kind == send`
- GET `close_all` unchanged; state not stopped

Keep empty-`last_prices` last_combined 0.40 → `live_limit` null.

## 3. Cockpit

HTML Caps after `#risk-cap-order`:

```html
          <p id="risk-cap-rebalance" class="muted nums"></p>
```

CSS: `#risk-cap-rebalance.warn { color: #f59e0b; }` `#risk-cap-rebalance.fail { color: #ef4444; }`

`renderRiskCaps`: paint `policyLabel("max_orders_per_rebalance") + " " + integer`; `markTighter` (smaller is tighter); `markLimit(..., "max_orders_per_rebalance")`. Skip fail while flattened.

Clock Next: `flatten send · ` when `live_limit.kind === "send"`. Keep `flatten · ` for book. Keep `held · ` / `flat · `.

LIMIT banner already uses send vs book copy. CLI already uses kind.

## 4. Help / README

Phrases (exact):

- `Caps LIMIT follows a next send through Orders / rebalance`
- `Clock Next is flatten send while a next send will flatten`

Add to `halt_flatten`, `how_risk`, `how_portfolio` (Clock Next), README Operator. Keep `Caps LIMIT follows a next send through Order size`. Keep `Clock Next is flatten while the live book is through the spoken cap`. Keep `Next rebalance`. Keep four Caps tiles.

## 5. In / out

**In:** `#risk-cap-rebalance`; Clock Next `flatten send`; API/unit/HTML/JS/CSS/help tests.

**Out:** GET flatten; fifth tile; book LIMIT from last_combined; live; sixth nav.

**Done when:**

1. GET `/api/status` three 1% names, Order size default, Orders / rebalance 2 → `live_limit.reason == max_orders_per_rebalance` and `kind == send`; `close_all` unchanged.
2. HTML has `#risk-cap-rebalance` inside Caps, not a fifth metrics tile. JS `markLimit`s it. CSS fail `#ef4444`.
3. JS Clock Next contains `flatten send · ` and `kind === "send"`. Keep `flatten · `.
4. Help contains both phrases. Five `#nav` screens. `"Gross cap"` not in assembled JS. No real broker.
