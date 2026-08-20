# alphastrategy Run Sleeves capacity tiles

**Date:** 2026-08-20
**Status:** Requirements (improvement cycle on v1)
**Repo:** `AlphaStrategyAI/alphastrategy`
**Parent contract:** [`2026-08-19-alphastrategy-v1-requirements.md`](2026-08-19-alphastrategy-v1-requirements.md)
**Technical design:** [`docs/plans/2026-08-20-alphastrategy-run-capacity-technical-design.md`](../plans/2026-08-20-alphastrategy-run-capacity-technical-design.md)

Paper only. Five screens. Quiet cockpit **tokens unchanged**. No sixth nav tab. No live. No WebSockets. No chart library. Keep the four Run bands and existing control ids. Do not revive `static/app.js`.

This cycle makes Run **Sleeves** use the same glance grammar as Inventory / Beat: Remaining, Spoken, Live, and Idle as tiles — not a blank card stack — and names the empty book.

## 1. Why this increment exists

Goal check against current main (`e987d01`):

| Goal slice | v1 / later contract | Current desk |
| --- | --- | --- |
| 风险可控 | §5 `Σ allocation_i <= 1`. Residual is cash. | Portfolio Sleeves has a spoken-for rail. Run is where the operator **sets** allocation, and it does not show remaining book. |
| 凭直觉交互 | Recognition over recall. NN/g empty states name what belongs here. | Empty `#run-sleeves` is a void. The start form is above; the operator cannot see Live vs Idle vs leftover capacity. |
| 界面令人眼前一亮 | Strategies Inventory, Activity Beat, Book are `metrics-4` | Sleeves is only cards (or nothing). Last core action screen without glance tiles. |
| 易于使用 | `how_run` names four bands | Does not say Sleeves is Remaining / Spoken / Live / Idle. |
| 可靠 | Header now shows Session and Supervisor on every screen | Run still cannot answer “how much book is left before Start paper.” |

Research applied:

- **Budget remaining (flatten-budget rails already on Portfolio):** show unused capacity next to the control that spends it. Do not add a fifth Run band (kill-switch ladder stays promote → sleeves → recover → flatten).
- **NN/g empty states:** empty sleeves copy points at Import, then Start paper. No ghost sleeves.
- **Quiet cockpit:** reuse `metrics metrics-4` and `metric hero`. Remaining uses warn/fail tokens at 90% / 100% spoken (same thresholds as the Portfolio spoken rail).

Header Session / Supervisor stay in chrome. Do not duplicate them on Run.

## 2. Sleeves tiles

Inside `#run-book`, after the Sleeves heading and **before** `#run-sleeve-error` / `#run-sleeves`:

```html
        <div class="metrics metrics-4 nums">
          <div class="metric hero">
            <div class="metric-label">Remaining</div>
            <div id="run-remaining" class="metric-value">—</div>
          </div>
          <div class="metric">
            <div class="metric-label">Spoken</div>
            <div id="run-spoken" class="metric-value">—</div>
          </div>
          <div class="metric">
            <div class="metric-label">Live</div>
            <div id="run-count-live" class="metric-value">—</div>
          </div>
          <div class="metric">
            <div class="metric-label">Idle</div>
            <div id="run-count-idle" class="metric-value">—</div>
          </div>
        </div>
```

Paint from existing `state.bundles` in `renderRunSleeves` (no API change):

| Tile | Value | Notes |
| --- | --- | --- |
| Remaining | `fmtPct(max(0, 1 − spoken))` | Hero. Class `warn` when spoken ≥ 0.9 and < 1. Class `fail` when spoken ≥ 1 |
| Spoken | `fmtPct(Σ paper allocation)` | Sum of `bundles.paper` values |
| Live | count of ids with allocation > 0 | |
| Idle | count of ids with allocation 0 (imported or paper-zero) | Includes never-started and stopped-at-zero |

Empty `#run-sleeves` (no bundle ids): `No sleeves yet. Import a qualified .asb, then start paper.`

Keep sleeve cards, Stop / Kill, and dirty-form skip unchanged.

## 3. Tokens

```css
#run-remaining.warn {
  color: #f59e0b;
}

#run-remaining.fail {
  color: #ef4444;
}
```

## 4. Help / README

`how_run`: still four bands. Sleeves is four tiles Remaining / Spoken / Live / Idle. Remaining is the hero.

Cockpit / README: same phrase.

## 5. In / out

**In:** Sleeves glance tiles; empty sleeves copy; warn/fail tokens; help/README; HTML/CSS/JS tests.

**Out:** fifth Run band; header kill switch; changing Start paper / flatten ritual; API/Supervisor schema; `app.js`; WebSockets.

## 6. Verification

- `#run-remaining`, `#run-spoken`, `#run-count-live`, `#run-count-idle` live inside `#run-book`. Remaining is the hero. `metrics-4`.
- `#run-sleeves`, `#start-form`, `#account-resume`, `#account-kill` keep their bands.
- JS paints remaining from `1 - spoken`. Empty copy includes `No sleeves yet`.
- Help contains `Remaining / Spoken / Live / Idle`. `#nav` still five screens.
- No real broker orders.
