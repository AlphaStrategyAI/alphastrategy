# alphastrategy flatten interrupt glance

**Date:** 2026-08-20
**Status:** Requirements (improvement cycle on v1)
**Repo:** `AlphaStrategyAI/alphastrategy`
**Parent contract:** [`2026-08-19-alphastrategy-v1-requirements.md`](2026-08-19-alphastrategy-v1-requirements.md)
**Related:** [`2026-08-20-alphastrategy-flattening-crash-requirements.md`](2026-08-20-alphastrategy-flattening-crash-requirements.md), [`2026-08-20-alphastrategy-interrupt-glance-requirements.md`](2026-08-20-alphastrategy-interrupt-glance-requirements.md), [`2026-08-20-alphastrategy-execution-honesty-requirements.md`](2026-08-20-alphastrategy-execution-honesty-requirements.md)
**Technical design:** [`docs/plans/2026-08-20-alphastrategy-flatten-interrupt-glance-technical-design.md`](../plans/2026-08-20-alphastrategy-flatten-interrupt-glance-technical-design.md)

Paper only. Five screens. Quiet cockpit **tokens unchanged**. No sixth nav tab. No live. No WebSockets. No chart library. Resume still does **not** catch up. Do not revive `static/app.js`. Do not change the flatten retry itself.

This cycle makes **interrupted flattening** visible. The engine already finishes `close_all` when a `flattening` snapshot is loaded. The flatten banner still always says `FLAT: paper account flattened`, so a host death mid-kill looks like the operator typed `FLATTEN`.

## 1. Why this increment exists

Goal check against current main (`5410dfd`):

| Goal slice | v1 / later contract | Current desk |
| --- | --- | --- |
| 凭直觉交互 | Execution honesty: flatten cannot look idle; banners cannot be quiet. Interrupt glance: sleeve isolate interrupt has a kill-outcome row. | Interrupted flattening records no `last_kill` and no flatten `reason`. Banner copy is the same as account kill. |
| 风险可控 | Flatten is the last kill-switch rung. | Operator cannot tell a recovered crash from a deliberate flatten. |
| 易于维护 | Same load-hook family as isolate recover | Isolate recover already writes `last_kill`. Flatten recover should too, with a **non-sleeve** reason so `#kill-outcome-banner` stays hidden. |

Research applied: paint the fork on the existing flatten banner, do not add a sixth banner id.

## 2. Recover records why

`_recover_interrupted_flatten` after a successful `_flatten_account`:

1. Flatten audit includes `reason: flatten_interrupted` (other flatten audits use `reason: account`).
2. `last_kill` is `isolated: false`, `flattened: true`, `scope: account`, `reason: flatten_interrupted`, `bundle_id: null`.

Do **not** show this reason on `#kill-outcome-banner` (that banner is sleeve-kill outcomes). Account kill (`reason: account`) still hides there.

## 3. Flatten banner

When the book is flattened:

| last_kill.reason | `#flatten-banner` text |
| --- | --- |
| `flatten_interrupted` | `FLAT: interrupted flattening — paper account flattened` |
| anything else (including missing) | `FLAT: paper account flattened` |

Interrupted sleeve isolate keeps the generic FLAT line plus the existing kill-outcome row.

## 4. Activity / help

Activity `flatten` summary includes `interrupted flattening` when `ev.reason === "flatten_interrupted"`.

Halt/flatten help: the flatten banner names interrupted flattening when the host died mid-close_all.

## 5. In / out

**In:** flatten audit `reason`; recover `last_kill.reason=flatten_interrupted`; flatten banner fork; Activity copy; help. Tests.

**Out:** changing flatten retry; sleeve-isolate halt path; Clock / Positions / Risk / Tighten tiles; live; WebSockets; `app.js`; sixth screen; a new banner id.

## 6. Verification

- Restart from a `flattening` snapshot: `last_kill.reason == flatten_interrupted`; flatten audit has that reason; `close_all` still ran.
- JS flatten banner contains both FLAT strings and `flatten_interrupted`. Activity flatten branch contains `interrupted flattening`.
- Help contains `flatten banner names interrupted flattening`. `#nav` five screens. No `Gross cap` in JS.
- No real broker orders.
