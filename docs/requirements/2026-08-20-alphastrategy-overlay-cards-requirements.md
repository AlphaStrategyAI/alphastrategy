# alphastrategy Risk overlay cards are glance then action

**Date:** 2026-08-20
**Status:** Requirements (improvement cycle on v1)
**Repo:** `AlphaStrategyAI/alphastrategy`
**Parent contract:** [`2026-08-19-alphastrategy-v1-requirements.md`](2026-08-19-alphastrategy-v1-requirements.md)
**Related:** [`2026-08-20-alphastrategy-risk-overlays-requirements.md`](2026-08-20-alphastrategy-risk-overlays-requirements.md)
**Technical design:** [`docs/plans/2026-08-20-alphastrategy-overlay-cards-technical-design.md`](../plans/2026-08-20-alphastrategy-overlay-cards-technical-design.md)

Paper only. Five screens. Quiet cockpit **tokens unchanged**. No sixth nav tab. No live. No WebSockets. No chart library. Keep `#risk-overlays`, `#risk-sleeves`, spoken glance tiles, tighten-only math, and PUT keys. Do not revive `static/app.js`. Do not clone Run allocation forms or account Tighten tiles onto overlay cards.

This cycle supersedes overlays-glance §2 for **cards that still dump the eight-field form**. Each card becomes glance (allocation rail + tighter count) then action (`<details>` **Tighten this sleeve**).

## 1. Why this increment exists

Goal check against current main (`63dd82e`):

| Goal slice | v1 / later contract | Current desk |
| --- | --- | --- |
| 凭直觉交互 | Recognition over recall. Control-tower: glance, then the action | Sleeve overlays band has Spoken / Overlays / Tighter / Idle. Each card still opens with a full Gross/Names/Orders/Deltas form. The tighter line is muted and easy to miss. |
| 界面令人眼前一亮 | Tighten account is tiles then a grouped form. Overlay cards should match that rhythm | Cards look like a config dump under the glance row. |
| 风险可控 | Overlays only tighten A∩B; stricter-than-account must be visible | Tighter count exists at the band. On the card it is a muted sentence beside eight inputs. |
| 易于使用 | `how_risk` names overlay tiles | Does not say the card is rail + tighter, form under Tighten this sleeve. |
| 架构 | `js/paint-risk.js` already builds cards | Wrap `buildRiskInputs` in `<details>`. No API change. |

Research applied:

- **Progressive disclosure:** show allocation and tightness first; keep the same PUT form one click away. Do not hide the form on another screen.
- **Match Tighten:** account policy is glance then form. Sleeve overlays should not invert that.
- **Quiet cockpit:** reuse `#f59e0b` when the card is tighter than account. No new colors. No charts.

## 2. Overlay card layout

For each id in `risk.sleeves`, `#risk-sleeves` still gets a `.panel`:

1. `h2` bundle id (unchanged)
2. Allocation label + `fmtPct(alloc)` (unchanged)
3. `.util-track` via `paintUtilTrack` (unchanged)
4. Line: `{n} tighter than account` or `Same as account`. Class `tighter-line`. Class `warn` when `n > 0`.
5. `<details class="risk-sleeve-tighten">` with `<summary>Tighten this sleeve</summary>` wrapping the existing `buildRiskInputs` form. Closed by default.

Empty copy unchanged: `No sleeve overlays. Import a qualified .asb, then tighten a sleeve here.`

Band tiles Spoken / Overlays / Tighter / Idle unchanged. `riskFormIsDirty` unchanged (open details with typed inputs still skip the wipe). Do not persist `open` across polls (YAGNI). Do not label a card `Live`.

Account Tighten form stays a visible grouped form, not `<details>`.

## 3. Tokens

```css
#risk-sleeves .tighter-line.warn {
  color: #f59e0b;
}

.risk-sleeve-tighten summary {
  cursor: pointer;
  color: #9ba3b4;
}
```

Separate CSS blocks so token tests can regex each selector.

## 4. Help / README

`how_risk`: each overlay card is allocation rail and tighter count; **Tighten this sleeve** holds the form.

Cockpit / README: same.

## 5. In / out

**In:** card glance-then-details; warn on tighter line; CSS; help/README; JS/CSS/help tests.

**Out:** API / PUT changes; cloning Tight / Delta tiles onto cards; cloning Run allocation inputs; opening details by default; sixth screen; `app.js`; WebSockets; charts.

## 6. Verification

- JS creates `details` with class `risk-sleeve-tighten` and summary `Tighten this sleeve`.
- Tighter line uses class `tighter-line` and `warn` when count > 0.
- Form still built with `buildRiskInputs` and still submits sleeve PUT.
- Help contains `Tighten this sleeve`. `#nav` still five screens. No `>Live<` label.
- No real broker orders.
