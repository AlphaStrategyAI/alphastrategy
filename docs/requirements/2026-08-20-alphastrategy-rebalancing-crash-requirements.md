# alphastrategy rebalancing crash recovery

**Date:** 2026-08-20
**Status:** Requirements (improvement cycle on v1)
**Repo:** `AlphaStrategyAI/alphastrategy`
**Parent contract:** [`2026-08-19-alphastrategy-v1-requirements.md`](2026-08-19-alphastrategy-v1-requirements.md)
**Technical design:** [`docs/plans/2026-08-20-alphastrategy-rebalancing-crash-technical-design.md`](../plans/2026-08-20-alphastrategy-rebalancing-crash-technical-design.md)

Paper only. Five screens. Quiet cockpit **tokens unchanged**. No sixth nav tab. No live. No WebSockets. No chart library. Resume still does **not** catch up. Do not revive `static/app.js`. Do not retry remaining orders in the same `{date}:{open|close}` event (no idempotency keys in v1).

This cycle closes the gap torn rebalance left explicit: **host death mid-batch**. An in-process `place_order` exception now counts fills and health-halts. A kill of the process still leaves the on-disk snapshot idle, so the next start can fire the same session event again.

## 1. Why this increment exists

Goal check against current main (`70a8a3b`):

| Goal slice | v1 / later contract | Current desk |
| --- | --- | --- |
| 稳定执行 / 可靠 | §6 persist `last_rebalance_event` so an event cannot fire twice. §6 step 7: record targets, order ids, fills, deviations. Host sleep/power-off stops the supervisor. | `_rebalance` sets `REBALANCING` in memory and persists only in `tick` `finally` (or `_halt`). A SIGKILL after order 1 of 2 leaves disk at the pre-batch idle snapshot. The next `alphastrategy start` treats the open (or close) as unseen and places again. |
| 风险可控 | Daily order cap is a flatten trigger. Duplicate paper buys on a torn book are a control failure. | `orders_today` is not on disk until the tick ends. Restart under-counts the day and can send the same names twice. |
| 凭直觉交互 | Halt banners cannot be quiet. Activity records target vs fill. | After a host kill the desk can come back `IN SESSION` with a partial book and no incomplete rebalance line. |
| 易于维护 | One Supervisor, one snapshot JSON | Torn-rebalance honesty already shares `_place_batch`. Persist that in-flight snapshot; recover `REBALANCING` the same way as an in-process torn halt. |

Research applied (not a full OMS):

- **Persist intent before the first send** when the batch is non-empty: `state=rebalancing`, consume `{session_date}:{event}`, store wanted / prices, `rebalance_placed=0`.
- **Persist after each successful `place_order`:** `orders_today` and `rebalance_placed`. Do not wait for `tick` `finally`.
- **Do not retry the remainder.** v1 has no client-order ids. Crash recovery health-halts, same as a torn `place_order` throw.
- **Do not flatten.** Broker / host faults in §7 are halt. Flatten stays kill and limit breach.
- **FLATTENING crash** (persist flattening, then die before `close_all`) stays out: this cycle is the rebalance send path only.

## 2. Persist-before-send

After `plan_orders` returns a **non-empty** batch, before the first `place_order`:

1. `state = rebalancing`
2. `last_rebalance_event = {session_date}:{event}` (consume the window)
3. `rebalance_placed = 0`
4. `last_combined` / `last_prices` / sleeve maps already written for this tick stay on the snapshot
5. `_persist()`

A zero-order rebalance does not need an in-flight persist. It still writes `last_rebalance_event` and `complete: true` at the end as today.

## 3. Persist-after-ack

In `_place_batch`, after each successful `place_order` (rebalance and sleeve isolate):

1. Audit `order` (isolate still adds `reason: sleeve_kill`)
2. `orders_today = already + placed`
3. If `state` is `rebalancing`, `rebalance_placed = placed`
4. `_persist()`

## 4. Recover `REBALANCING` on load

`Supervisor.__init__` and `reload_from_disk`, after loading the snapshot: if `state == rebalancing`:

1. Snapshot `last_got` from current broker positions using persisted `last_combined` / `last_prices` (same formula as `_snapshot_got`). If the broker call fails, still halt; `last_got` may stay empty.
2. Audit `execution_deviation` rows from that snapshot when the gap exceeds `max($1, 0.1% equity)`.
3. Audit one `rebalance` line: `session_event` from `last_rebalance_event`, `orders=rebalance_placed`, `wanted`, `got`, `complete: false`.
4. Health-halt. Reason includes **interrupted rebalancing** and the placed count. Do not `close_all`.

A later tick in the same session must not place more orders for that event. Resume still does not catch up.

Old snapshot files without `rebalance_placed` load as `0`.

## 5. Activity / help

The recovery `rebalance` line is the same incomplete shape Activity already paints (`incomplete`, Complete `no`).

Execution help: if the host dies mid-rebalance, the desk treats that as **interrupted rebalancing**: it writes Wanted / Got from the broker, health-halts, and does not flatten or retry that event.

## 6. In / out

**In:** persist-before-send for a non-empty rebalance batch; persist-after each successful place; `rebalance_placed` on the snapshot; load of `REBALANCING` → incomplete audit + halt; help phrase. Tests with a mocked broker that crashes after the first fill, plus a probe that reads the state file during `place_order`.

**Out:** catch-up rebalance; idempotent retries of the remainder; client-order ids; crash recovery of `FLATTENING`; changing Clock / Positions / Risk tiles; live; WebSockets; `app.js`; sixth screen.

## 7. Verification

- Two-name open rebalance: on the first `place_order` the on-disk state is `rebalancing`, `last_rebalance_event` is `YYYY-MM-DD:open`, `orders_today` is still the pre-batch value. After a clean finish, disk is idle (not `rebalancing`) and `complete` is true.
- Two-name open rebalance, process dies after one fill: restart loads `halted`, `close_all` not called, `orders_today == 1`, `last_rebalance_event` set, `rebalance.complete is False`, `last_got` present, second tick places nothing.
- Happy path still counts `orders_today == len(orders)` and still audits wanted/got.
- Help contains `interrupted rebalancing`. `#nav` still five screens.
- No real broker orders.
