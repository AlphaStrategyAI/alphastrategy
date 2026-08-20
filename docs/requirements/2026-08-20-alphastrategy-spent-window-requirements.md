# alphastrategy spent session window after persist-before-send

**Date:** 2026-08-20
**Status:** Requirements (improvement cycle on v1)
**Repo:** `AlphaStrategyAI/alphastrategy`
**Parent contract:** [`2026-08-19-alphastrategy-v1-requirements.md`](2026-08-19-alphastrategy-v1-requirements.md) §6–§8
**Related:** [`2026-08-20-alphastrategy-rebalancing-crash-requirements.md`](2026-08-20-alphastrategy-rebalancing-crash-requirements.md), [`2026-08-20-alphastrategy-durable-snapshot-requirements.md`](2026-08-20-alphastrategy-durable-snapshot-requirements.md), [`2026-08-20-alphastrategy-clock-continuity-requirements.md`](2026-08-20-alphastrategy-clock-continuity-requirements.md)
**Technical design:** [`docs/plans/2026-08-20-alphastrategy-spent-window-technical-design.md`](../plans/2026-08-20-alphastrategy-spent-window-technical-design.md)

Paper only. Five screens. Quiet cockpit **tokens unchanged**. No sixth nav tab. No live. No WebSockets. No chart library. Do not revive `static/app.js`. Do not retry remaining rebalance orders. Do not un-consume `last_rebalance_event`. `"Gross cap"` must not appear in assembled JS. `renderBanners` keeps a **single** `const reason`.

Persist-before-send already writes `state=rebalancing` and `last_rebalance_event={date}:{open|close}` **before the first** `place_order`. A host kill with **zero fills** still health-halts. Resume still does not catch up. The operator can read Clock Last as a finished open and wait for that same window to fire again. This cycle makes the spent window visible on halt copy, Clock Last, After halt (via `halt_reason`), and help.

## 1. Why this increment exists

Goal check against current main (`8f88130`):

| Goal slice | v1 / later contract | Current desk |
| --- | --- | --- |
| 稳定执行 | §6 persist `last_rebalance_event` so an event cannot fire twice. §7 resume does not catch up. | Persist-before-send consumes the window with `rebalance_placed=0`. Crash before the first fill still recovers as interrupted rebalancing. There is **no** test for `crash_after_place=0`. |
| 凭直觉交互 | §8 halt banners cannot be quiet. Clock Last already paints `last_rebalance_event`. | Halt reason is `interrupted rebalancing after 0 orders` — true, but it does not say **which** session event was spent. Clock Last still paints `open` / the date, the same chrome as a finished auction. |
| 可靠 | Recovery must not retry the torn batch (no client-order ids in v1). | Keep that. Do not place the leftover names after restart or after resume. |
| 易于使用 | Help already says interrupted rebalancing and resume does not catch up. | It does not say persist-before-send spends the window **even with 0 fills**, or that Clock Last is that spent marker. |
| 架构 | Snapshot already has `last_rebalance_event` and `rebalance_placed`. | Add a durable complete flag so Last stays honest after `paper resume` clears `halt_reason`. |

Research applied:

- **Consume-on-intent, name the consumption.** Session windows are one-shot. OMS desks mark an auction spent when the host accepted the batch, not when every child fill lands.
- **Do not look like a fill.** Last must not reuse the successful `open`/`close` value when the rebalance did not complete.
- **Resume is not a second open.** v1 already forbids catch-up. Tests must prove a 0-fill interrupt plus resume still places nothing in that open window.

## 2. Durable complete flag

`SupervisorSnapshot.last_rebalance_complete: bool`.

| Moment | Value |
| --- | --- |
| Persist-before-send (non-empty `plans`) | `False`, with `last_rebalance_event` and `rebalance_placed=0` |
| Interrupted-rebalance recovery | stays / set `False` |
| Successful rebalance (`place_error is None`), including a zero-plan skip | `True` |
| Missing field on old JSON | `True` (finished auctions from before this field) |

Do **not** change `last_rebalance_event` format (`{YYYY-MM-DD}:{open\|close}`). Countdown math stays on that string.

`GET /api/status` includes `last_rebalance_complete`. CLI offline `status` includes the same key. Portfolio payload may omit it; Clock paints from `status`.

## 3. Halt copy

`_recover_interrupted_rebalance` still audits `complete: false` and still health-halts. It still does not flatten and does not retry.

When `last_rebalance_event` is set:

```text
interrupted rebalancing after {placed} orders; {last_rebalance_event} spent
```

When it is missing, keep `interrupted rebalancing after {placed} orders`.

`#halt-banner` and `#run-halt-reason` already dump `halt_reason`. After halt therefore names the spent marker with no extra paint fork. Keep a single `const reason` in `renderBanners`.

## 4. Clock Last

`renderSessionMetrics` still splits `status.last_rebalance_event` on `:`.

| `last_rebalance_complete` | Last value | Last sub |
| --- | --- | --- |
| missing / `true` / no event | `open` / `close` (as today) or em dash | date or em dash |
| `false` | `spent` | event token (`open` / `close`) |

`#metric-last-rebalance.spent` uses halt/warn `#f59e0b` (not kill/fail). Class name `warn` on the value node, matching other halt chrome. Clear `warn` when the last event is complete or missing.

Do not add a fifth Clock tile. Do not put `Gross cap` in JS.

## 5. Help / README

`execution`: persist-before-send spends the session event **even with 0 fills**. Clock Last names the spent window. Recovery does not retry that event.

`how_portfolio`: Clock Last names the spent window when that event did not finish.

`how_run`: After halt names the spent session event (via the halt reason).

README Operator: persist-before-send spends the session event even with 0 fills; Clock Last names that spent window; resume does not catch up.

Keep existing phrases `interrupted rebalancing`, `does not catch up`, `Session / Now / Next / Last`.

## 6. In / out

**In:** `last_rebalance_complete`; halt reason `{event} spent`; 0-fill crash + resume tests; Clock Last `spent` + warn token; status/CLI field; help/README.

**Out:** retrying leftover orders; un-consuming `last_rebalance_event`; changing flatten / isolate recovery; a new banner id; live; sixth screen; `app.js`; WebSockets; `"Gross cap"` in JS.

## 7. Verification

- Two-name open rebalance, `crash_after_place=0`: on-disk `rebalancing`, `last_rebalance_event=2024-01-31:open`, `rebalance_placed=0`, `last_rebalance_complete is False`, `orders_today==0`, `len(orders)==0`. Restart: `halted`, `close_all` not called, incomplete audit `orders==0`, halt reason contains `interrupted rebalancing` and `2024-01-31:open spent`. Second tick places nothing.
- Same crash, then `resume` while still in that open window: still no new orders; `last_rebalance_event` unchanged; `last_rebalance_complete` stays False.
- Existing one-fill interrupt test still passes; halt reason may grow the spent suffix.
- Successful open rebalance: `last_rebalance_complete is True`. Persist-before-send probe still sees `False` before the first place.
- `GET /api/status` and CLI offline status include `last_rebalance_complete`.
- JS Clock Last paints `spent` when `last_rebalance_complete === false`; CSS `#metric-last-rebalance.warn` uses `#f59e0b`. `"Gross cap"` not in `js_text`. One `const reason`.
- Help contains `Clock Last names the spent window` and `even with 0 fills`.
- Five `#nav` screens. No real broker.
