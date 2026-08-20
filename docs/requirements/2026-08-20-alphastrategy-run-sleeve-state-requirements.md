# alphastrategy Run sleeve cards name imported / paper / halted / stopped

**Date:** 2026-08-20
**Status:** Requirements (improvement cycle on v1)
**Repo:** `AlphaStrategyAI/alphastrategy`
**Parent contract:** [`2026-08-19-alphastrategy-v1-requirements.md`](2026-08-19-alphastrategy-v1-requirements.md) §8
**Related:** [`2026-08-20-alphastrategy-strategies-inventory-requirements.md`](2026-08-20-alphastrategy-strategies-inventory-requirements.md), [`2026-08-20-alphastrategy-run-sleeve-controls-requirements.md`](2026-08-20-alphastrategy-run-sleeve-controls-requirements.md), [`2026-08-20-alphastrategy-start-held-requirements.md`](2026-08-20-alphastrategy-start-held-requirements.md)
**Technical design:** [`docs/plans/2026-08-20-alphastrategy-run-sleeve-state-technical-design.md`](../plans/2026-08-20-alphastrategy-run-sleeve-state-technical-design.md)

Paper only. Five screens. Quiet cockpit **tokens unchanged**. No sixth nav tab. No live. No WebSockets. No chart library. Do not revive `static/app.js`. `"Gross cap"` must not appear in assembled JS. `renderBanners` keeps a **single** `const reason`. Do not clone Risk tighten forms onto Run. Do not change `start_sleeve` / Stop / Kill semantics. Keep Start paper while halted waits for resume. Keep Tighten live-book flatten.

Strategies Roster already paints `imported` / `paper` / `halted` / `stopped` via `sleeveState`. Run is the screen that **changes** those states (Set allocation, Stop, Kill), but each sleeve card is only an `h3` plus forms. Active / Idle tiles count allocation, not the four v1 states. A halted paper sleeve looks the same as a running one except the Start paper hint two bands away. That fights 凭直觉 and 界面令人眼前一亮.

## 1. Why this increment exists

Goal check against current main (`9d89a0e`):

| Goal slice | v1 / later contract | Current desk |
| --- | --- | --- |
| 凭直觉交互 | §8 Run: per sleeve set allocation, Stop, Kill. Strategies four states. Start paper while halted is held. | Cards do not name the state the operator is about to change. |
| 界面令人眼前一亮 | Quiet cockpit: dense numbers, sparse chrome. Risk overlay cards are allocation rail then action. | Run cards are generic forms. No rail. No status color. |
| 稳定执行 | Halted allocation waits for resume. Stop waits for the next legal rebalance. | The card that submits those verbs does not say halted vs stopped. |
| 易于使用 | Help: Sleeves is Remaining / Spoken / Active / Idle. | Never says each card names imported / paper / halted / stopped. |
| 易于维护 | One `sleeveState` helper. | Reuse it. Do not invent a fifth state word. Never paint `Live` as a sleeve state. |

Research applied:

- **Recognition over recall.** The same four words as Strategies Roster. Do not invent “active/idle” on the card (those stay the band tiles).
- **Glance then action.** Overlay cards: rail, then form. Run cards: state + rail, then Set allocation / Stop / Kill.
- **Do not clone Risk.** Tighten stays on Risk. Run cards do not grow overlay forms.

## 2. Paint

In `renderRunSleeves`, for each card:

1. Call `sleeveState(id, bundles, state.status)`.
2. Map class like Strategies Roster: `paper` → `status-running`, `halted` → `status-halt`, `stopped` → `status-stopped`, `imported` → `muted`.
3. Header row: bundle id + a `span.sleeve-state` with that class and the state word (`imported` / `paper` / `halted` / `stopped`).
4. Allocation rail: an empty `.util-track`, then `paintUtilTrack(track, alloc, 1, "allocation " + fmtPct(alloc))` — same as overlay cards.
5. Existing allocation form, Stop, Confirm sleeve kill, Kill sleeve stay. Keep `sleeve-alloc-form`, `data-kill-confirm`, dirty skip.

Do not put `"Gross cap"` in JS. Do not use `>Live<` as a state label. Do not `innerHTML` `#run-start-hint` / `#run-stop-hint`.

CSS: `.sleeve-head` is a horizontal row (id + state). `.sleeve-card .util-track` has a little vertical gap under the head. Reuse existing status token colors. Optional `.status-muted { color: #5c6573 }` so imported matches `.muted`.

`paint-run.js` stays ≤ 400 lines.

## 3. Help / README

`how_run`: Each sleeve card names imported, paper, halted, or stopped. Allocation is a rail.

`REQUIRED_PHRASES`: `Each sleeve card names imported, paper, halted, or stopped`.

README Run: sleeve cards name imported / paper / halted / stopped; allocation is a rail.

Keep `Next rebalance`. Keep Start paper while halted waits for resume.

## 4. In / out

**In:** Run card state + rail; CSS; help/README; JS/CSS/help tests.

**Out:** API/Supervisor changes; cloning Risk; changing Stop/Kill; live; sixth screen; `app.js`; `Live` as a sleeve label.

**Done when:** assembled JS `renderRunSleeves` (before `renderRunStartHint`) contains `sleeveState` and `paintUtilTrack`; help contains the phrase; five `#nav` screens; `"Gross cap"` not in `js_text`; no real broker.
