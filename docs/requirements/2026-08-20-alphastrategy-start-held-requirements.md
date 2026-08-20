# alphastrategy Start paper while halted is held

**Date:** 2026-08-20
**Status:** Requirements (improvement cycle on v1)
**Repo:** `AlphaStrategyAI/alphastrategy`
**Parent contract:** [`2026-08-19-alphastrategy-v1-requirements.md`](2026-08-19-alphastrategy-v1-requirements.md) §5–§9
**Related:** [`2026-08-20-alphastrategy-halt-next-held-requirements.md`](2026-08-20-alphastrategy-halt-next-held-requirements.md), [`2026-08-20-alphastrategy-book-honesty-requirements.md`](2026-08-20-alphastrategy-book-honesty-requirements.md), [`2026-08-20-alphastrategy-flat-next-requirements.md`](2026-08-20-alphastrategy-flat-next-requirements.md)
**Technical design:** [`docs/plans/2026-08-20-alphastrategy-start-held-technical-design.md`](../plans/2026-08-20-alphastrategy-start-held-technical-design.md)

Paper only. Five screens. Quiet cockpit **tokens unchanged**. No sixth nav tab. No live. No WebSockets. No chart library. Do not revive `static/app.js`. `"Gross cap"` must not appear in assembled JS. `renderBanners` keeps a **single** `const reason`. Do not retry leftover orders. Resume does not catch up. Start paper after flatten starts the session loop again. Keep tutorial substring `Next rebalance`. Clock Next halted stays `held ·` / warn. Clock Next flattened stays `flat ·` / fail.

Halt-next-held marked Clock Next **held** while Supervisor is HALTED. Start paper on Run is still a primary action with no point-of-use copy. `start_sleeve` while `HALTED` records the allocation, stays HALTED, and does **not** leave halt (only `STOPPED` restarts the session loop). A halted tick returns before `_rebalance`. The operator can Start paper, see the sleeve on Inventory / Run, and still wait for **Resume after halt** plus the next *legal* window. That fights 凭直觉 and 稳定执行: the second explicit action looks like go.

## 1. Why this increment exists

Goal check against current main (`2bb30cf`):

| Goal slice | v1 / later contract | Current desk |
| --- | --- | --- |
| 稳定执行 | Halt: no new orders. Resume does not catch up. Halted tick does not rebalance. Import is not permission to trade; Start paper is the second explicit action. | `start_sleeve` while HALTED succeeds, stays HALTED, places nothing. Run Start paper never says so. |
| 凭直觉交互 | Nielsen: visibility of system status at the control. Clock Next is already `held ·`. After halt names the reason. | Start paper band is idle chrome plus a go button. Sleeve Stop has no “waits for next rebalance” at the button. |
| 可靠 | API and CLI are the same verbs as the cockpit. | `POST /api/paper/start` returns `{ok: true}` with no held flag. CLI `paper start` is silent. |
| 易于使用 | Help: Resume lives under After halt; Start paper after flatten restarts the loop. | Never says Start paper while halted waits for resume. |
| 易于维护 | One `start_sleeve` path for Web, CLI, and Set allocation. | Do not add a second start path or a 409. Return whether the book is held. |

Research applied:

- **Inhibit the next fire, do not refuse the allocation.** OMS desks still accept a working order while the session is held; they mark it **held**. Refusing Start paper with 409 would hide the sleeve and force the operator to re-enter allocation after resume.
- **Status at the control, not only in Help.** NN/g: put the constraint on the form that submits. After halt stays the resume control. Start paper stays the allocate control.
- **Do not merge Start paper into After halt.** Resume is halt-only. Start paper after flatten is a different restart. One persistent hint in Start paper switches copy; do not move the form.

Out of this cycle: refusing start during flatten (the lock already serializes; after flatten the STOPPED path is the documented restart). Sweeping staging on import. Changing crash-recovery actions. Changing Clock Next paint.

