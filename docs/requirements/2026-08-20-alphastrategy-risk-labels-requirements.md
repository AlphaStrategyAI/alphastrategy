# alphastrategy spoken risk labels

**Date:** 2026-08-20
**Status:** Requirements (improvement cycle on v1)
**Repo:** `AlphaStrategyAI/alphastrategy`
**Parent contract:** [`2026-08-19-alphastrategy-v1-requirements.md`](2026-08-19-alphastrategy-v1-requirements.md)
**Technical design:** [`docs/plans/2026-08-20-alphastrategy-risk-labels-technical-design.md`](../plans/2026-08-20-alphastrategy-risk-labels-technical-design.md)

Paper only. Five screens. Quiet cockpit **tokens unchanged**. No sixth nav tab. No live. No WebSockets. No chart libraries. Policy **keys and tighten math stay**. Envelope YAML and `PUT /api/risk` still speak `max_gross`.

This cycle makes Risk **readable in the same language as Portfolio flatten budgets**, so a personal investor can tighten caps without decoding the API schema.

## 1. Why this increment exists

Goal check against current main (`f934034`, after glance bands):

| Goal slice | v1 / later contract | Current desk |
| --- | --- | --- |
| 风险可控 | §7 B-limits; §8 Risk: account totals always visible; UI refuses looser values | Engine, utilization rails, and Portfolio **Flatten budgets** (Gross, Names, Orders today) exist. Risk still paints `max_gross`, `max_name_weight`, `max_orders_per_day`. |
| 凭直觉交互 | §8 Quiet cockpit: dense numbers, sparse chrome; same job as the book, not a research lab | Portfolio says **Gross**. Risk says **max_gross**. Two vocabularies for one cap. |
| 易于使用 | Operator desk, not an HTTP debugger | Tighten forms use machine keys as visible labels. |
| 易于维护 | Shared numbers (utilization already lives in Python) | A second English map in `app.js` would drift from the engine. |
| 界面令人眼前一亮 | Glance bands grouped book vs flatten vs clock | Risk remains a dump of snake_case keys beside already-spoken utilization. |
| 帮助文档 / 架构 | Canonical `helptext`; C4 already shipped | Help is still one runbook blob (out of this cycle). `app.js` is still one file (out). |

Research applied (not a new schema):

- **Nielsen heuristic 2 (match the real world) and 4 (consistency):** the desk already chose Gross / Names / Orders today. Risk must reuse those words, not the storage keys.
- **ISO 9241-110:** the UI speaks the operator’s language; the API may keep the implementation language.
- **Broker / EMS blotters:** screens say “buying power”, not `max_buying_power_usd`. Wire format stays the key.
- **Quiet cockpit:** labels only. No new tokens, no charts, no sixth screen.

## 2. One spoken map (Python is source of truth)

Add `alphastrategy.risk.labels.POLICY_LABELS`: a dict covering **every** `AccountPolicy` field. `label_for(key)` returns the spoken string, or the key itself when unknown.

| Policy key | Spoken label |
| --- | --- |
| `max_gross` | Gross cap |
| `max_name_weight` | Name cap |
| `max_names` | Names |
| `max_order_notional_frac` | Order size |
| `max_orders_per_rebalance` | Orders / rebalance |
| `max_orders_per_day` | Orders today |
| `min_delta_dollar` | Min delta $ |
| `min_delta_frac` | Min delta % of equity |
| `long_only` | Long only |

Do **not** rename YAML, dataclasses, audit JSON, or PUT bodies.

## 3. API

`GET /api/risk` includes `"labels": { ...POLICY_LABELS }` next to `account`, `sleeves`, and `utilization`.

`PUT /api/risk` is unchanged: patches still use policy keys. Extra `labels` on PUT is ignored (not stored).

`GET /api/status` does not need `labels` this cycle (CLI JSON stays keys).

## 4. Quiet cockpit

`app.js` paints Risk caps, Risk tighten `<label>` text, and the Strategies **Risk** column through `policyLabel(key)` reading `state.risk.labels`. Input `name` attributes stay the keys so submit still PATCHes `max_gross`.

`app.js` must **not** hardcode the English map (no `"Gross cap"` string in JS). If labels have not loaded, show the key.

## 5. Help / README

One sentence: Risk names caps in desk words (Gross cap, Names, Orders today). Tighten still posts the policy keys.

## 6. In / out

**In:** Python label map; `GET /api/risk` `labels`; cockpit uses it for Risk + Strategies risk column; help/README; unit/API/JS/e2e tests.

**Out:** renaming stored keys; changing tighten/flatten math; screen-aware Diátaxis Help; splitting `app.js`; sixth screen; new tokens; live.

## 7. Verification

- `set(POLICY_LABELS) == {AccountPolicy field names}`.
- `label_for("max_gross") == "Gross cap"`; unknown key echoes the key.
- `GET /api/risk` has `labels.max_gross == "Gross cap"` and still has `account.max_gross`.
- `PUT /api/risk` with `{account: {max_name_weight: 0.15}}` still tightens.
- JS contains `function policyLabel` and `risk.labels`; JS does not contain `Gross cap`.
- Help contains `Gross cap`.
- Five `#nav` screens. No `window.confirm`. No real broker orders.
