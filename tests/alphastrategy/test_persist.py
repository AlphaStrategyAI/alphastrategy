from __future__ import annotations

import os
import stat
from pathlib import Path

import pytest


def test_replace_text_source_uses_fsync_and_replace() -> None:
    from alphastrategy import persist

    src = Path(persist.__file__).read_text(encoding="utf-8")
    body = src.split("def replace_text", 1)[1].split("def append_text", 1)[0]
    assert "os.fsync" in body
    assert "os.replace" in body
    assert "write_text" not in body


def test_append_text_source_uses_fsync() -> None:
    from alphastrategy import persist

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
    from alphastrategy import persist

    persist.replace_text(path, "a: 1\n", prefix=".runtime.")
    assert kinds == ["file", "dir"]
    assert path.read_text(encoding="utf-8") == "a: 1\n"


def test_replace_text_keeps_previous_if_replace_fails(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    path = tmp_path / "runtime.yaml"
    from alphastrategy import persist

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
    from alphastrategy import persist

    persist.append_text(path, '{"event":"halt"}\n')
    assert kinds == ["file", "dir"]
    assert path.read_text(encoding="utf-8") == '{"event":"halt"}\n'


def test_append_text_keeps_prior_lines_if_fsync_fails(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    path = tmp_path / "audit.jsonl"
    from alphastrategy import persist

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
    text = path.read_text(encoding="utf-8")
    assert text.startswith('{"event":"one"}\n')


def test_save_runtime_source_uses_replace_text() -> None:
    from alphastrategy.api import handlers as handlers_mod

    src = Path(handlers_mod.__file__).read_text(encoding="utf-8")
    body = src.split("def _save_runtime", 1)[1].split("def _apply_startup_runtime", 1)[0]
    assert "replace_text" in body
    assert "write_text" not in body


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


def test_supervisor_init_calls_discard_stale() -> None:
    from alphastrategy.supervisor import loop as loop_mod

    src = Path(loop_mod.__file__).read_text(encoding="utf-8")
    body = src.split("def __init__", 1)[1].split("def state", 1)[0]
    assert "discard_stale" in body
    assert "load_state" in body
    assert body.index("discard_stale") < body.index("load_state")
