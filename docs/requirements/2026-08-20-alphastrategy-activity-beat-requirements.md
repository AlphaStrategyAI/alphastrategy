# alphastrategy Activity Beat glance tiles

**Date:** 2026-08-20
**Status:** Requirements (improvement cycle on v1)
**Repo:** `AlphaStrategyAI/alphastrategy`
**Parent contract:** [`2026-08-19-alphastrategy-v1-requirements.md`](2026-08-19-alphastrategy-v1-requirements.md)
**Technical design:** [`docs/plans/2026-08-20-alphastrategy-activity-beat-technical-design.md`](../plans/2026-08-20-alphastrategy-activity-beat-technical-design.md)

Paper only. Five screens. Quiet cockpit **tokens unchanged**. No sixth nav tab. No live. No WebSockets. No chart library. Keep `#act-beat` and `#activity-heartbeat`. Do not revive `static/app.js`.

This cycle makes Activity **Beat** use the same glance grammar as Tape / Book: Pulse, Age, Interval, and Supervisor as tiles — not a muted sentence.

## 1. Why this increment exists

Goal check against current main (`dc560d5`):

| Goal slice | v1 / later contract | Current desk |
| --- | --- | --- |
| 界面令人眼前一亮 | Tape is four metric tiles. Book is Equity / Cash / PnL / Drift. | Beat is `<p id="activity-heartbeat" class="muted">Beat LIVE · 12s ago · idle_in_session</p>`. The first Activity band looks like leftover chrome. |
| 凭直觉交互 | SRE heartbeat boards show **status, age, and expected interval** together (AlertOps grid: health + last ping + check interval). | Operator must parse a sentence and remember that LIVE means ≤45s against a 20s beat. Age is not next to the SLA. |
| 可靠 | Header already has LIVE/STALE/DEAD. Activity is the diagnostic screen. | Raw `idle_in_session` is machine state, not desk words. Halted/stopped do not take warn/fail color on Beat. |
| 帮助文档 | `how_activity` says Beat / Tape / Blotter | Does not say Beat is Pulse / Age / Interval / Supervisor. |

Research applied:

- **AlertOps / status grids:** pulse card = current status + last ping + interval. Do not add history sparklines (no chart library, v1 out).
- **Quiet cockpit:** reuse `metrics metrics-4` and `metric hero` from Tape. Pulse uses locked tokens `#10b981` / `#f59e0b` / `#ef4444` / `#5c6573` (missing).
- **Recognition over recall:** Age beside Interval. Spoken Supervisor (`IN SESSION`, `HALTED`) with raw state as `title`.

Supersedes activity-tape §3 Beat body (the muted `<p>` only). Keep the band id and `#activity-heartbeat`.

## 2. Beat tiles

Inside `#act-beat`, replace the paragraph with:

```html
        <div class="metrics metrics-4 nums">
          <div class="metric hero">
            <div class="metric-label">Pulse</div>
            <div id="activity-heartbeat" class="metric-value">—</div>
          </div>
          <div class="metric">
            <div class="metric-label">Age</div>
            <div id="act-beat-age" class="metric-value">—</div>
          </div>
          <div class="metric">
            <div class="metric-label">Interval</div>
            <div id="act-beat-interval" class="metric-value">—</div>
          </div>
          <div class="metric">
            <div class="metric-label">Supervisor</div>
            <div id="act-beat-state" class="metric-value">—</div>
          </div>
        </div>
```

Paint from existing `state.status.heartbeat` and `state.status.state`:

| Tile | Value | Notes |
| --- | --- | --- |
| Pulse | `LIVE` / `STALE` / `DEAD` / `NO BEAT` via existing `pulseLabel` | Class `live` / `stale` / `dead` / `missing` on `#activity-heartbeat` |
| Age | `{n}s` or em dash | From `age_seconds` |
| Interval | `{n}s` | `interval_seconds` or 20 |
| Supervisor | spoken: `IN SESSION`, `OUT OF SESSION`, `REBALANCING`, `HALTED`, `FLATTENING`, `STOPPED`, `STARTING` | `title` = raw `status.state`. HALTED uses warn color; FLATTENING/STOPPED use fail color |

No API change. Empty blotter copy unchanged.

## 3. Help / README

`how_activity`: Beat is four tiles Pulse / Age / Interval / Supervisor. Pulse is the hero.

Cockpit / README Activity: same.

## 4. In / out

**In:** Beat glance tiles; keep `#activity-heartbeat` as Pulse; spoken Supervisor; token colors; help/README; HTML/CSS/JS tests.

**Out:** WebSockets; pulse history charts; changing LIVE/STALE/DEAD thresholds; sixth screen; `app.js`; Supervisor/API schema.

## 5. Verification

- `#activity-heartbeat` lives inside `#act-beat` and is the Pulse hero value.
- `#act-beat-age`, `#act-beat-interval`, `#act-beat-state` exist. Beat uses `metrics-4`.
- JS paints Pulse via `pulseLabel` and Interval from `interval_seconds`.
- Help contains Pulse / Age / Interval / Supervisor. `#nav` still five screens.
- No real broker orders.
