# alphastrategy A sleeve overlay that breaches the live book flattens now

**Date:** 2026-08-20
**Status:** Requirements (improvement cycle on v1)
**Repo:** `AlphaStrategyAI/alphastrategy`
**Parent contract:** [`2026-08-19-alphastrategy-v1-requirements.md`](2026-08-19-alphastrategy-v1-requirements.md) §7–§8
**Related:** [`2026-08-20-alphastrategy-tighten-now-requirements.md`](2026-08-20-alphastrategy-tighten-now-requirements.md), [`2026-08-20-alphastrategy-start-held-requirements.md`](2026-08-20-alphastrategy-start-held-requirements.md)
**Technical design:** [`docs/plans/2026-08-20-alphastrategy-overlay-start-technical-design.md`](../plans/2026-08-20-alphastrategy-overlay-start-technical-design.md)

Paper only. Five screens. Quiet cockpit **tokens unchanged**. No sixth nav tab. No live. No WebSockets. No chart library. Do not revive `static/app.js`. `"Gross cap"` must not appear in assembled JS. `renderBanners` keeps a **single** `const reason`. Do not retry leftover orders. Resume does not catch up. Heartbeat still does **not** place orders and does **not** flatten. Keep tutorial substring `Next rebalance`. Start paper while halted still waits for resume. Tighten that breaches the live book still flattens now.

v1 §7: a limit breach of account policy B **or a tighter overlay** is the same as account kill if the broker is reachable. Tighten-now already `check_book`s the live book after `set_policy` and after sleeve overlay PUT. `_rebalance_policy()` still folds a sleeve overlay in **only when allocation > 0**. An operator can write Name cap 5% on an idle sleeve, then Start paper on a 15% live name, and the overlay stays silent until the next legal open/close. That is not 风险可控.

## 1. Why this increment exists

Goal check against current main (`fd37852`):

| Goal slice | v1 / later contract | Current desk |
| --- | --- | --- |
| 风险可控 | Overlay is a flatten-critical cap once the sleeve is spoken. | Overlay PUT while allocation is 0 does not enter `_rebalance_policy`. `start_sleeve` records allocation and does not enforce the live book. |
| 稳定执行 | Heartbeat does not flatten. Flatten is the kill-switch when a spoken cap is already breached. | Waiting for a scheduled rebalance after Start paper is a delayed control, not a skip of the 20s beat. |
| 凭直觉交互 | Start paper is the second explicit action that makes the sleeve spoken. Nielsen: status at the control. | Risk overlay Tighten looks saved. Flatten waits for Clock. |
| 易于使用 | Help already says Tighten on the account form flattens now. | Never says a sleeve overlay that breaches the live book flattens now — including when Start paper makes it spoken. |
| 易于维护 | One `_enforce_live_book` / `check_book`. | Call it after `start_sleeve` persist. Do not invent a second overlay matrix. |

Research applied:

- **Spoken policy is the live limit.** OMS desks apply a newly tighter sleeve overlay when that sleeve is allocated, not only on the next target. Idle overlays stay draft until allocation > 0 (same as `_rebalance_policy`).
- **Do not flatten on the 20s heartbeat.** Enforce on explicit Start paper / overlay PUT while allocated / Tighten. Same as tighten-now.
- **If unreachable, halt.** `_enforce_live_book` already health-halts on broker failure with `tighten live book:`.

Out: heartbeat flatten; 409 on start or overlay PUT; changing wanted `check_book` inside `_rebalance`; flattening on overlay PUT while allocation is 0; resume catch-up; Clock paint; live.

## 2. Engine

After `start_sleeve` writes allocation and persists (still holding `_lock`), call `_enforce_live_book()`.

Return value stays `state == HALTED` **after** enforce:

- Overlay / account cap does not breach → same as today (`held` true only if still HALTED).
- Live book already breaches the now-spoken policy → flatten (`STOPPED`), return `False`.
- Limit flatten still wins over HALTED (v1 table).

