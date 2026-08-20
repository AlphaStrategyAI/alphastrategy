# alphastrategy limit-breach flatten glance

**Date:** 2026-08-20
**Status:** Requirements (improvement cycle on v1)
**Repo:** `AlphaStrategyAI/alphastrategy`
**Parent contract:** [`2026-08-19-alphastrategy-v1-requirements.md`](2026-08-19-alphastrategy-v1-requirements.md) §7
**Technical design:** [`docs/plans/2026-08-20-alphastrategy-limit-flatten-glance-technical-design.md`](../plans/2026-08-20-alphastrategy-limit-flatten-glance-technical-design.md)

Paper only. Five screens. Quiet cockpit **tokens unchanged**. No sixth nav tab. No live. No WebSockets. No chart library. Do not revive `static/app.js`. Halt vs flatten unchanged: a cap breach still flattens; a broker/host fault still health-halts. Do not retry remaining orders. Do not change interrupted flattening / isolate recovery.

This cycle names the flatten the desk already does when Gross cap / Name cap / Names / order size / daily order cap fire, so it is not silent next to a typed `FLATTEN`.

## 1. Why this increment exists

Goal check against current main (`4e9135c`):

| Goal slice | v1 / later contract | Current desk |
| --- | --- | --- |
| 风险可控 | §7: limit breach is flatten, not halt. Daily order overflow is a limit flatten, not a partial batch. | `check_book` / `plan_orders` raise `FlattenRequested("account")`. `tick` calls `_flatten_account()` with default `reason="account"` and does **not** `_record_kill`. |
| 凭直觉交互 | Flatten banners cannot be quiet. Sleeve kill already reports isolated vs flattened. Interrupted flattening already has its own flatten-banner sentence. | Limit flatten looks identical to an operator `FLATTEN`: `FLAT: paper account flattened`, Activity `account`, `last_kill` still the previous sleeve kill or empty. |
| 易于使用 | Caps tiles are Gross cap / Name cap / Names / Orders today | Help never says the flatten banner names a limit breach. |
| 稳定执行 | Same flatten path (cancel + close_all, STOPPED, clear book) | Keep that path. Only name it. |
| 架构 | One `FlattenRequested`, one flatten banner | Add `reason="limit"` on the exception (default). `tick` persists `last_kill.reason=limit`. Reuse `killReason` in `renderBanners` (still a single `const reason` for halt). |

Research applied:

- **Name the trigger, not a new flatten.** OMS desks distinguish risk flatten from a manual flatten. Do not add a second banner id.
- **Kill-outcome banner stays sleeve-only.** `limit` is an account flatten, like `account` / `flatten_interrupted`. Hide `#kill-outcome-banner`.
- **One reason token `limit`.** Do not fork Gross vs Names vs Orders today on the banner this cycle.

## 2. Persist and audit

`FlattenRequested(scope, reason="limit")`. Existing `FlattenRequested("account")` raises from `check_book` and `plan_orders` keep `scope="account"` and pick up `reason="limit"`.

On `tick` `except FlattenRequested as exc`:

1. `_flatten_account(reason=exc.reason or "limit")` — audit `flatten` with that reason.
2. `_record_kill(KillOutcome(isolated=False, flattened=True, scope="account", reason=exc.reason or "limit"))`.

Operator `kill_account` stays `reason="account"`. Interrupted flattening stays `flatten_interrupted`.

Old snapshots without `last_kill` still show the generic flatten banner.

## 3. Desk copy

`#flatten-banner` (still `banner fail`):

| `last_kill.reason` | Copy |
| --- | --- |
| `flatten_interrupted` | `FLAT: interrupted flattening — paper account flattened` |
| `limit` | `FLAT: limit breach — paper account flattened` |
| `account` / missing / other non-sleeve | `FLAT: paper account flattened` |

`#kill-outcome-banner` stays hidden for `limit`.

Activity flatten row: `limit` → `limit breach` (same family as `interrupted flattening`).

## 4. Help / README

`halt_flatten` / `how_activity`: flatten banner names a limit breach; Activity flatten rows say limit breach.

README Operator: one sentence. Caps still flatten, they are just named.

## 5. In / out

**In:** `FlattenRequested.reason`; persist `last_kill.reason=limit`; flatten audit reason; flatten banner; Activity copy; help/README; tests.

**Out:** per-cap banner sentences; changing flatten math; live; sixth screen; `app.js`; WebSockets; a new banner id; showing limit flatten on `#kill-outcome-banner`.

## 6. Verification

- Limit-breach rebalance: `close_all`, `STOPPED`, `last_kill.reason=="limit"`, flatten audit `reason=="limit"`.
- JS flatten banner includes `FLAT: limit breach — paper account flattened` and still one `const reason` in `renderBanners`.
- Activity flatten branch includes `limit breach`.
- Help contains `flatten banner names a limit breach`.
- `#nav` still five screens. No real broker orders.
