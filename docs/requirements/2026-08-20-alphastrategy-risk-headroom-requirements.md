# alphastrategy Risk Headroom glance tiles

**Date:** 2026-08-20
**Status:** Requirements (improvement cycle on v1)
**Repo:** `AlphaStrategyAI/alphastrategy`
**Parent contract:** [`2026-08-19-alphastrategy-v1-requirements.md`](2026-08-19-alphastrategy-v1-requirements.md)
**Technical design:** [`docs/plans/2026-08-20-alphastrategy-risk-headroom-technical-design.md`](../plans/2026-08-20-alphastrategy-risk-headroom-technical-design.md)

Paper only. Five screens. Quiet cockpit **tokens unchanged**. No sixth nav tab. No live. No WebSockets. No chart library. Keep `#risk-headroom`, `#risk-utilization`, sticky Caps+Headroom, and the `utilization` object. Do not revive `static/app.js`. Do not hardcode `Gross cap` in JS.

This cycle makes **Headroom** use the same glance grammar as Caps: used flatten budgets and cash composition as tiles, not a three-row dump.

## 1. Why this increment exists

Goal check against current main (`c69ae35`):

| Goal slice | v1 / later contract | Current desk |
| --- | --- | --- |
| 风险可控 | §7 name count and daily orders flatten. §8 account totals always visible | Caps is Gross cap / Name cap / Names / Orders today **limits**. Headroom still paints `Names 0 / 50` + a rail, then Cash as a sentence. Used vs cap is not a hero number. |
| 凭直觉交互 | Limit vs utilization side by side (Sembricks / control-tower: exposure **and** remaining) | Caps and Headroom sit in one sticky bar but speak two layouts. Operator cannot scan remaining name/order budget the way they scan Caps. |
| 界面令人眼前一亮 | Caps, overlays, Run, Beat are `metrics-4` | Headroom is the last Risk band that still uses `.risk-caps` auto-fill rows. |
| 易于使用 | `how_risk` names Caps tiles | Does not say Headroom is Names / Orders today / Cash / Target cash. |
| 易于维护 | `utilization` already shared | Keep painting in `js/paint-rails.js` (`renderRiskUtilization`). Do not copy math into `paint-risk.js`. |

Research applied:

- **Caps vs Headroom:** Caps = the stop. Headroom = used against that stop (Portfolio Flatten budgets already do this). Do not merge the bands.
- **Signal over noise:** four tiles from the existing object: names, orders_today, cash_weight, target_cash_weight. Do not add Gross used here (Portfolio Gross already has it).
- **Quiet cockpit:** `metrics-4`, Names is the hero (name-count flatten). Rails reuse `paintUtilTrack` / cash-track. No Live label.

## 2. Headroom tiles

Inside `#risk-utilization`, replace the painted dump with static metrics (keep the wrapper id):

```html
          <div id="risk-utilization" class="metrics metrics-4 nums">
            <div class="metric hero">
              <div class="metric-label">Names</div>
              <div id="risk-head-names" class="metric-value">—</div>
              <div id="risk-head-names-cap" class="metric-sub">—</div>
              <div id="risk-head-names-bar" class="util-track hidden" aria-hidden="true"></div>
            </div>
            <div class="metric">
              <div class="metric-label">Orders today</div>
              <div id="risk-head-orders" class="metric-value">—</div>
              <div id="risk-head-orders-cap" class="metric-sub">—</div>
              <div id="risk-head-orders-bar" class="util-track hidden" aria-hidden="true"></div>
            </div>
            <div class="metric">
              <div class="metric-label">Cash</div>
              <div id="risk-head-cash" class="metric-value">—</div>
              <div id="risk-head-cash-sub" class="metric-sub">—</div>
              <div id="risk-head-cash-bar" class="cash-track hidden" aria-hidden="true"></div>
            </div>
            <div class="metric">
              <div class="metric-label">Target cash</div>
              <div id="risk-head-target" class="metric-value">—</div>
            </div>
          </div>
```

`renderRiskUtilization` fills from existing `utilization()` (no API change). **Do not** `innerHTML = ""` on `#risk-utilization` (that would wipe the mounts).

| Tile | Value | Notes |
| --- | --- | --- |
| Names | used count | Hero. Sub `of {max_names}`. Bar = used/cap via `paintUtilTrack`. Class `fail` on the value when used ≥ cap |
| Orders today | `orders_today` | Sub `of {max_orders_per_day}`. Same rail + fail |
| Cash | `fmtPct(cash_weight)` | Sub `invested {pct}` when known. Cash-track fill = invested_weight (same as Portfolio Cash bar) |
| Target cash | `fmtPct(target_cash_weight)` | Em dash when unknown |

Missing utilization fields: em dash; hide bars.

## 3. Tokens

```css
#risk-head-names.fail {
  color: #ef4444;
}

#risk-head-orders.fail {
  color: #ef4444;
}
```

Separate blocks so token tests can regex each selector.

## 4. Help / README

`how_risk`: Headroom is four tiles Names / Orders today / Cash / Target cash. Names is the hero.

Cockpit / README: same.

## 5. In / out

**In:** Headroom glance tiles; rails; fail tokens; help/README; HTML/CSS/JS tests. Keep `renderRiskUtilization` in `paint-rails.js`.

**Out:** changing Caps tiles; overlay tiles; PUT/tighten math; sixth screen; `app.js`; WebSockets; charts; Gross used on Headroom; Live label; cloning Run forms.

## 6. Verification

- `#risk-head-names`, `#risk-head-orders`, `#risk-head-cash`, `#risk-head-target` live inside `#risk-utilization` inside `#risk-headroom`. Names is the hero. `metrics-4`.
- JS paints those ids. `function renderRiskUtilization` stays in `paint-rails.js`. `Gross cap` still absent from JS.
- Help contains `Names / Orders today / Cash / Target cash`. `#nav` still five screens.
- No real broker orders.