## 2. Engine

`Supervisor.start_sleeve(bundle_id, allocation) -> bool`

Keep today’s rules: imported bundle; allocation finite in `[0, 1]`; spoken sum `<= 1`; `STOPPED` primes the clock and leaves `STOPPED` for idle-in/out; persist + `paper_start` audit.

Return `True` when, **after** those transitions, `state == HALTED`. Return `False` otherwise (including after flatten restart).

Do **not** leave `HALTED`. Do **not** catch up. Do **not** 409 because halted.

A halted `tick` still returns before `_rebalance`. Changing allocation while halted must not place orders.

## 3. API / CLI

`POST /api/paper/start` success body:

```text
{"ok": true, "held": <bool>}
```

`held` is the `start_sleeve` return value. Existing 409 allocation-sum and 400 validation stay.

CLI `paper start`:

- Help / description: while halted waits for resume and does not catch up.
- On success, if `held`: print to **stderr**  
  `held: start paper while halted waits for resume. Resume does not catch up.`
- Exit 0 either way. Do **not** print JSON on stdout (status tests compose `paper start` then parse `status` stdout).
- Control-plane path reads `held` from the JSON body and uses the same stderr line.

## 4. Run paint

Persistent elements. Do **not** `innerHTML` the start form. Do **not** put these ids inside `#run-sleeves` (that list rebuilds).

| Id | Band | Idle copy | Halted | Flattened (`status.flattened` or state `flattening`/`stopped`) |
| --- | --- | --- | --- | --- |
| `#run-start-hint` | Start paper, inside the panel, after `#start-form`, before `#run-error` | muted: `Start paper is a second explicit action. Import is not permission to trade.` | class `warn`, copy `Start paper while halted waits for resume. Resume does not catch up.` | class `fail`, copy `Start paper after flatten starts the session loop again and does not catch up.` |
| `#run-stop-hint` | Sleeves, after the four tiles, before `#run-sleeve-error` | muted (always): `Stop zeros that sleeve on the next legal rebalance and does not flatten now.` | same | same |

Halt wins if a payload were both halted and flattened (they are distinct supervisor states).

`renderRunStartHint` / `renderRunStopHint` in `paint-run.js`. `refresh()` always calls both (like `renderRunRecover`), not gated on `runFormIsDirty()`. `textContent` + `className` only. No `innerHTML`.

CSS: `#run-start-hint.warn` uses `#f59e0b`. `#run-start-hint.fail` uses `#ef4444`.

Keep `#start-form`, `#run-error`, Confirm paper start, four Run bands, five `#nav` screens.

## 5. Help / README

`how_run`: Start paper while halted waits for resume. Resume does not catch up.

`task_start`: same sentence after the flatten restart sentence.

`REQUIRED_PHRASES`: `Start paper while halted waits for resume`.

README Operator: Start paper while halted waits for resume; Resume does not catch up.

Keep `Next rebalance`. Keep `"Gross cap"` in help (Risk labels), not in assembled JS.

## 6. In / out

**In:** `start_sleeve` returns held; API `held`; CLI help + stderr; Run start/stop hints; CSS; help/README; supervisor / API / CLI / HTML / JS / CSS / e2e tests.

**Out:** 409 on halt; resume catch-up; changing Clock Next; changing flatten recovery; live; sixth screen; `app.js`; printing start JSON on stdout.

**Done when:**

1. `start_sleeve` while HALTED returns `True`, stays HALTED, records allocation, and a following `tick` places no orders.
2. `POST /api/paper/start` while halted is 200 with `held: true`.
3. Assembled JS contains the halted start copy and `function renderRunStartHint`; HTML has `#run-start-hint` and `#run-stop-hint`; CSS maps warn/fail tokens.
4. Help contains `Start paper while halted waits for resume` and still contains `Next rebalance`.
5. Five `#nav` screens. `"Gross cap"` not in `js_text`. No real broker.
