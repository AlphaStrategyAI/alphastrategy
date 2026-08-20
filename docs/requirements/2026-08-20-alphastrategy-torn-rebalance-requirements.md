# alphastrategy torn rebalance honesty

**Date:** 2026-08-20
**Status:** Requirements (improvement cycle on v1)
**Repo:** `AlphaStrategyAI/alphastrategy`
**Parent contract:** [`2026-08-19-alphastrategy-v1-requirements.md`](2026-08-19-alphastrategy-v1-requirements.md)
**Technical design:** [`docs/plans/2026-08-20-alphastrategy-torn-rebalance-technical-design.md`](../plans/2026-08-20-alphastrategy-torn-rebalance-technical-design.md)

Paper only. Five screens. Quiet cockpit **tokens unchanged**. No sixth nav tab. No live. No WebSockets. No chart library. Resume still does **not** catch up. Do not revive `static/app.js`. Do not retry the remaining orders in the same `{date}:{open|close}` event (no idempotency keys in v1).

This cycle makes a **torn rebalance** (some `place_order` calls succeed, a later one throws) honest: count the fills that happened, record Wanted / Got, health-halt, and do not flatten or pretend the batch never started.

## 1. Why this increment exists

Goal check against current main (`3f16941`):

| Goal slice | v1 / later contract | Current desk |
| --- | --- | --- |
| 稳定执行 / 可靠 | §6 step 6–7: place RTH paper market orders, then record targets, order ids, fills, deviations. Execution honesty: increment `orders_today` **per successful** `place_order`. | `_rebalance` sets `orders_today = already + len(plans)` only after the whole loop. A throw on order 2 of 2 leaves `orders_today` at the pre-batch value, skips `last_got`, skips `execution_deviation`, skips the `rebalance` audit. `tick` then health-halts and **consumes** the event. |
| 风险可控 | Daily order cap is a flatten trigger. A cap that under-counts is not a control. | The successful first order is live on the paper account but invisible to the daily budget. |
| 凭直觉交互 | Activity: rebalances with target vs fill. Halt banners cannot be quiet. | Operator sees HALTED. Positions may show a fill. Clock Last may show `open`. Blotter has order rows and a halt, but no rebalance Wanted / Got for the torn book. |
| 易于维护 | One Supervisor, one order loop | Rebalance and sleeve-isolate both add `len(plans)` after the loop. Share one placer. |

Research applied (not a full OMS):

- **Do not retry the whole batch** after a partial send (duplicate risk; v1 has no client-order-id). Consume the session event. Resume does not catch up; the next legal open/close does.
- **Do not ignore the successes.** Count each accepted `place_order`. Snapshot `last_got` from the broker. Audit deviations when the gap exceeds `max($1, 0.1% equity)`.
- **Halt, not flatten.** Broker errors in §7 are health halt (disconnect / unreachable). Flatten is for kill and limit breach, not a torn send.
- **OMS persist-before-ack** is out: this cycle covers in-process exceptions. Crash recovery of `REBALANCING` is a later increment.

## 2. Place loop

Shared helper used by `_rebalance` and `_isolate_sleeve`:

After **each successful** `place_order`:

1. Audit `order` (sleeve isolate still adds `reason: sleeve_kill`).
2. `orders_today = already + placed` (placed is 1-based count of successes in this batch).

Do **not** wait until the loop finishes to add `len(plans)`.

## 3. Torn `_rebalance`

If `place_order` throws after `placed` successes (`0 <= placed < len(plans)`):

1. Snapshot `last_got` from current broker positions (same formula as the success path).
2. Audit `execution_deviation` rows from `deviations_after`.
3. Set `last_rebalance_event` to `{session_date}:{event}`.
4. Audit one `rebalance` line: `session_event`, `orders=placed`, `wanted`, `got`, `complete: false`.
5. Raise `HaltRequested` (reason names `place_order` and `placed of {n}`). Do not `close_all`.

Success path still audits `rebalance` with `orders=len(plans)` and `complete: true`, then idle.

A later tick in the same session must not place more orders for that event.

## 4. Sleeve isolate

Increment per successful place as above. If isolate throws, existing `kill_sleeve` fallback still flattens the account. The successful isolate orders remain in `orders_today`.

## 5. Activity / help

Blotter rebalance summary includes the word `incomplete` when `complete === false`. Drill-in adds a Complete row (`yes` / `no`).

Execution help: an incomplete rebalance still writes Wanted / Got, counts those orders, and health-halts. It does not flatten and does not retry that event.

## 6. In / out

**In:** per-success `orders_today`; torn rebalance `last_got` + deviations + `rebalance` audit with `complete`; halt not flatten; Activity incomplete copy; help. Tests with a mocked broker that fails the second `place_order`.

**Out:** catch-up rebalance; idempotent retries of the remainder; crash recovery of `REBALANCING`; changing Clock / Positions / Risk tiles; live; WebSockets; `app.js`; sixth screen.

## 7. Verification

- Two-name open rebalance, second `place_order` raises: state `halted`, `close_all` not called, `orders_today == 1`, `last_rebalance_event` set, `rebalance.complete is False`, `execution_deviation` present, second tick places nothing.
- Happy path still counts `orders_today == len(orders)` and still audits wanted/got.
- Help contains `incomplete rebalance`. `#nav` still five screens.
- No real broker orders.
