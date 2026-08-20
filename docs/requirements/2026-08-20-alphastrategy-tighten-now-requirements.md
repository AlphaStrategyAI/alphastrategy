# alphastrategy Tighten that breaches the live book flattens now

**Date:** 2026-08-20
**Status:** Requirements (improvement cycle on v1)
**Repo:** `AlphaStrategyAI/alphastrategy`
**Parent contract:** [`2026-08-19-alphastrategy-v1-requirements.md`](2026-08-19-alphastrategy-v1-requirements.md) §7–§8
**Related:** [`2026-08-20-alphastrategy-execution-honesty-requirements.md`](2026-08-20-alphastrategy-execution-honesty-requirements.md), [`2026-08-20-alphastrategy-start-held-requirements.md`](2026-08-20-alphastrategy-start-held-requirements.md)
**Technical design:** [`docs/plans/2026-08-20-alphastrategy-tighten-now-technical-design.md`](../plans/2026-08-20-alphastrategy-tighten-now-technical-design.md)

Paper only. Five screens. Quiet cockpit **tokens unchanged**. No sixth nav tab. No live. No WebSockets. No chart library. Do not revive `static/app.js`. `"Gross cap"` must not appear in assembled JS. `renderBanners` keeps a **single** `const reason`. Do not retry leftover orders. Resume does not catch up. Heartbeat still does **not** place orders and does **not** flatten. Keep tutorial substring `Next rebalance`. Start paper while halted still waits for resume.

v1 §7: a limit breach of account policy B (or a tighter overlay) is the same as account kill **if the broker is reachable**. `check_book` already flattens on gross / name weight / name count / long-only — but only inside `_rebalance`, against the **combined target**. `set_policy` and `PUT /api/risk` persist a tighter cap and wait for the next legal open/close. An operator can cut Gross cap below a 40% live book and keep those names until the close window (or forever, if HALTED). That is not 风险可控.

## 1. Why this increment exists

Goal check against current main (`9eb7106`):

| Goal slice | v1 / later contract | Current desk |
| --- | --- | --- |
| 风险可控 | Limit breach → flatten if reachable. Caps on Risk are flatten-critical. | Tighten only mutates `_policy` / `runtime.yaml`. Live book is not checked until the next `_rebalance`. Halted desks never reach that check. |
| 稳定执行 | Heartbeat does not place orders. Flatten is the kill-switch for caps. | Waiting for a scheduled rebalance to honor a cap the operator just wrote is a delayed control, not a skip of the 20s beat. |
| 凭直觉交互 | Tighten is the form that changes the cap. Nielsen: status at the control. | Tighten looks like a config save. The FLAT banner appears later, on another screen’s clock. |
| 易于使用 | Help: flatten banner names the breached cap. | Never says Tighten that already breaches the live book flattens **now**. |
| 易于维护 | One `check_book` for gross / name / names / long-only. | Reuse it on the live (got) map. Do not invent a second flatten matrix. |

Research applied:

- **Pre-trade vs post-trade controls.** A cap written by the operator is a new limit on the **current** book, not only on the next target. OMS desks flatten or reject when a working book is already over a newly tighter limit.
- **Do not flatten on the 20s heartbeat.** v1: heartbeat is health, not orders. Enforce on the explicit Tighten / `set_policy` / overlay PUT path only.
- **If unreachable, halt.** Same as other flatten rungs when cancel/`close_all` cannot run: health-halt, do not guess.

Out: checking drift on every heartbeat; changing `check_book` during rebalance (wanted stays); 409 on tighten; resume catch-up; Clock Next paint; Start paper 409.

## 2. Engine

After an account policy overlay is applied (`Supervisor.set_policy`), and after sleeve overlays are published to `runtime.yaml`, enforce:

1. If state is `flattening` or `stopped`, return (already flat / in-flight flatten).
2. Read live equity and positions. On broker failure: `_halt` with a tighten-live-book reason. Do not flatten.
3. Build a weight map:
   - If equity > 0 and `last_prices` can price at least one live qty: `qty * price / equity` (got).
   - Else `last_got` if non-empty.
   - Else `last_combined`.
4. `check_book(weights, equity, self._rebalance_policy())`.
5. On `FlattenRequested`: `_flatten_account(reason=exc.reason)` then `_record_kill` with `isolated=False`, `flattened=True`, `scope="account"`, that reason (same shape as a rebalance limit flatten).

Do **not** flatten because `min_delta_*` or order-budget keys tightened. Those are not `check_book` triggers.

Do **not** leave HALTED when the live book already breaches: limit flatten wins (v1 table).

`set_policy` stays tighten-only math. Enforcement is a second step on the same lock (`RLock`).

Public `enforce_live_book()` for the API sleeve-overlay path (runtime must be on disk so `_rebalance_policy` sees the new overlay). `set_policy` calls it internally.

## 3. API

`PUT /api/risk` after a successful overlay write:

```text
{"ok": true, "flattened": <bool>}
```

`flattened` is true when supervisor state is `flattening` or `stopped` after enforcement. Existing 400 loosen / validation stay.

Order: apply account `set_policy` (enforces with new account caps + **current** sleeve overlays) → write `runtime.yaml` → if a sleeves patch was present, `enforce_live_book()` again.

## 4. Risk paint

Persistent `#risk-tighten-hint` in the Tighten band, **after** the four tiles, **before** the panel that rebuilds `#risk-account-form`. Do not put it inside the form. Do not `innerHTML` that node.

Default copy (class `warn`, token `#f59e0b`): `Tighten that breaches the live book flattens now.`

HTML can hold that copy; JS need not rewrite it. CSS: `#risk-tighten-hint.warn { color: #f59e0b; }`.

`"Gross cap"` still must not appear in assembled JS.

## 5. Help / README

`how_risk` and `task_tighten`: Tighten that breaches the live book flattens now.

`halt_flatten` may repeat that sentence next to the existing limit-breach flatten copy.

`REQUIRED_PHRASES`: `Tighten that breaches the live book flattens now`.

README Operator: same.

Keep `Next rebalance`. Keep Start paper while halted waits for resume.

## 6. In / out

**In:** live-book enforce on `set_policy` and after sleeve overlay PUT; API `flattened`; Tighten hint; CSS; help/README; supervisor / API / HTML / CSS / help / e2e tests.

**Out:** heartbeat flatten; refusing tighten with 409; changing wanted `check_book` inside `_rebalance`; live; sixth screen; `app.js`; Clock Next; Start paper 409.

**Done when:**

1. Live book ~40% gross + `set_policy({max_gross: 0.1})` flattens immediately (`STOPPED`, `close_all`, kill reason `max_gross`) without waiting for a session event.
2. Tightening only `min_delta_dollar` with the same book does not flatten.
3. `PUT /api/risk` with a breaching cap returns `{ok: true, flattened: true}`.
4. HTML has `#risk-tighten-hint` with the phrase; CSS maps warn to `#f59e0b`.
5. Help contains the phrase and still contains `Next rebalance`.
6. Five `#nav` screens. `"Gross cap"` not in `js_text`. No real broker.
