# alphastrategy overlay Tighten this sleeve survives the refresh

**Date:** 2026-08-20
**Status:** Requirements (improvement cycle on v1)
**Repo:** `AlphaStrategyAI/alphastrategy`
**Parent contract:** [`2026-08-19-alphastrategy-v1-requirements.md`](2026-08-19-alphastrategy-v1-requirements.md)
**Related:** [`2026-08-20-alphastrategy-overlay-cards-requirements.md`](2026-08-20-alphastrategy-overlay-cards-requirements.md)
**Technical design:** [`docs/plans/2026-08-20-alphastrategy-overlay-details-poll-technical-design.md`](../plans/2026-08-20-alphastrategy-overlay-details-poll-technical-design.md)

Paper only. Five screens. Quiet cockpit **tokens unchanged**. Keep overlay glance tiles, PUT keys, and `validateTighten`. Do not revive `static/app.js`. Account Tighten stays a visible grouped form, not `<details>`.

Overlay cards just moved the form under **Tighten this sleeve**. A 5s `refresh` still rebuilds `#risk-sleeves` unless an input has text or focus, so an open disclosure slams shut. Glance-then-action is not action if the desk closes it for you.

## 1. Why this increment exists

Goal check against current main (`186c38d`):

| Goal slice | v1 / later contract | Current desk |
| --- | --- | --- |
| 凭直觉交互 | Progressive disclosure: open the form, fill, Tighten | `riskFormIsDirty` ignores `<details open>`. Poll `innerHTML = ""` on `#risk-sleeves` closes it. |
| 易于使用 | `how_risk` names Tighten this sleeve | Does not say the disclosure survives the refresh. |
| 界面令人眼前一亮 | Cards are rail + tighter, then details | The details flicker closed every 5s while you read the fields. |
| 风险可控 | Tighten-only PUT unchanged | Unchanged. Do not skip glance paint (Tight / Spoken still move). |
| 架构 | `riskFormIsDirty` already gates the wipe | Treat `#screen-risk details[open]` as dirty. No API change. |

## 2. Dirty rule

`riskFormIsDirty` returns true when any of:

- a Risk form contains `document.activeElement`
- a Risk number input has a non-empty `value` (checkboxes skipped, as today)
- `#screen-risk details[open]` exists

`renderRisk` still paints Caps / Headroom / Tighten glance / overlay glance **before** the dirty return. Do not `innerHTML` the glance mounts.

Closing the details (and leaving inputs empty) lets the next poll rebuild cards.

## 3. Help / README

`how_risk`: opening **Tighten this sleeve** stays open across the refresh until you close it.

Cockpit / README: one sentence.

## 4. In / out

**In:** dirty includes open details; help/README; JS/help tests.

**Out:** persisting `open` in `state`; skipping glance paint; cloning account Tighten into details; API; sixth screen; `app.js`.

## 5. Verification

- `riskFormIsDirty` source contains `details[open]` scoped to `#screen-risk`.
- `renderTightenGlance` / `renderOverlayGlance` still run before `riskFormIsDirty` returns.
- Help contains `Tighten this sleeve stays open across the refresh`.
- Five `#nav` screens. No real broker.
