# alphastrategy Run-screen sleeve controls

**Date:** 2026-08-20
**Status:** Requirements (improvement cycle on v1)
**Repo:** `AlphaStrategyAI/alphastrategy`
**Parent contract:** [`2026-08-19-alphastrategy-v1-requirements.md`](2026-08-19-alphastrategy-v1-requirements.md)
**Technical design:** [`docs/plans/2026-08-20-alphastrategy-run-sleeve-controls-technical-design.md`](../plans/2026-08-20-alphastrategy-run-sleeve-controls-technical-design.md)

This document does **not** change product identity. Paper only. No sixth nav screen. No Supervisor kill/flatten behavior change. Risk tightening stays on the Risk screen (do not clone those forms onto Run).

It closes the remaining v1 §8 Run-screen gap: **per sleeve, set allocation**, and makes sleeve kill follow Nielsen heuristic 5 (confirmation before a high-cost flatten) without matching the louder account-kill `FLATTEN` ritual.

## 1. Why this increment exists

| v1 / operator need | Current Run screen |
| --- | --- |
| §8 Run: per sleeve **set allocation**, explicit confirm to start paper | One global Start form. Sleeve cards show allocation as text. |
| §8 Kill flattens per §7; account kill is separate and **louder** | Sleeve **Kill** POSTs on the first click. Account kill already requires checkbox + `FLATTEN`. |
| Operator-desk dirty-form rule (Risk) | `renderRunSleeves` rebuilds on every 5s poll. Adding inputs without a dirty skip would wipe in-progress allocation. |

Research (applied, not copied):

- **Nielsen heuristic 5 (Error Prevention):** present a confirmation option before an irreversible flatten. Sleeve kill is quieter than account kill, but it is still a flatten (isolated residual or whole-account fallback). A checkbox is enough. Do not use `window.confirm` (stocktrader workstation: no overlapping dialogs over the blotter).
- **Nielsen heuristic 3 (User control):** allocation is how the operator sizes a running alpha sleeve. It belongs on the sleeve card, not only on a global form that looks like “first start”.
- Kill-switch literature: flatten remains a human decision. Account `FLATTEN` stays the loud ritual. Sleeve kill must not skip confirmation entirely.

## 2. Positioning walls (unchanged)

All v1 hard walls remain. Five Quiet cockpit screens remain. Help stays an aside. Supervisor `start_sleeve` / `kill_sleeve` semantics stay as they are: Set allocation is `POST /api/paper/start` (already replaces allocation and clears `stopped`). Kill is `POST /api/paper/kill` with `bundle_id`.

## 3. Per-sleeve allocation

Each sleeve card on Run includes:

1. Number input `name="allocation"` (0–1, step 0.01), current allocation as the displayed value, `data-current` equal to that value.
2. Checkbox labelled **Confirm paper allocation**.
3. Submit **Set allocation**.

Submit POSTs `/api/paper/start` with `{bundle_id, allocation}` only if the checkbox is checked. Otherwise show `#run-error`: `Confirm paper allocation required`. The global Start form at the top of Run remains (first promote). Cards cover resize of an already listed bundle.

The 5s poll must **not** rebuild `#run-sleeves` while a Run card is dirty: focus inside the container, a checked confirm/kill checkbox, or an allocation value different from `data-current`. Same idea as `riskFormIsDirty`.

## 4. Sleeve kill confirmation

Each sleeve card’s Kill button requires a checkbox labelled **Confirm sleeve kill** (`data-kill-confirm="<bundle_id>"`). Unchecked click shows `#run-error`: `Confirm sleeve kill`. It must **not** call `window.confirm` and must **not** require typing `FLATTEN` (that phrase stays account-only).

Stop stays one click (it waits for the next rebalance; it is not flatten).

## 5. In / out

**In:** per-card allocation + confirm; dirty skip; sleeve-kill checkbox; tests on static JS/HTML and existing start/kill API.

**Out:** Risk-form clone on Run; changing `kill_sleeve` isolation rules; CLI `--yes`; live; sixth screen; modal dialogs.

## 6. Verification

- JS contains `sleeve-alloc-form`, `runFormIsDirty`, `data-kill-confirm`, `Confirm paper allocation`, `Confirm sleeve kill`.
- JS does not contain `window.confirm`.
- `#nav` still exactly five screens.
- `POST /api/paper/start` still replaces allocation (existing test).
- No real broker orders.
