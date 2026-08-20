# alphastrategy Activity blotter book drill-in

**Date:** 2026-08-20
**Status:** Requirements (improvement cycle on v1)
**Repo:** `AlphaStrategyAI/alphastrategy`
**Parent contract:** [`2026-08-19-alphastrategy-v1-requirements.md`](2026-08-19-alphastrategy-v1-requirements.md)
**Technical design:** [`docs/plans/2026-08-20-alphastrategy-blotter-book-technical-design.md`](../plans/2026-08-20-alphastrategy-blotter-book-technical-design.md)

Paper only. Five screens. Quiet cockpit **tokens unchanged**. No sixth nav tab. No live. No WebSockets. No chart libraries. Audit JSONL schema **unchanged**. `#activity-list` and expand-one-row behavior stay.

This cycle makes Activity drill-in match execution honesty: a personal investor expanding a rebalance sees a **Wanted / Got** book, not a JSON dump of leftover fields.

## 1. Why this increment exists

Goal check against current main (`5eacf6a`):

| Goal slice | v1 / later contract | Current desk |
| --- | --- | --- |
| 稳定执行 | §8 Activity: rebalances with **target vs fill**; drill into one event. Execution honesty: rebalance audit already stores `wanted` and `got`. | Tape counts exist. Expand still does `JSON.stringify(payload)`. The maps the Supervisor already persisted are hidden in JSON. |
| 凭直觉交互 | Operator desk §6: blotter is not a JSON dump; summary is human, drill-in is remaining fields. | Summary is human. Drill-in is a `<pre>` of JSON. A personal investor cannot read wanted vs got the way Portfolio’s Positions table does. |
| 界面令人眼前一亮 | Quiet cockpit: dense numbers, sparse chrome; Portfolio already has Wanted / Got columns. | Expanding a row drops into a debugger view. Same tokens, different job (research dump vs desk). |
| 易于使用 | `how_activity` says “Expand a blotter row for the payload.” | “Payload” teaches the operator to read JSON. |
| 架构 | `js/paint-activity.js` | Edit that part + CSS. Do not revive `static/app.js`. No new API. |

Research applied (not an EMS / not VWAP TCA):

- **Blotter practice:** intent (wanted) and fills (got) are separate columns. This desk rebalances at most twice per RTH session; the right drill-in is last combined target vs got weights, the same slice Portfolio already shows.
- **MiFID-style drill-down (applied, not copied):** summary row → audit drawer of the underlying book. No CSV export, no venue grid, no chart library.
- **Nielsen match the real world / consistency:** drill-in uses the same Wanted / Got words as Portfolio, not snake_case JSON keys.

## 2. Drill-in content

Keep click / Enter / Space: one expanded row at a time. Replace the JSON `<pre>` with a `.activity-detail` **div** that `eventDetail(ev)` fills:

| `event` | Drill-in |
| --- | --- |
| `rebalance` | Table `.activity-book`: Symbol / Wanted / Got for the union of `wanted` and `got` keys (sorted). Then labeled fields Session (`session_event`) and Orders (`orders`). |
| `execution_deviation` | Same table for that `asset` (wanted / got). |
| `order` | Labeled fields Symbol, Side, Qty. |
| `halt` | Labeled field Reason. |
| `kill` | Outcome (`isolated residual` or `flattened account`, same words as the summary), Bundle, Scope. |
| `flatten` | Scope (default `account`). |
| `paper_start` / `paper_stop` / `import` | Bundle (`bundle_id`). |
| anything else | Labeled fields for remaining keys except `ts` / `timestamp` / `event`. Object values render as `key value · …` text, **not** `JSON.stringify` of the whole payload. |

Wanted / Got cells use existing `fmtPct`. Empty book: one muted em dash row.

Do not add a new HTTP route. `GET /api/activity` stays the same array.

## 3. CSS

- `.activity-detail` stays hidden until `li.expanded`. Remove `white-space: pre-wrap` (it is no longer a `<pre>`).
- `.activity-book` uses existing table chrome (locked tokens).
- `.activity-fields` is a two-column `dt` / `dd` grid (`max-content` + `1fr`), muted labels, no new colors.

## 4. Help / README

`how_activity`: expand a blotter row for a **Wanted / Got** table, **not a JSON dump**.

Cockpit runbook and README Quiet cockpit: same sentence.

## 5. In / out

**In:** `eventDetail` / `bookTable`; CSS; help/README; JS/CSS/help tests; e2e `GET /app.js` contains `bookTable` and not `JSON.stringify(payload`.

**Out:** new audit events; VWAP/arrival TCA; CSV export; chart libraries; sixth screen; new tokens; changing Tape counts; reviving `static/app.js`.

## 6. Verification

- Assembled JS in the Activity painter contains `function bookTable` and `function eventDetail`.
- That painter slice does **not** contain `JSON.stringify(payload`.
- CSS `.activity-book` and `.activity-fields`. `.activity-detail` is not `white-space: pre-wrap` only.
- Help contains `not a JSON dump`. `#nav` still five screens.
- `paint-activity.js` stays ≤ 400 lines. No real broker orders.
