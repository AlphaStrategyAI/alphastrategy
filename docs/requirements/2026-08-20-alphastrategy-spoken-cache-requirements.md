# alphastrategy spoken policy is reused until overlays or allocations change

**Date:** 2026-08-20
**Status:** Requirements (improvement cycle on v1)
**Repo:** `AlphaStrategyAI/alphastrategy`
**Parent contract:** [`2026-08-19-alphastrategy-v1-requirements.md`](2026-08-19-alphastrategy-v1-requirements.md) §5–§8
**Related:** [`2026-08-20-alphastrategy-spoken-caps-requirements.md`](2026-08-20-alphastrategy-spoken-caps-requirements.md), [`2026-08-20-alphastrategy-caps-limit-requirements.md`](2026-08-20-alphastrategy-caps-limit-requirements.md)
**Technical design:** [`docs/plans/2026-08-20-alphastrategy-spoken-cache-technical-design.md`](../plans/2026-08-20-alphastrategy-spoken-cache-technical-design.md)

Paper only. Five screens. Quiet cockpit **tokens unchanged**. No sixth nav tab. No live. No WebSockets. No chart library. Do not revive `static/app.js`. `"Gross cap"` must not appear in assembled JS. `renderBanners` keeps a **single** `const reason`. Do not retry leftover orders. Resume does not catch up. Heartbeat still does **not** flatten. Keep `Next rebalance`. Keep live-limit banner, Clock `flatten ·`, Caps fail on `live_limit`. Keep overlay-on-start flatten. Idle overlays stay unpublished. Do not flatten on GET `/api/status` or `/api/risk`.

v1 §5: one Supervisor, combined book uses account policy tightened by each allocated sleeve. `spoken_policy()` is that merge. Every cockpit refresh hits GET status + GET risk; each calls `spoken_policy` / `from_supervisor` / `_rebalance_policy`, and `_rebalance_policy` re-reads `runtime.yaml` plus each allocated `risk-envelope.yaml` **per sleeve per call**. That is not 易于维护 and is a reliability footgun: a torn yaml read mid-poll can disagree with Caps vs utilization vs the next rebalance, and the 5s poll multiplies disk I/O. Disk overlay edits must still win on the next `spoken_policy()` — do not freeze a stale merge across a runtime.yaml write.

## 1. Why this increment exists

Goal check against current main (`165a339`):

| Goal slice | v1 / later contract | Current desk |
| --- | --- | --- |
| 可靠 | Spoken book is one merge per unchanged overlay/allocation/account policy. | `_effective_sleeve_policy` calls `_read_runtime()` once per allocated sleeve, every `spoken_policy()`. Status + risk polls do this several times per 5s. |
| 易于维护 | One `_rebalance_policy` result reused until inputs change. | No cache. Yaml parse on the hot path. |
| 风险可控 | Idle overlay still unpublished. Disk overlay write still tightens before the next flatten check. | Cache must miss when `runtime.yaml` mtime/size, envelope stamps, allocations, or `_policy` change. |
| 凭直觉交互 | Caps / LIMIT / Clock still follow the same spoken book. | Paint unchanged. Help names the reuse so operators know a runtime.yaml save is enough. |

Research applied:

- **Memoize by input stamp, not TTL.** Risk engines cache working limits until the overlay file or sleeve set changes. A 5s TTL would serve a stale cap after Tighten.
- **Stat is cheap; yaml parse is not.** Cache key uses `st_mtime_ns` + `st_size` for `runtime.yaml` and allocated envelopes. Hit returns the frozen `AccountPolicy`.
- **One runtime load per miss.** `_rebalance_policy` reads `runtime.yaml` once, then tightens each allocated sleeve.
- **Do not flatten on this path.** Cache is read-only. Heartbeat / GET still do not flatten.

Out: heartbeat flatten; GET flatten; cockpit JS paint; CLI LIMIT copy; changing Caps fail; live; `app.js`.

## 2. Engine

`Supervisor._rebalance_policy` (and therefore `spoken_policy()`):

1. Under the existing `RLock` family.
2. Build a cache key: runtime stamp, allocated-sleeve envelope stamps, allocated `(bundle_id, allocation)` pairs, and the current `_policy` object.
3. On hit, return the cached `AccountPolicy`.
4. On miss: `_read_runtime()` **once**; for each sleeve with allocation > 0, `tighten_policy` with envelope ∩ overlay from that runtime dict; store and return.

`start_sleeve` / `stop_sleeve` / `set_policy` change allocations or `_policy`, so the next call misses. Writing `runtime.yaml` changes the stamp, so the next call misses. Allocation 0 still does not publish that sleeve's overlay.

GET `/api/status` and GET `/api/risk` still must not `close_all`.

## 3. Help / README

- `Spoken policy is reused until overlays or allocations change`

Keep Caps / live-limit / Clock flatten sentences. `"Gross cap"` in help labels only.

## 4. In / out

**In:** `_rebalance_policy` stamp cache; one runtime yaml load per miss; help/README; tests.

**Out:** heartbeat flatten; GET flatten; JS paint; live; `app.js`.

**Done when:**

1. Two `spoken_policy()` calls with unchanged disk/allocations/`_policy` invoke `_read_runtime` only on the first.
2. Rewriting `runtime.yaml` overlay is visible on the next `spoken_policy()`.
3. `stop_sleeve` (allocation 0) drops that overlay from spoken (idle unpublished).
4. Help contains the new phrase. Five `#nav` screens. `"Gross cap"` not in `js_text`. No real broker.
