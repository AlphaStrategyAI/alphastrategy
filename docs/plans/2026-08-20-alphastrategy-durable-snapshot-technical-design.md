# Durable Supervisor Snapshot Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans (this cycle chose executing-plans). Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make `save_state` an atomic, fsynced replace so persist-before-send flags survive a host kill.

**Architecture:** Write JSON to a same-directory temp file, `fsync` the payload, `os.replace` onto `supervisor-state.json`, `fsync` the parent directory. On failure before replace, unlink the temp and leave the previous file. `load_state` and snapshot schema stay.

**Tech Stack:** stdlib `os` / `tempfile` / `json`, pytest, `helptext.py`.

**Requirements:** [`docs/requirements/2026-08-20-alphastrategy-durable-snapshot-requirements.md`](../requirements/2026-08-20-alphastrategy-durable-snapshot-requirements.md)

## Global Constraints

- Paper only. Five `#nav` screens. Locked tokens. No live. No WebSockets. No charts. No `app.js`.
- Do not change crash-recovery actions (interrupted rebalance halt, flatten retry, isolate fallback flatten).
- Tests: `PYTHONPATH=src python3 -m pytest tests/alphastrategy/ -q`.

## File map

- Modify: `src/alphastrategy/supervisor/state.py`, `src/alphastrategy/helptext.py`, `README.md`
- Add: `tests/alphastrategy/test_state_persist.py`
- Test: `tests/alphastrategy/test_helptext.py`

---

### Task 1: Failing tests

- [ ] **Step 1: Persist tests**

Create `tests/alphastrategy/test_state_persist.py`:

```python
from __future__ import annotations

import os
import stat
from pathlib import Path

import pytest

from alphastrategy.supervisor.state import (
    SupervisorSnapshot,
    SupervisorState,
    load_state,
    save_state,
)


def test_save_state_source_uses_fsync_and_replace() -> None:
    from alphastrategy.supervisor import state as state_mod

    src = Path(state_mod.__file__).read_text(encoding="utf-8")
    body = src.split("def save_state", 1)[1]
    assert "os.fsync" in body
    assert "os.replace" in body
    assert "write_text" not in body


def test_save_state_fsyncs_file_and_directory(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
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
    path = tmp_path / "supervisor-state.json"
    save_state(
        path,
        SupervisorSnapshot(state=SupervisorState.REBALANCING, rebalance_placed=2),
    )
    assert kinds == ["file", "dir"]
    loaded = load_state(path)
    assert loaded.state == SupervisorState.REBALANCING
    assert loaded.rebalance_placed == 2


def test_save_state_keeps_previous_file_if_replace_fails(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    path = tmp_path / "supervisor-state.json"
    save_state(path, SupervisorSnapshot(state=SupervisorState.IDLE_IN_SESSION))
    before = path.read_text(encoding="utf-8")

    def boom(src: str | os.PathLike[str], dst: str | os.PathLike[str]) -> None:
        raise OSError("simulated crash before rename")

    monkeypatch.setattr(os, "replace", boom)
    with pytest.raises(OSError):
        save_state(
            path,
            SupervisorSnapshot(
                state=SupervisorState.FLATTENING, isolate_in_flight="asb_x"
            ),
        )
    assert path.read_text(encoding="utf-8") == before
    assert load_state(path).state == SupervisorState.IDLE_IN_SESSION
    assert list(tmp_path.glob(".state.*.tmp")) == []


def test_save_state_keeps_previous_file_if_payload_fsync_fails(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    path = tmp_path / "supervisor-state.json"
    save_state(path, SupervisorSnapshot(state=SupervisorState.HALTED))
    calls = {"n": 0}
    real = os.fsync

    def boom(fd: int) -> None:
        calls["n"] += 1
        mode = os.fstat(fd).st_mode
        if stat.S_ISREG(mode) and calls["n"] > 1:
            raise OSError("simulated fsync fail")
        real(fd)

    monkeypatch.setattr(os, "fsync", boom)
    with pytest.raises(OSError):
        save_state(path, SupervisorSnapshot(state=SupervisorState.REBALANCING))
    assert load_state(path).state == SupervisorState.HALTED
    assert list(tmp_path.glob(".state.*.tmp")) == []
```

Note: first `save_state` in the fsync-fail test already fsyncs once (file+dir). The spy must let that first save succeed, then fail the **next** regular-file fsync. Using `calls["n"] > 1` on `S_ISREG` after the first complete save means: file1, dir1, then file2 fails. `calls["n"]` increments on every fsync including dirs. Safer: count only regular-file fsyncs:

```python
    files = {"n": 0}

    def boom(fd: int) -> None:
        mode = os.fstat(fd).st_mode
        if stat.S_ISREG(mode):
            files["n"] += 1
            if files["n"] > 1:
                raise OSError("simulated fsync fail")
        real(fd)
```

Use that version in the file.

- [ ] **Step 2: Help**

`REQUIRED_PHRASES` add `"flushes the snapshot to disk before orders"`.

- [ ] **Step 3: Run — FAIL.** Commit tests + docs.

Run: `PYTHONPATH=src python3 -m pytest tests/alphastrategy/test_state_persist.py tests/alphastrategy/test_helptext.py::test_help_text_contains_required_phrases -q`

Expected: FAIL (`write_text` still in `save_state`, phrase missing).

---

### Task 2: Implementation

- [ ] **Step 4: `save_state`** — `tempfile.mkstemp` in the parent dir, write + flush + `os.fsync`, `os.replace`, directory `os.fsync` via `os.open(..., os.O_RDONLY | os.O_DIRECTORY)`. `try/except`: `Path.unlink(missing_ok=True)` on the temp if replace has not consumed it. Import `os` and `tempfile`.

- [ ] **Step 5: Help + README** — execution (or halt_flatten) sentence with the exact phrase. README Operator one sentence.

- [ ] **Step 6: Full suite PASS. Commit.**

Run: `PYTHONPATH=src python3 -m pytest tests/alphastrategy/ -q`

Expected: PASS.

---

## Spec coverage

| Requirement | Task |
| --- | --- |
| fsync + replace, no in-place `write_text` | 1, 4 |
| file then directory fsync | 1, 4 |
| failed replace / fsync keeps previous | 1, 4 |
| temp cleanup | 1, 4 |
| Help phrase | 2, 5 |
