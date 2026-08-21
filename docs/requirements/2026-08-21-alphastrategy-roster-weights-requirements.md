# alphastrategy Roster names when a paper sleeve has no last weights

**Date:** 2026-08-21
**Status:** Requirements (improvement cycle on v1)
**Repo:** `AlphaStrategyAI/alphastrategy`
**Parent contract:** [`2026-08-19-alphastrategy-v1-requirements.md`](2026-08-19-alphastrategy-v1-requirements.md) §5, §8
**Related:** [`2026-08-21-alphastrategy-wait-weights-requirements.md`](2026-08-21-alphastrategy-wait-weights-requirements.md), [`2026-08-21-alphastrategy-resume-seed-requirements.md`](2026-08-21-alphastrategy-resume-seed-requirements.md), [`2026-08-20-alphastrategy-strategies-inventory-requirements.md`](2026-08-20-alphastrategy-strategies-inventory-requirements.md)
**Technical design:** [`docs/plans/2026-08-21-alphastrategy-roster-weights-technical-design.md`](../plans/2026-08-21-alphastrategy-roster-weights-technical-design.md)

Paper only. Five screens. Quiet cockpit **tokens unchanged**. No sixth nav tab. No live. No WebSockets. No chart library. Do not revive `static/app.js`. `"Gross cap"` must not appear in assembled JS. `renderBanners` keeps a **single** `const reason`. Do not retry leftover orders. Resume does not catch up. Resume does **not** seed. Heartbeat still does **not** flatten. GET must not flatten. GET must **not** evaluate DSL. Keep `Next rebalance`. Keep Caps **four tiles**. Keep Headroom **four tiles**. Keep Positions glance **Rows / Wanted / Got / At cap**. Keep After halt **Reason / Spent / Next / Resume**. Keep Strategies Inventory **Imported / Paper / Halted / Stopped**. Keep Roster columns **Bundle / State / Allocation / Risk** (`colspan='4'`). Keep `live_limit.kind` book / send / unknown. Keep Book LIMIT rail. Do **not** overwrite Cash composition labels. Each JS part stays ≤ 400 lines. **Do not feed `_place_batch` from `live_book()`.** Keep exact Start hint waits-for-resume and seed-hold sentences. Keep `formatHaltBanner` seed and resume-does-not-seed maps. Do **not** rewrite persisted `halt_reason`. Keep `sleeveState` four words `imported` / `paper` / `halted` / `stopped`.

v1 §8 Strategies is imported list: state, allocation, risk summary. After #93–#97, Caps / Clock Next / After halt name a paper sleeve with no last weights as **weights**. Strategies Roster and Run sleeve cards still paint a healthy allocation number. After Resume, inventory looks paper-ready while Caps cannot dry-run. That is not 可靠, 凭直觉交互, or 界面令人眼前一亮.

## 1. Why this increment exists

Goal check against current main (`35606a3`):

| Goal slice | v1 / later contract | Current desk |
| --- | --- | --- |
| 可靠 | Missing last weights stay visible until Start paper seeds. | Caps/Clock/After halt wait; Roster still looks like a funded paper sleeve. |
| 凭直觉交互 | Same desk word **weights** on the screen that lists sleeves. | Operator must leave Strategies to learn Caps cannot dry-run. |
| 界面令人眼前一亮 | Strategies is inventory, not a leftover spreadsheet. | Allocation is a percent; Run already paints a rail. |
| 易于使用 | Help names Roster imported at; Caps LIMIT waits. | Help never says Roster names the missing-weights wait. |
| 风险可控 | GET does not eval DSL; Resume does not seed. | Unchanged; this increment is glance + naming, not orders. |

Research applied:

- **Fail visible on the management list.** Trading desks show “can this book be sent,” not only “is it allocated.” Presence of persisted `last_sleeve_weights` is that tell. Do not infer it from contribution glance (another sleeve missing weights keeps last contribution only, which false-positives a seeded sibling).
- **Presence, not the map.** GET must not dump `last_sleeve_weights` (strategy weights, payload size). Sorted ids with a non-empty dict are enough for paint.
- **Same word as Clock Next.** Subtext is `weights` + warn `#f59e0b`. Do not invent a fifth sleeve state. Do not change `sleeveState`.
- **Recognition on Run too.** Run cards are the allocation control. Reuse one helper. Do not add a fifth Run glance tile.

