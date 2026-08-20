# alphastrategy Risk Sleeve overlay glance tiles

**Date:** 2026-08-20
**Status:** Requirements (improvement cycle on v1)
**Repo:** `AlphaStrategyAI/alphastrategy`
**Parent contract:** [`2026-08-19-alphastrategy-v1-requirements.md`](2026-08-19-alphastrategy-v1-requirements.md)
**Technical design:** [`docs/plans/2026-08-20-alphastrategy-risk-overlays-technical-design.md`](../plans/2026-08-20-alphastrategy-risk-overlays-technical-design.md)

Paper only. Five screens. Quiet cockpit **tokens unchanged**. No sixth nav tab. No live. No WebSockets. No chart library. Keep `#risk-overlays`, `#risk-sleeves`, tighten-only math, and PUT keys. Do not revive `static/app.js`. Do not clone Run allocation forms onto Risk.

This cycle supersedes desk-first-glance §7 (allocation as **text only**). Sleeve overlays become glanceable: Spoken / Overlays / Tighter / Idle, and each card shows allocation as a rail.

## 1. Why this increment exists

Goal check against current main (`79702b0`):

| Goal slice | v1 / later contract | Current desk |
| --- | --- | --- |
| 风险可控 | §8 Risk: per-sleeve **caps and allocation**; overlays only tighten A∩B | Caps / Headroom / Tighten are glance bands. Each overlay card is `Allocation 25.0%` muted text plus a full form. Stricter-than-account is invisible until you compare eight fields. |
| 凭直觉交互 | Recognition over recall. Control-tower: exposure vs limits at a glance | Operator cannot see how much book overlays cover, or how many sleeves are actually tighter than the account. |
| 界面令人眼前一亮 | Run Sleeves is Remaining / Spoken / Active / Idle | Sleeve overlays is the last core band that still looks like a config dump. |
| 易于使用 | `how_risk` names four bands | Does not say overlays are Spoken / Overlays / Tighter / Idle. Help still says allocation as text. |
| 架构 | JS parts; utilization already shared | Paint in `js/paint-risk.js`. Compare effective sleeve policy vs account in the browser. No API change. |

Research applied:

- **Dealing-desk control tower:** show exposure vs internal limits, then the tighten action. Do not hide overlay tightness inside a form.
- **Desk-first-glance deferred this:** allocation text was a stopgap so Risk would not grow Run’s allocation inputs. Keep that wall. Add a rail, not a form.
- **Quiet cockpit:** `metrics-4`, `metric hero`, existing `.util-track` 90% / 100% tokens. No pie charts.

## 2. Overlay glance tiles

Inside `#risk-overlays`, after the heading and **before** `#risk-sleeves`:

```html
        <div class="metrics metrics-4 nums">
          <div class="metric hero">
            <div class="metric-label">Spoken</div>
            <div id="risk-overlay-spoken" class="metric-value">—</div>
          </div>
          <div class="metric">
            <div class="metric-label">Overlays</div>
            <div id="risk-overlay-count" class="metric-value">—</div>
          </div>
          <div class="metric">
            <div class="metric-label">Tighter</div>
            <div id="risk-overlay-tighter" class="metric-value">—</div>
          </div>
          <div class="metric">
            <div class="metric-label">Idle</div>
            <div id="risk-overlay-idle" class="metric-value">—</div>
          </div>
        </div>
```

Paint from existing `GET /api/risk` (`account`, `sleeves`) and `state.bundles.paper`:

| Tile | Value | Notes |
| --- | --- | --- |
| Spoken | `fmtPct(Σ allocation of overlay ids)` | Hero. Class `warn` when spoken ≥ 0.9 and < 1. Class `fail` when spoken ≥ 1 |
| Overlays | count of `risk.sleeves` ids | Imported bundles (API already returns one effective policy per import) |
| Tighter | count of ids whose effective policy is stricter than account on ≥ 1 numeric cap | `min_delta_*` stricter when overlay > account; other caps when overlay < account. Class `warn` when count > 0 |
| Idle | count of overlay ids with allocation 0 | Never-started and paper-zero |

Empty `#risk-sleeves` (no ids): `No sleeve overlays. Import a qualified .asb, then tighten a sleeve here.`

Each overlay **card** keeps the tighten form. Replace the muted allocation sentence with:

- Allocation label + `fmtPct(alloc)`
- `.util-track` fill = `alloc / 1` via existing `paintUtilTrack` (same 90% / 100% classes)
- Line: `{n} tighter than account` or `Same as account`

No allocation `<input>` on Risk. `riskFormIsDirty` unchanged. Paint glance tiles even when the form is dirty so Spoken/Tighter stay current.

Do **not** label any tile `Live`.

## 3. Tokens

```css
#risk-overlay-spoken.warn,
#risk-overlay-tighter.warn {
  color: #f59e0b;
}

#risk-overlay-spoken.fail {
  color: #ef4444;
}
```

Use **separate** CSS blocks so token tests can regex each selector (grouped selectors hid Beat tokens).

## 4. Help / README

`how_risk`: Sleeve overlays is four tiles Spoken / Overlays / Tighter / Idle. Spoken is the hero. Allocation is a rail, not only text.

Cockpit / README: same. Drop “Risk lists sleeve allocation as text.”

## 5. In / out

**In:** overlay glance tiles; allocation rail; tighter-than-account count; empty copy; tokens; help/README; HTML/CSS/JS tests.

**Out:** cloning Run allocation forms; changing PUT / tighten math; Caps dump rewrite; sixth screen; `app.js`; WebSockets; charts; API schema.

## 6. Verification

- `#risk-overlay-spoken`, `#risk-overlay-count`, `#risk-overlay-tighter`, `#risk-overlay-idle` live inside `#risk-overlays`. Spoken is the hero. `metrics-4`.
- `#risk-sleeves` still inside overlays. `#risk-account-form` still inside Tighten.
- JS has `overlayTighterCount` and paints Spoken from allocations. Empty copy includes `No sleeve overlays`.
- Help contains `Spoken / Overlays / Tighter / Idle`. `#nav` still five screens. No `>Live<` label.
- No real broker orders.
