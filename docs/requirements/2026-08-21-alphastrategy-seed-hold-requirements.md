# alphastrategy Start paper that cannot seed last weights holds

**Date:** 2026-08-21
**Status:** Requirements (improvement cycle on v1)
**Repo:** `AlphaStrategyAI/alphastrategy`
**Parent contract:** [`2026-08-19-alphastrategy-v1-requirements.md`](2026-08-19-alphastrategy-v1-requirements.md) §5, §7, §8
**Related:** [`2026-08-21-alphastrategy-start-weights-requirements.md`](2026-08-21-alphastrategy-start-weights-requirements.md), [`2026-08-20-alphastrategy-start-held-requirements.md`](2026-08-20-alphastrategy-start-held-requirements.md)
**Technical design:** [`docs/plans/2026-08-21-alphastrategy-seed-hold-technical-design.md`](../plans/2026-08-21-alphastrategy-seed-hold-technical-design.md)

Paper only. Five screens. Quiet cockpit **tokens unchanged**. No sixth nav tab. No live. No WebSockets. No chart library. Do not revive `static/app.js`. `"Gross cap"` must not appear in assembled JS. `renderBanners` keeps a **single** `const reason`. Do not retry leftover orders. Resume does not catch up. Heartbeat still does **not** flatten. GET must not flatten. GET must **not** evaluate DSL. Keep `Next rebalance`. Keep Caps **four tiles**. Keep Headroom **four tiles**. Keep Positions glance **Rows / Wanted / Got / At cap**. Keep `live_limit.kind` book / send / unknown. Keep Book LIMIT rail. Do **not** overwrite Cash composition labels. Each JS part stays ≤ 400 lines. **Do not feed `_place_batch` from `live_book()`.** Keep `Start paper while halted waits for resume`. Keep `Start paper seeds last sleeve weights`. Keep overlay-on-start flatten. Illegal DSL / sandbox failure is **halt, not flatten**.

v1 §7: illegal DSL output and sandbox death are health halt (no new orders, do not flatten). Start paper now evaluates DSL on the write path to seed last sleeve weights. When that eval fails, the desk correctly HALTs and does not flatten — but Run Start hint still says only `Start paper while halted waits for resume`, CLI stderr prints the same held line, and POST `/api/paper/start` returns `{ok, held, flattened}` with no halt reason. The operator just pressed Start paper; the control replies as if the desk was already paused. That is not 凭直觉交互, 易于使用, or honest halt vs flatten.

## 1. Why this increment exists

Goal check against current main (`5687840`):

| Goal slice | v1 / later contract | Current desk |
| --- | --- | --- |
| 可靠 | Seed eval failure is a named health halt. | Halt reason is `no evaluator for sleeve …` with no Start paper tell. |
| 凭直觉交互 | The control that failed must name the failure. | Run hint / CLI held line are the already-halted resume sentence. |
| 风险可控 | Halt is not flatten. | close_all stays 0 (good) but the operator cannot tell seed-hold from stale-bars hold. |
| 易于使用 | Help: Start paper that cannot seed last weights holds. | Help only names seed success and halted-waits-resume. |

Research applied:

- **Name the write-path halt.** Prefix `_halt` with `start paper seeds last sleeve weights: ` so After halt, status, and Start hint share one tell. Do not flatten. Do not invent weights.
- **Keep already-halted copy exact.** Stale-bars + Start while HALTED still prints `Start paper while halted waits for resume. Resume does not catch up.`
- **POST returns halt_reason when held** so CLI stderr can choose the seed-hold line without a second GET.
- **Fail closed.** Missing evaluator / sandbox / illegal weights → held true, flattened false, `close_all` unchanged.

Out: GET flatten; DSL on GET; placing; rewriting last combined; changing wait-for-resume copy; live; sixth screen.

## 2. Engine / API

`_seed_last_sleeve_weights` on `HaltRequested` / `IllegalWeights`:

```text
_halt("start paper seeds last sleeve weights: " + str(exc))
```

Do not write weights. Do not flatten.

POST `/api/paper/start` 200:

```json
{"ok": true, "held": <bool>, "flattened": <bool>, "halt_reason": <str>}
```

Include `halt_reason` when `held` is true and the snapshot has a reason. Omit when not held. Keep 200. Do not 409.

CLI stderr when held:

- halt_reason contains `start paper seeds last sleeve weights` (case insensitive) → `held: start paper that cannot seed last weights holds. Resume does not catch up.`
- else keep exact `_HELD_START` (`held: start paper while halted waits for resume. Resume does not catch up.`).

Flatten still wins over held.

Fixture: imported `asb_z` with no evaluator; `POST /api/paper/start` allocation 0.18 → `held` true, `flattened` false, halt_reason contains both `start paper seeds last sleeve weights` and `asb_z`; `close_all` unchanged; sleeves[`asb_z`] == 0.18; last_sleeve_weights missing/empty.

Keep `test_start_while_halted_returns_held` (held true, flattened false, resume copy on CLI).
Keep `test_start_sleeve_halts_when_sleeve_has_no_evaluator` (extend halt_reason prefix).
Keep overlay flatten start tests.

## 3. Cockpit

`renderRunStartHint`: if halted and `halt_reason` contains `start paper seeds last sleeve weights`, warn copy `Start paper that cannot seed last weights holds. Resume does not catch up.` Else keep exact `Start paper while halted waits for resume. Resume does not catch up.` Keep flatten / idle sentences. No `innerHTML`. No `Order size` / `Gross cap` in JS.

Sleeve-card and `onStartSubmit` still read `started.held` / `started.flattened` (may also read `started.halt_reason`). Refresh still paints the hint from status.

## 4. Help / README

Phrase (exact): `Start paper that cannot seed last weights holds`

Add to `execution` (after Start paper seeds last sleeve weights), `halt_flatten` (same), `how_run` (after Start paper seeds last sleeve weights), `task_start` (after Start paper while halted). README Operator after Start paper seeds last sleeve weights. Keep `Start paper while halted waits for resume`. Keep `Start paper seeds last sleeve weights`. Keep `Next rebalance`.

## 5. In / out

**In:** halt_reason prefix on seed eval failure; POST `halt_reason` when held; Run hint + CLI seed-hold line; help/README; API + supervisor + JS + CLI tests.

**Out:** GET flatten; DSL on GET; placing; changing wait-for-resume copy; live; sixth nav.

**Done when:**

1. POST start `asb_z` with no evaluator → held, not flattened, halt_reason names start paper seeds last sleeve weights, `close_all` unchanged.
2. Run hint JS contains both the seed-hold sentence and the exact waits-for-resume sentence.
3. CLI seed-hold stderr uses the new held line; already-halted start still prints resume / catch up.
4. Help contains the phrase. Five `#nav` screens. `"Gross cap"` not in assembled JS. No real broker.
