# alphastrategy interrupt glance

**Date:** 2026-08-20
**Status:** Requirements (improvement cycle on v1)
**Repo:** `AlphaStrategyAI/alphastrategy`
**Parent contract:** [`2026-08-19-alphastrategy-v1-requirements.md`](2026-08-19-alphastrategy-v1-requirements.md)
**Related:** [`2026-08-20-alphastrategy-kill-outcome-requirements.md`](2026-08-20-alphastrategy-kill-outcome-requirements.md), [`2026-08-20-alphastrategy-rebalancing-crash-requirements.md`](2026-08-20-alphastrategy-rebalancing-crash-requirements.md), [`2026-08-20-alphastrategy-isolate-crash-requirements.md`](2026-08-20-alphastrategy-isolate-crash-requirements.md)
**Technical design:** [`docs/plans/2026-08-20-alphastrategy-interrupt-glance-technical-design.md`](../plans/2026-08-20-alphastrategy-interrupt-glance-technical-design.md)

Paper only. Five screens. Quiet cockpit **tokens unchanged**. No sixth nav tab. No live. No WebSockets. No chart library. Resume still does **not** catch up. Do not revive `static/app.js`. Do not change crash-recovery actions (halt vs flatten vs retry flatten).

This cycle makes host-interrupt outcomes **visible** on the desk. The engine already health-halts a torn rebalance, finishes a torn flatten, and account-flattens a torn sleeve isolate. The operator can still miss the fork: After halt is only a button, and `#kill-outcome-banner` never paints `fallback_interrupted`.

## 1. Why this increment exists

Goal check against current main (`3f75be9`):

| Goal slice | v1 / later contract | Current desk |
| --- | --- | --- |
| 凭直觉交互 | §8 halt/deviation banners cannot be quiet. Kill-outcome: after a kill, show **which** branch ran. | Halt banner dumps `halt_reason` (so “interrupted rebalancing after N orders” can appear). After halt on Run does not repeat it. `fallback_interrupted` is stored on `last_kill` and **hidden** — the kill-outcome table never named that reason. |
| 风险可控 | Sleeve isolate that is not clean flattens the account. | Flatten banner says `FLAT: paper account flattened` with no sleeve-isolate interrupt copy. Operator can think they flattened on purpose. |
| 易于使用 | Run how-to: Resume lives under After halt and does not catch up. | The band does not say why resume exists right now. |
| 稳定执行 | Resume does not catch up after halt. | Correct in the engine; the control does not show the halt that resume will not catch up from. |

Research applied:

- **Visibility of system status:** the three interrupt recoveries are consequential forks. Paint them where the operator already looks (desk banners, After halt, Activity kill row).
- **Do not add a sixth screen or a new banner id.** Extend `#kill-outcome-banner` and put one mount in `#run-recover`.

## 2. Kill-outcome banner

Add a row to the existing `#kill-outcome-banner` table (account kill stays hidden there; flatten banner still covers `reason=account`):

| last_kill.reason | class | text |
| --- | --- | --- |
| `fallback_interrupted` | `banner fail` | `SLEEVE KILL: interrupted sleeve isolate — whole paper account flattened` |

Keep the existing rows for `isolated`, `fallback_not_ready` / `fallback_error`, `unknown_sleeve`.

## 3. After halt reason

Inside `#run-recover` (not inside Flatten account), a persistent mount `#run-halt-reason` (do **not** `innerHTML` the recover panel; keep `#account-resume` and `#run-recover-error`).

Paint:

| Condition | class | text |
| --- | --- | --- |
| `status.halted` or a non-empty `halt_reason` | `warn` | the halt reason string (same source as `#halt-banner`) |
| else | `muted` | `Resume is only after halt.` |

Call this paint on every refresh, even when the sleeve allocation form is dirty.

## 4. Activity kill row

The interrupted-isolate recover audit already writes `kill` with `isolated: false`. Include `reason: fallback_interrupted` on that audit line.

Activity `eventSummary` for `kill`: when `ev.reason === "fallback_interrupted"`, summary includes `interrupted sleeve isolate`. Other kill rows stay isolated residual / flattened account.

## 5. Help

`how_run`: After halt shows the halt reason. Resume still does not catch up.

Do not change the five-screen nav. Do not change crash-recovery Supervisor actions except the recover `kill` audit field above.

## 6. In / out

**In:** kill-outcome row for `fallback_interrupted`; `#run-halt-reason`; recover `kill` audit `reason`; Activity copy; help. Tests on HTML/JS/help; existing isolate-crash test still passes.

**Out:** new Supervisor states; changing halt vs flatten matrix; Clock / Positions / Risk tiles; live; WebSockets; `app.js`; sixth screen; `window.confirm`; wiping `#run-recover` with `innerHTML`.

## 7. Verification

- JS kill-outcome paint contains `fallback_interrupted` and `interrupted sleeve isolate — whole paper account flattened`.
- `#run-halt-reason` lives in the After halt slice, not Flatten account. Recover error id stays. JS paints halt reason from `status.halt_reason` / `status.halted`.
- Activity kill branch contains `fallback_interrupted` and `interrupted sleeve isolate`.
- Help contains `After halt shows the halt reason`. `#nav` still five screens. No `Gross cap` in JS. No `window.confirm`.
- No real broker orders.
