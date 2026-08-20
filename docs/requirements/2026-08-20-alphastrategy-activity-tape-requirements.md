# alphastrategy Activity tape bands

**Date:** 2026-08-20
**Status:** Requirements (improvement cycle on v1)
**Repo:** `AlphaStrategyAI/alphastrategy`
**Parent contract:** [`2026-08-19-alphastrategy-v1-requirements.md`](2026-08-19-alphastrategy-v1-requirements.md)
**Technical design:** [`docs/plans/2026-08-20-alphastrategy-activity-tape-technical-design.md`](../plans/2026-08-20-alphastrategy-activity-tape-technical-design.md)

Paper only. Five screens. Quiet cockpit **tokens unchanged**. No sixth nav tab. No live. No WebSockets. No chart libraries. Audit JSONL schema **unchanged**. Existing blotter **ids stay**.

This cycle makes Activity match the desk grammar the other four screens now use: a personal investor sees **whether the Supervisor beat is live**, **how many** rebalances / halts / deviations / kills hit the tape, then the **blotter** — not one “Audit events” panel.

## 1. Why this increment exists

Goal check against current main (`82d265f`):

| Goal slice | v1 / later contract | Current desk |
| --- | --- | --- |
| 稳定执行 / 策略执行 | §8 Activity: time-ordered rebalances, target vs fill, deviations, halt/flatten | Those facts exist as expand-JSON rows. First glance is a muted beat line plus a list. |
| 凭直觉交互 | Portfolio / Strategies / Run / Risk are labeled glance bands | Activity is the last core screen that still looks like a log dump. |
| 界面令人眼前一亮 | Sparse chrome, hero number, halt/fail not quiet | No counts. A halted or flattened session is easy to miss if the operator does not expand rows. |
| 易于使用 | `how_activity` already says time-ordered audit and kill isolation copy | How-to describes a blotter; the layout does not name Beat / Tape / Blotter. |
| 架构 | `js/paint-activity.js` | Edit that part only. Do not revive `static/app.js`. |

Research applied:

- **Endsley SA / trading blotters:** status (beat) and exception counts before the tick-by-tick tape.
- **Gestalt common region:** Beat, Tape, and Blotter are three jobs. Do not put counts inside the JSON expand list.
- **Quiet cockpit:** reuse `glance-band` / `glance-heading` / `.metric.hero` / `.metrics-4`. Halt count uses `#f59e0b` when > 0; deviation and kill counts use `#ef4444` when > 0.

## 2. Three Activity bands

| id | heading | Contents (keep existing ids) |
| --- | --- | --- |
| `#act-beat` | Beat | `#activity-heartbeat` |
| `#act-tape` | Tape | Four tiles: Rebalances (**hero**), Halts, Deviations, Kills |
| `#act-blotter` | Blotter | `#activity-list` (unchanged expand-to-payload behavior) |

Each band: `class="glance-band"`, child `h2.glance-heading`. DOM order: beat → tape → blotter.

Keep `#activity-heartbeat` and `#activity-list`. Empty copy and kill-row wording stay. No `window.confirm`.

## 3. Tape tiles

| Label | id | Color when count > 0 |
| --- | --- | --- |
| Rebalances | `#act-count-rebalance` | hero + `status-running` |
| Halts | `#act-count-halt` | `status-halt` |
| Deviations | `#act-count-deviation` | `status-fail` |
| Kills | `#act-count-kill` | `status-fail` |

Counts are derived in `js/paint-activity.js` from `state.activity`:

- Rebalances: `event === "rebalance"`
- Halts: `event === "halt"`
- Deviations: `event === "execution_deviation"`
- Kills: `event === "kill"` or `event === "flatten"`

Other events stay on the blotter only. Empty activity paints `0` on every tile, then the existing empty-row copy. Do not skip counts when the list is empty.

Tape grid: existing `.metrics-4`.

## 4. Help / README

`how_activity`: Activity is three bands **Beat / Tape / Blotter**. Rebalances is the hero count. Halt / deviation / kill tiles are not quiet when > 0. Expand a blotter row for the payload.

## 5. In / out

**In:** three bands; tape counts; colors; help/README; HTML/CSS/JS/help tests; e2e GET `/` includes `act-tape`.

**Out:** new audit events; changing JSONL; sixth screen; new tokens; chart libraries; replacing expand-JSON with a new table widget this cycle; reviving `static/app.js`.

## 6. Verification

- HTML ids `act-beat`, `act-tape`, `act-blotter`. Headings `Beat`, `Tape`, `Blotter`.
- `#activity-heartbeat` inside `#act-beat`. Count ids inside `#act-tape`. `#activity-list` inside `#act-blotter`.
- Help contains `Beat / Tape / Blotter`. GET `/` includes `id="act-tape"`.
- `#nav` still five screens. No real broker orders.
