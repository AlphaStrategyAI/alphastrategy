# alphastrategy Caps is the spoken book

**Date:** 2026-08-20
**Status:** Requirements (improvement cycle on v1)
**Repo:** `AlphaStrategyAI/alphastrategy`
**Parent contract:** [`2026-08-19-alphastrategy-v1-requirements.md`](2026-08-19-alphastrategy-v1-requirements.md) §7–§8
**Related:** [`2026-08-20-alphastrategy-overlay-start-requirements.md`](2026-08-20-alphastrategy-overlay-start-requirements.md), [`2026-08-20-alphastrategy-risk-caps-requirements.md`](2026-08-20-alphastrategy-risk-caps-requirements.md), [`2026-08-20-alphastrategy-risk-remaining-requirements.md`](2026-08-20-alphastrategy-risk-remaining-requirements.md)
**Technical design:** [`docs/plans/2026-08-20-alphastrategy-spoken-caps-technical-design.md`](../plans/2026-08-20-alphastrategy-spoken-caps-technical-design.md)

Paper only. Five screens. Quiet cockpit **tokens unchanged**. No sixth nav tab. No live. No WebSockets. No chart library. Do not revive `static/app.js`. `"Gross cap"` must not appear in assembled JS. `renderBanners` keeps a **single** `const reason`. Do not retry leftover orders. Resume does not catch up. Heartbeat still does **not** flatten. Keep `Next rebalance`. Keep overlay-on-start flatten. Keep idle overlays unpublished.

v1 §7: flatten uses account policy B **tightened by each allocated sleeve** (envelope ∩ overlay). Overlay-start already enforces that spoken policy on the live book. Caps, Headroom, Gross rail, and Positions at-cap still read **writable account** `risk.account` / `supervisor.policy`. An operator can speak a 5% Name overlay, see Caps Name cap 20%, and watch Headroom / at-cap against the wrong limit. That is not 风险可控.

## 1. Why this increment exists

Goal check against current main (`a1067e8`):

| Goal slice | v1 / later contract | Current desk |
| --- | --- | --- |
| 风险可控 | Spoken policy is what `check_book` / `_enforce_live_book` flatten on. | Caps paints `risk.account`. `from_supervisor` uses `supervisor.policy`. Positions at-cap and Gross rail use `risk.account.max_name_weight` / `max_gross`. |
| 凭直觉交互 | Glance numbers must match the kill-switch. | Overlay cards say tighter; Caps still looks like the Tighten form. |
| 易于使用 | Caps is Gross cap / Name cap / Names / Orders today. | Never says Caps is the spoken book. |
| 易于维护 | One `_rebalance_policy`. | Public `spoken_policy()`. Utilization and Caps consume it. Tighten form stays on `account`. |

Research applied:

- **Pre-trade remaining vs working limit.** Risk desks show the *effective* cap the book is measured against, not only the firm-wide overlay the operator can still tighten. The writable account form is a different control.
- **Idle overlays stay draft.** Same as overlay-start: allocation 0 does not enter spoken policy. Caps must not jump to an idle overlay.
- **Do not flatten on this path.** Paint and `utilization` only. Heartbeat unchanged.

Out: heartbeat flatten; changing Tighten form to spoken; 409; live; Clock paint; cloning overlay forms onto Caps.

## 2. Engine / API

Public `Supervisor.spoken_policy()` returns `_rebalance_policy()` (account tightened by each sleeve with allocation > 0: envelope ∩ overlay). Same lock family (`RLock`).

`from_supervisor` passes `spoken_policy()` into `summarize`, not `supervisor.policy`.

`summarize` also emits `max_name_weight` (float) next to existing `max_gross` / `max_names` / `max_orders_per_day`.

`GET /api/risk` adds:

```text
"spoken": <AccountPolicy dict>
```

`account` remains the writable account policy (Tighten). Idle overlay: `spoken` matches account flatten-critical caps (envelope not spoken until allocated). Allocated overlay 5% Name: `spoken.max_name_weight == 0.05`, `account.max_name_weight` stays 0.20.

`GET /api/status` `utilization` follows spoken (same `from_supervisor`).

Do not 409. Do not call `_enforce_live_book` from this GET path.

## 3. Paint

Caps: `renderRiskCaps` fills from `risk.spoken` (fallback `risk.account`). Tighten form still uses `risk.account`.

When a Caps value is tighter than the matching `account` field, that metric-value gets class `warn` (`#f59e0b`). min-delta is not on Caps.

Gross rail: cap from `utilization.max_gross` (spoken), else `spoken.max_gross`, else 1.

Positions wanted/got scale and name-cap bar, and Positions glance At cap: cap from `spoken.max_name_weight` or `utilization.max_name_weight`, else 0.2.

Do not put `"Gross cap"` in JS. Do not `innerHTML` `#risk-overlay-hint` / `#risk-tighten-hint`. Each `js/` part stays ≤ 400 lines.

CSS: `#risk-cap-gross.warn`, `#risk-cap-name.warn`, `#risk-cap-names.warn`, `#risk-cap-orders.warn` use `#f59e0b`.

## 4. Help / README

`how_risk` and cockpit: Caps is the spoken book. Tighten still edits the account form.

`REQUIRED_PHRASES`: `Caps is the spoken book`.

README Caps line: same.

Keep `Next rebalance`. Keep overlay flatten copy.

## 5. In / out

**In:** `spoken_policy`; utilization from spoken + `max_name_weight`; GET `/api/risk` `spoken`; Caps paint; Gross/name rails; warn tokens; help/README; tests.

**Out:** heartbeat flatten; changing Tighten; idle overlay in spoken; live; sixth screen; `app.js`.

**Done when:**

1. Allocated overlay Name 5% → `GET /api/risk` `spoken.max_name_weight == 0.05` and `account.max_name_weight == 0.20`; `utilization.max_name_weight == 0.05`.
2. Same overlay while idle → spoken Name still 0.20; utilization Name still 0.20.
3. Allocated overlay `max_names: 10` → `utilization.max_names == 10`, account still 50.
4. Assembled JS Caps paint reads `spoken`; Positions/Gross rails do not use only `risk.account` for those caps.
5. Help contains `Caps is the spoken book`. Five `#nav` screens. `"Gross cap"` not in `js_text`. No real broker.
