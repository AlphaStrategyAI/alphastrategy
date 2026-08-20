# alphastrategy supervisor heartbeat pulse

**Date:** 2026-08-20
**Status:** Requirements (improvement cycle on v1)
**Repo:** `AlphaStrategyAI/alphastrategy`
**Parent contract:** [`2026-08-19-alphastrategy-v1-requirements.md`](2026-08-19-alphastrategy-v1-requirements.md)
**Technical design:** [`docs/plans/2026-08-20-alphastrategy-heartbeat-pulse-technical-design.md`](../plans/2026-08-20-alphastrategy-heartbeat-pulse-technical-design.md)

Paper only. Five screens. Quiet cockpit tokens unchanged. No sixth nav tab. No live money. No WebSockets. Heartbeat still does **not** place orders. Halt vs flatten matrix unchanged.

This cycle makes **whether the Supervisor loop is actually beating** a first-class fact on the desk — the reliability question v1 §6 states and the UI currently cannot answer.

## 1. Why this increment exists

Goal check against current main (`29d8c92`):

| Goal slice | v1 contract | Current desk |
| --- | --- | --- |
| Reliable | §6 Heartbeat every 20s: health and reconciliation. Closing the browser does not stop the Supervisor. Host sleep does. | HTTP poll every 5s is not a heartbeat. If the daemon thread dies, `/api/status` still 200s from a live process and the header still says `alphastrategy · paper`. |
| Stable execution | Heartbeat does not rebalance; open+3m / close−12m do. Activity is the blotter. | `tick()` returns immediately on `halted` / `stopped` / `flattening` **without persisting**. After halt or flatten the 20s thread is alive but leaves no stamp. Activity empty copy is `No events` — it does not say the loop is running or when rebalances fire. |
| Intuitive / striking | §8 Portfolio is home; banners cannot be visually quiet. | Session OPEN is the **market** clock. Operators read it as “the desk is live.” There is no pulse for the **Supervisor thread**. Quiet cockpit can still have a header beat (Bloomberg-style) without new colors. |
| Easy to maintain | One interval constant. | `HEARTBEAT_INTERVAL_SEC = 20` lives only in `api/app.py`. Pulse thresholds would drift if copied into JS. |

Research applied (not copied as an EMS):

- **Liveness vs readiness:** Kubernetes-style. HTTP serving is readiness. A 20s `tick()` stamp is liveness. Show both: control-plane banner (readiness) and header pulse (liveness).
- **SRE stale-heartbeat:** warn after ~2 missed beats, fail after ~4. Interval 20s → live ≤45s, stale ≤90s, else dead.
- **Quiet cockpit:** one header pulse + Activity beat line. Do not audit a JSONL row every 20s (that would bury real events).

Out of this cycle: splitting `app.js`; chart libraries; changing the 20s interval or rebalance schedule.

## 2. Stamp every tick

`Supervisor.tick()` sets `last_heartbeat_at` (UTC ISO-8601, `Z` suffix) at the start of every invocation, **including** `halted` / `flattening` / `stopped` early returns, then persists.

Heartbeat still does not place orders. Do not append audit lines for beats.

`SupervisorSnapshot.last_heartbeat_at: str | None` (default `None` for old state files).

## 3. Shared pulse helper

`alphastrategy.supervisor.heartbeat`:

| Constant | Value |
| --- | --- |
| `INTERVAL_SEC` | 20 |
| `LIVE_MAX_SEC` | 45 |
| `STALE_MAX_SEC` | 90 |

`describe(at, now=None) -> {at, age_seconds, pulse, interval_seconds}`

`pulse`: `missing` (`at` null) · `live` (age ≤ 45) · `stale` (age ≤ 90) · `dead` (else).

`api.app.HEARTBEAT_INTERVAL_SEC` imports `INTERVAL_SEC` (do not keep a second literal 20).

## 4. Status and CLI

`GET /api/status` includes `heartbeat` from `describe(snapshot.last_heartbeat_at)`.

Offline `alphastrategy status` includes the same object from the on-disk snapshot (age computed at print time).

## 5. Quiet cockpit

Header, left of the brand wordmark: `#desk-pulse` with `#desk-pulse-label` and a `.pulse-dot`.

| pulse | label | token |
| --- | --- | --- |
| live | LIVE | `#10b981` |
| stale | STALE | `#f59e0b` |
| dead | DEAD | `#ef4444` |
| missing | NO BEAT | `#5c6573` |

This is **not** Session OPEN/CLOSED. Help must say so.

Optional 1.6s opacity pulse on `.pulse-dot` when LIVE. `@media (prefers-reduced-motion: reduce)` disables it.

Activity:

- `#activity-heartbeat`: `Beat {LABEL} · {age}s ago · {supervisor state}` (em dash when missing).
- Empty list copy (exact): `Heartbeat is running. No audit events yet. Rebalances fire at open+3m and close−12m.` When pulse is `dead` or `missing`, use: `No audit events yet. Supervisor beat is not live.`

## 6. Help / README

Heartbeat every 20s does not place orders. Header LIVE/STALE/DEAD is the Supervisor beat, not the RTH session. Activity empty copy names the two legal rebalances.

## 7. In / out

**In:** stamp+persist on every tick; `heartbeat` helper; status/CLI; header pulse; Activity beat line + empty copy; help/README; unit/API/CLI/web/e2e tests.

**Out:** WebSockets; audit spam; changing halt/flatten; sixth screen; live money.

## 8. Verification

- After `tick()`, snapshot has `last_heartbeat_at`; disk has it; a second tick while `halted` or `stopped` updates it.
- `describe(None)` → `missing`; 0s → `live`; 46s → `stale`; 91s → `dead`.
- `GET /api/status` includes `heartbeat.pulse` and `interval_seconds` 20.
- Offline CLI `status` includes `heartbeat`.
- HTML: `desk-pulse`, `activity-heartbeat`. Five `#nav` screens.
- JS: `renderDeskPulse`. Empty Activity string as specified. No `window.confirm`.
- GET `/` includes `desk-pulse`.
- `app.py` has no second `= 20` heartbeat literal.
- No real broker orders.
