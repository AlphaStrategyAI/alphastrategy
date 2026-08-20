# alphastrategy Caps names the cap the live book is through

**Date:** 2026-08-20
**Status:** Requirements (improvement cycle on v1)
**Repo:** `AlphaStrategyAI/alphastrategy`
**Parent contract:** [`2026-08-19-alphastrategy-v1-requirements.md`](2026-08-19-alphastrategy-v1-requirements.md) §7–§9
**Related:** [`2026-08-20-alphastrategy-live-limit-requirements.md`](2026-08-20-alphastrategy-live-limit-requirements.md), [`2026-08-20-alphastrategy-spoken-caps-requirements.md`](2026-08-20-alphastrategy-spoken-caps-requirements.md), [`2026-08-20-alphastrategy-flatten-next-requirements.md`](2026-08-20-alphastrategy-flatten-next-requirements.md)
**Technical design:** [`docs/plans/2026-08-20-alphastrategy-caps-limit-technical-design.md`](../plans/2026-08-20-alphastrategy-caps-limit-technical-design.md)

Paper only. Five screens. Quiet cockpit **tokens unchanged**. No sixth nav tab. No live. No WebSockets. No chart library. Do not revive `static/app.js`. `"Gross cap"` must not appear in assembled JS. `renderBanners` keeps a **single** `const reason`. Do not retry leftover orders. Resume does not catch up. Heartbeat still does **not** flatten. Keep `Next rebalance`. Keep `held ·` / `flat ·` / `flatten ·`. Keep live-limit banner. Keep overlay-on-start flatten. Keep Book Drift on last fill. Keep spoken Caps. Idle overlays stay unpublished. CLI `status` stdout stays JSON.

Live-limit already paints a LIMIT banner and Clock Next `flatten ·` while `last_got` is through the spoken cap. Caps is the spoken book — the four flatten-critical numbers the operator came to Risk to read — and those tiles stay default color (or overlay-tighter warn) while the live book is already through one of them. CLI `status` dumps utilization JSON, including `live_limit`, with no operator line. That is not 凭直觉交互.

## 1. Why this increment exists

Goal check against current main (`8b71fc6`):

| Goal slice | v1 / later contract | Current desk |
| --- | --- | --- |
| 风险可控 | Spoken Caps are the flatten switch. A live book through a spoken cap must name **which** cap on Risk, not only a Portfolio banner. | Caps Name cap 20% looks healthy while LIMIT says Name cap. Overlay-tighter warn is a different signal. |
| 凭直觉交互 | The tile that is the kill switch lights up. CLI operators who never open the desk still hear LIMIT. | Risk Caps ignore `utilization.live_limit`. `alphastrategy status` stdout is JSON only. |
| 易于使用 | Help: Caps names the cap the live book is through. status names LIMIT. | Help says Caps is the spoken book and the banner warns; not that Caps tiles fail. |
| 界面 | Pending through-cap is fail `#ef4444` on that Caps tile (the switch that is tripped). Overlay-tighter stays warn `#f59e0b`. Fail wins. Already-flat still hides LIMIT (flatten clears `last_got`). | No Caps `.fail` token. |

Research applied:

- **Limit widget vs overlay widget.** Overlay-tighter warn means spoken is stricter than the writable account form. Live-limit fail means the **book** is through that spoken number. Same tile, two jobs, two tokens.
- **Same LIMIT sentence on CLI stderr.** paper start already writes held/flattened to stderr and keeps stdout clean. status JSON stays parseable.
- **Do not flatten on status.** GET `/api/status` and offline `from_supervisor` stay read-only. Heartbeat still does not flatten.

Out: heartbeat flatten; GET flatten; countdown JSON; sixth screen; `app.js`; spoken_policy yaml cache; changing LIMIT banner copy; putting `"Gross cap"` in JS.

## 2. Paint

`renderRiskCaps` after overlay-tighter `warn`:

| `utilization().live_limit.reason` | Tile | class |
| --- | --- | --- |
| `max_gross` | `#risk-cap-gross` | `fail` |
| `max_name_weight` | `#risk-cap-name` | `fail` |
| `max_names` | `#risk-cap-names` | `fail` |
| `max_orders_per_day` | `#risk-cap-orders` | `fail` |
| `long_only` | `#risk-cap-long` | `fail` |

Skip fail while flattened/flattening/stopped (FLAT owns that state). Overlay-tighter `warn` stays; if both apply, keep both classes and let `.fail` color win.

CSS (four Caps values + Long only), each its own rule like the existing `.warn` set:

`#risk-cap-gross.fail`, `#risk-cap-name.fail`, `#risk-cap-names.fail`, `#risk-cap-orders.fail`, `#risk-cap-long.fail` → `#ef4444`.

Do not put `"Gross cap"` in JS. Each `js/` part stays ≤ 400 lines.

## 3. CLI

`alphastrategy status`: stdout remains one JSON object.

When payload is not flattened and `utilization.live_limit.reason` is set, stderr one line:

`LIMIT: live book through <label_for(reason)> — next rebalance will flatten`

Same sentence family as the desk banner. Control-plane GET and offline `from_supervisor` both feed this. Do not flatten. Do not change JSON keys.

## 4. Help / README

- `Caps names the cap the live book is through`
- `status names LIMIT while the live book is through the spoken cap`

Keep Caps is the spoken book. Keep live-limit warn / Clock flatten sentences. `"Gross cap"` in help labels only.

## 5. In / out

**In:** Caps tile fail from `live_limit.reason`; Caps/Long only fail tokens; CLI status stderr LIMIT; help/README; tests.

**Out:** heartbeat flatten; GET flatten; live; `app.js`; spoken_policy cache.

**Done when:**

1. `renderRiskCaps` adds `fail` from `utilization().live_limit.reason` and still overlay-tighter `warn`.
2. CSS fail tokens are `#ef4444` on the five Caps ids.
3. `alphastrategy status` stderr contains LIMIT when `last_got` is through Name cap; stdout is still JSON; omitted when flattened.
4. Help contains both new phrases. Five `#nav` screens. `"Gross cap"` not in `js_text`. No real broker.
