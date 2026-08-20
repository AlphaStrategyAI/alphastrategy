# alphastrategy empty-desk band and paint rails

**Date:** 2026-08-20
**Status:** Requirements (improvement cycle on v1)
**Repo:** `AlphaStrategyAI/alphastrategy`
**Parent contract:** [`2026-08-19-alphastrategy-v1-requirements.md`](2026-08-19-alphastrategy-v1-requirements.md)
**Technical design:** [`docs/plans/2026-08-20-alphastrategy-empty-desk-technical-design.md`](../plans/2026-08-20-alphastrategy-empty-desk-technical-design.md)

Paper only. Five screens. Quiet cockpit **tokens unchanged**. No sixth nav tab. No live. No demo/ghost positions. Control ids `#first-run` and `data-go-screen` stay. Do not revive `static/app.js`.

This cycle makes the empty home match desk grammar, and splits shared utilization painters out of the Portfolio JS part so Risk Headroom is not painted from the wrong file.

## 1. Why this increment exists

Goal check against current main (`9c31b6f`):

| Goal slice | v1 / later contract | Current desk |
| --- | --- | --- |
| 凭直觉交互 | NN/g empty states live **in the empty container**. Diátaxis: import is a Strategies job; start paper is a Run job. | `#first-run` is a sibling of `#desk-banners` (desk-first-glance §3) so a generic panel sits above **every** screen. Strategies already has Import .asb. |
| 界面令人眼前一亮 | Portfolio is Book / Flatten budgets / Clock glance bands | Empty home is still `h2` + `.panel`, then the bands. The activation surface does not look like the desk. |
| 易于维护 | Cockpit JS parts match screens; each part ≤ 400 lines | `paint-portfolio.js` is 362 lines and owns `renderRiskUtilization` (Risk Headroom). |
| 组合管理 | Empty book must not look like a flattened book; no ghost fills | Keep real empty copy. Do **not** seed demo positions. |
| 帮助文档 | “An empty desk says Start this paper desk” | Copy still implies a global panel. |

Research applied:

- **NN/g empty states:** put the CTA in the empty region (Portfolio home), not as global chrome. Other screens already have their job empty states (Import .asb, Start paper, Tape zeros).
- **No fake book:** Lollypop/dashboard “preview data” is wrong for a trading desk. Keep Book / Flatten / Clock visible with em dashes so the operator sees the shape of a live desk.
- **Quiet cockpit:** reuse `glance-band` / `glance-heading`. Running token `#10b981` on the Start heading (same token family as LIVE / paper).
- **JS cohesion:** utilization rails and Risk Headroom belong in `js/paint-rails.js`, loaded after `core.js` and before screen painters.

This **supersedes** desk-first-glance §3 (first-run as a sibling of banners). `#first-run` moves **inside** `#screen-portfolio`.

## 2. Empty Portfolio band

Move `#first-run` to the **first child** of `#screen-portfolio`, before `#glance-book`.

```html
      <div id="first-run" class="glance-band first-run hidden" role="status">
        <h2 class="glance-heading">Start this paper desk</h2>
        <div class="panel">
          <p>Import a qualified .asb, then start a paper sleeve. Import is not permission to trade.</p>
          <button type="button" class="action primary" data-go-screen="strategies">Import .asb</button>
          <button type="button" class="action" data-go-screen="run">Open Run</button>
        </div>
      </div>
```

Keep `renderFirstRun`: show when `importedIds().length === 0`. Hidden on other screens because it is inside Portfolio.

CSS: `.first-run .glance-heading` and `.first-run .panel` use `#10b981`. `.first-run { }` still contains `#10b981` (locked-token test).

## 3. `js/paint-rails.js`

`JS_PARTS` becomes:

```text
js/core.js
js/paint-rails.js
js/paint-portfolio.js
js/paint-strategies.js
js/paint-run.js
js/paint-activity.js
js/paint-risk.js
js/boot.js
```

Move into `paint-rails.js` (keep function names): `wantedGotBar`, `paintUtilTrack`, `utilization`, `renderGrossUtilization`, `renderRemainingBudgets`, `renderCashComposition`, `renderRiskUtilization`, `nameCapBar`, `renderSleeveAllocBook`.

Leave in `paint-portfolio.js`: `renderFirstRun`, `renderSessionMetrics`, `renderBanners`, `renderPortfolio`, `pulseLabel`, `renderDeskPulse`.

Each part stays ≤ 400 lines. No `window.state`.

## 4. Help / README

`how_portfolio`: empty Portfolio starts with **Start this paper desk**, then Book / Flatten budgets / Clock.

Cockpit / README: empty Portfolio is that glance band, not a global panel.

## 5. In / out

**In:** first-run inside Portfolio as glance band; `paint-rails.js`; JS_PARTS; help/README; HTML/CSS/JS tests.

**Out:** ghost positions; sixth screen; new tokens; Supervisor/API change; reviving `app.js`; removing the two `data-go-screen` buttons.

## 6. Verification

- `#first-run` lives inside `#screen-portfolio` and **before** `#glance-book`. Heading `Start this paper desk` is `h2.glance-heading`.
- `#first-run` is **not** between banners and `#screen-portfolio`.
- `JS_PARTS` includes `js/paint-rails.js` immediately after `js/core.js`.
- `renderRiskUtilization` is in `paint-rails.js`, not `paint-portfolio.js`.
- Help contains that empty Portfolio is a Start this paper desk band. `#nav` still five screens.
- No real broker orders.
