# alphastrategy kill-outcome visibility

**Date:** 2026-08-20
**Status:** Requirements (improvement cycle on v1)
**Repo:** `AlphaStrategyAI/alphastrategy`
**Parent contract:** [`2026-08-19-alphastrategy-v1-requirements.md`](2026-08-19-alphastrategy-v1-requirements.md)
**Technical design:** [`docs/plans/2026-08-20-alphastrategy-kill-outcome-technical-design.md`](../plans/2026-08-20-alphastrategy-kill-outcome-technical-design.md)

This document does **not** change product identity. Paper only. Isolated sleeve-kill **behavior** stays as specified in [`2026-08-19-alphastrategy-sleeve-kill-requirements.md`](2026-08-19-alphastrategy-sleeve-kill-requirements.md). This cycle makes that behavior **visible**.

## 1. Why this increment exists

Gap pass against v1 §7–§8, the sleeve-kill contract, Quiet cockpit, and CLI:

| Need | Current behavior |
| --- | --- |
| v1 §7 sleeve kill is isolated residual **or** whole-account flatten | Supervisor already branches and audits `isolated: true/false`. |
| Operator must know **which** branch ran | `POST /api/paper/kill` returns `{ok: true}` either way. CLI prints nothing on success. |
| v1 §8 Portfolio banners “cannot be visually quiet” | `#halt-banner`, `#flatten-banner`, `#deviation-banner`, `#control-plane-banner` live **inside** `#screen-portfolio`. On Run (where Kill is) they are `display: none`. |

Research (applied, not copied):

- **Nielsen heuristic 1 (Visibility of system status):** no consequential action without informing the user. Isolated kill vs fallback flatten is a consequential fork.
- **Kill-switch runbooks** (operator literature; Gloo / agent kill-switch patterns): after a kill, confirm the **scope** that actually engaged (one agent vs global). Audit alone is not the operator surface.
- **Quiet cockpit / stocktrader tiling:** alerts must not live only on a hidden tile. Banners belong in chrome that stays visible while the operator is on any of the five screens.

## 2. Positioning walls (unchanged)

All v1 hard walls remain. Five screens remain. Help remains an aside. `kill_sleeve` isolation rules, halt ≠ flatten, and account `FLATTEN` confirm stay as they are. No live, no WebSockets, no `window.confirm`.

## 3. Kill outcome (machine-readable)

`Supervisor.kill_sleeve` and `Supervisor.kill_account` return a `KillOutcome`:

| Field | Values |
| --- | --- |
| `isolated` | `true` only when residual isolation placed orders (or a no-op residual) **without** `_flatten_account` |
| `flattened` | `true` when the whole paper account was flattened |
| `scope` | `sleeve` \| `account` \| `none` |
| `reason` | `isolated` \| `fallback_not_ready` \| `fallback_error` \| `account` \| `unknown_sleeve` |
| `bundle_id` | sleeve id or `null` for account kill |

Mapping:

| Situation | isolated | flattened | scope | reason |
| --- | --- | --- | --- | --- |
| Isolation succeeded | true | false | sleeve | isolated |
| Not RTH / missing last book | false | true | account | fallback_not_ready |
| Isolation raised | false | true | account | fallback_error |
| Account kill | false | true | account | account |
| Bundle not in sleeves | false | false | none | unknown_sleeve |

Persist the last outcome on the snapshot as `last_kill` (same fields). Overwrite on every kill attempt, including `unknown_sleeve`. Do not clear it on heartbeat.

`GET /api/status` includes `last_kill` (`null` if never killed).

`POST /api/paper/kill` 200 body is `{ok: true, **KillOutcome fields}`.

CLI `alphastrategy paper kill` prints that JSON object on stdout (control-plane or offline) and still exits 0 on HTTP 200. It does **not** add an interactive confirm (unattended scripts stay valid).

## 4. Desk banners (always visible)

Move these nodes **out of** `#screen-portfolio` into a `#desk-banners` region that is a sibling of the five `.screen` sections (inside `main`, not inside Help):

- `#halt-banner`
- `#flatten-banner`
- `#deviation-banner`
- `#control-plane-banner`
- `#kill-outcome-banner` (new)

They remain visible on Portfolio, Strategies, Run, Activity, and Risk.

`#kill-outcome-banner` copy (locked):

| last_kill.reason | class | text |
| --- | --- | --- |
| `isolated` | `banner halt` | `SLEEVE KILL: isolated residual for <id> — other sleeves still live` |
| `fallback_not_ready` or `fallback_error` | `banner fail` | `SLEEVE KILL: could not isolate — whole paper account flattened` |
| `unknown_sleeve` | `banner halt` | `SLEEVE KILL: unknown sleeve <id>` |
| `account` or missing | hidden | (account flatten stays on `#flatten-banner` only) |

Do not auto-dismiss. Do not use a toast. Do not cover the banners with the Help aside (Help stays a right-hand column).

## 5. Help / README

One sentence in `helptext` halt_flatten (and README Operator): sleeve kill reports whether isolation succeeded or the whole account was flattened; banners stay visible on every screen.

## 6. In / out

**In:** `KillOutcome`, `last_kill` on snapshot and `/api/status`, kill POST/CLI JSON, always-visible desk banners, kill-outcome copy, help/README one-liners.

**Out:** CLI `--yes` confirm, changing isolation math, WebSockets, sixth screen, dismissing banners, cloning Risk onto Run.

## 7. Verification

- Unit: `kill_sleeve` return values for isolated, fallback, unknown; snapshot persists `last_kill`.
- API: POST kill JSON; GET status `last_kill`; GET `/` HTML has `#desk-banners` outside `#screen-portfolio`.
- CLI: `paper kill --bundle` prints `"isolated":true` or `"flattened":true`.
- Web: `#kill-outcome-banner`; JS branches on `last_kill.reason`; five nav screens unchanged.
- E2E mocked: isolated kill returns isolated true and does not set STOPPED; fallback returns flattened true.
- No real broker orders.
