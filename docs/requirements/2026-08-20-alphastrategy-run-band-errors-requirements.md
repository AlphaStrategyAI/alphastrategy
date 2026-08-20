# alphastrategy Run band-local errors

**Date:** 2026-08-20
**Status:** Requirements (improvement cycle on v1)
**Repo:** `AlphaStrategyAI/alphastrategy`
**Parent contract:** [`2026-08-19-alphastrategy-v1-requirements.md`](2026-08-19-alphastrategy-v1-requirements.md)
**Technical design:** [`docs/plans/2026-08-20-alphastrategy-run-band-errors-technical-design.md`](../plans/2026-08-20-alphastrategy-run-band-errors-technical-design.md)

Paper only. Five screens. Tokens unchanged. No sixth tab. No `window.confirm`. Kill/resume **API unchanged**.

Run already has four kill-switch bands. Errors still all paint into `#run-error` inside **Start paper**. After the spatial split, a refused `FLATTEN` appears at the top of the screen — Nielsen 1 (visibility of system status) fails at the point of use.

## 1. Why this increment exists

| Goal slice | After run-zones (`3bf18ed`) |
| --- | --- |
| 凭直觉交互 | Flatten is last and red; its error is still in Start paper. |
| 风险可控 | Operator typing `FLATTEN` cannot see why the click refused without scrolling up. |
| 易于使用 | Screen how-to names four bands; feedback is one shared box. |

Research: Nielsen 1 (status at the control); WCAG 3.3.1 error identification next to the field; Quiet cockpit: reuse `.error-box`, no toast, no modal.

## 2. Four error mounts

| Band | Error id | Used by |
| --- | --- | --- |
| Start paper | `#run-error` (existing) | start-form only |
| Sleeves | `#run-sleeve-error` | set allocation, stop, sleeve kill |
| After halt | `#run-recover-error` | `#account-resume` |
| Flatten account | `#run-flatten-error` | `#account-kill` (including missing `FLATTEN`) |

Each is `class="error-box hidden"`. Showing one **clears** the other three so a stale start error does not linger while flatten fails.

`app.js` helper `setRunError(band, message)` with band in `promote` | `sleeves` | `recover` | `flatten`.

## 3. Help

`how_run` one sentence: each Run band shows its own error.

## 4. In / out

**In:** four error mounts; `setRunError`; help; HTML/JS tests.

**Out:** API/Supervisor change; toasts; `window.confirm`; sixth screen; splitting `app.js` into modules.

## 5. Verification

- HTML: each error id in its band slice; `#run-flatten-error` not inside `#run-promote`.
- JS: `function setRunError`; account-kill handler uses `flatten`; account-resume uses `recover`; sleeve kill uses `sleeves`; start-form uses `promote`.
- No `window.confirm`. Five `#nav` screens.
- Help contains `own error`.
- No real broker orders.
