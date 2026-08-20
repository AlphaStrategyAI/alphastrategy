# alphastrategy flattening crash recovery

**Date:** 2026-08-20
**Status:** Requirements (improvement cycle on v1)
**Repo:** `AlphaStrategyAI/alphastrategy`
**Parent contract:** [`2026-08-19-alphastrategy-v1-requirements.md`](2026-08-19-alphastrategy-v1-requirements.md)
**Technical design:** [`docs/plans/2026-08-20-alphastrategy-flattening-crash-technical-design.md`](../plans/2026-08-20-alphastrategy-flattening-crash-technical-design.md)

Paper only. Five screens. Quiet cockpit **tokens unchanged**. No sixth nav tab. No live. No WebSockets. No chart library. Resume still does **not** catch up. Do not revive `static/app.js`. Do not change the rebalancing-crash halt path.

This cycle closes the kill-switch hole that sits next to interrupted rebalancing: **host death while `state=flattening`**. `_flatten_account` already persists `FLATTENING` before `cancel_open_orders` / `close_all`. A kill of the process then leaves that snapshot on disk, and `tick` returns immediately, so the flatten never finishes.

## 1. Why this increment exists

Goal check against current main (`604b182`):

| Goal slice | v1 / later contract | Current desk |
| --- | --- | --- |
| 稳定执行 / 可靠 | §7 manual account kill / SIGTERM: if Alpaca reachable, cancel open orders and flatten the whole paper account. Host sleep/power-off stops the supervisor. | `_flatten_account` persists `flattening` first (good). `tick` treats `FLATTENING` like `STOPPED`: heartbeat only, no `close_all`. Restart shows flattening forever while names can still sit on the paper account. |
| 风险可控 | Flatten is the last kill-switch rung. A flatten that does not complete is not a control. | Operator typed `FLATTEN`. The book may still have qty. Risk Headroom / Positions can look live. |
| 凭直觉交互 | Flatten cannot look idle (execution honesty). Banners cannot be quiet. | After a host kill the desk can stick on `FLATTENING` with no second `close_all`, or look stopped only after a human kills again. |
| 易于维护 | One Supervisor, one snapshot JSON | Rebalancing crash already recovers on `__init__` / `reload_from_disk`. Flattening uses the same load hook, opposite action: finish the flatten, do not halt-and-hold. |

Research applied:

- **Retry the in-flight flatten.** Kill intent is already on disk. `close_all` on an empty book is the safe idempotent finish. Do not invent a second kill verb.
- **If the broker is unreachable, health-halt** (existing `_flatten_account` except path). Do not loop flatten on every heartbeat after that halt.
- **Do not flatten a `REBALANCING` snapshot.** That path health-halts. States are exclusive.

## 2. Recover `FLATTENING` on load

`Supervisor.__init__` and `reload_from_disk`, after interrupted-rebalance recovery: if `state == flattening`, call the same `_flatten_account` path used by account kill.

Success: `STOPPED`, last book cleared, sleeves zeroed, `flatten` audit, `close_all` ran.

Broker `cancel_open_orders` / `close_all` throw: existing health-halt reasons, no `close_all` success path. Positions may remain; the operator sees `HALTED`, not a silent `FLATTENING`.

## 3. Tick must not park on `FLATTENING`

After reload, if state is still `flattening` (recover missed, or a future caller persisted it without finishing), `tick` retries `_flatten_account` instead of returning as if the book were already flat.

`STOPPED` still heartbeats and returns. `HALTED` still heartbeats and returns.

## 4. Activity / help

A successful recovery writes the same `flatten` audit line Activity already paints.

Halt/flatten help: if the host dies while flattening, the desk treats that as **interrupted flattening**: it retries cancel and `close_all`. If the broker is unreachable it health-halts.

## 5. In / out

**In:** load of `FLATTENING` finishes flatten; `tick` retries flatten instead of parking; help phrase. Tests seed `flattening` on disk and simulate a host kill inside `close_all`.

**Out:** changing rebalancing-crash halt; catch-up rebalance; client-order ids; Clock / Positions / Risk tiles; live; WebSockets; `app.js`; sixth screen; SIGTERM handler rewrite (still goes through `_flatten_account` when reachable).

## 6. Verification

- Snapshot persisted as `flattening` with a live paper position: new `Supervisor` is `stopped`, `close_all` ran, positions empty, last book cleared.
- Account kill whose `close_all` raises a host-kill (not `Exception`): disk stays `flattening`; new `Supervisor` finishes flatten; no leftover qty.
- Existing flatten-clears-last-book and unreachable-flatten-halts tests still pass.
- Help contains `interrupted flattening`. `#nav` still five screens.
- No real broker orders.
