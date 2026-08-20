# alphastrategy Clock session continuity tiles

**Date:** 2026-08-20
**Status:** Requirements (improvement cycle on v1)
**Repo:** `AlphaStrategyAI/alphastrategy`
**Parent contract:** [`2026-08-19-alphastrategy-v1-requirements.md`](2026-08-19-alphastrategy-v1-requirements.md)
**Technical design:** [`docs/plans/2026-08-20-alphastrategy-clock-continuity-technical-design.md`](../plans/2026-08-20-alphastrategy-clock-continuity-technical-design.md)

Paper only. Five screens. Quiet cockpit **tokens unchanged**. No sixth nav tab. No live. No WebSockets. No chart library. Keep `#metric-session`, `#metric-countdown`, `#metric-countdown-kind`. Do not revive `static/app.js`. Do not hardcode `Gross cap` in JS. Header Session chip stays.

This cycle makes **Clock** a four-tile session continuity surface: exchange now and last legal rebalance sit next to Session and Next, so the operator can see whether today’s open already fired without reading `#clock-line` or `status` JSON.

## 1. Why this increment exists

Goal check against current main (`654c68f`):

| Goal slice | v1 / later contract | Current desk |
| --- | --- | --- |
| 稳定执行 | §6 at most two RTH rebalances; persist `last_rebalance_event` so an event cannot fire twice. §8 Portfolio: RTH countdown, next rebalance | Next countdown is a tile. **Now** is a leftover `#clock-line` footnote. **Last** lives only in `GET /api/status`. After Positions became glance tiles, Clock is the last Portfolio band with leftover chrome. |
| 可靠 | Header already shows Session OPEN/CLOSED | Duplicate Session on Clock is useful (detail band). Missing Last means a halted morning looks like “next = close” with no proof open already consumed. |
| 凭直觉交互 | Session clocks (Alpaca `timestamp`) and blotter “last print” | Two Clock tiles + a muted `now {iso}` line. ISO timestamps wrap; Last is invisible. |
| 界面令人眼前一亮 | Book, Flatten, Positions, Risk, Activity are `metrics-4` | Clock is still `metrics-2` plus a paragraph. |
| 易于使用 | `how_portfolio` names Clock tiles Session and Next rebalance | Does not say Clock is Session / Now / Next / Last. |
| 易于维护 | `clock.timestamp` and `last_rebalance_event` already on status | Fill mounts in existing `renderSessionMetrics`. No API change. |

Research applied:

- **Session clock vs desk clock:** Alpaca `GET /v2/clock` `timestamp` is venue now. Paint it as time + date sub, not a footnote sentence.
- **Last event visibility:** execution desks show last auction/rebalance next to next. `last_rebalance_event` is `{YYYY-MM-DD}:{open\|close}`.
- **Do not duplicate header jobs:** Header Session stays a chip. Clock Session stays the detailed tile.

## 2. Clock tiles

Replace Clock’s two tiles and delete `#clock-line`:

```html
        <div class="metrics metrics-4 nums">
          <div class="metric">
            <div class="metric-label">Session</div>
            <div id="metric-session" class="metric-value">—</div>
          </div>
          <div class="metric">
            <div class="metric-label">Now</div>
            <div id="metric-clock-now" class="metric-value">—</div>
            <div id="metric-clock-now-sub" class="metric-sub">—</div>
          </div>
          <div class="metric hero">
            <div class="metric-label">Next</div>
            <div id="metric-countdown" class="metric-value">—</div>
            <div id="metric-countdown-kind" class="metric-sub">—</div>
          </div>
          <div class="metric">
            <div class="metric-label">Last</div>
            <div id="metric-last-rebalance" class="metric-value">—</div>
            <div id="metric-last-rebalance-sub" class="metric-sub">—</div>
          </div>
        </div>
```

`renderSessionMetrics` fills from existing `status.clock`, `status.countdown`, and `status.last_rebalance_event`.

| Tile | Value | Notes |
| --- | --- | --- |
| Session | OPEN / CLOSED / UNAVAILABLE | Keep `#metric-session.open` green token |
| Now | `HH:MM:SS` from `clock.timestamp` or `clock.now` | Sub = `YYYY-MM-DD`. Unparseable raw string as value, sub em dash |
| Next | existing countdown | Hero. Sub remains `open` / `close` |
| Last | `open` / `close` from `last_rebalance_event` | Sub = the date. Missing: em dash |

Clock unavailable: Session UNAVAILABLE; Now / Next / Last em dash. Do not paint `Clock unavailable` as a sentence.

Keep `.metrics-2` in CSS (other tests lock the class). Clock uses `metrics-4`.

## 3. Help / README

`how_portfolio`: Clock is four tiles Session / Now / Next / Last. Next is the hero.

Cockpit / README: same. Keep `Book / Flatten budgets / Clock`.

## 4. In / out

**In:** Clock four tiles; remove `#clock-line`; help/README; HTML/CSS/JS tests. Keep `renderSessionMetrics` in `paint-portfolio.js`.

**Out:** changing Positions tiles; header chips; countdown math; Supervisor/API schema; sixth screen; `app.js`; WebSockets; charts; Live label; catch-up rebalance.

## 5. Verification

- `#metric-clock-now`, `#metric-last-rebalance` live inside `#glance-clock`. Next is the hero. `metrics-4`. No `#clock-line`.
- JS paints those ids plus `last_rebalance_event`. `Gross cap` still absent from JS.
- Help contains `Session / Now / Next / Last`. `#nav` still five screens.
- `test_html_glance_bands` slices Clock to `#glance-positions`, not `#clock-line`.
- No real broker orders.
