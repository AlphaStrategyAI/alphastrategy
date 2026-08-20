# alphastrategy durable imported members

**Date:** 2026-08-20
**Status:** Requirements (improvement cycle on v1)
**Repo:** `AlphaStrategyAI/alphastrategy`
**Parent contract:** [`2026-08-19-alphastrategy-v1-requirements.md`](2026-08-19-alphastrategy-v1-requirements.md) §4.2
**Related:** [`2026-08-20-alphastrategy-durable-import-requirements.md`](2026-08-20-alphastrategy-durable-import-requirements.md)
**Technical design:** [`docs/plans/2026-08-20-alphastrategy-durable-members-technical-design.md`](../plans/2026-08-20-alphastrategy-durable-members-technical-design.md)

Paper only. Five screens. Quiet cockpit **tokens unchanged**. No sixth nav tab. No live. No WebSockets. No chart library. Do not revive `static/app.js`. `"Gross cap"` must not appear in assembled JS. `renderBanners` keeps a **single** `const reason`. Do not retry leftover orders. Do not un-consume `last_rebalance_event`. Import still does not place orders.

The durable-import cycle flushed `import-meta.json` through `replace_text` **after** members were `Path.write_bytes` into a `tempfile.mkdtemp()` tree, then `shutil.move` into `imported/<bundle_id>/`. Staging often lives on `/tmp` (tmpfs) while `ALPHASTRATEGY_HOME` lives on the home filesystem. Cross-device `shutil.move` copies, then deletes. A host kill mid-copy can leave a directory that import treats as **duplicate** while members never reached stable storage. That fights 可靠 and 稳定执行. This cycle writes members through persist, stages **under `imported/`**, and publishes with same-filesystem `os.replace`.

## 1. Why this increment exists

Goal check against current main (`901b698`):

| Goal slice | v1 / later contract | Current desk |
| --- | --- | --- |
| 可靠 / 架构 | §4.2 unpack then store under `imported/<bundle_id>/`. Snapshot / audit / runtime / import-meta already fsync. | Members are `write_bytes` with no fsync. Staging is `mkdtemp()` default dir, not `imported/`. |
| 稳定执行 | Import is not permission to trade. A published tree is the input to sandbox rebalance. | Torn published tree + duplicate reject means the operator cannot re-import the same `.asb`. |
| 易于维护 | One persist helper for replace. | Binary members still bypass it. |
| 易于使用 | Import gates name a next action. Duplicate says the bundle is already in `imported/`. | Help never says members flush, or that staging lives under `imported/`. |
| 凭直觉交互 | Roster already names imported at. | Out of this cycle (no new tiles). Header OPEN-while-HALTED is a separate visual increment; a torn import that cannot be retried is the higher-leverage hole after spent-howto copy. |
| 风险可控 | Out of flatten math. | Out. |

Research applied:

- **Stage on the destination filesystem.** POSIX rename of a directory is atomic only on the same filesystem. `tempfile.mkdtemp(dir=imported/)` with a `.staging.` prefix keeps leftovers hidden from `_list_imported_bundles` (names starting with `.` are already skipped).
- **Complete files, then publish.** `replace_bytes` (temp + fsync + `os.replace` + dir fsync) for each member, then existing `replace_text` for meta, then `os.replace` of the staging bundle dir onto `imported/<bundle_id>/`, then `fsync_dir(imported/)`.
- **Do not copy-then-delete.** `import_asb` must not call `shutil.move`.

## 2. `persist.replace_bytes`

Public helper next to `replace_text`:

```text
replace_bytes(path: Path | str, payload: bytes, *, prefix: str = ".tmp.") -> None
```

Same dance as `replace_text`: same-directory temp, write bytes, `fsync` the file, `os.replace`, `fsync` the parent directory. Failed replace leaves the previous destination (or no file). Prefix for members: `.member.`.

## 3. `import_asb` staging

After the duplicate check (`bundle_dir.exists()`):

1. `imported.mkdir(parents=True, exist_ok=True)`.
2. `staging_parent = Path(tempfile.mkdtemp(prefix=".staging.", dir=imported))`.
3. `staging = staging_parent / bundle_id`; mkdir.
4. For each member (sorted path order, as today): `replace_bytes(staging / name, data, prefix=".member.")`.
5. `fsync_dir(staging)`.
6. Conformance against `staging` (unchanged).
7. `replace_text` import-meta (unchanged).
8. `os.replace(staging, bundle_dir)`.
9. `fsync_dir(imported)`.

`import_asb` body must contain `replace_bytes` and `os.replace`. It must not contain `write_bytes` or `shutil.move`. Keep `write_text` out. Failed import still rmtree `staging_parent` and a partial `bundle_dir`. Successful import still rmtree the empty `.staging.*` parent.

`GET /api/bundles` listing already skips `.` names. Do not list staging dirs as inventory.

## 4. Help / README

`execution`: imported members flush to disk; staging lives under imported/.

README Operator: same two facts.

No cockpit HTML/JS this cycle. `"Gross cap"` stays out of JS. One `const reason`.

## 5. In / out

**In:** `replace_bytes`; same-filesystem staging under `imported/`; `os.replace` publish; help/README; persist + import tests.

**Out:** changing import gates or hash rules; retrying orders; live; sixth screen; `app.js`; WebSockets; Roster paint; header Session color vs HALTED.

## 6. Verification

- `replace_bytes` source uses `os.fsync` and `os.replace` and does not call `write_bytes`.
- Successful `replace_bytes` fsyncs a regular file then a directory.
- Failed `replace_bytes` leaves the previous destination.
- `import_asb` body contains `replace_bytes` and `os.replace`; does not contain `write_bytes` or `shutil.move`.
- `tempfile.mkdtemp` is called with `dir=` the imported directory and `prefix=".staging."`.
- Golden import still has members + `import-meta.json`. Conformance failure still leaves `imported/` without published ids or leftover `.staging.*` children.
- Help contains `imported members flush to disk` and `staging lives under imported/`.
- Five `#nav` screens. `"Gross cap"` not in `js_text`. No real broker.
