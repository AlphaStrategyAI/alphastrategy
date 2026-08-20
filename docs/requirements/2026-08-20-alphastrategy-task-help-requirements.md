# alphastrategy task-shaped operator how-tos

**Date:** 2026-08-20
**Status:** Requirements (improvement cycle on v1)
**Repo:** `AlphaStrategyAI/alphastrategy`
**Parent contract:** [`2026-08-19-alphastrategy-v1-requirements.md`](2026-08-19-alphastrategy-v1-requirements.md)
**Technical design:** [`docs/plans/2026-08-20-alphastrategy-task-help-technical-design.md`](../plans/2026-08-20-alphastrategy-task-help-technical-design.md)

Paper only. Five screens. Quiet cockpit **tokens unchanged**. Help stays an **aside**, never a sixth `#nav` tab. No live. No in-app search. Canonical runbook `SECTIONS` and `SCREEN_HOWTOS` stay.

This cycle makes Help answer **jobs** (import, start paper, flatten, tighten, read wanted vs got), not only “On &lt;screen&gt;”.

## 1. Why this increment exists

Goal check against current main (`56f0545`):

| Goal slice | Contract / research | Current desk |
| --- | --- | --- |
| 易于使用 | Nielsen 10: help is **task**-focused, short, concrete steps | F1 is “On Portfolio / On Run …”. That is a map of chrome, not a job. `alphastrategy help` prints those maps first. |
| 凭直觉交互 | Diátaxis **how-to** is goal-oriented (“how to flatten”), not machinery-oriented (“On Run”) | Screen how-tos describe bands. The operator’s work is import → start → rebalance → tighten / flatten. |
| 帮助文档 | Operator-help + screen-help cycles: argparse is reference; aside + `alphastrategy help` are how-to | Two layers exist (screen how-to + six essays). The missing layer is the job list. |
| 风险可控 | Halt ≠ flatten; tighten only | Flatten and tighten steps live inside “On Run” / “On Risk” paragraphs, not as named jobs. |
| 架构 | `helptext.py` is the single source | Add `TASK_HOWTOS` there. Do not copy jobs into `app.js`. Do not revive `static/app.js`. |

Research applied:

- **Diátaxis how-to guides:** written from the user’s project, a sequence of actions, not a tour of the UI. “How to import a qualified .asb” is a how-to. “On Strategies” is not.
- **Nielsen heuristic 10 / NN/g contextual help:** F1 still opens on the current screen, then shows the jobs that apply there. The six essays stay behind Full runbook.
- **Stocktrader workstation:** Help remains a non-modal aside. No modal over halt/flatten banners.

## 2. Task how-tos (Python source of truth)

Add `TASK_HOWTOS` in `alphastrategy.helptext`. Each item: `id`, `screens` (list of nav ids), `title`, `body`. Titles start with **How to**. Bodies are numbered steps in one string.

| id | title | `screens` | Job |
| --- | --- | --- | --- |
| `task_import` | How to import a qualified .asb | `strategies` | Upload under Import .asb; failures name the gate; import is not permission to trade. |
| `task_start` | How to start a paper sleeve | `strategies`, `run` | Second explicit action under Start paper (Alt+3). |
| `task_flatten` | How to flatten the paper account | `run` | Flatten account band, checkbox + type `FLATTEN`. Halt is not flatten. Resume does not catch up. |
| `task_tighten` | How to tighten a cap | `risk` | Tighten groups Gross / Names / Orders / Deltas; looser values refused. |
| `task_wanted` | How to read wanted versus got | `portfolio`, `activity` | Positions columns + Activity blotter Wanted / Got table, not a JSON dump. |

`help_payload()` grows `"tasks"` and **keeps** `"howtos"` and `"sections"`.

`help_text()` print order: **tasks**, then screen how-tos, then the six runbook sections.

## 3. Quiet cockpit

Aside order:

1. `#help-howto` — current screen how-to (unchanged).
2. `#help-tasks` — every `TASK_HOWTOS` item whose `screens` contains the active `data-screen`. Title + body. Re-paint on screen change (same `renderHelp`).
3. `<details id="help-runbook">` — six essays (unchanged).

No sixth nav tab. Fetch errors still paint on `#help-howto`.

## 4. Help / README

Cockpit essay: F1 shows the screen how-to **and the jobs for that screen**.

README: `alphastrategy help` prints How-to jobs first. F1 lists jobs for the current screen.

## 5. In / out

**In:** `TASK_HOWTOS`; payload `tasks`; CLI order; `#help-tasks`; help/README; unit/API/e2e tests.

**Out:** sixth screen; in-app search; rewriting `SCREEN_HOWTOS` or `SECTIONS` ids; new tokens; live; copying job copy into JS strings.

## 6. Verification

- `TASK_HOWTOS` ids: `task_import`, `task_start`, `task_flatten`, `task_tighten`, `task_wanted`.
- `help_payload()["tasks"]` matches. `howtos` / `sections` ids unchanged.
- `help_text()` contains `How to import a qualified .asb` **before** `On Portfolio`.
- HTML `id="help-tasks"`. `#nav` still five screens.
- GET `/api/help` includes `tasks[0].id == task_import`. GET `/` includes `help-tasks`.
- Assembled JS paints `payload.tasks` into `#help-tasks` filtered by `item.screens`.
- No real broker orders.
