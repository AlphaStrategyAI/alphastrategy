# alphastrategy durable import-meta and Roster imported at

**Date:** 2026-08-20
**Status:** Requirements (improvement cycle on v1)
**Repo:** `AlphaStrategyAI/alphastrategy`
**Parent contract:** [`2026-08-19-alphastrategy-v1-requirements.md`](2026-08-19-alphastrategy-v1-requirements.md) §4, §8
**Related:** [`2026-08-20-alphastrategy-durable-desk-files-requirements.md`](2026-08-20-alphastrategy-durable-desk-files-requirements.md)
**Technical design:** [`docs/plans/2026-08-20-alphastrategy-durable-import-technical-design.md`](../plans/2026-08-20-alphastrategy-durable-import-technical-design.md)

Paper only. Five screens. Quiet cockpit **tokens unchanged**. No sixth nav tab. No live. No WebSockets. No chart library. Do not revive `static/app.js`. `"Gross cap"` must not appear in assembled JS. `renderBanners` keeps a **single** `const reason`. Do not retry leftover orders.

The durable-desk-files cycle explicitly left `import-meta.json` as `write_text`. Import is how a qualified `.asb` becomes inventory. A crash after `shutil.move` of the unpacked tree can leave a directory that `import` treats as duplicate while `imported_at` never reached disk. Strategies Roster also never shows that stamp, so Inventory looks like a bag of hashes. This cycle writes meta through `persist.replace_text` **inside staging before the move**, fsyncs `imported/`, and paints the date on Roster.

## 1. Why this increment exists

Goal check against current main (`b3e1cf2`):

| Goal slice | v1 / later contract | Current desk |
| --- | --- | --- |
| 可靠 / 架构 | §4.2 store under `imported/<bundle_id>/`. v1 design writes `import-meta.json` `{imported_at, source_path}`. Snapshot / audit / runtime already fsync. | Meta is `Path.write_text` **after** `shutil.move`. Host kill can yield a live imported dir with no meta, then duplicate reject. |
| 凭直觉交互 | §8 Strategies: imported list, state, allocation, risk. Import is not permission to trade. | Roster is Bundle / State / Allocation / Risk. Operator cannot see **when** the file landed. |
| 易于使用 | Import gates name a next action. | Help never says import-meta flushes, or that Roster names imported at. |
| 稳定执行 | Import does not place orders. | Keep that. Only the on-disk stamp and the Roster date change. |
| 风险可控 | Out of flatten math. | Out. |

Research applied:

- **Complete tree, then publish.** Write meta into staging, then rename the directory into `imported/`. Same-filesystem rename is the publish step. Then fsync the parent directory.
- **Recognition, not a fifth tile.** Date as a sub line under the bundle id. Inventory stays four tiles. No sixth screen.

## 2. Durable `import-meta.json`

After conformance in staging, before `shutil.move`:

1. Payload stays `{imported_at, source_path}` (ISO UTC, resolved source path).
2. `replace_text(staging / "import-meta.json", payload, prefix=".meta.")`.
3. `shutil.move` staging → `imported/<bundle_id>/`.
4. `fsync_dir` of `imported/` (the parent of the new bundle dir).

`import_asb` must not call `write_text`. Failed import still rmtree staging and a partial `bundle_dir`.

Old bundles without meta remain importable; `imported_at` is omitted.

## 3. `GET /api/bundles`

Keep `imported` as a sorted list of bundle id strings (JS and CLI already consume that).

Add `imported_at`: map `bundle_id → imported_at` string for ids whose `import-meta.json` parses. Missing or unreadable meta: omit that id.

## 4. Strategies Roster

Still four columns. Bundle cell: id, then a `metric-sub` date (`YYYY-MM-DD` from `imported_at.slice(0, 10)`). Missing: em dash.

Do not `innerHTML=""` Inventory glance mounts. Do not add a fifth column. `"Gross cap"` stays out of JS.

## 5. Help / README

`how_strategies`: Roster names imported at.

`execution` or identity: import-meta flushes to disk with the persist family.

README Operator: import-meta flushes; Roster names imported at.

## 6. In / out

**In:** staging `replace_text` + parent dir fsync; `imported_at` map; Roster date sub; help/README; unit + API + JS tests.

**Out:** changing import gates; retrying orders; live; sixth screen; `app.js`; WebSockets; a fifth Inventory tile; putting `Gross cap` in JS.

## 7. Verification

- `import_asb` body contains `replace_text` and does not contain `write_text`.
- Golden import still has `imported_at` and `source_path`; file exists after import.
- `GET /api/bundles` keeps `imported` as ids and includes `imported_at[id]` matching the file.
- JS Roster reads `imported_at` and `slice(0, 10)`. Five `#nav` screens. `"Gross cap"` not in `js_text`.
- Help contains `Roster names imported at` and `import-meta flushes to disk`.
- No real broker.
