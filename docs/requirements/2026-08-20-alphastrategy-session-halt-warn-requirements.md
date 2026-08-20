# alphastrategy Session OPEN is not running-green while HALTED

**Date:** 2026-08-20
**Status:** Requirements (improvement cycle on v1)
**Repo:** `AlphaStrategyAI/alphastrategy`
**Parent contract:** [`2026-08-19-alphastrategy-v1-requirements.md`](2026-08-19-alphastrategy-v1-requirements.md) §6–§8
**Related:** [`2026-08-20-alphastrategy-header-chips-requirements.md`](2026-08-20-alphastrategy-header-chips-requirements.md)
**Technical design:** [`docs/plans/2026-08-20-alphastrategy-session-halt-warn-technical-design.md`](../plans/2026-08-20-alphastrategy-session-halt-warn-technical-design.md)

Paper only. Five screens. Quiet cockpit **tokens unchanged**. No sixth nav tab. No live. No WebSockets. No chart library. Do not revive `static/app.js`. `"Gross cap"` must not appear in assembled JS. `renderBanners` keeps a **single** `const reason`. Do not retry leftover orders. Pulse LIVE stays the 20s beat (by design). Session still names RTH OPEN/CLOSED.

The header-chips cycle put Session next to Supervisor. Session still takes class `open` (`#10b981`) whenever Alpaca `is_open`. After a health halt the chrome is **green OPEN + amber HALTED**. That fights 凭直觉: running-green reads as “go” while the desk will not place new orders. v1 §8 says halt cannot be visually quiet. This cycle keeps the OPEN word (market fact) and paints it halt/warn while Supervisor is `halted`.

## 1. Why this increment exists

Goal check against current main (`6dff239`):

| Goal slice | v1 / later contract | Current desk |
| --- | --- | --- |
| 凭直觉交互 | Nielsen 1: system status visible and not contradictory. Halt ≠ flatten. Resume does not catch up. | Header Session is running-green OPEN during halt. Clock Session tile matches. |
| 可靠 | §8 halt/deviation banners cannot be visually quiet. | Banners exist; header Session still looks healthy. |
| 界面令人眼前一亮 | Locked tokens. Halt/warn is `#f59e0b`. Running is `#10b981`. | Two adjacent chips fight: go-green vs halt-amber. |
| 易于使用 | Help already: Header LIVE is the beat, not Session. | Never says OPEN is not go-green while HALTED. |
| 稳定执行 | Halt stops new orders. Session clock is still RTH. | Copy and color must not imply a catch-up. Engine unchanged. |

Research applied:

- **Do not merge Session and Supervisor.** OPEN still means Alpaca `is_open`. HALTED still lives on `#desk-supervisor`. Pulse stays liveness.
- **Color is the affordance.** Bloomberg-style toolbars keep the session word and change hue when the desk cannot act. Use existing halt/warn `#f59e0b`, not a new token.
- **One painter.** Header `#desk-session` and Clock `#metric-session` must not disagree.

Out of this cycle: flattening (Supervisor already `fail` red; flatten *does* send orders). CLOSED stays muted.

## 2. Paint

Shared helper `applySessionChip(el)` in `js/paint-portfolio.js`, used by `renderSessionMetrics` and `renderDeskPulse`:

| Clock | Supervisor `state` | Text | Classes |
| --- | --- | --- | --- |
| missing / `clock.error` | any | `UNAVAILABLE` | neither `open` nor `warn` |
| `is_open` | not `halted` | `OPEN` | `open` |
| `is_open` | `halted` | `OPEN` | `warn` (not `open`) |
| not open | any | `CLOSED` | neither |

Always `classList.remove("open", "warn")` first. Header `title` stays `RTH session`. Clock countdown / Now / Last paint unchanged.

## 3. Tokens

Keep `#desk-session.open` and `#metric-session.open` at `#10b981`.

Add:

```css
#desk-session.warn {
  color: #f59e0b;
}

#metric-session.warn {
  color: #f59e0b;
}
```

No new colors. No sixth `#nav` item.

## 4. Help / README

Cockpit / how_portfolio: Session OPEN is halt color while Supervisor is HALTED.

README Operator: Header Session stays the RTH word; it is not running-green while HALTED.

## 5. In / out

**In:** shared session chip painter; warn class while halted+open; CSS; help/README; JS/CSS/help tests.

**Out:** changing Pulse LIVE-during-halt; merging Session into Supervisor; flattening color; retrying orders; live; sixth screen; `app.js`.

## 6. Verification

- JS contains `function applySessionChip` and `halted ? "warn" : "open"` (or equivalent that adds `warn` when `state === "halted"` and `is_open`).
- `renderDeskPulse` and `renderSessionMetrics` both call `applySessionChip`.
- CSS `#desk-session.warn` and `#metric-session.warn` use `#f59e0b`. `#desk-session.open` still `#10b981`.
- Help contains `Session OPEN is halt color while Supervisor is HALTED`.
- Five `#nav` screens. `"Gross cap"` not in `js_text`. No real broker.
