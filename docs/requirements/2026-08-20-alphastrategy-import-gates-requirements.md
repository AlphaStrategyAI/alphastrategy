# alphastrategy readable import gates

**Date:** 2026-08-20
**Status:** Requirements (improvement cycle on v1)
**Repo:** `AlphaStrategyAI/alphastrategy`
**Parent contract:** [`2026-08-19-alphastrategy-v1-requirements.md`](2026-08-19-alphastrategy-v1-requirements.md)
**Technical design:** [`docs/plans/2026-08-20-alphastrategy-import-gates-technical-design.md`](../plans/2026-08-20-alphastrategy-import-gates-technical-design.md)

Paper only. Five screens. Quiet cockpit tokens unchanged. No sixth nav tab. No live. No WebSockets. Import still places no orders.

This cycle makes `.asb` rejection **readable** the way v1 §8 and §13 already require: hash, schema, and conformance failures are named, explained, and given a next action on Web and CLI.

## 1. Why this increment exists

Goal check against current main (`13adc8b`):

| Goal slice | v1 contract | Current desk |
| --- | --- | --- |
| Easy to use | §8 Strategies: “Failures are readable (hash, schema, conformance).” §13 Web tests: import error copy. | `POST /api/import` returns `{error: "<exception>"}`. The Strategies box dumps that string. CLI prints `error: {exc}`. No kind, no title, no next step. |
| Easy to maintain | One fail-closed pipeline for CLI and Web. | Message text is the only contract. A wording change would silently break “readable” without a shared payload. |
| Intuitive interaction | Import is the first human action after alphaloop export. | First-run sends the operator to Strategies. A hash mismatch looks like an internal exception. Success is silent (table appears). |
| Reliable | Tamper, unsupported versions, and conformance must fail closed (already true). | Fail-closed is real; the operator cannot tell *which* gate fired without reading Python phrasing. |

Research applied (not copied as a wizard):

- **Nielsen: error messages** must say what happened, why, and what to do next. Gate name first, detail second.
- **Diátaxis how-to:** import help states the gates, not the zip internals.
- **Fail closed:** classification must not open a path around hash/conformance. Kind is labeling, not a bypass.

Flatten-budget work stays; this cycle does not change risk math.

## 2. Rejection payload

Shared helper `alphastrategy.bundle.reject.payload(exc) -> dict`:

| Key | Meaning |
| --- | --- |
| `error` | Existing exception string (unchanged; tests that match substrings keep working). |
| `kind` | One of: `archive`, `hash`, `schema`, `lineage`, `evidence`, `conformance`, `duplicate`, `unknown`. |
| `title` | Short operator title for that kind. |
| `next` | One-sentence next action. |

`ImportRejected` may carry an optional `kind`. If missing or `unknown`, infer from the message (and from `zipfile.BadZipFile`). Risk overlay `ImportRejected` on `PUT /api/risk` stays `{error}` only — that is not import.

Kind rules (first match):

| kind | Signals |
| --- | --- |
| `archive` | illegal member, not a zip, path traversal, `.py` member, multipart parse failure |
| `hash` | content hash mismatch, bundle_id mismatch |
| `duplicate` | already imported |
| `conformance` | `conformance` in the message (weights, sandbox, missing bars) |
| `lineage` | `research_outcome` / `lineage.yaml` |
| `evidence` | `passes_all` / `evidence/` |
| `schema` | unsupported version pair, market profile, missing members/fields, secret-like keys, DSL version mismatch |
| `unknown` | anything else |

Titles / next (locked copy):

| kind | title | next |
| --- | --- | --- |
| archive | Archive rejected | Use a `.asb` zip from alphaloop export. No extra files, no `.py`. |
| hash | Content hash mismatch | Re-export the candidate from alphaloop. Do not edit the archive. |
| schema | Schema or DSL rejected | Need a supported schema/DSL pair and `us-equity-daily`. |
| lineage | Lineage rejected | Only FOUND candidates can be imported. |
| evidence | Evidence rejected | Evidence must declare `passes_all: true`. |
| conformance | Conformance failed | Frozen bars must reproduce expected weights. Re-export from alphaloop. |
| duplicate | Already imported | This bundle is already in imported/. Use it on Run. |
| unknown | Import rejected | Fix the `.asb` or re-export from alphaloop. |

`read_asb` wraps `zipfile.BadZipFile` as `ImportRejected` with kind `archive`.

## 3. API, CLI, Web

`POST /api/import` 400 body is the payload object (includes `error` so existing clients still work).

CLI `alphastrategy import` on rejection prints two stderr lines:

```text
error: {kind}: {error}
{next}
```

Strategies:

- `#import-error` shows kind, title, detail, next (not a single dumped string).
- `#import-ok` on success: `Imported {bundle_id}. Import is not permission to trade.` Running green token. Clear the error box.

## 4. Help / README

One sentence: import failures are named (`hash`, `schema`, `conformance`, …) with a next action; import is still not permission to trade.

## 5. In / out

**In:** `payload` helper; BadZip wrap; API 400 shape; CLI two-line stderr; Strategies error/success copy; help/README; tests for kinds + API + CLI + static web + e2e GET `/`.

**Out:** changing which bundles import; loosening hash/conformance; a sixth screen; live; rewriting risk overlay errors.

## 6. Verification

- Unit: hash / lineage / evidence / conformance / schema / duplicate / bad zip map to kinds; titles and next are present.
- API: bad zip and hash-mismatch 400 include `kind`, `title`, `next`, `error`.
- CLI: rejected import stderr contains `hash` (or the matching kind) and the next sentence.
- HTML ids `import-error-kind`, `import-error-title`, `import-error-detail`, `import-error-next`, `import-ok`. Five `#nav` screens.
- JS: `showImportRejection`, `showImportOk`. No `window.confirm`.
- GET `/` includes `import-error-kind`.
- No real broker orders.
