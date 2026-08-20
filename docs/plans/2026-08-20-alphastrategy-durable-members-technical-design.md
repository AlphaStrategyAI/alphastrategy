# Durable Imported Members Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans (this cycle chose executing-plans). Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Flush `.asb` members to disk on the imported filesystem, then publish the tree with an atomic directory rename so a host kill cannot leave a duplicate-blocked torn bundle.

**Architecture:** Add `persist.replace_bytes`. Stage under `imported/.staging.*`, write members through persist, keep meta `replace_text`, publish with `os.replace`, `fsync_dir` of `imported/`.

**Tech Stack:** `alphastrategy.persist`, import pipeline, pytest.

**Requirements:** [`docs/requirements/2026-08-20-alphastrategy-durable-members-requirements.md`](../requirements/2026-08-20-alphastrategy-durable-members-requirements.md)

## Global Constraints

- Paper only. Five `#nav` screens. Locked tokens. No `window.confirm`. No live.
- `"Gross cap"` must not appear in assembled JS.
- `renderBanners` keeps a **single** `const reason`.
- Do not retry leftover orders. Import still places no orders.
- Tests: `PYTHONPATH=src python3 -m pytest tests/alphastrategy/ -q`.

## File map

- Modify: `src/alphastrategy/persist.py`, `src/alphastrategy/bundle/import_bundle.py`, `src/alphastrategy/helptext.py`, `README.md`
- Test: `tests/alphastrategy/test_persist.py`, `tests/alphastrategy/test_bundle_import.py`, `tests/alphastrategy/test_helptext.py`

---

### Task 1: Failing tests

- [ ] **Step 1: persist + import + help**

In `tests/alphastrategy/test_persist.py` add:

```python
def test_replace_bytes_source_uses_fsync_and_replace() -> None:
    from alphastrategy import persist

    src = Path(persist.__file__).read_text(encoding="utf-8")
    body = src.split("def replace_bytes", 1)[1]
    assert "os.fsync" in body
    assert "os.replace" in body
    assert "write_bytes" not in body
    assert "wb" in body


def test_replace_bytes_fsyncs_file_and_directory(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    kinds: list[str] = []
    real = os.fsync

    def spy(fd: int) -> None:
        mode = os.fstat(fd).st_mode
        if stat.S_ISDIR(mode):
            kinds.append("dir")
        elif stat.S_ISREG(mode):
            kinds.append("file")
        else:
            kinds.append("other")
        real(fd)

    monkeypatch.setattr(os, "fsync", spy)
    path = tmp_path / "member.bin"
    from alphastrategy import persist

    persist.replace_bytes(path, b"hello\n", prefix=".member.")
    assert kinds == ["file", "dir"]
    assert path.read_bytes() == b"hello\n"


def test_replace_bytes_keeps_previous_if_replace_fails(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    path = tmp_path / "member.bin"
    from alphastrategy import persist

    persist.replace_bytes(path, b"old\n", prefix=".member.")

    def boom(src: str | os.PathLike[str], dst: str | os.PathLike[str]) -> None:
        raise OSError("simulated crash before rename")

    monkeypatch.setattr(os, "replace", boom)
    with pytest.raises(OSError):
        persist.replace_bytes(path, b"new\n", prefix=".member.")
    assert path.read_bytes() == b"old\n"
    assert list(tmp_path.glob(".member.*.tmp")) == []
```

In `tests/alphastrategy/test_bundle_import.py` extend `test_import_asb_writes_meta_through_persist` **or** add:

