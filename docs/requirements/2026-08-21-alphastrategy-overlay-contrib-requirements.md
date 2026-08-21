# alphastrategy Sleeve overlays name contribution last against next

**Date:** 2026-08-21
**Status:** Requirements (improvement cycle on v1)
**Repo:** `AlphaStrategyAI/alphastrategy`
**Parent contract:** [`2026-08-19-alphastrategy-v1-requirements.md`](2026-08-19-alphastrategy-v1-requirements.md) §7, §8
**Related:** [`2026-08-21-alphastrategy-run-contrib-requirements.md`](2026-08-21-alphastrategy-run-contrib-requirements.md), [`2026-08-20-alphastrategy-overlay-cards-requirements.md`](2026-08-20-alphastrategy-overlay-cards-requirements.md)
**Technical design:** [`docs/plans/2026-08-21-alphastrategy-overlay-contrib-technical-design.md`](../plans/2026-08-21-alphastrategy-overlay-contrib-technical-design.md)

Paper only. Five screens. Quiet cockpit **tokens unchanged**. No sixth nav tab. No live. No WebSockets. No chart library. Do not revive `static/app.js`. `"Gross cap"` must not appear in assembled JS. `renderBanners` keeps a **single** `const reason`. Do not retry leftover orders. Resume does not catch up. Resume does **not** seed. Heartbeat still does **not** flatten. GET must not flatten. GET must **not** evaluate DSL. Keep `Next rebalance`. Keep Caps **four tiles**. Keep Headroom **four tiles**. Keep Sleeve overlays tiles **Spoken / Overlays / Tighter / Idle**. Keep After halt **Reason / Spent / Next / Resume**. Keep `live_limit.kind` book / send / unknown. Do **not** overwrite Cash composition labels. Each JS part stays ≤ 400 lines. **Do not feed `_place_batch` from `live_book()`.** Keep exact Start hint waits-for-resume and seed-hold sentences. Keep `formatHaltBanner` maps. Keep `sleeveState` four words. Keep `formatContributionInner`. Keep `Tighten this sleeve` details that stay open across refresh. Do **not** grow `paint-rails.js` / `paint-portfolio.js` past 400. Do **not** change CLI BOOK / HALT / LIMIT exact splitlines.

v1 §8 Risk is per-sleeve caps and allocation. Overlay cards already have an allocation rail and a tighter count. Run cards now name imported / paper / halted / stopped and contribution last against next (including weights wait). Overlay Spoken is a leftover percent with no rail. The operator who tightens a sleeve overlay that can flatten now cannot see that sleeve’s state or next send contribution on the same card. That is not 风险可控, 凭直觉交互, or 界面令人眼前一亮.

## 1. Why this increment exists

Goal check against current main (`4b09dd9`):

| Goal slice | v1 / later contract | Current desk |
| --- | --- | --- |
| 风险可控 | Overlay tighten can flatten now. The card must show the sleeve being tightened. | Card is an id, allocation %, rail, tighter line, form. |
| 凭直觉交互 | Same four sleeve words and same contribution grammar as Run. | Operator must leave Risk to see state / names / weights wait. |
| 界面令人眼前一亮 | Spoken is the overlay glance hero. Run Remaining is a rail. | Spoken is a number only. |
| 稳定执行 | Contribution is `alloc × last sleeve weights`. GET already exposes glance maps. | Unchanged engine; paint only. |

Research applied:

- **Tighten next to the book it constrains.** Risk desks put limit controls beside the sleeve’s proposed book, not a detached id. Reuse `sleeveState` and `formatContributionInner`. Do not invent a fifth sleeve word.
- **Spoken rail matches Remaining.** Fill = spoken share of 1. The hero number stays `fmtPct(spoken)`.
- **Do not dump last_sleeve_weights.** Cards read `/api/portfolio` maps already in `refresh()`.

Out: GET flatten; DSL on GET; placing; seeding on resume; dumping weight maps; fifth overlay tile; changing Tighten this sleeve dirty/open details; CLI splitlines; live; sixth nav.

## 2. Engine / API

No new endpoints. GET `/api/portfolio` already has `sleeve_contribution`, `last_sleeve_contribution`, `last_sleeve_weight_ids`. Overlay ids still come from GET `/api/risk` `sleeves`.

## 3. Cockpit

`paint-risk.js` overlay cards:

- `sleeve-head`: `h3` id + `sleeve-state` with the same class map as Run (`paper` → `status-running`, `halted` → `status-halt`, `stopped` → `status-stopped`, else muted).
- Keep muted Allocation line, allocation `paintUtilTrack`, tighter line, `Tighten this sleeve` details.
- After the allocation rail, `formatContributionInner` from portfolio maps for that id.

Overlay Spoken: HTML `#risk-overlay-spoken-bar` `util-track` under `#risk-overlay-spoken`. `renderOverlayGlance` calls `paintUtilTrack(bar, spoken, 1, "spoken " + fmtPct(spoken))`. Keep spoken warn ≥ 0.9 and < 1, fail ≥ 1.

No `window.confirm`. No `window.state`. `"Gross cap"` not in JS.

## 4. Help / README

Phrases (exact):

- `Sleeve overlays name contribution last against next`
- `Each overlay card names imported, paper, halted, or stopped`
- `Sleeve overlay Spoken is a rail`

Add the first two to `how_risk` after `Each overlay card is allocation rail and tighter count`. Add `Sleeve overlay Spoken is a rail` after `Spoken is the hero.` Add the first to `cockpit` after `Risk lists sleeve overlays as Spoken / Overlays / Tighter / Idle.`

README Operator after `Run Remaining is a rail.` Keep `Next rebalance`. Keep waits-for-resume. Keep `Tighten this sleeve stays open across the refresh`.

## 5. In / out

**In:** overlay card state + contribution; Spoken rail; help/README.

**Out:** GET flatten; DSL on GET; placing; seeding; weight maps in JSON; fifth overlay tile; CLI splitlines; live; sixth nav.

## 6. Verification

- JS: overlay cards call `sleeveState` and `formatContributionInner`; `risk-overlay-spoken-bar` + `paintUtilTrack` + `"spoken "`; keep `Tighten this sleeve` / `details`; `"Gross cap"` not in JS.
- HTML `id="risk-overlay-spoken-bar"` inside `#risk-overlays`. Keep four overlay tiles. Five `#nav` screens.
- Help contains the three phrases.
- `PYTHONPATH=src python3 -m pytest tests/alphastrategy/ -q`
