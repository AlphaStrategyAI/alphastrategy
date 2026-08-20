# Readable Import Gates Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans (this cycle chose executing-plans). Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Name each `.asb` import gate (hash, schema, conformance, …) with a title and next action on API, CLI, and Strategies.

**Architecture:** Pure `alphastrategy.bundle.reject.payload` classifies `ImportRejected` / `BadZipFile`. Handlers and CLI emit that dict. The cockpit paints it. Gates still fail closed.

**Tech Stack:** Python 3.9+, stdlib HTTP, static HTML/CSS/JS, pytest.

**Requirements:** [`docs/requirements/2026-08-20-alphastrategy-import-gates-requirements.md`](../requirements/2026-08-20-alphastrategy-import-gates-requirements.md)

## Global Constraints

- Paper only. Five `#nav` screens. Locked tokens. No `window.confirm`.
- Do not change which bundles import. Do not change `PUT /api/risk` error shape.
- Tests: `PYTHONPATH=src python3 -m pytest tests/alphastrategy/ -q`.

## File map

- Create: `src/alphastrategy/bundle/reject.py`
- Modify: `src/alphastrategy/errors.py`, `bundle/archive.py`, `api/handlers.py`, `cli/main.py`
- Modify: `web/static/index.html`, `styles.css`, `app.js`
- Modify: `helptext.py`, `README.md`
- Test: `tests/alphastrategy/test_bundle_import.py`, `test_api.py`, `test_cli.py`, `test_web_tokens.py`, `test_helptext.py`, `test_e2e_mocked.py`

---

### Task 1: `payload` classifier

**Files:** `src/alphastrategy/errors.py`, `src/alphastrategy/bundle/reject.py`, `src/alphastrategy/bundle/archive.py`, `tests/alphastrategy/test_bundle_import.py`

- [ ] **Step 1: Failing tests** in `test_bundle_import.py`

```python
from alphastrategy.bundle.reject import payload
from alphastrategy.errors import ImportRejected
import zipfile


def test_payload_classifies_hash_lineage_evidence_conformance() -> None:
    cases = [
        ("content hash mismatch: expected a, got b", "hash", "Re-export"),
        ("research_outcome must be FOUND, got 'NO_EVIDENCE'", "lineage", "FOUND"),
        ("evidence/summary.yaml passes_all must be true", "evidence", "passes_all"),
        ("conformance weights mismatch", "conformance", "Frozen bars"),
        ("unsupported version pair: x, y", "schema", "us-equity-daily"),
        ("bundle already imported: asb_x", "duplicate", "already"),
        ("illegal member: evil.py", "archive", "No extra files"),
    ]
    for message, kind, needle in cases:
        body = payload(ImportRejected(message))
        assert body["kind"] == kind
        assert body["error"] == message
        assert body["title"]
        assert needle.lower() in (body["title"] + body["next"]).lower() or needle.lower() in body["next"].lower()


def test_payload_wraps_bad_zip() -> None:
    body = payload(zipfile.BadZipFile("File is not a zip file"))
    assert body["kind"] == "archive"
    assert "error" in body
```

Also extend `test_import_rejects_hash_mismatch` to `assert e.kind == "hash"` **after** `ImportRejected` grows `kind` and `import_asb` tags it — first assert via `payload(e)["kind"] == "hash"` so existing raises work through infer.

- [ ] **Step 2:** Run those tests — FAIL (`No module named 'alphastrategy.bundle.reject'`).

- [ ] **Step 3: Implementation**

`ImportRejected.__init__(self, message: str, kind: str = "unknown")` with `self.kind = kind`.

`reject.py`: `KINDS`, `TITLES`, `NEXT`, `infer_kind(message: str) -> str`, `payload(exc: BaseException) -> dict`. If `getattr(exc, "kind", None)` is a known kind other than `unknown`, use it; else infer.

`read_asb`: `except zipfile.BadZipFile as exc: raise ImportRejected(f"not a zip archive: {exc}", kind="archive") from exc`

Tag `import_bundle.py` raises: hash, bundle_id → `kind="hash"`; already imported → `duplicate`; conformance → `conformance`; dsl_version mismatch → `schema`.

- [ ] **Step 4:** Tests PASS.

---

### Task 2: API 400 and CLI stderr

**Files:** `handlers.py`, `cli/main.py`, `test_api.py`, `test_cli.py`

- [ ] **Step 1: Failing tests**

Extend `test_import_bad_zip_returns_400`:

```python
    assert body["kind"] == "archive"
    assert body["title"]
    assert body["next"]
```

Add `test_import_hash_mismatch_returns_kind` using `mutate_member` + `post_file`.

CLI: `test_cli_import_rejected_prints_kind` imports a hash-mutated asb, `rc == 1`, stderr contains `hash` and `Re-export`.

- [ ] **Step 2:** FAIL (`kind` missing).

- [ ] **Step 3:** `handle_post_import` 400 uses `payload(exc)` JSON (not `_error` string-only). CLI `_cmd_import` prints `error: {kind}: {error}` and `{next}` on stderr.

- [ ] **Step 4:** PASS.

---

### Task 3: Strategies UI

**Files:** `index.html`, `styles.css`, `app.js`, `test_web_tokens.py`, `test_e2e_mocked.py`

- [ ] **Step 1: Failing tests** for ids `import-error-kind`, `import-error-title`, `import-error-detail`, `import-error-next`, `import-ok`; JS `showImportRejection`, `showImportOk`; GET `/` includes `import-error-kind`.

- [ ] **Step 2:** FAIL.

- [ ] **Step 3:** Structured `#import-error` children; `#import-ok` running-green `.ok-box`. `onImportSubmit` calls `showImportRejection(payload)` / `showImportOk(bundle_id)`. Do not `textContent`-wipe the error box via `setError`.

CSS: `.ok-box` border/color `#10b981`, same padding as `.error-box`. `.error-kind` uppercase `#9ba3b4`. `.error-next` `#e5e9f0`.

- [ ] **Step 4:** PASS.

---

### Task 4: Help / README

Add phrases `hash`, `conformance`, `Import is not permission to trade` already exist; add `named` gate copy: “Import failures name the gate (hash, schema, conformance) and a next action.”

`REQUIRED_PHRASES` add `"next action"` or `"conformance"`.

Full suite green.

## Spec coverage

| Requirement | Task |
| --- | --- |
| payload kinds + titles | 1 |
| BadZip wrap | 1 |
| API/CLI | 2 |
| Strategies UI | 3 |
| Help/README | 4 |
| Risk overlay unchanged | no `handle_put_risk` edit |
