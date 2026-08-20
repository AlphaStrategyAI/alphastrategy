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


def test_save_state_fsyncs_file_and_directory(
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
    files = {"n": 0}
    real = os.fsync

    def boom(fd: int) -> None:
        mode = os.fstat(fd).st_mode
        if stat.S_ISREG(mode):
            files["n"] += 1
            raise OSError("simulated fsync fail")
        real(fd)

    monkeypatch.setattr(os, "fsync", boom)
    with pytest.raises(OSError):
        save_state(path, SupervisorSnapshot(state=SupervisorState.REBALANCING))
    assert files["n"] == 1
    assert load_state(path).state == SupervisorState.HALTED
    assert list(tmp_path.glob(".state.*.tmp")) == []
