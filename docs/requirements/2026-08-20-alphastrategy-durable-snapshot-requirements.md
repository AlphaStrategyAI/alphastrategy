# alphastrategy durable supervisor snapshot

**Date:** 2026-08-20
**Status:** Requirements (improvement cycle on v1)
**Repo:** `AlphaStrategyAI/alphastrategy`
**Parent contract:** [`2026-08-19-alphastrategy-v1-requirements.md`](2026-08-19-alphastrategy-v1-requirements.md)
**Related:** [`2026-08-20-alphastrategy-rebalancing-crash-requirements.md`](2026-08-20-alphastrategy-rebalancing-crash-requirements.md), [`2026-08-20-alphastrategy-flattening-crash-requirements.md`](2026-08-20-alphastrategy-flattening-crash-requirements.md), [`2026-08-20-alphastrategy-isolate-crash-requirements.md`](2026-08-20-alphastrategy-isolate-crash-requirements.md)
**Technical design:** [`docs/plans/2026-08-20-alphastrategy-durable-snapshot-technical-design.md`](../plans/2026-08-20-alphastrategy-durable-snapshot-technical-design.md)

Paper only. Five screens. Quiet cockpit **tokens unchanged**. No sixth nav tab. No live. No WebSockets. No chart library. Do not revive `static/app.js`. Do not change crash-recovery *actions* (halt torn rebalance, finish flatten, fallback isolate). This cycle makes the persist-before-send those recoveries already rely on actually reach disk.

## 1. Why this increment exists

Goal check against current main (`7433c82`):

| Goal slice | v1 / later contract | Current desk |
| --- | --- | --- |
| 稳定执行 / 可靠 | Persist-before-send: `REBALANCING`, `FLATTENING`, `isolate_in_flight` must be on disk **before** the first broker send so SIGKILL recovers the right path. | `save_state` is `Path.write_text`. That returns when the page cache has the bytes, not when the device does. A host kill or power loss after `_persist()` can still boot as idle and re-fire the same session event, skip flatten retry, or miss a torn isolate. |
| 风险可控 | Daily order cap and isolate fallback depend on those flags surviving the crash. | Duplicate paper buys and a guessed residual are still possible if the kernel never flushed. |
| 易于维护 | One snapshot JSON | Keep one file. Make that write atomic (temp + replace) and durable (fsync file + directory). |
| 易于使用 | Operator runbook already names interrupted rebalancing / flattening / sleeve isolate | It does not say the snapshot is flushed before orders, so the recoveries look like magic. |
| 界面令人眼前一亮 | Desk already names those recoveries | Out of this cycle. No new tiles. |

Research applied (POSIX durable replace, not a full WAL):

- **Same-directory temp file**, `fsync` the payload, `os.replace` onto `supervisor-state.json`, `fsync` the parent directory. Rename is atomic on the same filesystem.
- **Do not clobber the previous snapshot** if the new payload never fsyncs. A failed write must leave the last good file and must not leave a `.state.*.tmp` behind.
- **Do not expand into audit JSONL or runtime YAML** this cycle. Load hooks key off the snapshot. Audit remaining torn is written *during* recovery.

## 2. `save_state` contract

`src/alphastrategy/supervisor/state.py` `save_state`:

1. `mkdir` the parent as today.
2. Write JSON (same `json.dumps(..., separators=(",", ":"), sort_keys=True) + "\n"` payload) to a temp file in that parent (`prefix=".state."`, `suffix=".tmp"`).
3. `flush` + `os.fsync` the temp file descriptor.
4. `os.replace` temp → destination (atomic on POSIX).
5. `os.fsync` the parent directory.
6. On any failure before a successful replace: delete the temp if it still exists. Do not truncate or overwrite the destination in place.

`load_state` stays `read_text` + `from_dict`. Old files remain valid. Payload schema unchanged (`rebalance_placed`, `isolate_in_flight`, `last_kill`, …).

Callers stay `_persist()` / existing `save_state(...)`. No new snapshot fields.

## 3. Help / README

`execution` (or `halt_flatten`): persist-before-send **flushes the snapshot to disk before orders**, so a host kill still sees `REBALANCING`, `FLATTENING`, or `isolate_in_flight`.

README Operator: one sentence, same fact. No cockpit HTML/JS.

## 4. In / out

**In:** atomic durable `save_state`; file + directory fsync; failed write leaves the previous snapshot; temp cleanup; help/README; unit tests. Existing crash-recovery tests keep passing.

**Out:** audit JSONL fsync; runtime overlay YAML fsync; WAL; SQLite; changing halt / flatten / isolate recovery actions; retry remaining orders; live; sixth screen; `app.js`; WebSockets; new glance tiles.

## 5. Verification

- `save_state` source uses `os.fsync` and `os.replace`. The `save_state` function body does not call `write_text`.
- A successful save `fsync`s a regular file and a directory, then `load_state` returns the new snapshot.
- If `os.replace` raises, the previous destination bytes are unchanged and no `.state.*.tmp` remains.
- If the payload `fsync` raises, the previous destination is unchanged.
- Help contains `flushes the snapshot to disk before orders`.
- `PYTHONPATH=src python3 -m pytest tests/alphastrategy/ -q` — no real broker.
