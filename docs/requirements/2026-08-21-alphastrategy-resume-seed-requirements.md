# alphastrategy Resume does not seed last weights

**Date:** 2026-08-21
**Status:** Requirements (improvement cycle on v1)
**Repo:** `AlphaStrategyAI/alphastrategy`
**Parent contract:** [`2026-08-19-alphastrategy-v1-requirements.md`](2026-08-19-alphastrategy-v1-requirements.md) §7, §8
**Related:** [`2026-08-21-alphastrategy-seed-hold-requirements.md`](2026-08-21-alphastrategy-seed-hold-requirements.md), [`2026-08-21-alphastrategy-halt-names-requirements.md`](2026-08-21-alphastrategy-halt-names-requirements.md), [`2026-08-21-alphastrategy-after-halt-requirements.md`](2026-08-21-alphastrategy-after-halt-requirements.md)
**Technical design:** [`docs/plans/2026-08-21-alphastrategy-resume-seed-technical-design.md`](../plans/2026-08-21-alphastrategy-resume-seed-technical-design.md)

Paper only. Five screens. Quiet cockpit **tokens unchanged**. No sixth nav tab. No live. No WebSockets. No chart library. Do not revive `static/app.js`. `"Gross cap"` must not appear in assembled JS. `renderBanners` keeps a **single** `const reason`. Do not retry leftover orders. Resume does not catch up. Heartbeat still does **not** flatten. GET must not flatten. GET must **not** evaluate DSL. Keep `Next rebalance`. Keep Caps **four tiles**. Keep Headroom **four tiles**. Keep Positions glance **Rows / Wanted / Got / At cap**. Keep After halt **Reason / Spent / Next / Resume**. Keep `live_limit.kind` book / send / unknown. Keep Book LIMIT rail. Do **not** overwrite Cash composition labels. Each JS part stays ≤ 400 lines. **Do not feed `_place_batch` from `live_book()`.** Keep exact Start hint waits-for-resume and seed-hold sentences. Keep HALT banner `formatHaltBanner` for the seed prefix. Do **not** rewrite persisted `halt_reason` on the halt path. Resume still clears `halt_reason` and leaves HALTED (v1: resume is not catch-up). Do **not** call `_seed_last_sleeve_weights` from `resume()`.

v1 §7: Resume does not fire a catch-up rebalance. After #94–#96, Start paper seed failure is a named hold on Run, HALT, and status. The operator then presses Resume after halt — the control the desk just named. `resume()` correctly clears HALTED and `halt_reason`, and does not invent weights. After halt goes idle (`—`), Start hint returns to “Import is not permission to trade,” while paper sleeves still have no `last_sleeve_weights` and Caps LIMIT is `unknown`. The next rebalance health-halts as `no evaluator for sleeve …` without the Start paper prefix. That is not 可靠, 凭直觉交互, or honest halt vs “all clear.”

## 1. Why this increment exists

Goal check against current main (`fb34d4a`):

| Goal slice | v1 / later contract | Current desk |
| --- | --- | --- |
| 可靠 | Resume does not seed. Missing last weights stay visible. | After halt / Start hint go idle while Caps/Clock still wait. |
| 凭直觉交互 | The control that cannot seed (Resume) must say so. | Resume looks like it cleared the seed-hold. |
| 易于使用 | Activity halt rows use the same desk words as HALT. | Blotter dumps the engine string. |
| 风险可控 | Halt is not flatten. Resume does not place. | Unchanged; this increment is naming + glance, not orders. |

Research applied:

- **Do not re-seed on resume.** Inventing weights on Resume would catch up. Keep `resume()` as today.
- **Paint the remaining wait.** `live_limit.kind === "unknown"` is the same tell Caps and Clock Next already use. After halt and Start hint must use it after resume.
- **Map the second halt.** Rebalance `no evaluator for sleeve` is the same missing-weights failure after resume. `formatHaltBanner` maps it to desk words *after* the Start paper prefix check.

Out: GET flatten; DSL on GET; placing; seeding on resume; changing wait-for-resume copy; live; sixth screen.

## 2. Engine / API

No `resume()` schema change. Resume after seed-hold: state not halted, `halt_reason` None, sleeves still allocated, `last_sleeve_weights` still empty, GET `/api/status` `utilization.live_limit.kind` is `"unknown"`, `close_all` unchanged.

`formatHaltBanner` / CLI `_status_halt_line`:

1. `halt_reason` contains `start paper seeds last sleeve weights` → existing seed-hold desk words / `HALT: start paper that cannot seed last weights holds`
2. else contains `no evaluator for sleeve` → `resume does not seed last weights` / `HALT: resume does not seed last weights`
3. else existing raw reason

## 3. Cockpit

`renderRunStartHint` after flatten, before idle: if `utilization().live_limit.kind === "unknown"`, warn copy exact `Resume does not seed last weights. Start paper seeds last sleeve weights.` Keep halted / flatten / idle sentences. No `innerHTML`.

`renderRunRecover` when not (`halted` or `halt_reason`) and kind is `"unknown"`:

| Tile | Value |
| --- | --- |
| Reason | `weights` warn |
| Reason sub | `—` |
| Spent | unchanged spent-window rule |
| Next | `weights` warn |
| Resume | `—` |
| Hint | `Resume does not seed last weights. Start paper seeds last sleeve weights.` |

Halted / raw `halt_reason` still win over unknown. Idle copy stays `Resume is only after halt.` Keep `#account-resume`. No `innerHTML`.

Activity `eventSummary` halt: `formatHaltBanner(ev.reason, "halt")`. Drill-in Reason stays the engine `ev.reason` (sleeve id).

## 4. Help / README

Phrases (exact):

- `Resume does not seed last weights`
- `Activity halt rows name Start paper that cannot seed last weights holds`

Add the first to `execution` (after Start paper that cannot seed last weights holds), `halt_flatten` (after HALT names…), `how_run` (after After halt is four tiles), `task_start` (after Start paper that cannot seed last weights holds).

Add the second to `how_activity` (after Halt, deviation, and kill tiles are not quiet when above zero).

README Operator after After halt is four tiles. Keep `Next rebalance`. Keep waits-for-resume. Keep Start paper seeds last sleeve weights.

## 5. In / out

**In:** API lock that resume after seed-hold stays unknown LIMIT; After halt / Start hint paint unknown as weights; `formatHaltBanner` + status HALT map `no evaluator for sleeve`; Activity halt summary desk words; help/README.

**Out:** GET flatten; DSL on GET; placing; seeding on resume; changing wait-for-resume copy; live; sixth nav.

**Done when:**

1. POST start `asb_z` then POST resume → not halted, unknown LIMIT, no last weights, `close_all` unchanged.
2. Start hint and After halt JS contain `Resume does not seed last weights. Start paper seeds last sleeve weights.` and `kind === "unknown"`. Keep exact waits-for-resume and seed-hold sentences.
3. Activity halt summary calls `formatHaltBanner`; mapper maps `no evaluator for sleeve`.
4. `status` stderr for that reason prints `HALT: resume does not seed last weights`. Seed-prefix HALT line unchanged.
5. Help contains both phrases. Five `#nav` screens. `"Gross cap"` not in assembled JS. No real broker.
