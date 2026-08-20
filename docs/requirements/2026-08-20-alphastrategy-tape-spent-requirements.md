# alphastrategy Activity tape names spent rebalances

**Date:** 2026-08-20
**Status:** Requirements (improvement cycle on v1)
**Repo:** `AlphaStrategyAI/alphastrategy`
**Parent contract:** [`2026-08-19-alphastrategy-v1-requirements.md`](2026-08-19-alphastrategy-v1-requirements.md) §8
**Related:** [`2026-08-20-alphastrategy-spent-window-requirements.md`](2026-08-20-alphastrategy-spent-window-requirements.md)
**Technical design:** [`docs/plans/2026-08-20-alphastrategy-tape-spent-technical-design.md`](../plans/2026-08-20-alphastrategy-tape-spent-technical-design.md)

Paper only. Five screens. Quiet cockpit **tokens unchanged**. No sixth nav tab. No live. No WebSockets. No chart library. Do not revive `static/app.js`. Do not retry leftover orders. Do not un-consume `last_rebalance_event`. `"Gross cap"` must not appear in assembled JS. `renderBanners` keeps a **single** `const reason`.

The spent-window cycle made Portfolio Clock Last and the halt reason say a session event was **spent**. Activity still counts that same `complete: false` audit line as a happy green Rebalances hero and a blotter suffix `incomplete`. Two screens, two words, one green number. This cycle makes Tape and Blotter use **spent** and refuse the running token when any rebalance did not finish.

## 1. Why this increment exists

Goal check against current main (`53ca331`):

| Goal slice | v1 / later contract | Current desk |
| --- | --- | --- |
| 凭直觉交互 | §8 Activity: time-ordered rebalances, target vs fill, halt/flatten. Halt chrome cannot be quiet. Clock Last now paints `spent`. | Tape Rebalances uses `status-running` (`#10b981`) for every `event=rebalance`, including `complete: false`. Blotter says `incomplete`. |
| 稳定执行 | Persist-before-send can spend a window with 0 fills. Recovery audits `complete: false`. | The tape looks like a finished auction. Operator can think the open worked. |
| 易于使用 | `how_activity`: Rebalances is the hero count. | Help never says Tape/Blotter name a spent window. |
| 可靠 | Audit schema already has `complete`. | No new event type. Paint the flag that is already on disk. |
| 界面 | Tape is already four tiles. | Add a **sub** on the Rebalances hero, not a fifth tile and not a sixth screen. |

Research applied:

- **Same word on every surface.** Clock Last, halt reason, Tape sub, blotter row: **spent**. Keep `incomplete rebalance` in the execution essay as the engine/audit phrase.
- **Do not celebrate a torn batch.** Running green is for a finished rebalance count with zero spent rows.
- **Hero + sub, not a fifth tile.** Caps/Clock already teach this pattern (value + sub). Keep `metrics-4`.

## 2. Tape Rebalances

Keep four tiles: Rebalances (hero) / Halts / Deviations / Kills.

Under Rebalances add `#act-count-spent` (`metric-sub`):

| Spent count | Sub copy | Rebalances value class |
| --- | --- | --- |
| 0 | em dash | `status-running` when the rebalance count is &gt; 0 (today) |
| ≥ 1 | `{n} spent` | `warn` (`#f59e0b`). **Not** `status-running` |

Hero value stays the count of `event=rebalance` rows (complete and spent). Blotter length for that type still matches the hero number.

Do not `innerHTML=""` the Tape mounts. Clear `warn` / `status-running` when painting.

## 3. Blotter copy

`eventSummary` for `rebalance`: when `complete === false`, suffix **spent** (replace `incomplete`).

`eventDetail` Complete row becomes Spent: `yes` when `complete === false`, else `no`.

## 4. Help / README

`how_activity`: Tape Rebalances sub names spent. Blotter rebalance rows say spent when that event did not finish.

Keep `incomplete rebalance` in the execution section.

README Operator: Activity Tape names spent rebalances on the Rebalances sub.

## 5. In / out

**In:** Rebalances sub; warn vs running; blotter `spent`; help/README; HTML/JS/CSS tests.

**Out:** a fifth Tape tile; changing audit schema; retrying orders; live; sixth screen; `app.js`; WebSockets; `"Gross cap"` in JS.

## 6. Verification

- HTML Tape contains `id="act-count-spent"` inside the Rebalances hero, still `metrics-4`, still four tile values.
- JS Tape paints `act-count-spent`, uses `complete === false` for the spent count, toggles `warn` when spent &gt; 0, and does not apply `status-running` then.
- `eventSummary` contains `spent` and does not contain `incomplete`.
- CSS `#act-count-rebalance.warn` uses `#f59e0b`.
- Help contains `Tape Rebalances sub names spent`. Execution still contains `incomplete rebalance`.
- Five `#nav` screens. `"Gross cap"` not in `js_text`. No real broker.
