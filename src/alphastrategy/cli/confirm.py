"""Fail-closed confirmation for CLI account kill."""
from __future__ import annotations

import sys
from collections.abc import Callable
from typing import TextIO

ACCOUNT_KILL_PHRASE = "FLATTEN"
NON_TTY_ERROR = "error: account kill requires confirmation; pass --force"
WRONG_PHRASE_ERROR = "error: type FLATTEN to flatten the whole paper account"
PROMPT = "Type FLATTEN to flatten the whole paper account:"


def confirm_account_kill(
    *,
    force: bool,
    stdin: TextIO | None = None,
    stderr: TextIO | None = None,
    isatty: Callable[[], bool] | None = None,
) -> int | None:
    """Return None if account flatten may proceed, else a process exit code."""
    if force:
        return None
    in_stream = sys.stdin if stdin is None else stdin
    err_stream = sys.stderr if stderr is None else stderr
    tty = in_stream.isatty() if isatty is None else isatty()
    if not tty:
        print(NON_TTY_ERROR, file=err_stream)
        return 1
    print(PROMPT, file=err_stream)
    phrase = in_stream.readline()
    if phrase.rstrip("\r\n") != ACCOUNT_KILL_PHRASE:
        print(WRONG_PHRASE_ERROR, file=err_stream)
        return 1
    return None