```python
def test_import_asb_writes_members_through_persist() -> None:
    from alphastrategy.bundle import import_bundle as mod

    src = Path(mod.__file__).read_text(encoding="utf-8")
    body = src.split("def import_asb", 1)[1]
    assert "replace_bytes" in body
    assert "replace_text" in body
    assert "fsync_dir" in body
    assert "os.replace" in body
    assert "write_bytes" not in body
    assert "write_text" not in body
    assert "shutil.move" not in body


def test_import_stages_on_imported_filesystem(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import tempfile

    seen: dict[str, object] = {}
    real = tempfile.mkdtemp

    def spy(*args: object, **kwargs: object) -> str:
        seen["kwargs"] = kwargs
        return real(*args, **kwargs)

    monkeypatch.setattr(tempfile, "mkdtemp", spy)
    dest = tmp_path / "golden.asb"
    dest.write_bytes(build_golden_asb())
    home = _home(tmp_path)
    bundle_id = import_asb(dest, home)
    kwargs = seen["kwargs"]
    assert isinstance(kwargs, dict)
    assert Path(str(kwargs["dir"])) == home.imported_dir()
    assert kwargs["prefix"] == ".staging."
    leftovers = [
        p for p in home.imported_dir().iterdir() if p.name.startswith(".staging.")
    ]
    assert leftovers == []
    assert (home.bundle_dir(bundle_id) / "strategy.dsl.yaml").is_file()
```

`REQUIRED_PHRASES` add `"imported members flush to disk"` and `"staging lives under imported/"`.

Keep `test_import_staging_removed_on_conformance_failure` (empty `imported/` after reject).

- [ ] **Step 2: Run — FAIL.** Commit tests + docs.

Run: `PYTHONPATH=src python3 -m pytest tests/alphastrategy/test_persist.py::test_replace_bytes_source_uses_fsync_and_replace tests/alphastrategy/test_persist.py::test_replace_bytes_fsyncs_file_and_directory tests/alphastrategy/test_persist.py::test_replace_bytes_keeps_previous_if_replace_fails tests/alphastrategy/test_bundle_import.py::test_import_asb_writes_members_through_persist tests/alphastrategy/test_bundle_import.py::test_import_stages_on_imported_filesystem tests/alphastrategy/test_helptext.py::test_help_text_contains_required_phrases -q`

---

### Task 2: Implementation

- [ ] **Step 3: `replace_bytes`**

Append to `src/alphastrategy/persist.py`:

```python
def replace_bytes(path: Path | str, payload: bytes, *, prefix: str = ".tmp.") -> None:
    dest = Path(path)
    dest.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(
        dir=dest.parent,
        prefix=prefix,
        suffix=".tmp",
    )
    tmp_path = Path(tmp_name)
    replaced = False
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp_path, dest)
        replaced = True
        fsync_dir(dest.parent)
    except Exception:
        if not replaced:
            tmp_path.unlink(missing_ok=True)
        raise
```

- [ ] **Step 4: `import_asb`**

```python
from alphastrategy.persist import fsync_dir, replace_bytes, replace_text
```

Add `import os`. After the duplicate check, replace the `tempfile.mkdtemp()` / `write_bytes` / `shutil.move` block with:

```python
    imported = home.imported_dir()
    imported.mkdir(parents=True, exist_ok=True)
    staging_parent = Path(tempfile.mkdtemp(prefix=".staging.", dir=imported))
    staging = staging_parent / bundle_id
    staging.mkdir(parents=True, exist_ok=False)
    try:
        for name, data in sorted(members.items()):
            dest = staging / name
            dest.parent.mkdir(parents=True, exist_ok=True)
            replace_bytes(dest, data, prefix=".member.")
        fsync_dir(staging)

        _run_conformance(staging, members)

        meta = {
            "imported_at": datetime.now(timezone.utc).isoformat(),
            "source_path": str(path.resolve()),
        }
        replace_text(
            staging / "import-meta.json",
            json.dumps(meta, indent=2) + "\n",
            prefix=".meta.",
        )
        os.replace(staging, bundle_dir)
        fsync_dir(imported)
    except Exception:
        shutil.rmtree(staging_parent, ignore_errors=True)
        if bundle_dir.exists():
            shutil.rmtree(bundle_dir, ignore_errors=True)
        raise
    finally:
        if staging_parent.exists():
            shutil.rmtree(staging_parent, ignore_errors=True)
```

Keep `shutil` for `rmtree` only.

- [ ] **Step 5: help + README**

`execution` after import-meta sentence: `Imported members flush to disk. Staging lives under imported/.`

README Operator: same two sentences.

- [ ] **Step 6: Full suite PASS.** Commit.

Run: `PYTHONPATH=src python3 -m pytest tests/alphastrategy/ -q`
