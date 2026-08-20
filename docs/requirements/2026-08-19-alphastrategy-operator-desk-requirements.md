# alphastrategy operator desk requirements

**Date:** 2026-08-19
**Status:** Requirements (improvement cycle on v1)
**Repo:** `AlphaStrategyAI/alphastrategy`
**Parent contract:** [`2026-08-19-alphastrategy-v1-requirements.md`](2026-08-19-alphastrategy-v1-requirements.md)
**Technical design:** [`docs/plans/2026-08-19-alphastrategy-operator-desk-technical-design.md`](../plans/2026-08-19-alphastrategy-operator-desk-technical-design.md)

This document does **not** change product identity. alphastrategy remains a local Alpaca **paper** execution desk. alphaloop still searches; this product still runs qualified `.asb` bundles. Live money, crypto, WebSockets, a strategy editor, VWAP/TWAP, and public bind stay out of scope.

It closes gaps between v1 §6–§8 and the current modules (`supervisor`, `api`, Quiet cockpit) so an operator can see **when** the next legal rebalance is, **what** each sleeve last contributed, and **which** audit event they are looking at — without confusing halt with flatten.

## 1. Why this increment exists

v1 is implemented as an execution runtime. Against the locked v1 contract, the operator surface is still incomplete:

| v1 requirement | Current behavior |
| --- | --- |
| Portfolio shows RTH countdown and next rebalance | `#clock-line` prints raw Alpaca `next_open` / `next_close`. `GET /api/status` omits `last_rebalance_event` and any countdown. |
| Portfolio shows sleeve **contribution** | Sleeves table shows **allocation** only. Last target weights are not persisted or exposed. |
| Strategies list state `imported` / `paper` / `halted` / `stopped` | UI maps allocation>0 → paper/halted, else imported. Explicit `paper stop` (allocation 0 until next rebalance) is indistinguishable from never started. |
| Activity is a blotter with drill-in | Events render as a JSON dump on one line. |
| Halt/deviation banners cannot be visually quiet | Poll failure is `console.error` only. Control-plane disconnect looks like a healthy desk. |
| Risk UI refuses looser values | Forms are rebuilt every 5s poll, wiping in-progress tighten inputs. |
| Account kill is louder than paper start | Paper start requires a checkbox. Account kill POSTs on the first click. |
| Positions are the combined book | Table is symbol + qty. No last-target weight / notional. |

Execution research (applied, not copied):

- MiFID II RTS 6 kill functionality and operator literature treat **cancel / halt** and **flatten** as different rungs. Flatten is the loud, last step. This desk already implements that matrix in the Supervisor; the Web must not make flatten as easy as a navigation click.
- Rebalancing operations care about **wanted vs got** and **time-to-next-event**. This product rebalances at most twice per RTH session; a countdown and last combined book are the right TCA slice. Do not add child orders or participation algos.
- Quiet / sterile cockpits interrupt on abnormal state. A failed refresh is abnormal. In-progress forms are not discarded by a background poll.

## 2. Positioning walls (unchanged)

All v1 hard walls remain:

1. Alpaca paper only. No live control in CLI or Web.
2. No credentials in `.asb`, logs, or UI.
3. Interpreters never see secrets, network, or the broker.
4. Import is not permission to trade.
5. Supervisor is the only order placer. Heartbeat still does not place orders.
6. Resume still does not catch-up rebalance.
7. Quiet cockpit tokens stay locked.

## 3. Clock and next rebalance

Clock source of truth remains Alpaca `GET /v2/clock`.

Add a pure helper next to `next_rebalance_event` that answers the operator question **“what is the next legal rebalance, and how many whole seconds until it?”** from a `ClockSnapshot` plus `last_rebalance_event`.

Rules:

1. Session key is `cur.next_close.date()` (same as the Supervisor). Open key `{date}:open`. Close key `{date}:close`.
2. **Market closed:** next rebalance is **open**, at `next_open + 3 minutes`.
3. **Market open** and last event is this session’s **close:** next rebalance is **open** of the following session, at `next_open + 3 minutes`.
4. **Market open** and last event is this session’s **open** (close not yet done): next rebalance is **close**, at `next_close − 12 minutes`. Seconds may be 0 if already inside the close window.
5. **Market open** and this session’s open is **not** recorded: the 3-minute open delay cannot be reconstructed from Alpaca’s `next_open` (that field is the *following* session). Treat next rebalance as **open** due now (`seconds = 0`, `at = now`). The Supervisor still decides whether a tick actually fires; the UI must not invent a fake 3-minute clock.
6. `seconds` is `max(0, floor((at − now).total_seconds()))`. Never negative.

`GET /api/status` includes:

- existing `state`, `clock`, `halted`, `halt_reason`
- `last_rebalance_event` (`null` or `{YYYY-MM-DD}:{open|close}`)
- `countdown`: `{ "next_rebalance": "open"|"close", "at": <ISO-8601>, "seconds": <int> }`

Portfolio `#clock-line` must show, in this order: market OPEN/CLOSED, next rebalance kind, countdown `H:MM:SS` or `MM:SS`, and `at`. Raw `next_open`/`next_close` alone is not sufficient.

