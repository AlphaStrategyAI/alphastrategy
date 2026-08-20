from __future__ import annotations

import os
import tempfile
from pathlib import Path


def fsync_dir(directory: Path) -> None:
    dir_fd = os.open(os.fspath(directory), os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(dir_fd)
    finally:
        os.close(dir_fd)


def replace_text(path: Path | str, payload: str, *, prefix: str = ".tmp.") -> None:
    dest = Path(path)
    dest.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(
        dir=dest.parent,
        prefix=prefix,
        suffix=".tmp",
        text=True,
    )
    tmp_path = Path(tmp_name)
    replaced = False
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
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


def append_text(path: Path | str, payload: str) -> None:
    dest = Path(path)
    dest.parent.mkdir(parents=True, exist_ok=True)
    fd = os.open(os.fspath(dest), os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o644)
    try:
        data = memoryview(payload.encode("utf-8"))
        while data:
            written = os.write(fd, data)
            data = data[written:]
        os.fsync(fd)
    finally:
        os.close(fd)
    fsync_dir(dest.parent)


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
