# alphastrategy how to read a spent window

**Date:** 2026-08-20
**Status:** Requirements (improvement cycle on v1)
**Repo:** `AlphaStrategyAI/alphastrategy`
**Parent contract:** [`2026-08-19-alphastrategy-v1-requirements.md`](2026-08-19-alphastrategy-v1-requirements.md) §6–§8
**Related:** [`2026-08-20-alphastrategy-spent-window-requirements.md`](2026-08-20-alphastrategy-spent-window-requirements.md), [`2026-08-20-alphastrategy-help-tutorial-requirements.md`](2026-08-20-alphastrategy-help-tutorial-requirements.md)
**Technical design:** [`docs/plans/2026-08-20-alphastrategy-spent-howto-technical-design.md`](../plans/2026-08-20-alphastrategy-spent-howto-technical-design.md)

Paper only. Five screens. Quiet cockpit **tokens unchanged**. Help stays an aside. No sixth nav tab. No live. No WebSockets. No chart library. Do not revive `static/app.js`. `"Gross cap"` must not appear in assembled JS. `renderBanners` keeps a **single** `const reason`. Do not retry leftover orders. Do not un-consume `last_rebalance_event`. Keep the first-session tutorial from requiring a live rebalance or flatten.

The desk now names spent windows on Clock Last, Tape, After halt, and the DEVIATION banner. Help still teaches Session / Next rebalance and empty Positions that “the next legal open or close rebalance will trade” even when Last is spent. That fights 易于使用 and 凭直觉. This cycle adds a **How to** job, updates the first-session lesson to the current Clock/Roster chrome, and changes the empty Positions copy when the last event is spent.

## 1. Why this increment exists

Goal check against current main (`e175fde`):

| Goal slice | v1 / later contract | Current desk |
| --- | --- | --- |
| 易于使用 | Diátaxis: tutorial = first success; how-to = a job. §7 resume does not catch up. | `tutorial_first_session` still says Clock shows Session and Next rebalance. No job for a spent window. |
| 凭直觉交互 | Clock Last / Tape / Drift banner already speak **spent**. | Empty Positions with a paper sleeve always says the next legal rebalance will trade — true of the *next remaining* event, false if the operator thinks today’s spent open will fire again. |
| 稳定执行 | Persist-before-send spends the window even with 0 fills. | Engine unchanged. Copy must not undo that honesty. |
| 帮助文档 | Jobs live in `TASK_HOWTOS`. Titles start with `How to`. | Five jobs. Missing: read a spent window. |
| 架构 | `helptext.py` is the source. | Add one task. Keep six runbook ids. Keep one tutorial id. |

Research applied:

- **How-to, not a second tutorial.** Reading a halt after persist-before-send is a job. Title starts with `How to`.
- **First lesson still cannot wait for RTH.** Name Clock Last and Roster imported at as chrome the learner will see, without requiring a fill.
- **Empty table copy follows Last.** When `last_rebalance_complete === false`, do not use the generic next-rebalance sentence alone.

## 2. Tutorial (same id)

`tutorial_first_session` keeps title `Your first paper session`, `You will see`, `You finished the lesson`, `Flatten account`, and **Next rebalance**.

Update doing:

- Strategies: Inventory Imported count 1. Roster names imported at. Still not trading.
- Clock is Session / Now / Next / Last. Next is the hero. Last stays an em dash until a session event is spent or finishes.
- Finish still: sleeve on Run and Clock shows Next rebalance. Do not flatten.

## 3. New job

`task_spent`:

- title: `How to read a spent window`
- screens: `portfolio`, `activity`, `run`
- body (numbered): Clock Last names the spent window. Tape Rebalances sub names spent. The deviation banner follows Book Drift. After halt names the spent session event. Resume does not catch up.

Insert after `task_wanted` (still a reading job). Every title still starts with `How to`.

## 4. Empty Positions copy

When `positions.length === 0` and there is a paper sleeve:

| Condition | Copy |
| --- | --- |
| `status.last_rebalance_complete === false` | `No positions yet. Clock Last is spent. Resume does not catch up.` |
| otherwise (today) | `No positions yet. The next legal open or close rebalance will trade.` |

Keep the import-empty and imported-not-trading sentences. Keep `colspan='7'`. `"Gross cap"` stays out of JS. One `const reason`.

## 5. Help / README

README Operator: How to read a spent window is in Help. Empty Positions names a spent Last.

## 6. In / out

**In:** tutorial Clock/Roster chrome; `task_spent`; spent empty-table copy; tests; README.

**Out:** a second tutorial; requiring a live rebalance to finish the first lesson; retrying orders; live; sixth screen; `app.js`; WebSockets.

## 7. Verification

- `TASK_HOWTOS` ids end with `task_spent`. Title starts with `How to`. Help contains `How to read a spent window` and `Clock Last is spent`.
- Tutorial still has `Next rebalance`, `You will see`, `Roster names imported at`, `Session / Now / Next / Last`.
- JS contains `Clock Last is spent. Resume does not catch up.` and still contains `The next legal open or close rebalance will trade.`
- `GET /api/help` tasks include `task_spent`. Five `#nav` screens. `"Gross cap"` not in `js_text`. No real broker.
