# alphastrategy Strategies inventory bands

**Date:** 2026-08-20
**Status:** Requirements (improvement cycle on v1)
**Repo:** `AlphaStrategyAI/alphastrategy`
**Parent contract:** [`2026-08-19-alphastrategy-v1-requirements.md`](2026-08-19-alphastrategy-v1-requirements.md)
**Technical design:** [`docs/plans/2026-08-20-alphastrategy-strategies-inventory-technical-design.md`](../plans/2026-08-20-alphastrategy-strategies-inventory-technical-design.md)

Paper only. Five screens. Quiet cockpit **tokens unchanged**. No sixth nav tab. No live. No WebSockets. No chart libraries. No Supervisor or import-pipeline math change. Existing import **ids stay** so the upload painter keeps working.

This cycle makes Strategies match the desk grammar Portfolio and Run already use: a personal investor sees **how many** qualified bundles sit in each lifecycle state, **then** the import gate, **then** the roster — not two unlabeled CRUD panels.

## 1. Why this increment exists

Goal check against current main (`61409df`):

| Goal slice | v1 / later contract | Current desk |
| --- | --- | --- |
| 界面令人眼前一亮 | §8 Quiet cockpit: dense numbers, **sparse chrome**. Portfolio is Book / Flatten budgets / Clock. Run is Start paper / Sleeves / After halt / Flatten account. | Strategies is still `h2` Import bundle + Imported strategies. Same chrome as a generic form, not a desk. |
| 凭直觉交互 | §8 Strategies: state `imported` / `paper` / `halted` / `stopped`, allocation, risk summary. Import is not permission to trade. | Lifecycle lives only in a table column. An operator cannot answer “how many are paper vs sitting imported?” without scanning rows. Import and the roster look like the same job. |
| 策略管理 | Product is strategy **management and running**. Strategies is the inventory; Run is the working book. | Inventory has no first-glance counts. Paper (what is allowed to trade after a second action) is not the hero. |
| 风险可控 | Halted sleeves must not be visually quiet (§8 banners; operator desk). | Halted is a table cell. A halted book can look like a quiet imported list if the operator does not read the column. |
| 易于使用 / 帮助 | `how_strategies` already says upload, gate, start on Run. | How-to describes a gate plus a list; the layout still shows two generic panels. |
| 架构 | Cockpit JS is assembled from `js/` parts. | Edit `js/paint-strategies.js` only. Do not revive `static/app.js`. |

Research applied (not a new palette, not a sixth screen):

- **Endsley situation awareness / trading UI hierarchy:** first-glance status (how many in each state) before the action (import) and the detail (roster). Paper count is the hero because that is what the desk is allowed to run.
- **Gestalt proximity + common region:** Inventory counts, the import gate, and the roster are three regions. Import is not grouped with the roster as “the Strategies form.”
- **Nielsen visibility of system status:** the four v1 states are tiles, not only row text. Halted count uses halt color `#f59e0b` when greater than zero so halt is not quiet.
- **Quiet cockpit:** reuse `glance-band` / `glance-heading` / `.metric.hero` (1.85rem). No new tokens.

## 2. Three Strategies bands

Replace the Strategies screen’s two-panel stack with:

| id | heading | Contents (keep existing control ids) |
| --- | --- | --- |
| `#strat-inventory` | Inventory | Four tiles: Imported, Paper (**hero**), Halted, Stopped |
| `#strat-import` | Import .asb | `#import-form`, `#import-file`, upload button, `#import-error*` , `#import-ok` |
| `#strat-roster` | Roster | `#strategies-table` (Bundle, State, Allocation, Risk) |

Each band: `class="glance-band"`, child `h2.glance-heading`. Inventory then uses `.metrics.metrics-4.nums`. Import and Roster wrap their existing panel/table.

DOM order is awareness → gate → detail: inventory → import → roster. Do **not** put import beside the roster in a two-column grid (that would recreate “same family of jobs”).

Keep every existing import and table **id**. Upload still runs the same fail-closed pipeline. Start paper remains on Run. No allocation or kill controls on Strategies.

## 3. Inventory tiles

Tile value ids:

| Label | id | Hero / color |
| --- | --- | --- |
| Imported | `#strat-count-imported` | default |
| Paper | `#strat-count-paper` | **hero** (`class="metric hero"`). `status-running` (`#10b981`) when count > 0 |
| Halted | `#strat-count-halted` | `status-halt` (`#f59e0b`) when count > 0 |
| Stopped | `#strat-count-stopped` | `status-stopped` when count > 0 |

Counts are derived in `js/paint-strategies.js` from the existing `sleeveState(id, bundles, status)` helper (same four strings as the roster column). No new API field.

Empty inventory paints `0` on every tile and still shows the roster empty row. Do not skip painting counts when there are no bundles.

Band metric grid: `.metrics-4` is `repeat(4, minmax(0, 1fr))`. Below 640px: one column (`grid-template-columns: 1fr`), same breakpoint as `.metrics-3` / `.metrics-2`.

## 4. Help / README

`how_strategies`: Strategies is three bands **Inventory / Import .asb / Roster**. Paper is the hero count. The four tiles are the v1 states. Import is not permission to trade. Failures still name the gate. Start paper on Run.

Cockpit runbook and README Quiet cockpit: same three band names.

## 5. In / out

**In:** three Strategies bands; inventory counts; hero Paper; halt/running/stopped tile colors; `.metrics-4`; help/README; HTML/CSS/JS/help tests; e2e GET `/` includes `strat-inventory`.

**Out:** new tokens; sixth screen; Supervisor/API/import pipeline changes; changing import form ids; allocation or kill on Strategies; chart libraries; reviving `static/app.js`; putting import and roster side by side.

## 6. Verification

- HTML ids `strat-inventory`, `strat-import`, `strat-roster`. Headings `Inventory`, `Import .asb`, `Roster`.
- `#strat-count-paper` lives inside `#strat-inventory` on a `hero` metric. `#import-form` inside `#strat-import`. `#strategies-table` inside `#strat-roster`.
- CSS `.metrics-4` and `repeat(4, minmax(0, 1fr))`. `#nav` still five screens.
- Assembled JS contains `strat-count-paper` and paints halt class from counts.
- Help contains `Inventory / Import .asb / Roster`. GET `/` includes `id="strat-inventory"`.
- No real broker orders.
