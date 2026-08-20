# alphastrategy first paper session tutorial

**Date:** 2026-08-20
**Status:** Requirements (improvement cycle on v1)
**Repo:** `AlphaStrategyAI/alphastrategy`
**Parent contract:** [`2026-08-19-alphastrategy-v1-requirements.md`](2026-08-19-alphastrategy-v1-requirements.md)
**Technical design:** [`docs/plans/2026-08-20-alphastrategy-help-tutorial-technical-design.md`](../plans/2026-08-20-alphastrategy-help-tutorial-technical-design.md)

Paper only. Five screens. Quiet cockpit **tokens unchanged**. No sixth nav tab. No live. Help stays an aside. Do not revive `static/app.js`. Do not turn the lesson into a wizard that places orders.

This cycle adds the missing Diátaxis **tutorial** layer: a learning-oriented first paper session, distinct from job how-tos, screen maps, and runbook essays.

## 1. Why this increment exists

Goal check against current main (`c5a50b6`):

| Goal slice | v1 / later contract | Current desk |
| --- | --- | --- |
| 易于使用 | Diátaxis four kinds. `docs/index.md` already names the framework. | Help has **how-tos** (`TASK_HOWTOS`), **screen maps** (`SCREEN_HOWTOS`), **explanation** (`SECTIONS`). There is no tutorial. |
| 帮助文档 | A new operator needs a lesson that produces a first success. | F1 opens the current screen map plus jobs. CLI prints jobs first. A learner is handed work recipes. |
| 凭直觉交互 | Empty Portfolio CTA and Start paper are the two-step handoff. | The lesson that *uses* those surfaces is missing, so Help still feels like a runbook. |
| 界面令人眼前一亮 | Quiet tokens; lesson should look like a lesson. | Aside headings are all muted `#9ba3b4`. |

Research applied ([Diátaxis tutorials](https://diataxis.fr/tutorials/)):

- A tutorial is a **lesson**, not a how-to. Titles do **not** start with `How to`.
- Directions plus expected results (`You will see…`). Minimize theory. Halt-vs-flatten essays stay in the runbook.
- Every step must succeed without waiting for RTH. Do **not** require a live rebalance to finish the lesson.
- Do not flatten in this lesson. Resume is not part of this lesson.

## 2. Canonical tutorial

`helptext.py` `TUTORIALS` (one item in v1 of this cycle):

- `id`: `tutorial_first_session`
- `title`: `Your first paper session`
- `body`: numbered doing with expected results:

  1. `alphastrategy start` and open the Quiet cockpit. You will see empty Portfolio: Start this paper desk, then Book / Flatten budgets / Clock.
  2. Open Strategies (Alt+2). Under Import .asb upload a qualified file. You will see Inventory Imported count 1. You are not trading yet.
  3. Open Run (Alt+3). Under Start paper pick the bundle, set a small allocation, check Confirm paper start, then Start paper. You will see the sleeve on Run. Portfolio Clock shows Session and Next rebalance.
  4. Open Portfolio Positions. Empty rows until the next legal rebalance are expected. Book Drift stays an em dash or 0 until then.
  5. You finished the lesson when the sleeve is on Run and Clock shows Next rebalance. Do not use Flatten account in this lesson.

Keep `TASK_HOWTOS` titles starting with `How to`. Do not merge this lesson into a task.

## 3. Payload, CLI, aside

`help_payload()` adds `tutorials` (copy of `TUTORIALS`). Existing `howtos`, `tasks`, `sections` stay.

`help_text()` print order:

1. title
2. tutorials
3. tasks (How to jobs)
4. screen how-tos
5. runbook sections

Quiet cockpit aside, still not a sixth screen:

```html
      <div id="help-tutorial"></div>
      <div id="help-howto"></div>
      <div id="help-tasks"></div>
```

`#help-tutorial` is first, always painted (not filtered by screen). `renderHelp` fills it from `payload.tutorials`. Keep `#help-howto` / `#help-tasks` behavior.

CSS: `#help-tutorial h3 { color: #10b981; }` so the lesson heading uses the running token. `#help-panel h3` may stay muted for jobs and screen maps.

## 4. Help / README / docs index

Cockpit essay: F1 opens Help. Help starts with Your first paper session, then the screen how-to and the jobs for that screen.

README Quiet cockpit: `alphastrategy help` prints **Your first paper session** first, then How to jobs, then screen how-tos, then the runbook.

`docs/index.md` Start here: in-desk tutorial **Your first paper session**.

## 5. In / out

**In:** `TUTORIALS`; payload `tutorials`; CLI order; `#help-tutorial`; JS paint; green lesson heading; README/index/cockpit copy; tests.

**Out:** sixth screen; wizard/auto-trade; extra tutorials; changing TASK_HOWTOS ids; live; `app.js`.

## 6. Verification

- `GET /api/help` `tutorials[0].id == tutorial_first_session`; title is `Your first paper session` and does not start with `How to`.
- `help_text()` has that title **before** `How to import a qualified .asb`.
- HTML `#help-tutorial` is before `#help-howto`. `#nav` still five screens.
- JS `renderHelp` reads `payload.tutorials`.
- No real broker orders.
