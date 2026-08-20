# alphastrategy Tighten PUT reads runtime overlays from the Supervisor

**Date:** 2026-08-20
**Status:** Requirements (improvement cycle on v1)
**Repo:** `AlphaStrategyAI/alphastrategy`
**Parent contract:** [`2026-08-19-alphastrategy-v1-requirements.md`](2026-08-19-alphastrategy-v1-requirements.md) §5–§8
**Related:** [`2026-08-20-alphastrategy-book-enforce-requirements.md`](2026-08-20-alphastrategy-book-enforce-requirements.md), [`2026-08-20-alphastrategy-runtime-book-requirements.md`](2026-08-20-alphastrategy-runtime-book-requirements.md), [`2026-08-20-alphastrategy-live-glance-requirements.md`](2026-08-20-alphastrategy-live-glance-requirements.md)
**Technical design:** [`docs/plans/2026-08-20-alphastrategy-risk-put-cache-technical-design.md`](../plans/2026-08-20-alphastrategy-risk-put-cache-technical-design.md)

Paper only. Five screens. Quiet cockpit **tokens unchanged**. No sixth nav tab. No live. No WebSockets. No chart library. Do not revive `static/app.js`. `"Gross cap"` must not appear in assembled JS. `renderBanners` keeps a **single** `const reason`. Do not retry leftover orders. Resume does not catch up. Heartbeat still does **not** flatten. GET `/api/status` and `/api/risk` must not flatten. Keep `Next rebalance`. Keep sticky heartbeat live book, Book flatten-now, Book/Beat/Headroom source labels, LIMIT/BOOK stderr. Idle overlays stay unpublished. **Do not feed order sizing from the glance cache.** Each JS part stays ≤ 400 lines.

v1 §5: Supervisor is the sole order placer and the owner of spoken caps. GET `/api/risk` already builds sleeves from `supervisor.sleeve_policies` (digest-cached `runtime.yaml` and envelopes). PUT `/api/risk` still calls `handlers._load_runtime` + `handlers._bundle_envelope` — a second YAML parse that can disagree with Caps after a same-size rewrite, and that bypasses the spoken cache. That is not 风险可控 or 易于维护.

## 1. Why this increment exists

Goal check against current main (`310895b`):

| Goal slice | v1 / later contract | Current desk |
| --- | --- | --- |
| 风险可控 | Overlay bytes on disk **are** the spoken flatten book. | GET uses SHA-256 cache. PUT re-parses with `read_text` / `load_risk_envelope` and never asks the Supervisor. |
| 易于维护 | One runtime/envelope parser. | Two copies: `handlers._load_runtime` vs `Supervisor._read_runtime`. |
| 可靠 | Tighten validate → persist → flatten-now is one lock. | PUT plans overlays unlocked, then `set_policy` / `enforce_live_book` take the lock separately. |
| 凭直觉交互 | Caps after Tighten match what just saved. | Independent parse can keep an old envelope if handlers ever drift from digest cache. |
| 稳定执行 | Flatten-now still uses the Book glance. | Unchanged if PUT still ends in `enforce_live_book`. |

Research applied:

- **One writer for overlay yaml.** OMS desks do not let the HTTP adapter parse risk files the matching engine does not see. PUT becomes `Supervisor.apply_risk`.
- **Copy before mutate.** `_read_runtime` returns the cached dict. Planning overlays must `copy.deepcopy` so a refused PUT cannot poison Caps.
- **Durable persist stays `replace_text`.** Move the write next to `_read_runtime`. `test_save_runtime_source_uses_replace_text` follows the new function.
- **Startup overlay uses the same read.** `_apply_startup_runtime` calls `supervisor._read_runtime()` instead of `handlers._load_runtime`.

Out: heartbeat flatten; GET flatten; glance-fed orders; Cash/PnL source subs; JS paint; live; sixth screen; changing merge_limits tighten-only rules.

## 2. Engine / API

`Supervisor.apply_risk(account_patch, sleeves_patch) -> bool` under `_lock`:

1. `runtime = copy.deepcopy(self._read_runtime())`.
2. Same validation as today’s PUT (`account`/`sleeves` must be objects; sleeve patches objects; `merge_limits` tighten-only via `_bundle_envelope`).
3. Account patch: `self._policy = merge_limits({}, self._policy, account_patch)` then `_enforce_live_book()` (same as `set_policy`).
4. Persist planned overlays with `replace_text(..., prefix=".runtime.")` (same dump: `yaml.safe_dump(..., sort_keys=True)`).
5. Sleeve patch: `_enforce_live_book()` after the file is on disk so `_rebalance_policy` digest-misses.
6. Return whether state is `flattening` or `stopped`.

`handle_put_risk` reads JSON, calls `apply_risk`, returns `{ok, flattened}`. It must not call `_load_runtime` or `_bundle_envelope`.

Delete `handlers._load_runtime` and `handlers._bundle_envelope` once unused. `_apply_startup_runtime` uses `supervisor._read_runtime()`. If `_save_runtime` moves onto Supervisor, the persist source lock moves with it.

Do not flatten on GET. Do not publish idle overlays. Flatten-now still uses the Book live book.

## 3. Help / README

Phrase (exact): `Tighten PUT reads runtime overlays from the Supervisor`

Add it to `execution`, `halt_flatten`, `how_risk`, `task_tighten`, README Operator. Keep `Runtime overlays load once until the file changes`. Keep `Next rebalance`.

## 4. In / out

**In:** `apply_risk`; PUT thin wrapper; startup uses `_read_runtime`; persist `replace_text` stays; help/README; source + API + envelope-cache tests.

**Out:** heartbeat flatten; GET flatten; JS; live; sixth nav; changing Book flatten-now.

**Done when:**

1. `handle_put_risk` source contains `apply_risk` and does not contain `_load_runtime` or `_bundle_envelope`.
2. PUT overlay after `sleeve_policies` does not call `handlers.load_risk_envelope`.
3. PUT account tighten still persists `runtime.yaml` via `replace_text` and can flatten the live book.
4. Same-size `runtime.yaml` rewrite is still visible on the next `spoken_policy()` (existing lock).
5. Help contains the new phrase and `Next rebalance`. Five `#nav` screens. `"Gross cap"` not in assembled JS. No real broker.
