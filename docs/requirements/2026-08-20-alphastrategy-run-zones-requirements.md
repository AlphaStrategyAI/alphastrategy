# alphastrategy Run kill-switch zones

**Date:** 2026-08-20
**Status:** Requirements (improvement cycle on v1)
**Repo:** `AlphaStrategyAI/alphastrategy`
**Parent contract:** [`2026-08-19-alphastrategy-v1-requirements.md`](2026-08-19-alphastrategy-v1-requirements.md)
**Technical design:** [`docs/plans/2026-08-20-alphastrategy-run-zones-technical-design.md`](../plans/2026-08-20-alphastrategy-run-zones-technical-design.md)

Paper only. Five screens. Quiet cockpit **tokens unchanged**. No sixth nav tab. No live. No `window.confirm`. Control ids stay so painters keep working.

This cycle makes Run match the kill-switch ladder the engine already implements: start paper, size sleeves, resume after halt, and flatten the account are **different rungs**, not one “Account” panel.

## 1. Why this increment exists

Goal check against current main (`dcae9ad`):

| Goal slice | v1 / later contract | Current desk |
| --- | --- | --- |
| 风险可控 | §7 halt ≠ flatten; §8 Run: account kill is **separate and louder** | `#account-resume` sits in the same `.panel` as `#account-kill` + `FLATTEN`. Resume is a warn button next to flatten-all. |
| 凭直觉交互 | Nielsen 5 (error prevention); Gestalt proximity | Same panel ⇒ same family of actions. An operator leaving halt reaches for the amber button beside the red one. |
| 界面令人眼前一亮 | Portfolio already has Book / Flatten budgets / Clock bands | Run is still “Paper control” + a soup of sleeve cards + one Account box. |
| 易于使用 | Screen how-to already says start / stop / kill / resume | The how-to describes four jobs; the layout still shows two panels. |
| 稳定执行 | Resume does not catch up; kill flattens | Layout does not encode that difference. |
| 架构 / 帮助 | `app.js` still one file (out). F1 how-tos exist | Update `how_run` to name the four bands. Do not split `app.js` this cycle. |

Research applied (not a new kill ritual):

- **Kill-switch ladder** (operator runbooks / HFT Book): halt (hold), resume (re-enter the session loop), flatten (trade to flat) are separate rungs. The Supervisor already does that. The desk must look like it.
- **Nielsen heuristic 5:** do not place a recovery control next to an irreversible flatten in the same visual group.
- **Gestalt proximity:** group Start paper with the start form; group Flatten account with the `FLATTEN` ritual; keep After halt in its own band **above** flatten, never beside it (a two-column recover|flatten grid would recreate the bug).
- **Quiet cockpit:** reuse `glance-heading` / `glance-band`. Louder flatten = `#ef4444` border on that band’s panel only. No new tokens. No modal.

## 2. Four Run bands

Replace the Run screen’s two-panel stack with:

| id | heading | Contents (existing control ids) |
| --- | --- | --- |
| `#run-promote` | Start paper | `#start-form` (bundle, allocation, confirm, Start paper), `#run-error` |
| `#run-book` | Sleeves | `#run-sleeves` (unchanged card painters) |
| `#run-recover` | After halt | `#account-resume` only |
| `#run-flatten` | Flatten account | `#account-kill-confirm`, `#account-kill-phrase`, `#account-kill` |

Each band: `class="glance-band"` (flatten also `flatten-zone`), child `h2.glance-heading`, then the panel or `#run-sleeves`.

DOM order is the ladder: promote → sleeves → recover → flatten. Flatten is last. Do **not** put recover and flatten in one `.book-grid`.

Keep every existing control **id**. No `window.confirm`. Account kill still requires checkbox + typing `FLATTEN`. Resume still POSTs `/api/paper/resume` with no extra ritual (it is not flatten).

## 3. Louder flatten

CSS (locked tokens only):

- `.flatten-zone { margin-top: 1.25rem; }` — extra separation from After halt.
- `.flatten-zone .panel { border-color: #ef4444; }`
- `.flatten-zone .glance-heading { color: #ef4444; }`
- `.recover-zone .glance-heading { color: #f59e0b; }` (`#run-recover` also has `recover-zone`)

Start paper and Sleeves use the existing glance-heading color (`#9ba3b4`).

## 4. Help / README

`how_run`: Run is four bands Start paper, Sleeves, After halt, Flatten account. Resume lives under After halt. Account kill lives under Flatten account and still requires `FLATTEN`.

README Operator: same split.

## 5. In / out

**In:** four Run bands; resume isolated from flatten; louder flatten chrome; help/README; HTML/CSS/help tests; e2e GET `/` includes `run-flatten`.

**Out:** changing kill/resume API or Supervisor; `window.confirm`; sixth screen; new tokens; splitting `app.js`; putting recover and flatten side by side; renaming control ids.

## 6. Verification

- HTML ids `run-promote`, `run-book`, `run-recover`, `run-flatten`. Headings `Start paper`, `Sleeves`, `After halt`, `Flatten account`.
- `#account-resume` lives inside `#run-recover`. `#account-kill` lives inside `#run-flatten`. Resume is **not** in the flatten slice; kill is **not** in the recover slice.
- `#start-form` and `#run-error` live inside `#run-promote`. `#run-sleeves` inside `#run-book`.
- CSS `.flatten-zone` and `.recover-zone`. `#nav` still five screens. No `window.confirm`.
- Help contains `Flatten account`. GET `/` includes `id="run-flatten"`.
- No real broker orders.
