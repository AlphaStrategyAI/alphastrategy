# Durable Desk Files Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans (this cycle chose executing-plans). Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Flush snapshot, audit JSONL, and runtime overlays with one POSIX persist helper so a host kill cannot drop Activity lines or loosen Tightened caps.

**Architecture:** New `alphastrategy.persist` with `replace_text` (temp + fsync + replace + dir fsync) and `append_text` (`O_APPEND` + fsync file + dir). `save_state`, `_save_runtime`, and `audit.append` call it. Redaction stays in `audit.append`.

**Tech Stack:** stdlib `os` / `tempfile`, pytest, `helptext.py`.

**Requirements:** [`docs/requirements/2026-08-20-alphastrategy-durable-desk-files-requirements.md`](../requirements/2026-08-20-alphastrategy-durable-desk-files-requirements.md)

## Global Constraints

- Paper only. Five `#nav` screens. Locked tokens. No live. No WebSockets. No charts. No `app.js`.
- Do not change crash-recovery actions. Snapshot JSON schema unchanged.
- Tests: `PYTHONPATH=src python3 -m pytest tests/alphastrategy/ -q`.

## File map

- Add: `src/alphastrategy/persist.py`, `tests/alphastrategy/test_persist.py`
- Modify: `src/alphastrategy/supervisor/state.py`, `src/alphastrategy/supervisor/audit.py`, `src/alphastrategy/api/handlers.py`, `src/alphastrategy/helptext.py`, `README.md`, `tests/alphastrategy/test_state_persist.py`, `tests/alphastrategy/test_helptext.py`

---

### Task 1: Failing tests

- [ ] **Step 1: persist + wiring tests**

Create `tests/alphastrategy/test_persist.py`:

```python
from __future__ import annotations

import os
import stat
from pathlib import Path

import pytest

from alphastrategy import persist


def test_replace_text_source_uses_fsync_and_replace() -> None:
    src = Path(persist.__file__).read_text(encoding="utf-8")
    body = src.split("def replace_text", 1)[1].split("def append_text", 1)[0]
    assert "os.fsync" in body
    assert "os.replace" in body
    assert "write_text" not in body


def test_append_text_source_uses_fsync() -> None:
    src = Path(persist.__file__).read_text(encoding="utf-8")
    body = src.split("def append_text", 1)[1]
    assert "os.fsync" in body
    assert "O_APPEND" in body
    assert 'open("a"' not in body


def test_replace_text_fsyncs_file_and_directory(
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
    path = tmp_path / "runtime.yaml"
    persist.replace_text(path, "a: 1\n", prefix=".runtime.")
    assert kinds == ["file", "dir"]
    assert path.read_text(encoding="utf-8") == "a: 1\n"


def test_replace_text_keeps_previous_if_replace_fails(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    path = tmp_path / "runtime.yaml"
    persist.replace_text(path, "old\n", prefix=".runtime.")

    def boom(src: str | os.PathLike[str], dst: str | os.PathLike[str]) -> None:
        raise OSError("simulated crash before rename")

    monkeypatch.setattr(os, "replace", boom)
    with pytest.raises(OSError):
        persist.replace_text(path, "new\n", prefix=".runtime.")
    assert path.read_text(encoding="utf-8") == "old\n"
    assert list(tmp_path.glob(".runtime.*.tmp")) == []


def test_append_text_fsyncs_file_and_directory(
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
    path = tmp_path / "audit.jsonl"
    persist.append_text(path, '{"event":"halt"}\n')
    assert kinds == ["file", "dir"]
    assert path.read_text(encoding="utf-8") == '{"event":"halt"}\n'


def test_append_text_keeps_prior_lines_if_fsync_fails(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    path = tmp_path / "audit.jsonl"
    persist.append_text(path, '{"event":"one"}\n')
    real = os.fsync

    def boom(fd: int) -> None:
        mode = os.fstat(fd).st_mode
        if stat.S_ISREG(mode):
            raise OSError("simulated fsync fail")
        real(fd)

    monkeypatch.setattr(os, "fsync", boom)
    with pytest.raises(OSError):
        persist.append_text(path, '{"event":"two"}\n')
    assert path.read_text(encoding="utf-8") == '{"event":"one"}\n'
```

Update `test_save_state_source_uses_fsync_and_replace` to:

```python
    body = src.split("def save_state", 1)[1]
    assert "replace_text" in body
    assert "write_text" not in body
```

Add `tests/alphastrategy/test_audit.py`:

```python
def test_append_source_uses_append_text() -> None:
    from alphastrategy.supervisor import audit as audit_mod

    src = Path(audit_mod.__file__).read_text(encoding="utf-8")
    body = src.split("def append", 1)[1]
    assert "append_text" in body
    assert 'open("a"' not in body
```

Add in `test_api.py` after an existing import-of-handlers test, or a small test in `test_persist.py`:

```python
def test_save_runtime_source_uses_replace_text() -> None:
    from alphastrategy.api import handlers as handlers_mod

    src = Path(handlers_mod.__file__).read_text(encoding="utf-8")
    body = src.split("def _save_runtime", 1)[1].split("def _apply_startup_runtime", 1)[0]
    assert "replace_text" in body
    assert "write_text" not in body
```

`REQUIRED_PHRASES` add `"audit and runtime overlays flush to disk"`.

- [ ] **Step 2: Run — FAIL.** Commit tests + docs.

Run: `PYTHONPATH=src python3 -m pytest tests/alphastrategy/test_persist.py tests/alphastrategy/test_state_persist.py::test_save_state_source_uses_fsync_and_replace tests/alphastrategy/test_audit.py::test_append_source_uses_append_text tests/alphastrategy/test_helptext.py::test_help_text_contains_required_phrases -q`

Expected: FAIL (module / wiring / phrase missing). Include `test_save_runtime_source_uses_replace_text` in that pytest line once it lives in `test_persist.py`.

---

### Task 2: Implementation

- [ ] **Step 3: `persist.py`** — `replace_text` and `append_text` as specified. `append_text` writes the full UTF-8 payload (`os.write` loop until complete), then `os.fsync` the fd, then directory fsync. `replace_text` matches current `save_state` control flow (`replaced` flag, unlink temp on failure before replace).

- [ ] **Step 4: Wire** — `save_state` → `replace_text(..., prefix=".state.")`. `_save_runtime` → `replace_text(..., prefix=".runtime.")`. `audit.append` → `append_text(path, line)` after redact. Drop unused `os`/`tempfile` from `state.py` if they become unused.

- [ ] **Step 5: Help + README** — execution sentence with exact phrase `audit and runtime overlays flush to disk`. README Operator one sentence.

- [ ] **Step 6: Full suite PASS. Commit.**

Run: `PYTHONPATH=src python3 -m pytest tests/alphastrategy/ -q`

Expected: PASS. Existing `test_save_state_fsyncs_file_and_directory` and audit redact tests still pass.

---

## Spec coverage

| Requirement | Task |
| --- | --- |
| persist helper | 1, 3 |
| snapshot / runtime replace | 1, 4 |
| audit append | 1, 4 |
| failed write safety | 1, 3 |
| Help phrase | 1, 5 |