## 4. Last book: contribution, combined, prices

On every completed `_rebalance` (including a rebalance that places zero orders), persist:

| Field | Meaning |
| --- | --- |
| `last_combined` | Combined target weights used for that event: `Σ allocation_i * weight_i` |
| `last_sleeve_weights` | Per running sleeve, the DSL weights **before** allocation |
| `last_sleeve_contribution` | Per running sleeve, `{asset: allocation_i * weight_i[asset]}` at that event |
| `last_prices` | Last bar close used to size orders |

Stopped sleeves (allocation 0) are omitted from the collected book, so their contribution disappears on the **next** legal rebalance, not at the moment of Stop. Until then, Portfolio still shows the last stored contribution. That matches v1: Stop waits for the next rebalance to zero the sleeve.

Do not recompute contribution from *current* allocation × last weights; that would zero a stopped sleeve immediately.

`GET /api/portfolio` adds:

- `last_combined`
- `sleeve_contribution` (the persisted last contribution map)
- `last_rebalance_event`
- For each position, when a last price exists: `notional` (`qty * last_price`) and `weight` (`notional / equity`, 0 if equity is 0)

Portfolio tables:

- Positions: Symbol, Qty, Notional, Weight (em dash if unknown)
- Sleeves: Bundle, Allocation, Contribution (human-readable map or `cash residual`; em dash before the first rebalance)

Deviation banner may use portfolio `deviations` if present; otherwise keep scanning audit `execution_deviation` as today.

## 5. Sleeve lifecycle on Strategies

Persist an explicit `stopped` list of bundle ids the operator has stopped via `paper stop` / `POST /api/paper/stop`.

- `start_sleeve` removes the id from `stopped`.
- `stop_sleeve` sets allocation to 0 **and** adds the id to `stopped` (even if allocation was already 0).
- Account flatten (`SupervisorState.STOPPED`) does not have to clear `stopped`; the Web maps account `state === "stopped"` to sleeve state `stopped` for any id that is not merely `imported`.

`GET /api/bundles` adds `stopped: [bundle_id, ...]`.

Strategies state column (exactly these four strings):

1. `paper` — allocation > 0, supervisor not halted, supervisor not account-stopped
2. `halted` — allocation > 0 and supervisor halted
3. `stopped` — id in `stopped`, **or** supervisor state is `stopped` and the bundle is not a never-started import-only row
4. `imported` — otherwise

## 6. Activity blotter

`GET /api/activity` stays a time-ordered JSON array of audit objects (existing shape, `ts` + `event` + fields). No new event schema.

The Activity screen is a blotter, not a JSON dump:

- Each row shows `ts`, `event`, and a one-line summary (`symbol`/`qty`/`side` for orders; `reason` for halt; `session_event` + `orders` for rebalance; `asset` wanted/got for deviation; `bundle_id` for paper_start/stop).
- Click (or keyboard activation) expands that row to the remaining fields. Collapse the previous expansion. This is client-side drill-in; no new HTTP route.

## 7. Control-plane honesty and form hygiene

1. If any of the five poll requests fail, show a persistent banner (halt/fail token `#ef4444` or halt `#f59e0b` is acceptable; fail red preferred) that the control plane is unreachable or the last refresh failed. Do **not** only `console.error`. Do not clear the last good snapshot.
2. While a Risk tighten input is focused, or any of those inputs has a non-empty value the operator is editing, **do not** rebuild the Risk forms. Caps readout may still update.
3. Account kill on Run is louder than paper start: require a checkbox **and** the operator to type `FLATTEN` (exact, case-sensitive) before `POST /api/paper/kill` without `bundle_id`. Sleeve kill may keep a single confirm (`window.confirm` is acceptable). API and CLI stay as they are (explicit verbs already).

## 8. Upload parser

`cgi.FieldStorage` is deprecated (removed in some Python 3.13+ builds). Multipart `.asb` upload must parse the `file` part with stdlib only (no `cgi`, no new dependency). Behavior of `POST /api/import` is otherwise unchanged.

## 9. In / out

**In**

- Countdown helper + status/portfolio/bundles fields above
- Persist last book on rebalance; persist `stopped`
- Quiet cockpit: countdown, contribution, position weight/notional, `stopped`, blotter drill-in, disconnect banner, risk-form preserve, louder account flatten confirm
- Stdlib multipart import
- Unit, API integration, and mocked e2e tests; no real broker

**Out**

- Live trading, WebSockets, strategy editor, VWAP/TWAP, isolated sleeve flatten that guesses a residual book
- New audit event types, Bundle Registry, team auth
- Changing halt vs flatten matrix, session times, or sandbox limits
- Rewriting v1 identity or growing `src/openstrategy/`

**Done when:** mocked tests show (1) status countdown matches the helper rules, (2) after a simulated open rebalance, portfolio `sleeve_contribution` equals allocation × sleeve weights and survives `paper stop` until the next rebalance, (3) bundles lists `stopped` after stop, (4) Web static assets contain countdown rendering, blotter expansion, disconnect banner, `FLATTEN` confirm, and `stopped`, (5) import still works without `import cgi`.
