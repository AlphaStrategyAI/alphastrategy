# Durable Import Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans (this cycle chose executing-plans). Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Flush `import-meta.json` through persist before the imported tree is published, and paint the imported date on Strategies Roster.

**Architecture:** Write meta into staging with `replace_text`, move the directory, `fsync_dir` of `imported/`. `GET /api/bundles` adds `imported_at` without changing `imported` id lists. Roster shows `YYYY-MM-DD` under the bundle id.

**Tech Stack:** `alphastrategy.persist`, import pipeline, Quiet cockpit JS, pytest.

**Requirements:** [`docs/requirements/2026-08-20-alphastrategy-durable-import-requirements.md`](../requirements/2026-08-20-alphastrategy-durable-import-requirements.md)

## Global Constraints

- Paper only. Five `#nav` screens. Locked tokens. No `window.confirm`. No live.
- `"Gross cap"` must not appear in assembled JS.
- `renderBanners` keeps a **single** `const reason`.
- Keep `imported` as a list of id strings.
- Tests: `PYTHONPATH=src python3 -m pytest tests/alphastrategy/ -q`.

## File map

- Modify: `src/alphastrategy/persist.py`, `src/alphastrategy/bundle/import_bundle.py`, `src/alphastrategy/api/handlers.py`, `src/alphastrategy/web/static/js/paint-strategies.js`, `src/alphastrategy/helptext.py`, `README.md`
- Test: `tests/alphastrategy/test_bundle_import.py`, `tests/alphastrategy/test_golden_import.py`, `tests/alphastrategy/test_api.py`, `tests/alphastrategy/test_web_tokens.py`, `tests/alphastrategy/test_helptext.py`

---

### Task 1: Failing tests

- [ ] **Step 1: Import persist + API + JS + help**

In `tests/alphastrategy/test_bundle_import.py`:

```python
def test_import_asb_writes_meta_through_persist() -> None:
    from alphastrategy.bundle import import_bundle as mod

    src = Path(mod.__file__).read_text(encoding="utf-8")
    body = src.split("def import_asb", 1)[1]
    assert "replace_text" in body
    assert "fsync_dir" in body
    assert "write_text" not in body
```

In `tests/alphastrategy/test_golden_import.py` `test_import_golden_asb_records_imported_state`, keep existing meta asserts.

In `tests/alphastrategy/test_api.py` `test_import_golden_asb_via_api` (or the test that already checks `"asb_test" in body["imported"]`), after the imported assert add:

```python
    assert "imported_at" in body
    assert body["imported"][0] in body["imported_at"]
    assert "T" in body["imported_at"][body["imported"][0]]
```

If that test's bundle id is `asb_test` from a fixture dir without meta, pick the golden import API test instead. Prefer adding to `test_import_asb_via_http` if present; otherwise add:

```python
def test_bundles_include_imported_at(api_stack, tmp_path):
    # only if an existing import-via-API test does not already create import-meta
```

Use the existing golden import if the API test imports a real `.asb`. Read `test_api.py` for `import` POST tests and attach `imported_at` there.

In `test_js_paints_strategy_inventory` add:

```python
    assert "imported_at" in paint
    assert "slice(0, 10)" in paint
    assert "Gross cap" not in js_text
```

`REQUIRED_PHRASES` add `"Roster names imported at"` and `"import-meta flushes to disk"`.

- [ ] **Step 2: Run — FAIL.** Commit tests + docs.

Run: `PYTHONPATH=src python3 -m pytest tests/alphastrategy/test_bundle_import.py::test_import_asb_writes_meta_through_persist tests/alphastrategy/test_web_tokens.py::test_js_paints_strategy_inventory tests/alphastrategy/test_helptext.py::test_help_text_contains_required_phrases -q`

---

### Task 2: Implementation

- [ ] **Step 3: `persist.fsync_dir`**

Rename/export `_fsync_dir` as `fsync_dir` (keep `_fsync_dir = fsync_dir` if callers inside the module use the old name). Public signature: `fsync_dir(directory: Path) -> None`.

- [ ] **Step 4: `import_asb`**

```python
from alphastrategy.persist import fsync_dir, replace_text
```

After `_run_conformance`, before `shutil.move`:

```python
        meta = {
            "imported_at": datetime.now(timezone.utc).isoformat(),
            "source_path": str(path.resolve()),
        }
        replace_text(
            staging / "import-meta.json",
            json.dumps(meta, indent=2) + "\n",
            prefix=".meta.",
        )
        bundle_dir.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(staging), str(bundle_dir))
        fsync_dir(bundle_dir.parent)
```

Delete the post-move `write_text`. Keep the existing except/finally rmtree.

- [ ] **Step 5: API**

In `handlers.py`:

```python
def _imported_at_map(home: AlphaStrategyHome) -> dict[str, str]:
    out: dict[str, str] = {}
    for bundle_id in _list_imported_bundles(home):
        meta_path = home.bundle_dir(bundle_id) / "import-meta.json"
        if not meta_path.is_file():
            continue
        try:
            doc = json.loads(meta_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if isinstance(doc, dict) and doc.get("imported_at"):
            out[bundle_id] = str(doc["imported_at"])
    return out
```

`handle_get_bundles` add `"imported_at": _imported_at_map(home)`.

- [ ] **Step 6: Roster JS**

In `renderStrategies` bundle cell, replace the bare id `<td>` with id plus date sub from `bundles.imported_at[id]`. Date = `String(raw).slice(0, 10)` when raw is present, else em dash. Keep four columns.

- [ ] **Step 7: help + README**

`how_strategies`: Roster names imported at.

`execution` after persist family: import-meta flushes to disk with that snapshot family.

README Operator: import-meta flushes to disk; Roster names imported at.

- [ ] **Step 8: Full suite PASS.** Commit.

Run: `PYTHONPATH=src python3 -m pytest tests/alphastrategy/ -q`

---
