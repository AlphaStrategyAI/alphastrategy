# alphastrategy kill outcome on remaining operator surfaces

**Date:** 2026-08-20
**Status:** Requirements (improvement cycle on v1)
**Repo:** `AlphaStrategyAI/alphastrategy`
**Parent contract:** [`2026-08-19-alphastrategy-v1-requirements.md`](2026-08-19-alphastrategy-v1-requirements.md)
**Prior increment:** [`2026-08-20-alphastrategy-kill-outcome-requirements.md`](2026-08-20-alphastrategy-kill-outcome-requirements.md)
**Technical design:** [`docs/plans/2026-08-20-alphastrategy-activity-kill-blotter-technical-design.md`](../plans/2026-08-20-alphastrategy-activity-kill-blotter-technical-design.md)

This document does **not** change product identity. Paper only. Isolation math, Web/CLI `FLATTEN` confirm, and `KillOutcome` JSON stay as they are. This cycle finishes **visibility** of isolated vs whole-account flatten on the two operator surfaces the kill-outcome increment left out.

## 1. Why this increment exists

Kill outcome is already on POST `/api/paper/kill`, `GET /api/status` (control plane up), CLI `paper kill` JSON, and `#kill-outcome-banner`. Remaining holes:

| Need | Current behavior |
| --- | --- |
| v1 §8 Activity: halt/flatten with drill-in | `eventSummary` for `kill` is only `bundle_id \|\| scope`. Isolated vs flatten is in the expanded JSON, not the row the operator scans. |
| CLI `status` when the desk is down | Offline payload omits `last_kill` even though `supervisor-state.json` persists it. Control-plane status already includes it. |

Research (applied, not copied):

- **Nielsen heuristic 1 (Visibility of system status):** the blotter row is the scan line. Drill-in is for detail, not for learning *which* flatten branch ran. The banner covers only the **latest** kill; Activity is the history.
- **Audit-log UX** (blotter / trade-journal practice): the closed row states the consequence; the open row holds the payload. Isolated residual vs whole-account flatten is the consequence.
- **Same JSON both paths:** CLI `status` without a live control plane should not silently drop fields the HTTP status already promises.

## 2. Positioning walls (unchanged)

All v1 hard walls remain. Five screens. Help aside. No isolation-math change. No sixth screen. No `window.confirm`. CLI account-kill `FLATTEN` / `--force` stay as specified. Do not clone Risk forms onto Run.

## 3. Activity kill rows

`eventSummary` for `event === "kill"` (locked scan text, then id):

| Audit payload | Summary (plus `bundle_id` when present) |
| --- | --- |
| `isolated === true` | `isolated residual` |
| `isolated === false` **or** `scope === "account"` | `flattened account` |
| neither | `bundle_id` or `scope` as today |

The Activity line stays `timestamp event summary`. Example: `… kill isolated residual asb_x`. Drill-in JSON is unchanged.

Account kill audit today is `{event: "kill", scope: "account"}` with no `isolated`. That still maps to `flattened account`. Do **not** require a Supervisor audit schema change. Do **not** add a sixth banner.

## 4. Offline CLI status

When `GET /api/status` is unreachable, `alphastrategy status` still prints JSON from the on-disk snapshot. That object **must** include `last_kill` (the snapshot value, or `null` if never killed) — the same key as the control-plane handler.

Do not invent `countdown` or a live clock when the control plane is down. Keep `clock: {error: "control plane unavailable"}`.

## 5. Help / README

One sentence: Activity kill rows say isolated residual vs flattened account; `status` includes `last_kill` even when the desk is down.

## 6. In / out

**In:** Activity `kill` scan text; offline `status.last_kill`; help/README one-liners.

**Out:** changing isolation math; rewriting audit JSONL; WebSockets; sixth screen; Risk allocation clone; sleeve CLI confirm; live.

## 7. Verification

- JS `eventSummary` kill branch contains `isolated residual` and `flattened account`.
- `GET /api/activity` after an isolated kill still carries `isolated: true` (existing).
- CLI `status` after `--force` account kill, no control plane: JSON has `last_kill.reason == "account"`.
- CLI `status` after paper start, never killed: `last_kill` is `null`.
- Five nav screens unchanged. No real broker orders.
