# alphastrategy runtime overlay digest and Book Beat/Glance

**Date:** 2026-08-20
**Status:** Requirements (improvement cycle on v1)
**Repo:** `AlphaStrategyAI/alphastrategy`
**Parent contract:** [`2026-08-19-alphastrategy-v1-requirements.md`](2026-08-19-alphastrategy-v1-requirements.md) §5–§8
**Related:** [`2026-08-20-alphastrategy-beat-book-requirements.md`](2026-08-20-alphastrategy-beat-book-requirements.md), [`2026-08-20-alphastrategy-sticky-book-requirements.md`](2026-08-20-alphastrategy-sticky-book-requirements.md), [`2026-08-20-alphastrategy-spoken-cache-requirements.md`](2026-08-20-alphastrategy-spoken-cache-requirements.md)
**Technical design:** [`docs/plans/2026-08-20-alphastrategy-runtime-book-technical-design.md`](../plans/2026-08-20-alphastrategy-runtime-book-technical-design.md)

Paper only. Five screens. Quiet cockpit **tokens unchanged**. No sixth nav tab. No live. No WebSockets. No chart library. Do not revive `static/app.js`. `"Gross cap"` must not appear in assembled JS. `renderBanners` keeps a **single** `const reason`. Do not retry leftover orders. Resume does not catch up. Heartbeat still does **not** flatten. Keep `Next rebalance`. Keep sticky heartbeat live book, envelope SHA-256 cache, live-limit / Caps / Clock. Idle overlays stay unpublished. GET `/api/status` and `/api/risk` must not flatten. Do not feed order sizing from the glance cache. Each JS part stays ≤ 400 lines.

v1 §7: sleeve overlays only tighten; Caps must follow the spoken flatten book. Envelope yaml already keys on SHA-256 because a same-size rewrite can keep `mtime_ns+size`. `runtime.yaml` (operator Tighten / disk overlay) still keys spoken merge and `_read_runtime` on stamp. A same-length overlay rewrite (`0.10` → `0.05`) can leave Caps and the next flatten check on the old cap. That is not 风险可控.

v1 §8: Portfolio Book Equity is the hero NAV. Sticky-book made that NAV the last heartbeat (or a 1s glance fetch). The tile still paints a bare number, so it still looks like a live stream. That is not 凭直觉交互 or 界面令人眼前一亮.

## 1. Why this increment exists

Goal check against current main (`5695b45`):

| Goal slice | v1 / later contract | Current desk |
| --- | --- | --- |
| 风险可控 | Overlay bytes on disk **are** the spoken flatten book. | Envelope digest-cached. Runtime stamp-cached. Same-size Tighten can no-op. |
| 易于维护 | One runtime parse until bytes change. | `_read_runtime` yaml on every stamp miss; spoken key ignores content. |
| 凭直觉交互 | Equity says whether Book is the beat or a glance fetch. | Pulse is in the header. Book Equity has no source. |
| 界面 | Hero tile names Beat Ns / Glance in muted subcopy. | Four Book tiles; only Cash has a sub. |
| 稳定执行 | Kill still drops the sticky book so refresh is not pre-kill NAV. | Already true; Book source must become `glance` after kill. |

Research applied:

- **Content-address research/runtime caps.** Overlay yaml is operator-authored. Parse once per SHA-256. mtime+size is not enough (envelope cycle).
- **Name the snapshot on the blotter.** OMS desks label NAV as the last snapshot (beat) vs an on-demand poll. They do not leave a hero number unlabeled after making it sticky.
- **Do not add a sixth tile or a Live trading mode.** Subcopy on Equity. Words are `Beat` and `Glance`, never sleeve-state `Live`.
- **Do not flatten on GET.** Unchanged.

Out: heartbeat flatten; GET flatten; JS chart; live; `app.js`; changing Caps/Clock paint besides Equity sub; merging HTTP routes.

## 2. Engine / API / paint

`_read_runtime` caches `{digest, doc}` keyed by SHA-256 of `runtime.yaml` bytes (missing → digest `""` and `{}`). `_spoken_cache_key` uses that digest, not `_file_stamp`. A same-size rewrite misses both.

`Supervisor.live_book_source() -> str` under the existing lock: `"none"` if cache empty, `"heartbeat"` if sticky, else `"glance"`.

`GET /api/status` includes `"book": {"source": ...}` **after** utilization (so `live_book()` has run). `GET /api/portfolio` includes the same object.

Portfolio Book Equity grows `#metric-equity-sub`. Paint: heartbeat → `Beat {age}s` (age from `status.heartbeat.age_seconds` when finite) else `Beat`; glance → `Glance`; none/missing → `—`. Helper lives in `paint-rails.js` so `paint-portfolio.js` stays ≤ 400 lines.

Flatten/place still invalidate. After kill, the next status/portfolio source is `glance`.

## 3. Help / README

- `Runtime overlays load once until the file changes`
- `Book Equity names Beat or Glance`

Keep sticky-book and envelope sentences. `"Gross cap"` in help labels only.

## 4. In / out

**In:** runtime digest cache; spoken key uses it; status/portfolio `book.source`; Equity sub; help/README; tests (frozen mtime overlay rewrite, glance vs heartbeat source, kill → glance, paint/html).

**Out:** heartbeat flatten; GET flatten; JS; live; `app.js`; sixth nav.

**Done when:**

1. Rewriting `runtime.yaml` overlay at the same byte length with frozen mtime is visible on the next `spoken_policy()`.
2. Two spoken / sleeve_policies calls with unchanged runtime bytes do not `yaml.safe_load` again.
3. GET status before a beat has `book.source == "glance"`; after `tick()` has `"heartbeat"`; after account kill has `"glance"`.
4. HTML has `#metric-equity-sub`. Assembled JS contains `Beat` and `Glance` book-source paint and does not contain `"Gross cap"`.
5. Help contains both new phrases. Five `#nav` screens. No real broker.
