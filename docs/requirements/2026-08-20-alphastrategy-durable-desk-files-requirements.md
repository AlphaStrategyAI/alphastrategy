# alphastrategy durable audit and runtime files

**Date:** 2026-08-20
**Status:** Requirements (improvement cycle on v1)
**Repo:** `AlphaStrategyAI/alphastrategy`
**Parent contract:** [`2026-08-19-alphastrategy-v1-requirements.md`](2026-08-19-alphastrategy-v1-requirements.md) §6–7
**Related:** [`2026-08-20-alphastrategy-durable-snapshot-requirements.md`](2026-08-20-alphastrategy-durable-snapshot-requirements.md)
**Technical design:** [`docs/plans/2026-08-20-alphastrategy-durable-desk-files-technical-design.md`](../plans/2026-08-20-alphastrategy-durable-desk-files-technical-design.md)

Paper only. Five screens. Quiet cockpit **tokens unchanged**. No sixth nav tab. No live. No WebSockets. No chart library. Do not revive `static/app.js`. Do not change crash-recovery *actions*. Snapshot persist-before-send stays.

The durable-snapshot cycle left audit JSONL and `runtime.yaml` as `write` / `write_text`. This cycle makes the other two on-disk operator truths reach the device the same way the snapshot already does.

## 1. Why this increment exists

Goal check against current main (`68016bc`):

| Goal slice | v1 / later contract | Current desk |
| --- | --- | --- |
| 稳定执行 / 可靠 | §6 step 7: record targets, fills, deviations in **append-only JSONL**. Activity is that tape. | `audit.append` opens `"a"` and writes. A host kill after `_audit("rebalance", complete=False)` / flatten `reason=limit` can drop the line while the snapshot already has halt / `last_kill`. The desk banners and the tape disagree. |
| 风险可控 | §7: overlays only tighten. PUT `/api/risk` persists `account_overlay` / `sleeve_overlays` in `runtime.yaml`. | `_save_runtime` is `Path.write_text`. A crash after Tighten can reload v1 defaults and **loosen** the next rebalance against a book sized for the tighter cap. |
| 易于维护 | One snapshot JSON already uses temp + fsync + replace | Duplicate that dance in three places, or one `persist` helper. One helper. |
| 易于使用 | Runbook says the snapshot flushes before orders | Does not say audit and runtime overlays flush too, so Activity / Risk look optional. |
| 界面令人眼前一亮 | Out | No new tiles. |

Research applied (POSIX, not a WAL):

- **Replace files** (`supervisor-state.json`, `runtime.yaml`): same-directory temp, `fsync` payload, `os.replace`, `fsync` directory. Failed write leaves the previous file.
- **Append-only JSONL**: `O_APPEND` write of the full line, `fsync` the file, `fsync` the directory. Do not rewrite the whole tape. A failed append must not truncate prior lines.
- **Do not fsync import-meta.json** this cycle (import is not persist-before-send).

## 2. `alphastrategy.persist`

New module, stdlib only:

| Function | Use |
| --- | --- |
| `replace_text(path, payload, *, prefix=".tmp.")` | Atomic durable replace. Prefix distinguishes leftover globs (`.state.`, `.runtime.`). |
| `append_text(path, payload)` | Durable append of `payload` (caller includes the trailing newline). |

`save_state` calls `replace_text(..., prefix=".state.")`. `_save_runtime` calls `replace_text(..., prefix=".runtime.")`. `audit.append` still redacts, then `append_text`.

Payload bytes for snapshot JSON stay `json.dumps(..., separators=(",", ":"), sort_keys=True) + "\n"`. Runtime stays `yaml.safe_dump(runtime, sort_keys=True)`.

## 3. Help / README

`execution`: persist-before-send still flushes the snapshot before orders; **audit and runtime overlays flush to disk** with that snapshot family.

README Operator: one sentence, same fact. No cockpit HTML/JS.

## 4. In / out

**In:** `persist.replace_text` / `append_text`; snapshot + runtime + audit wired through them; failed replace keeps previous; failed append keeps prior JSONL lines; help/README; unit tests.

**Out:** WAL; SQLite; fsync of import-meta; changing halt / flatten / isolate recovery; live; sixth screen; `app.js`; WebSockets; new glance tiles.

## 5. Verification

- `persist.replace_text` source uses `os.fsync` and `os.replace`. `save_state` / `_save_runtime` bodies call `replace_text` and do not call `write_text`.
- `audit.append` source uses `append_text` and does not `open("a"`.
- Successful replace fsyncs a regular file then a directory. Successful append does the same.
- Failed replace leaves the previous destination. Failed append leaves prior lines. No leftover `.state.*.tmp` / `.runtime.*.tmp`.
- Help contains `audit and runtime overlays flush to disk`.
- Existing snapshot persist tests and audit redact tests still pass.
- `PYTHONPATH=src python3 -m pytest tests/alphastrategy/ -q` — no real broker.
