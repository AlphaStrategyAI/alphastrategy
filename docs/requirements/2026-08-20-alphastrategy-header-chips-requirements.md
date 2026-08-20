# alphastrategy header Session and Supervisor chips

**Date:** 2026-08-20
**Status:** Requirements (improvement cycle on v1)
**Repo:** `AlphaStrategyAI/alphastrategy`
**Parent contract:** [`2026-08-19-alphastrategy-v1-requirements.md`](2026-08-19-alphastrategy-v1-requirements.md)
**Technical design:** [`docs/plans/2026-08-20-alphastrategy-header-chips-technical-design.md`](../plans/2026-08-20-alphastrategy-header-chips-technical-design.md)

Paper only. Five screens. Quiet cockpit **tokens unchanged**. No sixth nav tab. No live. No WebSockets. No chart library. Keep `#desk-pulse`. Do not revive `static/app.js`.

This cycle puts **Session** and **Supervisor** in the header chrome next to Pulse, so the operator can see whether RTH is open and whether the desk is halted without leaving Run / Risk / Strategies.

## 1. Why this increment exists

Goal check against current main (`b3b2819`):

| Goal slice | v1 / later contract | Current desk |
| --- | --- | --- |
| 可靠 | §6 session loop; §8 halt/deviation cannot be visually quiet | Header Pulse answers Supervisor **liveness**. RTH OPEN/CLOSED lives only on Portfolio Clock. Spoken Supervisor lives only on Activity Beat. |
| 凭直觉交互 | Nielsen 1 (visibility of system status). Operator consoles keep session + runtime state in the toolbar. | On Run the operator starts paper or types FLATTEN without seeing Session. Pulse LIVE + Session CLOSED is two different facts; they are not next to each other. |
| 界面令人眼前一亮 | Pulse is a Quiet chip. Book / Inventory / Beat / Caps are glance tiles. | Header after Pulse is still the brand wordmark. Session and Supervisor are screen-local. |
| 易于使用 | Help already says Header LIVE is the beat, not Session | Does not say the header also shows Session and Supervisor. |
| 稳定执行 | Resume does not catch up; rebalances need an open session | Chrome does not show OPEN vs CLOSED while the operator is on the kill ladder. |

Research applied:

- **Operator toolbars (Jesse / HFT desks):** connection/heartbeat, session, and runtime state stay in chrome. Do not hide them inside one screen. Do not add a kill switch to the header (Run already has the flatten ritual).
- **Liveness vs session (heartbeat-pulse):** Pulse is the 20s thread. Session is Alpaca `is_open`. Keep both; do not merge labels.
- **Quiet cockpit:** small chips, locked tokens, no new colors, no sixth `#nav` item.

Supersedes heartbeat-pulse §5 only for “header is Pulse alone.” Keep `#desk-pulse` and Portfolio Clock Session. Keep Activity Beat Supervisor.

## 2. Header chips

Inside `<header> .brand`, after `#desk-pulse` and before the wordmark:

```html
      <span id="desk-session" class="desk-chip">—</span>
      <span id="desk-supervisor" class="desk-chip">—</span>
```

Paint from existing `state.status` in `renderDeskPulse` (header is outside screens; that painter already runs on every refresh):

| Chip | Value | Notes |
| --- | --- | --- |
| Pulse | unchanged | Keep `#desk-pulse` / `#desk-pulse-label` |
| Session | `OPEN` / `CLOSED` / `UNAVAILABLE` | Same rules as `#metric-session`. Class `open` when OPEN. `title` = `RTH session` |
| Supervisor | spoken: `IN SESSION`, `OUT OF SESSION`, `REBALANCING`, `HALTED`, `FLATTENING`, `STOPPED`, `STARTING` | Same `supervisorLabel` as Activity Beat. `title` = raw `status.state`. Class `halt` when halted; `fail` when flattening or stopped |

Move `supervisorLabel` to `js/paint-portfolio.js` next to `pulseLabel` so header chrome owns spoken labels. Activity keeps calling the same function (one IIFE).

No API change. No Next-rebalance chip (Clock already has it).

## 3. Tokens

```css
.desk-chip {
  font-size: 0.72rem;
  letter-spacing: 0.06em;
  color: #5c6573;
}

#desk-session.open {
  color: #10b981;
}

#desk-supervisor.halt {
  color: #f59e0b;
}

#desk-supervisor.fail {
  color: #ef4444;
}
```

CLOSED and UNAVAILABLE stay muted (`#5c6573`). Missing Pulse stays on `#desk-pulse`, not on these chips.

## 4. Help / README

Cockpit: Header shows **Pulse, Session, and Supervisor**. Header LIVE is still the Supervisor beat, not Session.

README Operator: Header **LIVE / STALE / DEAD** is the beat; **OPEN / CLOSED** is RTH; spoken Supervisor is the runtime state.

## 5. In / out

**In:** `#desk-session` and `#desk-supervisor` in header; paint from existing status; shared `supervisorLabel` in portfolio JS; token CSS; help/README; HTML/CSS/JS tests.

**Out:** WebSockets; header kill switch; sixth screen; `app.js`; changing Clock or Activity Beat tiles; API/Supervisor schema.

## 6. Verification

- `#desk-session` and `#desk-supervisor` live in `<header>`, not inside a `.screen`.
- `#desk-pulse` still exists. `#nav` still five screens.
- JS `renderDeskPulse` writes both new ids. `supervisorLabel` still exists. `window.confirm` still absent.
- CSS `#desk-session.open` uses `#10b981`. `#desk-supervisor.halt` uses `#f59e0b`. `#desk-supervisor.fail` uses `#ef4444`.
- Help contains `Pulse, Session, and Supervisor`.
- No real broker orders.
