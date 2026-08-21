# alphastrategy After halt is four tiles Reason / Spent / Next / Resume

**Date:** 2026-08-21
**Status:** Requirements (improvement cycle on v1)
**Repo:** `AlphaStrategyAI/alphastrategy`
**Parent contract:** [`2026-08-19-alphastrategy-v1-requirements.md`](2026-08-19-alphastrategy-v1-requirements.md) §7, §8
**Related:** [`2026-08-21-alphastrategy-halt-names-requirements.md`](2026-08-21-alphastrategy-halt-names-requirements.md)
**Technical design:** [`docs/plans/2026-08-21-alphastrategy-after-halt-technical-design.md`](../plans/2026-08-21-alphastrategy-after-halt-technical-design.md)

Paper only. Five screens. Quiet cockpit **tokens unchanged**. No sixth nav tab. No live. No WebSockets. No chart library. Do not revive `static/app.js`. `"Gross cap"` must not appear in assembled JS. `renderBanners` keeps a **single** `const reason`. Do not retry leftover orders. Resume does not catch up. Heartbeat still does **not** flatten. GET must not flatten. GET must **not** evaluate DSL. Keep `Next rebalance`. Keep Caps **four tiles**. Keep Headroom **four tiles**. Keep Positions glance **Rows / Wanted / Got / At cap**. Keep Sleeves glance **Remaining / Spoken / Active / Idle**. Keep `live_limit.kind` book / send / unknown. Keep Book LIMIT rail. Do **not** overwrite Cash composition labels. Each JS part stays ≤ 400 lines. **Do not feed `_place_batch` from `live_book()`.** Keep Start hint seed-hold and waits-for-resume copy. Keep HALT banner `formatHaltBanner`. Keep `status names HALT`. Do **not** rewrite persisted `halt_reason`. Keep `#account-resume` and `#run-halt-reason`.

v1 §8 Quiet cockpit: dense numbers, sparse chrome, halt cannot go visually quiet. Run already has Sleeves as four tiles (Remaining is the hero). After halt is still a panel paragraph of engine/desk copy plus a button — the weakest band on the primary kill-switch screen. That is not 眼前一亮 or 凭直觉交互: spent, held, and wait are Clock/Start words the operator already knows, but After halt does not show them as instruments.

## 1. Why this increment exists

Goal check against current main (`a334ac2`):

| Goal slice | v1 / later contract | Current desk |
| --- | --- | --- |
| 眼前一亮 | After halt matches Sleeves / Clock glance chrome. | One muted/warn paragraph in a panel. |
| 凭直觉交互 | Reason / Spent / Next / Resume are readable without scanning prose. | Spent lives on Clock Last; held lives on Clock Next; After halt repeats the reason only. |
| 易于使用 | Help: After halt is four tiles Reason / Spent / Next / Resume. | Help only says After halt shows the halt reason. |
| 可靠 | Reason still maps seed-hold through `formatHaltBanner`; sub keeps the engine tell (sleeve id). | Engine string is the only After halt value. |

Research applied:

- **Same glance grammar as Sleeves.** Four tiles, first is hero. Reason wraps at 1.15rem (do not blow a paragraph to 2.35rem).
- **Reuse desk words.** Spent / held / wait already exist on Clock and Start. Do not invent a fifth halt taxonomy.
- **Keep Resume as an explicit action.** The Resume tile is state (`wait` / `—`), not a replacement for `#account-resume`.

Out: GET flatten; DSL on GET; placing; rewriting halt_reason; changing Start hint copy; live; sixth screen; growing `paint-portfolio.js` / `paint-rails.js` past 400.

## 2. Engine / API

No supervisor or API schema change. Tiles read GET `/api/status`: `halted`, `halt_reason`, `last_rebalance_complete`, `last_rebalance_event`.

## 3. Cockpit

`#run-recover` After halt:

```text
Reason (hero) / Spent / Next / Resume
```

| Tile | id | Halted (or halt_reason) | Idle |
| --- | --- | --- | --- |
| Reason | `#run-halt-reason` | `formatHaltBanner(reason, state)` warn | `—` |
| Reason sub | `#run-halt-reason-sub` | raw `halt_reason` when it differs from the banner text, else `—` | `—` |
| Spent | `#run-halt-spent` | `spent` warn when `last_rebalance_complete === false`, else `—` | same spent rule (spent window is independent of halt) |
| Next | `#run-halt-next` | `held` warn | `—` |
| Resume | `#run-halt-resume` | `wait` warn | `—` |

Hint `#run-halt-hint` under the tiles (not the hero):

- halted and seed prefix → exact `Start paper that cannot seed last weights holds. Resume does not catch up.`
- other halt → `Resume does not catch up.`
- idle → exact `Resume is only after halt.`

Keep the Resume after halt button and `#run-recover-error` in the panel below. No `innerHTML` in `renderRunRecover`. No `Order size` / `Gross cap` in JS.

CSS: `#run-recover .metric.hero .metric-value` is `1.15rem` / normal wrap (tokens otherwise unchanged). `#run-halt-reason.warn`, `#run-halt-spent.warn`, `#run-halt-next.warn`, `#run-halt-resume.warn` use `#f59e0b`. Keep `.recover-zone` heading color.

## 4. Help / README

Phrase (exact): `After halt is four tiles Reason / Spent / Next / Resume`

Add to `cockpit` (after Run Sleeves is Remaining / Spoken / Active / Idle), `how_run` (after Sleeves is four tiles… Remaining is the hero), `halt_flatten` (after HALT names Start paper that cannot seed last weights holds). Keep `After halt shows the halt reason`. Keep `After halt names the spent session event`.

README Operator after HALT names Start paper that cannot seed last weights holds. Keep `Next rebalance`.

## 5. In / out

**In:** After halt four-tile glance; hint under tiles; CSS wrap for Reason hero; help/README; HTML / JS / CSS tests.

**Out:** GET flatten; DSL on GET; placing; rewriting halt_reason; changing Start hint; live; sixth nav.

**Done when:**

1. Recover HTML has `metrics-4`, Reason hero, Spent / Next / Resume ids, `#run-halt-hint`, and still `#account-resume` / `#run-halt-reason`.
2. `renderRunRecover` paints `formatHaltBanner`, `spent`, `held`, `wait`, both hint sentences, no `innerHTML`.
3. CSS Reason hero is 1.15rem; warn tiles use `#f59e0b`.
4. Help contains the phrase. Five `#nav` screens. `"Gross cap"` not in assembled JS. No real broker.
