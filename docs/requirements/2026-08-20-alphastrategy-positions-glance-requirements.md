# alphastrategy Portfolio Positions glance tiles

**Date:** 2026-08-20
**Status:** Requirements (improvement cycle on v1)
**Repo:** `AlphaStrategyAI/alphastrategy`
**Parent contract:** [`2026-08-19-alphastrategy-v1-requirements.md`](2026-08-19-alphastrategy-v1-requirements.md)
**Technical design:** [`docs/plans/2026-08-20-alphastrategy-positions-glance-technical-design.md`](../plans/2026-08-20-alphastrategy-positions-glance-technical-design.md)

Paper only. Five screens. Quiet cockpit **tokens unchanged**. No sixth nav tab. No live. No WebSockets. No chart library. Keep `#positions-table`, `#sleeves-table`, `.book-grid`, wanted-only rows, and the Book Drift tile. Do not revive `static/app.js`. Do not hardcode `Gross cap` in JS. Do not clone Run Remaining / Spoken / Active / Idle onto Portfolio Sleeves.

This cycle makes **Positions** and **Sleeves** use the same glance grammar as Book / Clock: a labeled band first, then the table. Positions adds four count tiles so a personal investor does not have to subtract a seven-column book to learn how many names are intended, filled, or sitting on the single-name stop.

## 1. Why this increment exists

Goal check against current main (`e7a25cd`):

| Goal slice | v1 / later contract | Current desk |
| --- | --- | --- |
| 组合管理 | §8 Portfolio: combined positions, sleeve contribution | Book is Equity / Cash / PnL / Drift. Drift is names *off target*. The holdings table is still a generic `h2` + `.panel`. Wanted-only rows exist, but the operator cannot see “how many names the desk wants” without counting rows. |
| 风险可控 | §7 single-name weight ≤ 20% flatten. Positions already have a Cap rail per row | Cap hits are invisible until the operator scans every Cap cell. |
| 凭直觉交互 | Rebalancing dashboards: KPI row, then holdings (MarketXLS pass-1 tiles, then the screener). Target vs actual without spreadsheet subtraction (Stock Rover) | Book Drift answers “how many drifted.” It does not answer intended vs filled vs at the name cap. |
| 界面令人眼前一亮 | Strategies Roster, Activity Blotter, Risk bands are glance regions | Positions and Sleeves are the last Portfolio chrome that still looks like a leftover spreadsheet pair. |
| 易于使用 | `how_portfolio` names Book / Flatten budgets / Clock | Still says “three bands.” Does not say Positions is Rows / Wanted / Got / At cap. |
| 易于维护 | `GET /api/portfolio` already returns `wanted`, `qty`, `weight` | Count on the client from that array. No API change. Paint in `js/paint-portfolio.js`. |

Research applied:

- **KPI then table:** MarketXLS-class rebalancing sheets put Out of Band / Largest Drift on a two-second pass, then the holdings screener. This desk already put Drift on Book. Positions tiles are the *holdings* pass: row count, intended names, filled names, name-cap hits.
- **Do not duplicate Drift:** Off-target count stays on Book. Positions Wanted is names with `wanted > 0`, not names whose gap exceeds min delta.
- **Gestalt common region:** Positions and Sleeves become `#glance-positions` and `#glance-sleeves` inside the existing `.book-grid`. Keep side-by-side from `min-width: 800px`.
- **Run wall:** Sleeves on Portfolio is contribution + spoken rail. Do not paint Remaining / Spoken / Active / Idle here (Run Sleeves already does).

## 2. Positions tiles

Inside `#glance-positions`, above `#positions-table` (keep the table and its seven columns):

```html
        <div id="glance-positions" class="glance-band">
          <h2 class="glance-heading">Positions</h2>
          <div class="metrics metrics-4 nums">
            <div class="metric">
              <div class="metric-label">Rows</div>
              <div id="pos-count-rows" class="metric-value">—</div>
            </div>
            <div class="metric hero">
              <div class="metric-label">Wanted</div>
              <div id="pos-count-wanted" class="metric-value">—</div>
            </div>
            <div class="metric">
              <div class="metric-label">Got</div>
              <div id="pos-count-got" class="metric-value">—</div>
            </div>
            <div class="metric">
              <div class="metric-label">At cap</div>
              <div id="pos-count-cap" class="metric-value">—</div>
            </div>
          </div>
          <div class="panel">
            <table id="positions-table">…</table>
          </div>
        </div>
```

`renderPositionsGlance` in `js/paint-portfolio.js` fills from the same `portfolio.positions` array the table uses (no API change).

| Tile | Value | Notes |
| --- | --- | --- |
| Rows | `positions.length` | Includes wanted-only rows. Empty book is `0`, not an em dash |
| Wanted | names with `wanted` set and `wanted > 0` | Hero |
| Got | names with `qty != 0` | Wanted-only rows (qty 0) do not count |
| At cap | names with `weight >=` account `max_name_weight` (default `0.2` if risk has not loaded) | Class `fail` on the value when the count is `> 0` |

Missing positions array: paint `0` on every tile. Do not skip the painter when the table shows empty copy.

## 3. Sleeves band

Wrap the existing sleeve rail + `#sleeves-table` in `#glance-sleeves` with heading `Sleeves`. Keep `#sleeve-alloc-label`, `#sleeve-alloc-track`, and the three table columns. **No** Remaining / Spoken / Active / Idle tiles.

```html
        <div id="glance-sleeves" class="glance-band">
          <h2 class="glance-heading">Sleeves</h2>
          <p id="sleeve-alloc-label" class="muted hidden"></p>
          <div id="sleeve-alloc-track" class="util-track hidden" aria-hidden="true"></div>
          <div class="panel">
            <table id="sleeves-table">…</table>
          </div>
        </div>
```

Keep the wrapper `class="grid book-grid stack"` around both bands.

## 4. Tokens

```css
#pos-count-cap.fail {
  color: #ef4444;
}
```

Separate block so token tests can regex the selector. No new colors.

## 5. Help / README

`how_portfolio`: after Book / Flatten budgets / Clock, Positions / Sleeves. Positions is four tiles Rows / Wanted / Got / At cap. Wanted is the hero.

Cockpit / README: same phrase. Keep the required substring `Book / Flatten budgets / Clock`.

## 6. In / out

**In:** Positions glance tiles; Sleeves glance band chrome; fail token on At cap; help/README; HTML/CSS/JS tests. Keep `renderPositionsGlance` in `paint-portfolio.js`.

**Out:** changing Book Drift math; cloning Run sleeve tiles; sixth screen; `app.js`; WebSockets; charts; API/Supervisor schema; Live label; removing wanted-only rows or the Book column; Clock `#clock-line` rewrite.

## 7. Verification

- `#pos-count-rows`, `#pos-count-wanted`, `#pos-count-got`, `#pos-count-cap` live inside `#glance-positions`. Wanted is the hero. `metrics-4`. `#positions-table` still inside that band.
- `#glance-sleeves` contains `#sleeves-table`. `.book-grid` still wraps both bands.
- JS paints those ids from `wanted` / `qty` / `weight`. `Gross cap` still absent from JS.
- Help contains `Rows / Wanted / Got / At cap`. `#nav` still five screens.
- No real broker orders.
