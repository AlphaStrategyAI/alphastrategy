# alphastrategy Risk Caps glance tiles

**Date:** 2026-08-20
**Status:** Requirements (improvement cycle on v1)
**Repo:** `AlphaStrategyAI/alphastrategy`
**Parent contract:** [`2026-08-19-alphastrategy-v1-requirements.md`](2026-08-19-alphastrategy-v1-requirements.md)
**Technical design:** [`docs/plans/2026-08-20-alphastrategy-risk-caps-technical-design.md`](../plans/2026-08-20-alphastrategy-risk-caps-technical-design.md)

Paper only. Five screens. Quiet cockpit **tokens unchanged**. No sixth nav tab. No live. No WebSockets. No chart library. Keep `#risk-caps`, `#risk-account-caps`, sticky Caps+Headroom, tighten-only math, and PUT keys. Do not revive `static/app.js`. Do not hardcode spoken labels in JS (`policyLabel` / HTML stay the map).

This cycle makes **Caps** use the same glance grammar as overlays / Run / Beat: the four flatten-critical account limits, not an eight-row key dump.

## 1. Why this increment exists

Goal check against current main (`ebca1d2`):

| Goal slice | v1 / later contract | Current desk |
| --- | --- | --- |
| 风险可控 | §7 B-limits flatten on gross, name weight, name count, daily orders. §8 account totals always visible | Caps is sticky but paints every `NUMERIC_CAPS` row as `Gross cap 1` / `Name cap 0.2` / … Headroom already shows **used / cap**. The limit itself is a spreadsheet. |
| 凭直觉交互 | Risk dashboards: four to six decision numbers, not eight undifferentiated fields (Risk Companion: if you can keep three, which stay?) | Operator tightening Gross cannot see the current cap as a hero number next to Headroom. |
| 界面令人眼前一亮 | Overlays are Spoken / Overlays / Tighter / Idle. Headroom has rails | Caps is the last Risk band that still looks like a config dump. |
| 易于使用 | Spoken labels already Gross cap / Name cap / Names / Orders today | How-to names bands and Tighten groups; it does not say Caps is those four tiles. |
| 易于维护 | Labels from `POLICY_LABELS`, not a second map in JS | JS must not contain `Gross cap` (existing test). Tile **labels** live in HTML; **values** from `risk.account`. |

Research applied:

- **Signal over noise:** flatten-critical limits are Gross cap, Name cap, Names, Orders today (`check_book` + `plan_orders` daily budget). Order size, orders/rebalance, and min-delta stay on Tighten.
- **Headroom vs limit:** Headroom is used vs cap. Caps is the cap. Do not merge them.
- **Quiet cockpit:** `metrics-4`, Gross cap is the hero. No charts. No Live label.

## 2. Caps tiles

Inside `#risk-account-caps`, replace the painted dump with static metrics (keep the wrapper id):

```html
          <div id="risk-account-caps" class="metrics metrics-4 nums">
            <div class="metric hero">
              <div class="metric-label">Gross cap</div>
              <div id="risk-cap-gross" class="metric-value">—</div>
            </div>
            <div class="metric">
              <div class="metric-label">Name cap</div>
              <div id="risk-cap-name" class="metric-value">—</div>
            </div>
            <div class="metric">
              <div class="metric-label">Names</div>
              <div id="risk-cap-names" class="metric-value">—</div>
            </div>
            <div class="metric">
              <div class="metric-label">Orders today</div>
              <div id="risk-cap-orders" class="metric-value">—</div>
            </div>
          </div>
          <p id="risk-cap-long" class="muted nums"></p>
```

`renderRiskCaps` fills values from `risk.account` (no API change):

| Tile | Value |
| --- | --- |
| Gross cap | `fmtPct(max_gross)` |
| Name cap | `fmtPct(max_name_weight)` |
| Names | integer `max_names` |
| Orders today | integer `max_orders_per_day` |
| Long only | `#risk-cap-long`: `policyLabel("long_only")` + value; em dash when missing |

Missing policy: all values em dash. `#risk-utilization` keeps class `risk-caps` (Headroom dump+rails). Caps wrapper uses `metrics metrics-4`, not `.risk-caps`.

Tighten still groups every numeric key. Do not clone the form onto Caps.

## 3. Help / README

`how_risk`: Caps is four tiles Gross cap / Name cap / Names / Orders today. Gross cap is the hero. Long only stays a line under the tiles.

Cockpit / README: same.

## 4. In / out

**In:** Caps glance tiles; Long only line; help/README; HTML/JS tests. Keep sticky bar.

**Out:** changing Headroom rails; overlay tiles; PUT/tighten math; sixth screen; `app.js`; WebSockets; charts; hardcoding `Gross cap` in JS; Live label.

## 5. Verification

- `#risk-cap-gross`, `#risk-cap-name`, `#risk-cap-names`, `#risk-cap-orders` live inside `#risk-account-caps` inside `#risk-caps`. Gross cap is the hero. `metrics-4`.
- `#risk-cap-long` exists. `#risk-utilization` still inside Headroom.
- JS paints those ids from `max_gross` / `max_name_weight` / `max_names` / `max_orders_per_day`. `Gross cap` still absent from JS.
- Help contains `Gross cap / Name cap / Names / Orders today`. `#nav` still five screens.
- No real broker orders.
