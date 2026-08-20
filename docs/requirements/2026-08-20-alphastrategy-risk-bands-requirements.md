# alphastrategy Risk glance bands

**Date:** 2026-08-20
**Status:** Requirements (improvement cycle on v1)
**Repo:** `AlphaStrategyAI/alphastrategy`
**Parent contract:** [`2026-08-19-alphastrategy-v1-requirements.md`](2026-08-19-alphastrategy-v1-requirements.md)
**Technical design:** [`docs/plans/2026-08-20-alphastrategy-risk-bands-technical-design.md`](../plans/2026-08-20-alphastrategy-risk-bands-technical-design.md)

Paper only. Five screens. Quiet cockpit **tokens unchanged**. No sixth nav tab. No live. No WebSockets. No chart libraries. Policy **keys and tighten math stay**. Envelope YAML and `PUT /api/risk` still speak `max_gross`. Spoken labels from `POLICY_LABELS` stay.

This cycle makes Risk match the desk grammar the other operator screens already use: a personal investor sees **caps**, **remaining headroom**, a **grouped tighten** form, then **sleeve overlays** — not a sticky dump plus a wall of eight inputs.

## 1. Why this increment exists

Goal check against current main (`30c9cc9`):

| Goal slice | v1 / later contract | Current desk |
| --- | --- | --- |
| 风险可控 | §7 B-limits; §8 Risk: account totals **always visible**; UI refuses looser values | Caps and utilization exist, but they share one unlabeled sticky dump. Flatten budgets on Portfolio are Gross / Names / Orders today; Risk tighten is one `.inline` wrap of every numeric key. |
| 凭直觉交互 | Nielsen 4 (consistency) and 8 (minimalist design); Gestalt common region | Portfolio, Strategies, and Run are glance bands. Risk still looks like a config form from a different product. |
| 易于使用 | Spoken labels already ship (`Gross cap`, `Names`, `Orders today`) | Labels are readable; grouping is not. An operator tightening “orders today” hunts through eight fields. |
| 界面令人眼前一亮 | Sparse chrome, labeled regions | `h2` Account caps / Tighten account policy / Sleeve overlays — generic panels, not desk bands. |
| 帮助文档 | `how_risk` says spoken words and tighten-only | How-to does not name bands or Gross / Names / Orders / Deltas groups. |
| 架构 | Cockpit JS parts | Edit `js/paint-risk.js` (and HTML/CSS). Do not revive `static/app.js`. Do not move utilization math. |

Research applied (not a new palette, not a new policy schema):

- **Gestalt common region:** Caps, Headroom, Tighten, and Sleeve overlays are four regions. Tighten’s Gross / Names / Orders / Deltas are inner regions that match Portfolio flatten-budget language.
- **Nielsen consistency:** the same four words the book already uses (Gross, Names, Orders, plus Deltas for the skip threshold) are how you tighten.
- **ISO 9241-110 / progressive disclosure:** always-visible totals stay sticky; the form is grouped, not hidden behind a sixth screen.
- **Quiet cockpit:** reuse `glance-band` / `glance-heading`. No new tokens. No modal.

## 2. Four Risk regions

Replace the Risk screen’s sticky bar + two panels with:

| id | heading | Contents (keep existing control ids) |
| --- | --- | --- |
| `#risk-caps` | Caps | `#risk-account-caps` (spoken labels + values, including Long only) |
| `#risk-headroom` | Headroom | `#risk-utilization` (existing Names / Orders today / Cash paint) |
| `#risk-tighten` | Tighten | `#risk-account-form`, `#risk-error` |
| `#risk-overlays` | Sleeve overlays | `#risk-sleeves` |

`#risk-caps` and `#risk-headroom` stay inside the existing sticky wrapper (keep `class="risk-account-bar"` on that wrapper so account totals remain always visible while scrolling Tighten / overlays). DOM order: caps → headroom → tighten → overlays.

Each region: `class="glance-band"`, child `h2.glance-heading`. Tighten wraps the form in `.panel` like Run’s Start paper.

Keep `#risk-account-form`, `#risk-error`, `#risk-account-caps`, `#risk-utilization`, `#risk-sleeves`. Tighten-only validation is unchanged. Polls still must not wipe a dirty form (`riskFormIsDirty`).

## 3. Tighten groups

`buildRiskInputs` groups `NUMERIC_CAPS` into four fieldsets (same groups for account and sleeve overlay forms):

| Legend | Keys (PUT keys unchanged) |
| --- | --- |
| Gross | `max_gross`, `max_name_weight`, `max_order_notional_frac` |
| Names | `max_names` |
| Orders | `max_orders_per_rebalance`, `max_orders_per_day` |
| Deltas | `min_delta_dollar`, `min_delta_frac` |

Every numeric cap appears in **exactly one** group. Visible labels stay `policyLabel(key)`. Inputs keep `name="<key>"`.

CSS: `.risk-tighten-groups` is a two-column grid from `min-width: 800px` (reuse the book-grid breakpoint). Below that, one column. Fieldsets use existing border token `#2a3142` and background `#11151d`. No new colors.

## 4. Help / README

`how_risk`: Risk is four bands **Caps / Headroom / Tighten** plus Sleeve overlays. Tighten groups Gross / Names / Orders / Deltas. Account totals stay sticky. Tighten only; PUT keys unchanged.

README Quiet cockpit: same band names.

## 5. In / out

**In:** four Risk regions; sticky caps+headroom; grouped tighten fieldsets; CSS grid; help/README; HTML/CSS/JS/help tests; e2e GET `/` includes `risk-tighten`.

**Out:** new tokens; sixth screen; renaming policy keys; changing tighten math or `riskFormIsDirty`; Supervisor/API schema; chart libraries; reviving `static/app.js`; moving utilization onto Portfolio; live controls.

## 6. Verification

- HTML ids `risk-caps`, `risk-headroom`, `risk-tighten`, `risk-overlays`. Headings `Caps`, `Headroom`, `Tighten`, `Sleeve overlays`.
- `#risk-account-caps` inside `#risk-caps`. `#risk-utilization` inside `#risk-headroom`. `#risk-account-form` inside `#risk-tighten`. `#risk-sleeves` inside `#risk-overlays`.
- Sticky `risk-account-bar` still wraps Caps and Headroom (not Tighten).
- JS source includes `RISK_TIGHTEN_GROUPS` with legends Gross, Names, Orders, Deltas.
- CSS `.risk-tighten-groups`. `#nav` still five screens.
- Help contains `Caps / Headroom / Tighten`. GET `/` includes `id="risk-tighten"`.
- No real broker orders.
