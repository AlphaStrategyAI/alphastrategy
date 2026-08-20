# alphastrategy remaining flatten budgets and cash composition

**Date:** 2026-08-20
**Status:** Requirements (improvement cycle on v1)
**Repo:** `AlphaStrategyAI/alphastrategy`
**Parent contract:** [`2026-08-19-alphastrategy-v1-requirements.md`](2026-08-19-alphastrategy-v1-requirements.md)
**Technical design:** [`docs/plans/2026-08-20-alphastrategy-risk-remaining-technical-design.md`](../plans/2026-08-20-alphastrategy-risk-remaining-technical-design.md)

Paper only. Five screens. Quiet cockpit tokens unchanged. No sixth nav tab. No live. No WebSockets. No chart libraries. Flatten math unchanged.

This cycle makes every **flatten-capable remaining budget** that the engine already enforces glanceable, and shows **cash versus invested** as book composition — so a personal investor can see risk *before* a limit flatten, not after.

## 1. Why this increment exists

Goal check against current main (`c4e877b`):

| Goal slice | v1 contract | Current desk |
| --- | --- | --- |
| Risk controllable | §7 B-limits: name count ≤ 50; orders per day ≤ 200. Breach = account flatten. | Gross has a util bar. Single-name **weight** has Cap. **Name count** and **daily order budget** fire flatten with no used/cap on Portfolio, Risk, or `status`. |
| Portfolio construction | §5 residual cash after `Σ allocation_i`; §8 Portfolio shows equity, cash, gross. | Cash is a dollar number. Spoken sleeve share exists. There is no invested-versus-cash split, and no target residual (`1 − Σ last_combined`). |
| Reliable / easy to maintain | §9 `status`; architecture: one Supervisor, shared numbers. | `orders_today` lives on the snapshot only. CLI/Web re-derive nothing. A second copy in JS would drift. |
| Intuitive interaction | §8 halt/deviation cannot be visually quiet; Risk totals always visible. | Risk lists cap values as text. Used amounts are absent, so 90% of a flatten limit looks the same as 0%. |

Research applied (not copied as an EMS):

- **Pre-trade remaining limits** (FIA / broker risk desks): show *used / cap* with a warn band before the hard stop. 90% warn / 100% fail already exists for Gross; reuse it for names and daily orders.
- **Portfolio construction:** cash is an asset class, not leftover chrome. Ibbotson-style policy weights treat residual cash as `1 − invested`. This desk already combines to residual cash; surface actual `cash / equity` against target residual from `last_combined`.
- **Quiet cockpit:** metric tiles + `.util-track`. No pie charts. No sixth screen.

Out of this cycle (still real, next pass): structured import `kind` (v1 §8 hash/schema/conformance copy is still a raw string); Activity empty-state tone; visual hierarchy beyond these rails.

## 2. Shared utilization object

Add `alphastrategy.risk.utilization.summarize` (pure). API and CLI both emit that dict. Do not compute names or order budget only in JS.

Fields:

| Key | Meaning |
| --- | --- |
| `names` | Count of live positions with `qty ≠ 0`. If no live list, count nonzero `last_got`, else nonzero `last_combined`. Else `0`. |
| `max_names` | Effective account policy. |
| `orders_today` | Snapshot counter (already persisted). |
| `max_orders_per_day` | Effective account policy. |
| `cash_weight` | `cash / equity` when both are known and `equity > 0`; `0` when `equity == 0`; `null` when cash/equity are unknown (offline CLI without broker). |
| `invested_weight` | `1 − cash_weight` when `cash_weight` is a number; else `null`. |
| `target_cash_weight` | `max(0, 1 − Σ last_combined.values())` when `last_combined` is non-empty; else `null`. |
| `max_gross` | Effective account policy (desk already has Gross; include so Risk can label consistently). |

No new Supervisor counters. No change to `check_book` or `plan_orders`.

## 3. Status, Risk, CLI

`GET /api/status` includes `utilization` (always an object, never omitted).

`GET /api/risk` includes the same `utilization` object next to `account` / `sleeves`.

`alphastrategy status`:

- Control plane up: JSON already includes `utilization` from the API.
- Control plane down: build `utilization` from on-disk snapshot + supervisor policy; `cash_weight` and `invested_weight` are `null` (no live account). Still include names from `last_got` / `last_combined` and `orders_today`.

## 4. Quiet cockpit

Portfolio metric tiles (same `.metrics` grid, locked tokens):

1. **Names** (`#metric-names`): value is `names`. Subline `#metric-names-cap` is `of {max_names}`. Track `#metric-names-bar` fill = `names / max_names` (0 if cap is 0). Same 90% warn / 100% fail as Gross. `aria-label` includes used and cap.
2. **Orders today** (`#metric-orders`): value is `orders_today`. Subline `#metric-orders-cap` is `of {max_orders_per_day}`. Track `#metric-orders-bar` fill = `orders_today / max_orders_per_day`. Same warn/fail. `aria-label` includes used and cap.

**Cash** tile keeps the dollar value. Add:

- `#metric-cash-bar` composition track: fill width = `invested_weight` (running `#10b981`); track background is residual cash (`#0b0e14`). If `target_cash_weight` is a number, a `#e5e9f0` marker (reuse `.wg-wanted` pattern) at invested target `1 − target_cash_weight`.
- `#metric-cash-sub`: `invested {pct} · cash {pct}`. When target residual is known, append ` · target cash {pct}`. Missing weights: `—`.

Risk screen sticky account bar: `#risk-utilization` lists Names, Orders today, and Cash composition as used/cap (or invested/cash) text plus the same track treatment. Caps form is unchanged.

## 5. Help / README

One sentence: Portfolio Names and Orders today are remaining flatten budgets; Cash shows invested versus residual against the last combined target. `status` includes `utilization`.

## 6. In / out

**In:** `summarize`; status/risk/CLI `utilization`; Names and Orders tiles; Cash composition; Risk utilization row; help/README; unit, API, CLI, web-token, e2e tests.

**Out:** changing flatten thresholds; sixth screen; charts; live; import `kind` classification; daily-order reset rules (already specified).

## 7. Verification

- `summarize` unit tests: live names; fallback to `last_got`; empty book zeros; cash_weight; target residual; `equity == 0`; unknown cash → null.
- `GET /api/status` and `GET /api/risk` include `utilization` with matching `orders_today` / `max_names`.
- Offline CLI `status` JSON has `utilization` and null cash weights.
- HTML ids: `metric-names`, `metric-orders`, `metric-cash-bar`, `risk-utilization`. `#nav` still five screens.
- JS: `renderRemainingBudgets`, `renderCashComposition`. Reuse 90/100 util classes. No `window.confirm`.
- GET `/` includes `metric-names`.
- No real broker orders.
