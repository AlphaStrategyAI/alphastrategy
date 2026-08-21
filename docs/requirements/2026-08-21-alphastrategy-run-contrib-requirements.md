# alphastrategy Run sleeves name contribution last against next

**Date:** 2026-08-21
**Status:** Requirements (improvement cycle on v1)
**Repo:** `AlphaStrategyAI/alphastrategy`
**Parent contract:** [`2026-08-19-alphastrategy-v1-requirements.md`](2026-08-19-alphastrategy-v1-requirements.md) §5, §8
**Related:** [`2026-08-21-alphastrategy-sleeves-last-requirements.md`](2026-08-21-alphastrategy-sleeves-last-requirements.md), [`2026-08-21-alphastrategy-sleeves-weights-requirements.md`](2026-08-21-alphastrategy-sleeves-weights-requirements.md)
**Technical design:** [`docs/plans/2026-08-21-alphastrategy-run-contrib-technical-design.md`](../plans/2026-08-21-alphastrategy-run-contrib-technical-design.md)

Paper only. Five screens. Quiet cockpit **tokens unchanged**. No sixth nav tab. No live. No WebSockets. No chart library. Do not revive `static/app.js`. `"Gross cap"` must not appear in assembled JS. `renderBanners` keeps a **single** `const reason`. Do not retry leftover orders. Resume does not catch up. Resume does **not** seed. Heartbeat still does **not** flatten. GET must not flatten. GET must **not** evaluate DSL. Keep `Next rebalance`. Keep Caps **four tiles**. Keep Headroom **four tiles**. Keep Positions glance **Rows / Wanted / Got / At cap**. Keep After halt **Reason / Spent / Next / Resume**. Keep Run Sleeves tiles **Remaining / Spoken / Active / Idle**. Keep Roster columns and Sleeves columns. Keep `live_limit.kind` book / send / unknown. Do **not** overwrite Cash composition labels. Each JS part stays ≤ 400 lines. **Do not feed `_place_batch` from `live_book()`.** Keep exact Start hint waits-for-resume and seed-hold sentences. Keep `formatHaltBanner` maps. Keep `sleeveState` four words. Keep GET `/api/portfolio` `last_sleeve_weight_ids` (no `"last_sleeve_weights"` key). Keep `formatWeightsWaitSub`. Do **not** grow `paint-rails.js` / `paint-portfolio.js` past 400.

v1 §8 Run is the screen that **changes** allocation. Portfolio Sleeves already names contribution last against next (and weights wait). Run sleeve cards still show only an allocation rail plus forms. Remaining is a leftover percent with no rail. Activity `paper_start` rows are a bare bundle id even though the audit stores `allocation`. The operator who sets size cannot see what the next send will contribute without leaving Run, and the tape of that start does not name the size. That is not 凭直觉交互, 稳定执行, or 界面令人眼前一亮.

## 1. Why this increment exists

Goal check against current main (`b812caa`):

| Goal slice | v1 / later contract | Current desk |
| --- | --- | --- |
| 稳定执行 | Combined target is `alloc × last sleeve weights`. Run is the control that changes `alloc`. | Contribution lives only on Portfolio Sleeves. |
| 凭直觉交互 | Recognition: the control that changes contribution shows contribution. | Operator must Alt+1 to see names vs last. |
| 界面令人眼前一亮 | Remaining is the Run Sleeves hero. Utilization elsewhere is a rail. | Remaining is a number only. |
| 易于使用 | Activity is time-ordered start/stop as well as rebalance. | `paper_start` summary is the id only. |
| 风险可控 | GET does not eval DSL. Cards read glance maps already on `/api/portfolio`. | Unchanged; no new engine path. |

Research applied:

- **Size control shows the resulting book.** Blotters put proposed vs last next to the size field. Reuse `formatContributionInner` (same last/next/weights wait as Portfolio Sleeves). Do not duplicate a second weights sub on the card.
- **Remaining is leftover; the rail is spoken share.** Same grammar as Gross: fill = used (`spoken`) of cap `1`. The hero number stays `fmtPct(remaining)`.
- **Tape names the start size.** `paper_start` audit already has `allocation`. Summary uses `fmtPct`. Drill-in adds Allocation. Do not change `paper_stop` / `import` beyond keeping Bundle.

Out: GET flatten; DSL on GET; placing; seeding on resume; dumping weight maps; fifth Run tile; fifth sleeve state; live; sixth nav; CLI splitline changes.

## 2. Engine / API

No new endpoints. `paper_start` audit already records `bundle_id` and `allocation`. GET `/api/portfolio` already has `sleeve_contribution`, `last_sleeve_contribution`, `last_sleeve_weight_ids`.

## 3. Cockpit

`core.js`: extract `formatContributionInner(nextMap, lastMap, bundleId, alloc)` with the current cell body (weights wait, else next + optional `last ` sub). `formatContributionCell` wraps that inner in `<td class="nums">`. Portfolio call unchanged.

Run sleeve cards (`paint-run.js`): after the allocation rail, paint `formatContributionInner` from `state.portfolio` maps for that id (not a second `formatWeightsWaitSub`). Keep Stop / Kill / Set allocation. Keep four tiles.

Run Remaining: HTML `#run-remaining-bar` `util-track` under `#run-remaining`. `paintUtilTrack(bar, spoken, 1, "spoken " + fmtPct(spoken))`. Keep remaining warn when spoken ≥ 0.9 and < 1, fail when ≥ 1.

Activity `eventSummary` `paper_start`: `` `${ev.bundle_id || ""} ${fmtPct(ev.allocation)}`.trim() ``. `eventDetail` for `paper_start` adds Allocation as `fmtPct(ev.allocation)`. Keep `paper_stop` / `import` Bundle-only.

No `window.confirm`. No `window.state`. `"Gross cap"` not in JS. `renderRunStartHint` still has no `innerHTML`.

## 4. Help / README

Phrases (exact):

- `Run sleeves name contribution last against next`
- `Run Remaining is a rail`
- `Activity paper_start names allocation`

Add the first two to `how_run` after `Allocation is a rail.` Add the first to `cockpit` after `Run Sleeves is Remaining / Spoken / Active / Idle.`

Add the third to `how_activity` after `Activity halt rows name Start paper that cannot seed last weights holds.`

README Operator after `Sleeves names when a paper sleeve has no last weights.` Keep `Next rebalance`. Keep waits-for-resume. Keep Roster / Sleeves weights sentences.

## 5. In / out

**In:** `formatContributionInner`; Run card contribution; Remaining rail; Activity `paper_start` allocation; help/README.

**Out:** GET flatten; DSL on GET; placing; seeding; weight maps in JSON; fifth Run tile; CLI splitlines; live; sixth nav.

## 6. Verification

- JS: `formatContributionInner` used by the cell helper and Run cards; Run paints `run-remaining-bar` with `paintUtilTrack` and `spoken`; `paper_start` summary has `fmtPct(ev.allocation)`; drill-in Allocation; `"Gross cap"` not in JS.
- HTML `id="run-remaining-bar"` inside `#run-book`. Keep four Sleeves tiles. Five `#nav` screens.
- Help contains the three phrases.
- `PYTHONPATH=src python3 -m pytest tests/alphastrategy/ -q`
