# alphastrategy Clock Next is flatten while the live book is through the spoken cap

**Date:** 2026-08-20
**Status:** Requirements (improvement cycle on v1)
**Repo:** `AlphaStrategyAI/alphastrategy`
**Parent contract:** [`2026-08-19-alphastrategy-v1-requirements.md`](2026-08-19-alphastrategy-v1-requirements.md) §6–§8
**Related:** [`2026-08-20-alphastrategy-live-limit-requirements.md`](2026-08-20-alphastrategy-live-limit-requirements.md), [`2026-08-20-alphastrategy-flat-next-requirements.md`](2026-08-20-alphastrategy-flat-next-requirements.md), [`2026-08-20-alphastrategy-halt-next-held-requirements.md`](2026-08-20-alphastrategy-halt-next-held-requirements.md), [`2026-08-20-alphastrategy-overlay-start-requirements.md`](2026-08-20-alphastrategy-overlay-start-requirements.md)
**Technical design:** [`docs/plans/2026-08-20-alphastrategy-flatten-next-technical-design.md`](../plans/2026-08-20-alphastrategy-flatten-next-technical-design.md)

Paper only. Five screens. Quiet cockpit **tokens unchanged**. No sixth nav tab. No live. No WebSockets. No chart library. Do not revive `static/app.js`. `"Gross cap"` must not appear in assembled JS. `renderBanners` keeps a **single** `const reason`. Do not retry leftover orders. Resume does not catch up. Heartbeat still does **not** flatten. Keep `Next rebalance`. Keep `held ·` / `flat ·`. Keep live-limit banner. Keep overlay-on-start flatten. Keep Book Drift on last fill. Keep spoken Caps. Idle overlays stay unpublished.

Live-limit already paints a LIMIT banner when `last_got` is through the spoken cap, and close flattens. Clock Next is the hero. While that banner is up, Next still ticks `open`/`close` in default color — the same lie halt-next-held and flat-next already fixed for HALTED and FLAT. After Start paper (or tighten) flattens, Run Start hint still says only the generic restart sentence. POST `/api/paper/start` already returns `flattened`; both start handlers discard it. That is not 凭直觉交互.

## 1. Why this increment exists

Goal check against current main (`e991313`):

| Goal slice | v1 / later contract | Current desk |
| --- | --- | --- |
| 凭直觉交互 | Clock Next names inhibit: held, flat, and **pending flatten**. | LIMIT banner warns; Next still looks like a normal auction. |
| 风险可控 | Next legal send will flatten. Operator must see it on the Clock hero, not only a banner. | Hero countdown is unmarked. |
| 易于使用 | Start paper that flattens names the breached cap, then the restart sentence. | Run hint after overlay/tighten flatten is only “Start paper after flatten starts the session loop again…”. POST `flattened` is unused. |
| 界面 | Pending flatten is warn `#f59e0b` (not yet fail). Already-flat stays fail `#ef4444`. | No `flatten ·` state. |

Research applied:

- **Same Clock inhibit family.** Halt = `held ·` + warn. Flattened = `flat ·` + fail. Pending live-limit = `flatten ·` + warn (matches LIMIT banner, not FLAT).
- **Do not change countdown JSON.** Paint is the honesty layer, same as held/flat.
- **POST `flattened` is not optional copy.** Start handlers must read it so the control plane contract is visible on Run, then refresh still loads `last_kill`.

Out: heartbeat flatten; GET flatten; changing LIMIT banner copy; 409; live; sixth screen; `app.js`; spoken_policy yaml cache.

## 2. Paint

`renderSessionMetrics` countdown fork, first match:

| Condition | `#metric-countdown` | class | `#metric-countdown-kind` |
| --- | --- | --- | --- |
| halted | seconds | `warn` | `held · ` + kind |
| flattened | seconds | `fail` | `flat · ` + kind |
| `utilization().live_limit.reason` | seconds | `warn` | `flatten · ` + kind |
| else | seconds | neither | kind |

Keep `countEl.classList.remove("warn", "fail")` first.

`renderRunStartHint` while flattened: if `last_kill.reason` is `long_only` or a numeric cap, prefix `policyLabel(reason) + " flattened the paper account. "` then keep the exact restart sentence `Start paper after flatten starts the session loop again and does not catch up.` Generic flatten keeps that sentence alone.

`onStartSubmit` and the sleeve-card start POST: assign the JSON (`started.flattened` / `started.held`) before `refresh()`. Do not `window.confirm`. Do not skip refresh.

## 3. Help / README

- `Clock Next is flatten while the live book is through the spoken cap`
- `Start paper that flattens names the breached cap`

Keep held/flat Next sentences. Keep overlay flatten. Keep live-limit warn sentence. `"Gross cap"` in help labels only.

## 4. In / out

**In:** Clock `flatten ·` + warn; Run start hint names cap; both start POSTs read `flattened`; help/README; tests.

**Out:** heartbeat flatten; countdown JSON; live; `app.js`.

**Done when:**

1. `renderSessionMetrics` contains `flatten · ` and adds countdown `warn` when `live_limit` is set; halt still `held ·`; flattened still `flat ·` + fail.
2. `renderRunStartHint` reads `last_kill.reason` and `policyLabel`.
3. `onStartSubmit` and sleeve start POST read `.flattened`.
4. Help contains both new phrases. Five `#nav` screens. `"Gross cap"` not in `js_text`. No real broker.
