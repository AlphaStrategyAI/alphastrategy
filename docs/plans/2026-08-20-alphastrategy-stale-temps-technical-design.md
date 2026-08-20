# Stale Temps Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans (this cycle chose executing-plans). Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** On Supervisor start, delete leftover persist temp files and `imported/.staging.*` dirs left by a host kill, without touching published bundles or in-flight imports after boot.

**Architecture:** `persist.discard_stale(root)` is the janitor. `Supervisor.__init__` calls it before `load_state`. Not on tick or `import_asb`.

**Tech Stack:** `alphastrategy.persist`, Supervisor, pytest.

**Requirements:** [`docs/requirements/2026-08-20-alphastrategy-stale-temps-requirements.md`](../requirements/2026-08-20-alphastrategy-stale-temps-requirements.md)

## Global Constraints

- Paper only. Five `#nav` screens. Locked tokens. No `window.confirm`. No live.
- `"Gross cap"` must not appear in assembled JS.
- `renderBanners` keeps a **single** `const reason`.
- Do not retry leftover orders. Do not change halt/flatten/isolate actions.
- Tests: `PYTHONPATH=src python3 -m pytest tests/alphastrategy/ -q`.

## File map

- Modify: `src/alphastrategy/persist.py`, `src/alphastrategy/supervisor/loop.py`, `src/alphastrategy/helptext.py`, `README.md`
- Test: `tests/alphastrategy/test_persist.py`, `tests/alphastrategy/test_halt_flatten.py`, `tests/alphastrategy/test_helptext.py`

---

### Task 1: Failing tests

- [ ] **Step 1: persist + supervisor + help**

In `tests/alphastrategy/test_persist.py` add:

```python
def test_discard_stale_removes_temps_and_staging(tmp_path: Path) -> None:
    from alphastrategy import persist

    root = tmp_path / "home"
    imported = root / "imported"
    staging = imported / ".staging.xyz"
    bundle = imported / "asb_keep"
    staging.mkdir(parents=True)
    bundle.mkdir(parents=True)
    (staging / "junk").write_text("z\n", encoding="utf-8")
    (bundle / "strategy.dsl.yaml").write_text("ok\n", encoding="utf-8")
    (root / ".state.abc.tmp").write_text("old\n", encoding="utf-8")
    (root / ".runtime.abc.tmp").write_text("old\n", encoding="utf-8")
    (root / "supervisor-state.json").write_text("{}\n", encoding="utf-8")
    persist.discard_stale(root)
    assert not (root / ".state.abc.tmp").exists()
    assert not (root / ".runtime.abc.tmp").exists()
    assert not staging.exists()
    assert (root / "supervisor-state.json").read_text(encoding="utf-8") == "{}\n"
    assert (bundle / "strategy.dsl.yaml").is_file()


def test_discard_stale_source_does_not_touch_published_names() -> None:
    from alphastrategy import persist

    src = Path(persist.__file__).read_text(encoding="utf-8")
    body = src.split("def discard_stale", 1)[1]
    assert ".staging." in body
    assert "supervisor-state.json" not in body
    assert "rmtree" in body
```

In `tests/alphastrategy/test_halt_flatten.py` add:

```python
def test_supervisor_init_discards_stale_temps(tmp_path: Path) -> None:
    home_root = tmp_path
    imported = home_root / "imported"
    staging = imported / ".staging.dead"
    staging.mkdir(parents=True)
    (staging / "x").write_text("n\n", encoding="utf-8")
    (home_root / ".state.dead.tmp").write_text("n\n", encoding="utf-8")
    supervisor = _make_supervisor(tmp_path, FakeBroker())
    assert supervisor.snapshot is not None
    assert not staging.exists()
    assert not (home_root / ".state.dead.tmp").exists()
```

And a source check (same file or persist tests):

```python
def test_supervisor_init_calls_discard_stale() -> None:
    from alphastrategy.supervisor import loop as loop_mod

    src = Path(loop_mod.__file__).read_text(encoding="utf-8")
    body = src.split("def __init__", 1)[1].split("def state", 1)[0]
    assert "discard_stale" in body
    assert "load_state" in body
    assert body.index("discard_stale") < body.index("load_state")
```

`REQUIRED_PHRASES` add `"stale persist temps and import staging are removed on start"`.

- [ ] **Step 2: Run — FAIL.** Commit tests + docs.

Run: `PYTHONPATH=src python3 -m pytest tests/alphastrategy/test_persist.py::test_discard_stale_removes_temps_and_staging tests/alphastrategy/test_persist.py::test_discard_stale_source_does_not_touch_published_names tests/alphastrategy/test_halt_flatten.py::test_supervisor_init_discards_stale_temps tests/alphastrategy/test_halt_flatten.py::test_supervisor_init_calls_discard_stale tests/alphastrategy/test_helptext.py::test_help_text_contains_required_phrases -q`

If `test_supervisor_init_calls_discard_stale` cannot live in `test_halt_flatten.py` because Path is not imported, add `from pathlib import Path` there or put the source test in `test_persist.py` with a loop.py read.

---

### Task 2: Implementation

- [ ] **Step 3: `discard_stale`**

In `src/alphastrategy/persist.py` add `import shutil` and:

```python
_STALE_FILE_GLOBS = (
    ".state.*.tmp",
    ".runtime.*.tmp",
    ".meta.*.tmp",
    ".member.*.tmp",
)


def discard_stale(root: Path | str) -> None:
    base = Path(root)
    if not base.is_dir():
        return
    for pattern in _STALE_FILE_GLOBS:
        for path in base.glob(pattern):
            if path.is_file():
                path.unlink(missing_ok=True)
    imported = base / "imported"
    if not imported.is_dir():
        return
    for pattern in _STALE_FILE_GLOBS:
        for path in imported.rglob(pattern):
            if path.is_file():
                path.unlink(missing_ok=True)
    for path in list(imported.iterdir()):
        if path.is_dir() and path.name.startswith(".staging."):
            shutil.rmtree(path, ignore_errors=True)
```

- [ ] **Step 4: Supervisor**

```python
from alphastrategy.persist import discard_stale
```

In `__init__`, before `load_state`:

```python
        discard_stale(home.root)
        self._snapshot = load_state(home.state_path())
```

- [ ] **Step 5: help + README**

`execution` after staging sentence: `Stale persist temps and import staging are removed on start.`

README Operator: same sentence after Staging lives under imported/.

- [ ] **Step 6: Full suite PASS.** Commit.

Run: `PYTHONPATH=src python3 -m pytest tests/alphastrategy/ -q`
