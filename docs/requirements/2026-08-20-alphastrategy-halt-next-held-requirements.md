# alphastrategy Clock Next is held while HALTED

**Date:** 2026-08-20
**Status:** Requirements (improvement cycle on v1)
**Repo:** `AlphaStrategyAI/alphastrategy`
**Parent contract:** [`2026-08-19-alphastrategy-v1-requirements.md`](2026-08-19-alphastrategy-v1-requirements.md) §6–§8
**Related:** [`2026-08-20-alphastrategy-session-halt-warn-requirements.md`](2026-08-20-alphastrategy-session-halt-warn-requirements.md), [`2026-08-20-alphastrategy-spent-howto-requirements.md`](2026-08-20-alphastrategy-spent-howto-requirements.md)
**Technical design:** [`docs/plans/2026-08-20-alphastrategy-halt-next-held-technical-design.md`](../plans/2026-08-20-alphastrategy-halt-next-held-technical-design.md)

Paper only. Five screens. Quiet cockpit **tokens unchanged**. No sixth nav tab. No live. No WebSockets. No chart library. Do not revive `static/app.js`. `"Gross cap"` must not appear in assembled JS. `renderBanners` keeps a **single** `const reason`. Do not retry leftover orders. Resume does not catch up. Pulse LIVE stays the 20s beat. Session still names RTH. Keep tutorial substring `Next rebalance`.

The session-halt-warn cycle stopped Session OPEN from looking like go-green during halt. Clock **Next** (the hero) still ticks `fmtCountdown` with sub `open` / `close` as if that window will place orders. While `SupervisorState.HALTED` the tick returns before `next_rebalance_event`. That fights 凭直觉 and 稳定执行: the countdown is a live auction clock for a window the desk will skip until resume. This cycle keeps the remaining time (when resume can still meet a legal window) and marks Next **held**.

## 1. Why this increment exists

Goal check against current main (`7bfaa5c`):

| Goal slice | v1 / later contract | Current desk |
| --- | --- | --- |
| 稳定执行 | Halt: no new orders. Resume does not catch up; the next *legal* open/close after resume does. Halted tick does not call `_rebalance`. | Clock Next still counts down to open/close with no held mark. |
| 凭直觉交互 | §8 RTH countdown, next rebalance. Nielsen: status must not contradict halt. Spent empty Positions already refuses “the next legal rebalance will trade” when Last is spent. | Next hero looks like the next fire. Session is amber; Next is still default text color. |
| 可靠 | Banners cannot be visually quiet. | Halt banner exists; the Clock hero still looks healthy. |
| 易于使用 | Help: Next is the hero. Resume lives under After halt. | Never says Clock Next is held while HALTED. |
| 界面令人眼前一亮 | Halt/warn `#f59e0b` already on Session, Last spent, Supervisor. | Next does not use it. |

Research applied:

- **Inhibit, do not blank the auction clock.** Execution desks keep time-to-next even when trading is blocked, and flag **held**. Dropping the seconds would hide whether resume can still meet today’s close.
- **Do not merge Next into Supervisor.** HALTED stays on `#desk-supervisor` / After halt. Next stays the Clock hero.
- **API countdown stays a clock fact.** `GET /api/status` `countdown.{next_rebalance,at,seconds}` unchanged. Paint is the honesty layer.

Leftover `imported/.staging.*` after a crash between publish and rmtree is a separate architecture increment (listing already skips `.` names). Flattening still sends flatten orders — out.

## 2. Paint

In `renderSessionMetrics`, after `applySessionChip`:

| Condition | `#metric-countdown` | class | `#metric-countdown-kind` |
| --- | --- | --- | --- |
| no clock / `clock.error` | `—` (today) | neither `warn` | `—` |
| countdown present, not halted | `fmtCountdown(seconds)` (today) | neither `warn` | `open` / `close` (today) |
| countdown present, halted (`status.state === "halted"` or `status.halted`) | `fmtCountdown(seconds)` | `warn` | `held · ` + existing kind |
| countdown missing, halted | `—` | neither `warn` | `—` |

Always `countEl.classList.remove("warn")` before the fork. Keep Last spent `warn` on `#metric-last-rebalance` only.

No HTML mount change. No countdown payload change.

## 3. Tokens

```css
#metric-countdown.warn {
  color: #f59e0b;
}
```

No new colors.

## 4. Help / README

`how_portfolio`: Clock Next is held while Supervisor is HALTED.

README Clock: same. Keep `Next rebalance` in the first-session tutorial.

## 5. In / out

**In:** Next held sub + warn while halted; CSS; help/README; JS/CSS/help tests.

**Out:** changing halt skip in the Supervisor tick; resume catch-up; flattening Next color; leftover `.staging.*` sweep; live; sixth screen; `app.js`; changing `countdown` JSON.

## 6. Verification

- `renderSessionMetrics` contains `held · ` and adds `warn` on `#metric-countdown` when halted.
- Non-halted path still uses `fmtCountdown` and `countdown.next_rebalance`.
- CSS `#metric-countdown.warn` is `#f59e0b`.
- Help contains `Clock Next is held while Supervisor is HALTED` and still contains `Next rebalance`.
- Five `#nav` screens. `"Gross cap"` not in `js_text`. No real broker.
