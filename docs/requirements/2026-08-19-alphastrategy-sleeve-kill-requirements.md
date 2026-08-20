# alphastrategy isolated sleeve kill requirements

**Date:** 2026-08-19
**Status:** Requirements (improvement cycle 2)
**Parent contracts:**
- [`2026-08-19-alphastrategy-v1-requirements.md`](2026-08-19-alphastrategy-v1-requirements.md) §7
- [`2026-08-19-alphastrategy-operator-desk-requirements.md`](2026-08-19-alphastrategy-operator-desk-requirements.md)

This increment does not change product identity, paper walls, or the halt-vs-flatten matrix for **account** kill. It implements the v1 sleeve-kill row that the Supervisor currently skips: when isolation is clean, do not flatten the whole paper account.

## 1. Why this increment exists

v1 §7:

> Manual sleeve kill — If reachable: flatten that sleeve’s implied positions (combined book minus that sleeve); if that cannot be isolated cleanly, flatten whole account rather than guess.

Today `kill_sleeve` always calls `_flatten_account()`, which `close_all`s and sets `SupervisorState.STOPPED`. Killing one sleeve therefore stops every other running sleeve. Cycle 1 now persists `last_combined`, `last_sleeve_contribution`, and `last_prices`, so isolation is no longer a guess when that last book exists.

Kill-switch practice still applies: flatten is louder than halt; prefer the smallest effective scope (this sleeve) before the firm-wide flatten. If the residual book cannot be formed without inventing weights or prices, keep today’s whole-account flatten.

## 2. Isolation is clean when all of these hold

1. `bundle_id` is in `sleeves`.
2. `last_sleeve_contribution[bundle_id]` is a non-empty weight map.
3. `last_combined` is a non-empty weight map.
4. `last_prices` contains a price for every symbol in `(current positions) ∪ last_combined ∪ last_sleeve_contribution[bundle_id]`.
5. Alpaca clock is reachable and `is_open` is true (RTH paper market orders only; do not invent an off-hours child order).

Otherwise: same as today — `cancel_open_orders` + `close_all`, state `STOPPED`, audit `kill` with `isolated: false`.

## 3. Isolated kill behavior

1. Set that sleeve allocation to 0 and add it to `stopped` (same as Stop, immediately).
2. Residual target:

   ```text
   residual[asset] = last_combined[asset] - last_sleeve_contribution[sleeve][asset]
   ```

   Drop assets whose residual weight is `<= 0` (or abs `< 1e-12`). Do not invent assets that were never in `last_combined` or the killed contribution.
3. `cancel_open_orders`, then `plan_orders(residual, current positions, last_prices, equity, rebalance policy)` and place those paper market orders. Do **not** call `close_all`.
4. Persist `last_combined = residual`, drop the killed id from `last_sleeve_contribution` and `last_sleeve_weights`.
5. Supervisor state stays `idle_in_session` / `idle_out_of_session` / `halted` as it was, except it must **not** become `STOPPED` solely because one sleeve was isolated-killed. Other sleeves keep their allocations.
6. Audit: `kill` with `bundle_id` and `isolated: true`. Order lines may include `reason: sleeve_kill`.
7. If `plan_orders`, `place_order`, or `cancel_open_orders` raises: fall back to whole-account flatten (`isolated: false`). Do not leave a half-applied residual and pretend isolation succeeded.

Account kill (`paper kill` without bundle, SIGINT/SIGTERM, limit breach) is unchanged: whole account, `STOPPED`.

## 4. Web / CLI

No new buttons. Existing **Kill sleeve** and `alphastrategy paper kill --bundle <id>` call the same Supervisor method. Do not require typing `FLATTEN` for sleeve kill (that phrase remains account-only).

## 5. In / out

**In:** isolated sleeve kill when last book + RTH clock allow it; fallback flatten when they do not; tests with two sleeves.

**Out:** live trading, VWAP, guessing a sleeve’s share of overlapping names without last contribution, changing account kill, WebSockets.

**Done when:** two paper sleeves rebalance; killing one sells only that sleeve’s implied names; `close_all` is not called; the other sleeve’s allocation remains; supervisor is not `STOPPED`. With no last book, `kill_sleeve` still `close_all`s once.
