# alphastrategy flatten banner names the breached cap

**Date:** 2026-08-20
**Status:** Requirements (improvement cycle on v1)
**Repo:** `AlphaStrategyAI/alphastrategy`
**Parent contract:** [`2026-08-19-alphastrategy-v1-requirements.md`](2026-08-19-alphastrategy-v1-requirements.md) §7
**Related:** [`2026-08-20-alphastrategy-limit-flatten-glance-requirements.md`](2026-08-20-alphastrategy-limit-flatten-glance-requirements.md)
**Technical design:** [`docs/plans/2026-08-20-alphastrategy-cap-flatten-names-technical-design.md`](../plans/2026-08-20-alphastrategy-cap-flatten-names-technical-design.md)

Paper only. Five screens. Quiet cockpit **tokens unchanged**. No sixth nav tab. No live. No WebSockets. No chart library. Do not revive `static/app.js`. Halt vs flatten unchanged. Do not retry remaining orders. `"Gross cap"` must not appear in assembled JS (labels still come from `GET /api/risk`).

The limit-flatten cycle named every cap flatten `reason=limit`. Caps tiles already speak Gross cap / Name cap / Names / Orders today. This cycle stores the **policy key** on `FlattenRequested` / `last_kill` / flatten audit so the banner and Activity name the same cap the operator just looked at.

## 1. Why this increment exists

Goal check against current main (`4e35c8b`):

| Goal slice | v1 / later contract | Current desk |
| --- | --- | --- |
| 风险可控 | §7 table: Gross, single-name, name count, order size, orders/rebalance, orders/day each flatten | All seven raises are `FlattenRequested("account")` with default `reason="limit"`. After flatten the operator cannot tell which envelope fired. |
| 凭直觉交互 | Recognition: Risk Caps and flatten banner should use the same words | `FLAT: limit breach` is a generic bucket. Tighten groups Gross / Names / Orders / Deltas, but the kill tape does not. |
| 易于使用 | `how_risk` names Gross cap / Name cap / Names / Orders today | Help still only says “a limit breach”. |
| 稳定执行 | Same cancel + `close_all` path | Keep that path. Only the reason token changes. |
| 架构 | `POLICY_LABELS` already maps keys to desk words; cockpit `policyLabel` | Raise with the storage key. Paint with `policyLabel`. Keep `limit` as the fallback for old snapshots. |

Research applied:

- **One banner, specific trigger.** OMS risk flatten names the limit, not a new panel.
- **Do not hardcode Gross cap in JS.** `test_js_paints_risk_caps_tiles` scans whole `js_text`.
- **Kill-outcome banner stays sleeve-only.** Cap keys are account flattens.

## 2. Reason tokens

`FlattenRequested("account", reason=<key>)` where `<key>` is one of:

| Raise site | Reason |
| --- | --- |
| `check_book` long_only | `long_only` |
| `check_book` gross | `max_gross` |
| `check_book` name weight | `max_name_weight` |
| `check_book` name count | `max_names` |
| `plan_orders` order notional | `max_order_notional_frac` |
| `plan_orders` orders/rebalance | `max_orders_per_rebalance` |
| `plan_orders` orders/day | `max_orders_per_day` |

Default on the exception class stays `"limit"` for any unspecified raise. Operator kill stays `"account"`. Interrupted flattening stays `"flatten_interrupted"`. Old `last_kill.reason=limit` still paints the generic limit sentence.

`tick` already does `_flatten_account(reason=exc.reason)` and `_record_kill(... reason=exc.reason)`.

## 3. Desk copy

`#flatten-banner` (still `banner fail`):

| `last_kill.reason` | Copy |
| --- | --- |
| `flatten_interrupted` | `FLAT: interrupted flattening — paper account flattened` |
| cap key (`long_only` or a `NUMERIC_CAPS` key) | `FLAT: ` + `policyLabel(reason)` + ` — paper account flattened` |
| `limit` | `FLAT: limit breach — paper account flattened` |
| `account` / missing / other | `FLAT: paper account flattened` |

Activity flatten row: cap key → `policyLabel(reason) + " breach"`; `limit` → `limit breach`; interrupted unchanged.

`#kill-outcome-banner` stays hidden for cap keys.

Single halt `const reason` in `renderBanners`.

## 4. Help / README

`halt_flatten` / `how_activity`: flatten banner names the breached cap in desk words (Gross cap, Name cap, Names, Orders today). Generic `limit` remains the fallback for old snapshots.

README Operator: the flatten banner names the cap that fired.

## 5. In / out

**In:** per-raise `reason` keys; banner + Activity via `policyLabel`; keep `limit` fallback; help/README; unit + JS + halt_flatten tests.

**Out:** changing flatten math; a new banner id; putting `Gross cap` in JS; live; sixth screen; `app.js`; WebSockets; sleeve kill copy.

## 6. Verification

- Gross-cap rebalance: `last_kill.reason=="max_gross"`, flatten audit `reason=="max_gross"`.
- `check_book` / `plan_orders` tests assert the matching reason key.
- JS flatten banner uses `policyLabel(killReason)` and `NUMERIC_CAPS`; still contains the `limit` fallback; `"Gross cap"` not in `js_text`; one `const reason`.
- Help contains `flatten banner names the breached cap`.
- Five `#nav` screens. No real broker.
