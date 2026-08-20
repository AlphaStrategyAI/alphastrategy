# alphastrategy execution honesty requirements

**Date:** 2026-08-20
**Status:** Requirements (improvement cycle 3)
**Parent contract:** [`2026-08-19-alphastrategy-v1-requirements.md`](2026-08-19-alphastrategy-v1-requirements.md)
**Technical design:** [`docs/plans/2026-08-20-alphastrategy-execution-honesty-technical-design.md`](../plans/2026-08-20-alphastrategy-execution-honesty-technical-design.md)

This increment does not change product identity, paper walls, or the halt-vs-flatten matrix. It closes three honesty gaps so an operator (Web, CLI, README) can see **whether the book is flat**, **whether the day order budget is exhausted**, and **wanted vs got** after a rebalance.

## 1. Why this increment exists

Against v1 §7–§9 and the Quiet cockpit contract:

| v1 requirement | Current behavior |
| --- | --- |
| Limit: orders per trading day ≤ 200 | `AccountPolicy.max_orders_per_day` exists and the Risk UI can tighten it. Supervisor never counts or enforces it. Only `max_orders_per_rebalance` is checked. |
| Activity: rebalances with **target vs fill** | Rebalance audit is `{session_event, orders}`. `execution_deviation` is a sidecar and is skipped unless every order in the batch reports `filled`. Portfolio Weight is got-only; there is no wanted column. |
| Halt/deviation banners cannot be visually quiet | Halt uses amber. After account flatten, state is `stopped` with no `halt_reason`. Portfolio looks like a healthy empty book (cash, no banner). Flatten is the loudest kill-switch rung; the desk currently whispers it. |
| README is the operator entry | README positions the paper desk but does not say halt ≠ flatten, that account kill types `FLATTEN`, that sleeve kill isolates when last book is clean, or that countdown lives on Portfolio. |

Execution / blotter practice applied here (not copied as an EMS):

- A blotter records **intent (wanted)** separately from **fills (got)**. This desk rebalances at most twice per RTH session; the right TCA slice is last combined target vs current weights, not VWAP/arrival-price children.
- Kill-switch literature: flatten is the last, loudest rung. A flattened book must not reuse the quiet idle palette.
- Daily order caps are pre-trade controls (v1 table). A cap that cannot fire is not a control.

## 2. Daily order budget

Persist on `SupervisorSnapshot`:

- `orders_date`: session calendar date (`next_close.date()`, same key as rebalance events), or `null`
- `orders_today`: integer count of paper orders **placed** on that date (rebalance + isolated sleeve-kill orders)

Rules:

1. When the session date changes, reset `orders_today` to 0 and set `orders_date`.
2. Before placing a planned batch of size `n`, if `orders_today + n > max_orders_per_day` (effective rebalance policy, stricter wins), raise account flatten — same as other B-limit breaches. Do not place a partial batch.
3. After a successful `place_order` call (including isolated sleeve kill), increment `orders_today` by 1 per call.
4. Heartbeat still does not place orders and does not increment the counter.
5. Account `close_all` is not an “order” for this budget (it is flatten). Isolated kill’s `plan_orders` batch **is**.

## 3. Wanted vs got

On every completed `_rebalance` (including zero-order rebalances):

1. After the order loop, compute `got[asset] = qty * last_price / equity` from broker positions (0 if equity is 0). Missing prices omit that asset from `got`.
2. Persist `last_got` on the snapshot.
3. Audit one `rebalance` line that includes `session_event`, `orders`, `wanted` (`last_combined`), and `got`.
4. Still emit `execution_deviation` rows when gaps exceed `max($1, 0.1% equity)`. Compute those from this `got`, **even if** some orders did not report `status=filled` (today’s all-filled gate hides drift).

`GET /api/portfolio` positions include:

- existing `qty`, `notional`, `weight` (got)
- `wanted`: `last_combined[symbol]` when present, else omitted

Portfolio Positions table columns: Symbol, Qty, Notional, Wanted, Got (got = current `weight`). Em dash when unknown.

Activity rebalance summary includes a compact wanted-vs-got hint (e.g. asset count or first gap), not a JSON dump. Drill-in still shows the full maps.

## 4. Flatten cannot look idle

`GET /api/status` adds `flattened: true` when `state` is `flattening` or `stopped` (else `false`). Existing `state` / `halted` stay.

Quiet cockpit:

- New fail-red banner `#flatten-banner` (token `#ef4444`), `role="alert"`.
- Copy: `FLAT: paper account flattened` (append halt-style reason only if one exists; flatten itself is the signal).
- Show whenever `status.flattened` or `status.state` is `flattening`/`stopped`.
- Do not reuse the amber halt banner for flatten. Halt remains `#f59e0b`.

CLI `alphastrategy status`:

- When the control plane is up, the JSON already includes new status fields.
- When the control plane is down, include `last_rebalance_event` and `flattened` from the on-disk snapshot (still `clock.error` if no daemon). Do not invent a countdown without a clock.

## 5. README

README remains the paper-desk entry. Add a short **Operator** section (not a second product story) that states:

1. Halt stops new orders and does not flatten; Resume does not catch up.
2. Account kill requires the Web operator to type `FLATTEN`; CLI `paper kill` without `--bundle` is the same flatten.
3. Sleeve kill isolates to the residual book when last book and RTH allow it; otherwise it flattens the whole account.
4. Portfolio shows next-rebalance countdown and wanted vs got; a flattened desk shows a red FLAT banner, not a green empty book.
5. Tests: `PYTHONPATH=src python3 -m pytest tests/alphastrategy/`.

Do not promise alpha. Do not document live trading.

## 6. In / out

**In:** daily order budget, last_got + rebalance wanted/got, flatten banner + status.flattened, CLI offline snapshot fields, README operator notes, unit / API / e2e tests.

**Out:** VWAP/TWAP, arrival-price TCA, WebSockets, live money, changing halt vs flatten triggers, CSV exports.

**Done when:** (1) a mocked rebalance that would exceed `max_orders_per_day` flattens without placing the overflowing batch; (2) after a rebalance, portfolio positions expose `wanted` and `weight`, and the rebalance audit line contains both maps; (3) after account flatten, `/api/status` has `flattened: true` and the cockpit HTML/JS contains the flatten banner; (4) README states halt ≠ flatten.