Out: GET flatten; DSL on GET; placing; seeding on resume; dumping weight maps; sixth screen; changing Inventory tiles; adding a Roster contribution column.

## 2. Engine / API

Add `last_sleeve_weight_ids(snapshot) -> list[str]` in `src/alphastrategy/risk/utilization.py` next to the other glance helpers:

- Walk `snapshot.last_sleeve_weights`.
- Include `str(bundle_id)` when the value is a **non-empty** `dict`.
- Skip empty dicts, non-dicts, and missing ids.
- Return **sorted** unique ids.
- Do **not** evaluate DSL. Do **not** read sleeves/allocation (presence is independent of stop).

GET `/api/portfolio` adds `"last_sleeve_weight_ids": last_sleeve_weight_ids(snapshot)` next to `last_sleeve_contribution`.

Must **not** include a `"last_sleeve_weights"` key.

GET still must not flatten (`close_all` unchanged). After seed-fail + resume (`asb_z` 0.18, no evaluator): `asb_z` is not in `last_sleeve_weight_ids`; `live_limit.kind` stays `"unknown"`.

Partial: `asb_x` has `{AAPL: 1.0}` and `asb_z` has `{}` or is missing → `["asb_x"]` only.

## 3. Cockpit

`core.js` helpers (do not grow `paint-rails.js` / `paint-portfolio.js`):

- `sleeveHasLastWeights(bundleId)` — `indexOf` on `state.portfolio.last_sleeve_weight_ids`.
- `formatWeightsWaitSub(bundleId, alloc)` — if `Number(alloc) > 0` and not `sleeveHasLastWeights`, return `<div class="metric-sub nums warn">weights</div>`; else `""`.

Roster Allocation cell: `fmtPct(alloc)`, a `data-alloc-rail` `util-track` painted with `paintUtilTrack(track, alloc, 1, "allocation " + fmtPct(alloc))` (same grammar as Run), then `formatWeightsWaitSub(id, alloc)`. Keep Bundle / State / Risk. Keep imported-at date sub. Empty still `colspan='4'`.

Run sleeve cards: after the existing allocation rail, append `formatWeightsWaitSub(id, alloc)`. Keep Stop / Kill / Set allocation. Keep Remaining / Spoken / Active / Idle tiles.

CSS warn token `#f59e0b` for `#strategies-table .metric-sub.warn` and `.sleeve-card .metric-sub.warn`.

Do not use `innerHTML` for the wait word except the existing cell template (same as contribution last sub). No `window.confirm`. No `window.state`.

## 4. Help / README

Phrase (exact): `Roster names when a paper sleeve has no last weights`

Add to `how_strategies` after `Roster names imported at`. Add to `cockpit` after `Paper is the hero count.` Add to `how_run` after `Allocation is a rail.` (`Run sleeves name when a paper sleeve has no last weights` is allowed as surrounding copy; the required phrase is the Roster sentence.)

README Operator after `Caps LIMIT waits when a paper sleeve has no last weights.` Keep `Next rebalance`. Keep waits-for-resume. Keep `Resume does not seed last weights`.

## 5. In / out

**In:** `last_sleeve_weight_ids` glance helper + GET `/api/portfolio`; Roster allocation rail + `weights` wait sub; Run card wait sub; CSS warn; help/README.

**Out:** GET flatten; DSL on GET; placing; seeding on resume; `"last_sleeve_weights"` in the portfolio JSON; fifth sleeve state; fifth Inventory tile; Roster contribution column; live; sixth nav.

## 6. Verification

- Unit: empty / non-empty / empty-dict ids; sorted.
- API: lists ids; omits weight maps; omits id when paper sleeve has no last weights; resume after seed-fail keeps unknown LIMIT and omits `asb_z`; GET does not flatten.
- JS: `formatWeightsWaitSub` / `last_sleeve_weight_ids` / Roster `paintUtilTrack` + `data-alloc-rail`; Run cards call the helper; `"Gross cap"` not in JS.
- CSS warn `#f59e0b`.
- Help contains the Roster sentence. Five `#nav` screens. `colspan='4'`.
- `PYTHONPATH=src python3 -m pytest tests/alphastrategy/ -q`
