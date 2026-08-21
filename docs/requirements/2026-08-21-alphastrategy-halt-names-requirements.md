# alphastrategy HALT names Start paper that cannot seed last weights holds

**Date:** 2026-08-21
**Status:** Requirements (improvement cycle on v1)
**Repo:** `AlphaStrategyAI/alphastrategy`
**Parent contract:** [`2026-08-19-alphastrategy-v1-requirements.md`](2026-08-19-alphastrategy-v1-requirements.md) §7, §8, §9
**Related:** [`2026-08-21-alphastrategy-seed-hold-requirements.md`](2026-08-21-alphastrategy-seed-hold-requirements.md)
**Technical design:** [`docs/plans/2026-08-21-alphastrategy-halt-names-technical-design.md`](../plans/2026-08-21-alphastrategy-halt-names-technical-design.md)

Paper only. Five screens. Quiet cockpit **tokens unchanged**. No sixth nav tab. No live. No WebSockets. No chart library. Do not revive `static/app.js`. `"Gross cap"` must not appear in assembled JS. `renderBanners` keeps a **single** `const reason`. Do not retry leftover orders. Resume does not catch up. Heartbeat still does **not** flatten. GET must not flatten. GET must **not** evaluate DSL. Keep `Next rebalance`. Keep Caps **four tiles**. Keep Headroom **four tiles**. Keep Positions glance **Rows / Wanted / Got / At cap**. Keep `live_limit.kind` book / send / unknown. Keep Book LIMIT rail. Do **not** overwrite Cash composition labels. Each JS part stays ≤ 400 lines. **Do not feed `_place_batch` from `live_book()`.** Keep `Start paper while halted waits for resume`. Keep `Start paper seeds last sleeve weights`. Keep `Start paper that cannot seed last weights holds` on Run Start hint and CLI paper start. Keep overlay-on-start flatten. Illegal DSL / sandbox failure is **halt, not flatten**. Do **not** rewrite persisted `halt_reason`.

v1 §7/§8: health halt must be visible in desk words; halt/deviation banners cannot go quiet. After #94, Run Start hint and `paper start` stderr name seed-hold. The loud surfaces still dump the engine string `start paper seeds last sleeve weights: no evaluator for sleeve …` on `#halt-banner` and After halt, and `alphastrategy status` stderr never says HALT (only BOOK / PNL / LIMIT). The operator who did not just press Start paper still reads sandbox English. That is not 凭直觉交互, 易于使用, or status-as-instrument.

## 1. Why this increment exists

Goal check against current main (`42a81a4`):

| Goal slice | v1 / later contract | Current desk |
| --- | --- | --- |
| 凭直觉交互 | HALT banner and After halt use the same seed-hold tell as Start paper. | Banner / After halt print the prefixed engine string. |
| 易于使用 | `status` names HALT the way it names LIMIT / BOOK / PNL. | JSON has `halt_reason`; stderr is silent while HALTED. |
| 可靠 | Other health halts still show the stored reason. | Do not invent a second halt taxonomy. |
| 风险可控 | Halt is not flatten. | Unchanged; this increment is naming only. |

Research applied:

- **Map at the paint/CLI edge.** Keep snapshot `halt_reason` as the engine tell (prefix + sleeve id). Banner, After halt, and status stderr map the seed prefix to desk words.
- **Status is an instrument.** When `halted` is true, stderr prints a `HALT:` line. Seed prefix uses desk words; every other halt prints `HALT: {halt_reason or state}`.
- **Keep Start hint copy exact.** Do not change waits-for-resume or seed-hold Run sentences.

Out: GET flatten; DSL on GET; placing; rewriting snapshot halt_reason; changing wait-for-resume copy; live; sixth screen; growing `paint-portfolio.js` / `paint-rails.js` past 400 lines.

## 2. Engine / API

No supervisor or POST schema change. `halt_reason` stays `start paper seeds last sleeve weights: ` + exception. GET `/api/status` already returns `halted` and `halt_reason`.

CLI `_print_status` after PNL and before LIMIT:

- If `halted` is not true → no HALT line (keep exact BOOK / PNL / LIMIT splitlines).
- If `halt_reason` contains `start paper seeds last sleeve weights` (case insensitive) → `HALT: start paper that cannot seed last weights holds`
- Else → `HALT: {halt_reason or state or halted}`

## 3. Cockpit

`formatHaltBanner(reason, fallback)` in `js/core.js` (do not grow `paint-portfolio.js`):

- If `reason` matches `/start paper seeds last sleeve weights/i` → `start paper that cannot seed last weights holds`
- Else → `reason || fallback || "halted"`

`renderBanners` halt text: `"HALT: " + formatHaltBanner(reason, state.status && state.status.state)`. Keep a **single** `const reason`. Keep flatten / LIMIT / deviation / kill banners.

`renderRunRecover`: if the same prefix, warn copy `Start paper that cannot seed last weights holds. Resume does not catch up.` Else keep `reason || state || "halted"`. Idle stays exact `Resume is only after halt.` No `innerHTML`. No `Order size` / `Gross cap` in JS.

Keep `renderRunStartHint` seed-hold and waits-for-resume sentences unchanged.

## 4. Help / README

Phrases (exact):

- `HALT names Start paper that cannot seed last weights holds`
- `status names HALT`

Add `HALT names Start paper that cannot seed last weights holds` to `execution` (after Start paper that cannot seed last weights holds), `halt_flatten` (same), `how_portfolio` (after the deviation banner sentence), `how_run` (after After halt shows the halt reason).

Add `status names HALT` to `cli` (after status names Day PnL).

README Operator after Start paper that cannot seed last weights holds. Keep `Next rebalance`. Keep waits-for-resume. Keep Start paper seeds last sleeve weights.

## 5. In / out

**In:** `formatHaltBanner`; HALT banner desk words for seed-hold; After halt seed-hold sentence; status stderr `HALT:` when halted; help/README; JS + CLI + help tests.

**Out:** GET flatten; DSL on GET; placing; rewriting snapshot halt_reason; changing Start hint copy; live; sixth nav.

**Done when:**

1. Assembled JS `formatHaltBanner` maps the seed prefix to `start paper that cannot seed last weights holds`; `renderBanners` still has exactly one `const reason`.
2. After halt JS contains both the seed-hold sentence and exact `Resume is only after halt.`
3. `alphastrategy status` with halted + seed prefix prints `HALT: start paper that cannot seed last weights holds`; non-seed halt prints `HALT:` plus the stored reason; existing BOOK / PNL / LIMIT exact stderr tests stay green.
4. Help contains both phrases. Five `#nav` screens. `"Gross cap"` not in assembled JS. No real broker.
