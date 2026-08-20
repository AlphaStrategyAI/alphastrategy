# alphastrategy sleeve-isolate crash recovery

**Date:** 2026-08-20
**Status:** Requirements (improvement cycle on v1)
**Repo:** `AlphaStrategyAI/alphastrategy`
**Parent contract:** [`2026-08-19-alphastrategy-v1-requirements.md`](2026-08-19-alphastrategy-v1-requirements.md) §7
**Related:** [`2026-08-19-alphastrategy-sleeve-kill-requirements.md`](2026-08-19-alphastrategy-sleeve-kill-requirements.md), [`2026-08-20-alphastrategy-rebalancing-crash-requirements.md`](2026-08-20-alphastrategy-rebalancing-crash-requirements.md), [`2026-08-20-alphastrategy-flattening-crash-requirements.md`](2026-08-20-alphastrategy-flattening-crash-requirements.md)
**Technical design:** [`docs/plans/2026-08-20-alphastrategy-isolate-crash-technical-design.md`](../plans/2026-08-20-alphastrategy-isolate-crash-technical-design.md)

Paper only. Five screens. Quiet cockpit **tokens unchanged**. No sixth nav tab. No live. No WebSockets. No chart library. Resume still does **not** catch up. Do not revive `static/app.js`. Do not retry the remaining isolate orders (no idempotency keys in v1). Do not change interrupted-rebalancing halt or interrupted-flattening retry.

This cycle closes the kill-switch hole next to those two: **host death during an isolated sleeve kill**. In-process `place_order` exceptions already fall back to whole-account flatten. A SIGKILL after the first isolate fill leaves the other sleeves on a torn residual with no in-flight marker.

## 1. Why this increment exists

Goal check against current main (`808a476`):

| Goal slice | v1 / later contract | Current desk |
| --- | --- | --- |
| 稳定执行 / 可靠 | §7 sleeve kill: flatten that sleeve’s implied positions; **if that cannot be isolated cleanly, flatten whole account rather than guess**. Sleeve-kill §3.7: if `place_order` raises, fallback flatten; do not leave a half-applied residual. | `_place_batch` now persists `orders_today` after each fill, but isolate does not persist an in-flight marker. Restart looks idle. The killed sleeve may already be allocation 0 in memory only; the surviving sleeve’s book can be a one-leg residual. |
| 风险可控 | Flatten is the last rung when isolation is not clean. | A torn isolate is a guess. The surviving sleeve still looks paper-live. |
| 凭直觉交互 | Sleeve kill reports whether isolation succeeded or the account was flattened. | After a host kill the desk can come back `IN SESSION` with a partial sleeve-kill book and `last_kill` still showing the previous outcome. |
| 易于维护 | One snapshot JSON, same load-hook family | Rebalancing crash → halt. Flattening crash → finish flatten. Isolate crash → **fallback flatten** (not halt, not retry isolate). |

Research applied:

- **Do not finish the residual.** Same rule as torn rebalance: no client-order ids, do not send the remainder.
- **Do not halt-and-hold.** Sleeve kill already chose flatten-the-sleeve. A torn isolate is “not clean” → account flatten, matching §7 and sleeve-kill §3.7.
- **Persist intent before the isolate send** so a crash after `cancel_open_orders` is visible on disk.

## 2. In-flight isolate marker

On `SupervisorSnapshot`: `isolate_in_flight: str | null` (bundle id). Old files load as `null`.

At the start of `_isolate_sleeve`, before `cancel_open_orders` / `_place_batch`:

1. `isolate_in_flight = bundle_id`
2. `_persist()` (also writes the allocation-0 / `stopped` mutation already in memory)

On successful isolate: `isolate_in_flight = null` before the caller persists the isolated `KillOutcome`.

`_flatten_account` always sets `isolate_in_flight = null` so a finished account flatten cannot be re-read as a torn isolate.

## 3. Recover on load

`Supervisor.__init__` and `reload_from_disk`, after interrupted-rebalance and interrupted-flatten recovery: if `isolate_in_flight` is a non-empty bundle id:

1. Remember the id, then `_flatten_account()` (same cancel + `close_all` path as account kill).
2. Audit `kill` with `bundle_id`, `isolated: false`.
3. `last_kill` reason `fallback_interrupted`. Scope `account`. Flattened true.

A later tick must not place more isolate remainder orders. Other sleeves are stopped with the account.

In-process `place_order` `Exception` still uses existing `fallback_error` flatten. Host-kill (`BaseException` that `except Exception` does not catch) uses this load recovery.

## 4. Help

Halt/flatten help: if the host dies during a sleeve isolate, the desk treats that as **interrupted sleeve isolate**: it flattens the whole paper account rather than guess the residual.

## 5. In / out

**In:** `isolate_in_flight` persist-before-isolate; load recovery flattens the account; `last_kill.reason=fallback_interrupted`; help phrase. Tests: two sleeves, two-name isolate batch, host-kill after the first isolate fill, new Supervisor flattens.

**Out:** retrying the residual; changing isolation math; changing rebalancing-crash halt; changing flattening-crash retry; Clock / Positions / Risk tiles; live; WebSockets; `app.js`; sixth screen.

## 6. Verification

- Two sleeves, last book exists, isolate of a two-name sleeve, process dies after one isolate fill: disk has `isolate_in_flight`; restart is `stopped`, `close_all` ran, positions empty, `last_kill.reason == fallback_interrupted`.
- Happy isolated kill still does not call `close_all` and does not leave `isolate_in_flight` on disk.
- Help contains `interrupted sleeve isolate`. `#nav` still five screens.
- No real broker orders.
