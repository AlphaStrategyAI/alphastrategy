# alphastrategy Risk Tighten glance tiles

**Date:** 2026-08-20
**Status:** Requirements (improvement cycle on v1)
**Repo:** `AlphaStrategyAI/alphastrategy`
**Parent contract:** [`2026-08-19-alphastrategy-v1-requirements.md`](2026-08-19-alphastrategy-v1-requirements.md)
**Technical design:** [`docs/plans/2026-08-20-alphastrategy-tighten-glance-technical-design.md`](../plans/2026-08-20-alphastrategy-tighten-glance-technical-design.md)

Paper only. Five screens. Quiet cockpit **tokens unchanged**. No sixth nav tab. No live. No WebSockets. No chart library. Keep `#risk-tighten`, `#risk-account-form`, `#risk-error`, `RISK_TIGHTEN_GROUPS`, tighten-only math, and PUT keys. Do not revive `static/app.js`. Do not clone Caps Gross/Names/Orders onto Tighten.

This cycle supersedes risk-bands §2 for Tighten as **form-only**. Tighten becomes glanceable: Tight / Delta $ / Delta % / Fields, then the existing grouped form.

## 1. Why this increment exists

Goal check against current main (`b6dc5f7`):

| Goal slice | v1 / later contract | Current desk |
| --- | --- | --- |
| 风险可控 | §8 Risk: account policy is the flatten envelope; overlays only tighten | Caps shows Gross/Name/Names/Orders. Skip floors (`min_delta_*`) and “already tighter than ship defaults” live only inside eight unlabeled-until-grouped inputs. |
| 凭直觉交互 | Recognition over recall. Control-tower: limits at a glance, then the action | Operator cannot see how many account caps already left v1 defaults, or the skip floors Caps omits, without opening every Deltas input. |
| 界面令人眼前一亮 | Caps / Headroom / Sleeve overlays are `metrics-4` | Tighten is the last core Risk band that still looks like a config dump. |
| 易于使用 | `how_risk` names Caps / Headroom / overlay tiles | Does not say Tighten is Tight / Delta $ / Delta % / Fields. Help still treats Tighten as groups only. |
| 架构 | JS parts; `overlayTighterCount` already compares two policies | Paint in `js/paint-risk.js`. Compare account vs v1 defaults in the browser. `GET /api/risk` must expose those defaults. PUT must not accept them. |

Research applied:

- **Dealing-desk control tower:** show how far the book already sits from ship defaults, then the tighten action. Do not hide skip floors inside a form.
- **Risk-bands deferred this:** grouped fieldsets were a stopgap so Tighten would not clone Caps tiles. Keep that wall. Add glance tiles for what Caps does **not** show.
- **Quiet cockpit:** `metrics-4`, `metric hero`, warn token `#f59e0b`. No charts.

## 2. Tighten glance tiles

Inside `#risk-tighten`, after the heading and **before** the form panel:

```html
        <div class="metrics metrics-4 nums">
          <div class="metric hero">
            <div class="metric-label">Tight</div>
            <div id="risk-tighten-tight" class="metric-value">—</div>
          </div>
          <div class="metric">
            <div class="metric-label">Delta $</div>
            <div id="risk-tighten-delta-dollar" class="metric-value">—</div>
          </div>
          <div class="metric">
            <div class="metric-label">Delta %</div>
            <div id="risk-tighten-delta-frac" class="metric-value">—</div>
          </div>
          <div class="metric">
            <div class="metric-label">Fields</div>
            <div id="risk-tighten-fields" class="metric-value">—</div>
          </div>
        </div>
        <div class="panel">
          <form id="risk-account-form"></form>
          <div id="risk-error" class="error-box hidden"></div>
        </div>
```

Keep `#risk-account-form` and `#risk-error` inside the existing `.panel`. Do not move the form into the metrics row.

Paint from `GET /api/risk` (`account`, **`defaults`**):

| Tile | Value | Notes |
| --- | --- | --- |
| Tight | `overlayTighterCount(account, defaults)` | Hero. Count of numeric caps where account is stricter than v1 `AccountPolicy.defaults()`. `min_delta_*` stricter when account > defaults; other caps when account < defaults. Class `warn` when count > 0 |
| Delta $ | `fmtNum(account.min_delta_dollar, 2)` | Skip floor Caps does not show |
| Delta % | `fmtPct(account.min_delta_frac)` | Skip floor Caps does not show |
| Fields | `NUMERIC_CAPS.length` | Always 8 on v1; the count of keys the form can tighten |

Reuse `overlayTighterCount`. Do not invent a second comparison. Do not clone Caps Gross/Names/Orders tiles. Do **not** label any tile `Live` or `Tighter` (Sleeve overlays already owns **Tighter**).

`riskFormIsDirty` unchanged. Paint glance tiles even when the form is dirty so Tight/Deltas stay current. Do not `innerHTML = ""` the glance mounts.

`validateTighten` and PUT keys unchanged.

## 3. API

`GET /api/risk` adds `"defaults": _policy_to_dict(AccountPolicy.defaults())` beside `account` / `sleeves` / `utilization` / `labels`.

PUT `/api/risk` still reads only `account` and `sleeves`. A `defaults` key in the body is ignored. Do not persist ship defaults as an overlay.

## 4. Tokens

```css
#risk-tighten-tight.warn {
  color: #f59e0b;
}
```

Use a **separate** CSS block so token tests can regex the selector.

## 5. Help / README

`how_risk`: Tighten is four tiles Tight / Delta $ / Delta % / Fields. Tight is the hero. Tight counts account caps stricter than v1 defaults. Delta $ and Delta % are skip floors Caps does not show. Then groups Gross / Names / Orders / Deltas.

Cockpit / README: same.

## 6. In / out

**In:** Tighten glance tiles; `GET /api/risk` `defaults`; Tight vs v1 defaults; skip-floor tiles; tokens; help/README; HTML/CSS/JS/API/e2e tests.

**Out:** changing PUT / tighten math; cloning Caps Gross/Names/Orders onto Tighten; rewriting overlay cards; sixth screen; `app.js`; WebSockets; charts; accepting `defaults` on PUT.

## 7. Verification

- `#risk-tighten-tight`, `#risk-tighten-delta-dollar`, `#risk-tighten-delta-frac`, `#risk-tighten-fields` live inside `#risk-tighten`. Tight is the hero. `metrics-4`.
- `#risk-account-form` and `#risk-error` still inside Tighten, after the tiles.
- JS has `renderTightenGlance`, reuses `overlayTighterCount`, paints before `riskFormIsDirty` returns. `"Gross cap"` stays out of JS.
- `GET /api/risk` includes `defaults` matching `AccountPolicy.defaults()`. PUT with `defaults` does not change ship defaults or account unless `account` is also patched.
- Help contains `Tight / Delta $ / Delta % / Fields`. `#nav` still five screens. No `>Live<` label.
- No real broker orders.