Do **not** fold idle overlays into `_rebalance_policy`. Allocation 0 keeps the overlay unpublished. PUT overlay while idle must **not** flatten; Start paper must.

CLI `paper start` without a running control plane still constructs the Supervisor with `broker=None` so allocation can persist without Alpaca. `_enforce_live_book` returns immediately when there is no broker (do **not** health-halt). Flatten-on-start is the control-plane path (`alphastrategy start` then `paper start` / web Set allocation).

Reuse `_live_book_weights`: priced live qty, else `last_got`, else `last_combined`. Fixture: 15 AAPL × $100 / $10k = 0.15 (under default 20% name cap, over a 5% overlay). Do not use 40 shares (already 40% vs 20%).

`PUT /api/risk` overlay while allocation > 0 already calls `enforce_live_book()` after `runtime.yaml` is on disk. Lock that. Do not flatten because only `min_delta_*` tightened.

## 3. API / CLI

`POST /api/paper/start` after a successful start:

```text
{"ok": true, "held": <bool>, "flattened": <bool>}
```

`flattened` is true when supervisor state is `flattening` or `stopped` after `start_sleeve`. Do **not** 409. `held` remains whether the desk is still `HALTED`. Flatten wins: `held` false, `flattened` true.

CLI `paper start` still prints **no** JSON on stdout. If `flattened`, stderr:

```text
flattened: a sleeve overlay that breaches the live book flattens now.
```

Else if `held`, existing held line. Existing paper-start help (halted waits for resume) stays.

## 4. Risk paint

Persistent `#risk-overlay-hint` in Sleeve overlays, **after** the four tiles, **before** `#risk-sleeves`. Do not put it inside a sleeve card. Do not `innerHTML` that node (`#risk-sleeves` rebuild is fine).

Default copy (class `warn`, token `#f59e0b`): `A sleeve overlay that breaches the live book flattens now.`

HTML can hold that copy; JS need not rewrite it. CSS: `#risk-overlay-hint.warn { color: #f59e0b; }`.

Keep `#risk-tighten-hint`. `"Gross cap"` still must not appear in assembled JS.

## 5. Help / README

`how_risk`, `how_run`, `task_start`, `task_tighten`, `halt_flatten`: A sleeve overlay that breaches the live book flattens now.

`REQUIRED_PHRASES`: `A sleeve overlay that breaches the live book flattens now`.

README Operator: same.

Keep `Next rebalance`. Keep Start paper while halted waits for resume. Keep Tighten that breaches the live book flattens now.

## 6. In / out

**In:** `_enforce_live_book` after `start_sleeve` persist; start API `flattened`; CLI stderr; overlay hint; CSS; help/README; supervisor / API / CLI / HTML / CSS / help tests.

**Out:** heartbeat flatten; 409 on start; overlay PUT while allocation 0 flattening; changing wanted `check_book` inside `_rebalance`; live; sixth screen; `app.js`; Clock Next paint; Start paper 409; changing halt/flatten/isolate crash recovery.

**Done when:**

1. Idle overlay Name cap 5% + live book 15% + `start_sleeve` flattens immediately (`STOPPED`, `close_all`, kill reason `max_name_weight`) without waiting for a session event. Return `held` false.
2. Same overlay PUT while allocation is 0 does **not** flatten.
3. Overlay PUT while allocation > 0 and live book 15% vs Name cap 5% flattens (`PUT` `{ok: true, flattened: true}`).
4. `POST /api/paper/start` in the idle-then-start case returns `{ok: true, held: false, flattened: true}`.
5. HTML has `#risk-overlay-hint` with the phrase after overlay tiles and before `#risk-sleeves`; CSS maps warn to `#f59e0b`.
6. Help contains the phrase and still contains `Next rebalance`.
7. Five `#nav` screens. `"Gross cap"` not in `js_text`. No real broker.
