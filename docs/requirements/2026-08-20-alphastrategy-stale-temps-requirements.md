# alphastrategy discard stale persist temps on start

**Date:** 2026-08-20
**Status:** Requirements (improvement cycle on v1)
**Repo:** `AlphaStrategyAI/alphastrategy`
**Parent contract:** [`2026-08-19-alphastrategy-v1-requirements.md`](2026-08-19-alphastrategy-v1-requirements.md) §4.2, §6–7
**Related:** [`2026-08-20-alphastrategy-durable-members-requirements.md`](2026-08-20-alphastrategy-durable-members-requirements.md), [`2026-08-20-alphastrategy-durable-desk-files-requirements.md`](2026-08-20-alphastrategy-durable-desk-files-requirements.md)
**Technical design:** [`docs/plans/2026-08-20-alphastrategy-stale-temps-technical-design.md`](../plans/2026-08-20-alphastrategy-stale-temps-technical-design.md)

Paper only. Five screens. Quiet cockpit **tokens unchanged**. No sixth nav tab. No live. No WebSockets. No chart library. Do not revive `static/app.js`. `"Gross cap"` must not appear in assembled JS. `renderBanners` keeps a **single** `const reason`. Do not retry leftover orders. Do not un-consume `last_rebalance_event`. Do not change halt / flatten / isolate recovery *actions*.

Durable replace/append already fsyncs successful writes. A host kill **during** the dance still leaves siblings: `.state.*.tmp`, `.runtime.*.tmp`, `.meta.*.tmp`, `.member.*.tmp`, and `imported/.staging.*` directories. Listing already skips `.` names, so Inventory does not show them — they still occupy the desk home and can confuse a later crash autopsy. Threaded HTTP can import while the desk is up, so this cycle must **not** delete staging on every import or every tick. Sweep once when the Supervisor process starts.

## 1. Why this increment exists

Goal check against current main (`1bce408`):

| Goal slice | v1 / later contract | Current desk |
| --- | --- | --- |
| 可靠 / 架构 | Persist helpers unlink tmp only in `except`. Staging `finally` rmtree only if the process still runs. | SIGKILL after `os.replace` of the bundle dir, or mid-`replace_text`, leaves temps. No start-time janitor. |
| 稳定执行 | Import publish is same-filesystem rename. Snapshot persist-before-send. | Leftover `.state.*.tmp` next to a good snapshot is harmless to load, noisy on disk. Leftover `.staging.*` can hold a full unpacked tree forever. |
| 易于维护 | One persist module. | Duplicate glob logic in import vs snapshot, or one `discard_stale`. One helper. |
| 易于使用 | Help already: members flush; staging lives under imported/. | Never says start removes stale temps. |
| 凭直觉交互 | Roster skips `.` names. | Out of paint this cycle. |

Research applied:

- **Janitor at process start, not on the hot path.** systemd/postgres-style: remove leftover pid/temp files when the daemon boots, never while a writer may hold them.
- **Do not sweep inside `import_asb`.** `ThreadingHTTPServer` can run two imports. Deleting every `.staging.*` at import start would rmtree the other request.
- **Do not delete published bundles.** Only files matching persist prefixes and directories named `.staging.*` under `imported/`.

## 2. `persist.discard_stale`

```text
discard_stale(root: Path | str) -> None
```

If `root` is not a directory, return.

1. Unlink files in `root` matching `.state.*.tmp`, `.runtime.*.tmp`, `.meta.*.tmp`, `.member.*.tmp`.
2. If `root/imported/` is a directory: unlink those same globs under it (`rglob`); `shutil.rmtree` each child directory whose name starts with `.staging.`.
3. Never unlink `supervisor-state.json`, `runtime.yaml`, `audit.jsonl`, or a published `imported/<bundle_id>/`.
4. Missing files are fine (`unlink(missing_ok=True)`, `rmtree(..., ignore_errors=True)`).

## 3. When it runs

`Supervisor.__init__` calls `discard_stale(home.root)` **before** `load_state`. That covers `alphastrategy start` and any CLI path that constructs a Supervisor while the control plane is down.

Do not call it from `tick`, `import_asb`, or HTTP handlers.

## 4. Help / README

`execution`: stale persist temps and import staging are removed on start.

README Operator: same.

No cockpit JS/HTML this cycle.

## 5. In / out

**In:** `discard_stale`; Supervisor start hook; persist + supervisor tests; help/README.

**Out:** changing import gates; sweeping on every import; changing crash-recovery actions; live; sixth screen; `app.js`; Clock paint.

## 6. Verification

- `discard_stale` removes the four tmp globs at home root, rmtree `imported/.staging.*`, and leaves `supervisor-state.json` and a published bundle dir.
- `Supervisor.__init__` source contains `discard_stale`. Constructing a Supervisor deletes a planted `.staging.*` and `.state.*.tmp`.
- Help contains `stale persist temps and import staging are removed on start`.
- Five `#nav` screens. `"Gross cap"` not in `js_text`. No real broker.
