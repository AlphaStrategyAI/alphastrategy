# alphastrategy Start paper seeds last sleeve weights

**Date:** 2026-08-21
**Status:** Requirements (improvement cycle on v1)
**Repo:** `AlphaStrategyAI/alphastrategy`
**Parent contract:** [`2026-08-19-alphastrategy-v1-requirements.md`](2026-08-19-alphastrategy-v1-requirements.md) §5, §7, §8
**Related:** [`2026-08-21-alphastrategy-wait-weights-requirements.md`](2026-08-21-alphastrategy-wait-weights-requirements.md)
**Technical design:** [`docs/plans/2026-08-21-alphastrategy-start-weights-technical-design.md`](../plans/2026-08-21-alphastrategy-start-weights-technical-design.md)

Paper only. Five screens. Quiet cockpit **tokens unchanged**. No sixth nav tab. No live. No WebSockets. No chart library. Do not revive `static/app.js`. `"Gross cap"` must not appear in assembled JS. `renderBanners` keeps a **single** `const reason`. Do not retry leftover orders. Resume does not catch up. Heartbeat still does **not** flatten. GET must not flatten. GET must **not** evaluate DSL. Keep `Next rebalance`. Keep Caps **four tiles**. Keep Headroom **four tiles**. Keep Positions glance **Rows / Wanted / Got / At cap**. Keep `live_limit.kind` book / send / unknown. Keep Book LIMIT rail. Do **not** overwrite Cash composition labels. Each JS part stays ≤ 400 lines. **Do not feed `_place_batch` from `live_book()`.** Positions **Wanted stays last combined**. Book Drift still last wanted vs last fill. Do not invent conformance weights as the next send. Keep `Caps LIMIT waits when a paper sleeve has no last weights` for incomplete injected state.

v1 §5: the next legal send evaluates DSL then combines current paper allocations. Wait-weights fail-closes Caps / Next / Headroom when any positive sleeve lacks `last_sleeve_weights`. That is correct for torn state. After flatten, or when adding a second sleeve, Start paper is the explicit write path — and it currently persists allocation only. Caps then say `next send waits for last sleeve weights` until the next RTH rebalance. The operator just named 18% and the whole next-send desk goes mute. Pre-trade research: a control that changes the next book must refresh the state that gate needs, on that write, not on glance. Waiting until open+3 minutes is not 可靠, 风险可控, or 凭直觉交互.

## 1. Why this increment exists

Goal check against current main (`c9431f8`):

| Goal slice | v1 / later contract | Current desk |
| --- | --- | --- |
| 可靠 | Next send uses current paper sleeves’ DSL weights. | Start paper leaves `last_sleeve_weights` empty. |
| 风险可控 | Caps dry-run the next send. | After Start, LIMIT is `unknown`; leftover last combined must not certify. |
| 组合管理 | §8 combined positions at a glance | Positions Next / Headroom / Contribution stay fail-closed. |
| 凭直觉交互 | Start paper is the allocation control | Clock Next stays `weights ·` after the operator just started. |

Research applied:

- **Write path, not GET.** Evaluate DSL in `start_sleeve` (same `_sleeve_weights` as rebalance). Do not sandbox on GET / status / heartbeat.
- **Seed only when missing.** If `last_sleeve_weights[id]` is already a non-empty dict, keep last-rebalance DSL (Caps LIMIT follows current allocations on **last** sleeve weights). Do not re-eval on Set allocation.
- **Do not place.** Seeding is not a rebalance. Do not update `last_combined` / `last_sleeve_contribution` / last fill.
- **Fail closed on eval.** `HaltRequested` / `IllegalWeights` → health halt, do not flatten, do not invent weights. Incomplete snapshot inject without Start still yields `unknown`.
- **Offline.** `broker is None` → skip seed (same as skip live-book flatten).
- **Live bars, not conformance.** `_sleeve_weights` / `weight_fn` fetch broker bars. Do not copy `conformance/` expected weights.

Out: GET flatten; DSL on GET; placing on start (except existing live-book flatten); rewriting last combined; live; sixth screen.

## 2. Engine / API

`Supervisor.start_sleeve`, after `paper_start` audit, before persist + `_enforce_live_book`:

`_seed_last_sleeve_weights(bundle_id, allocation)`:

1. Return if `allocation <= 0` or `self._broker is None`.
2. Return if `last_sleeve_weights[bundle_id]` is a non-empty dict.
3. `weights = _sleeve_weights(bundle_id)` then `_validate_weights`.
4. On success: `last_sleeve_weights[bundle_id] = dict(weights)` (do not drop other ids).
5. On `HaltRequested` or `IllegalWeights`: `_halt(str(exc))`, do not write weights, do not flatten.

Do not `check_book` the implied next book here (send-time / Caps GET). Do not call `_place_batch`.

Fixture (do **not** use 0.40 name weight):

- leftover last combined AAPL **0.18**, empty weights, empty sleeves, marks $100, Order size **0.10**, empty qty
- `POST /api/paper/start` `asb_y` allocation **0.18** (evaluator `{MSFT: 1.0}`)
- `live_limit.kind == "send"`, reason `max_order_notional_frac` (MSFT 0.18 notional $1,800 > $1,000)
- **not** `next_send_unknown`
- Positions: AAPL `wanted == 0.18` (last combined), no `next`; MSFT `next == 0.18`
- `last_sleeve_weights["asb_y"]["MSFT"] == 1.0`
- `last_combined` still `{AAPL: 0.18}`
- GET `close_all` unchanged

Keep `test_status_live_limit_unknown_when_paper_sleeve_has_no_last_weights` (inject sleeves, no Start).
Keep `test_status_live_limit_unknown_when_one_paper_sleeve_missing_weights`.
Keep `test_flatten_clears_last_book_and_zeros_sleeves`.
Keep `test_start_sleeve_after_flatten_leaves_stopped_without_catchup`.

Second: existing `last_sleeve_weights[asb_test] = {AAPL: 1.0}`; `weight_fn` would return `{MSFT: 1.0}`; Start 0.18 → **no** `weight_fn` call; AAPL 1.0 kept.

Third: eval failure (no evaluator) → HALTED, no weights, `close_all` unchanged.

## 3. Cockpit / CLI

No JS/HTML change required: after Start, GET already paints Next / Caps / Clock from seeded weights. Unknown copy stays for injected incomplete state.

Do not put `Order size` / `Gross cap` in JS.

## 4. Help / README

Phrase (exact): `Start paper seeds last sleeve weights`

Add to `execution` (after Caps LIMIT waits when a paper sleeve has no last weights), `halt_flatten` (same block), `how_run` (after Start paper is a second explicit action). README Operator after Caps LIMIT waits. Keep `Caps LIMIT waits when a paper sleeve has no last weights`. Keep `Clock Next is weights while a paper sleeve has no last weights`. Keep `Next rebalance`.

## 5. In / out

**In:** seed `last_sleeve_weights` on Start paper when missing; halt on eval failure; help/README; supervisor + API tests.

**Out:** GET flatten; DSL on GET; placing; rewriting last combined / contribution; conformance as next send; live; sixth nav.

**Done when:**

1. POST start `asb_y` 0.18 after leftover last combined AAPL 0.18 → send LIMIT through Order size, not unknown; MSFT next 0.18; Wanted AAPL stays 0.18; `close_all` unchanged.
2. Allocation replace does not re-eval existing last weights.
3. Injected sleeve without Start still unknown.
4. Help contains the phrase. Five `#nav` screens. `"Gross cap"` not in assembled JS. No real broker.
