from __future__ import annotations

from io import StringIO

from alphastrategy.cli.confirm import (
    ACCOUNT_KILL_PHRASE,
    NON_TTY_ERROR,
    PROMPT,
    WRONG_PHRASE_ERROR,
    confirm_account_kill,
)


def test_force_skips_prompt_and_proceeds() -> None:
    stderr = StringIO()
    stdin = StringIO("FLATTEN\n")
    result = confirm_account_kill(
        force=True, stdin=stdin, stderr=stderr, isatty=lambda: False
    )
    assert result is None
    assert stderr.getvalue() == ""
    assert stdin.read() == "FLATTEN\n"


def test_non_tty_without_force_refuses() -> None:
    stderr = StringIO()
    result = confirm_account_kill(
        force=False,
        stdin=StringIO("FLATTEN\n"),
        stderr=stderr,
        isatty=lambda: False,
    )
    assert result == 1
    assert stderr.getvalue().strip() == NON_TTY_ERROR
    assert "--force" in NON_TTY_ERROR


def test_tty_flatten_proceeds() -> None:
    stderr = StringIO()
    result = confirm_account_kill(
        force=False,
        stdin=StringIO("FLATTEN\n"),
        stderr=stderr,
        isatty=lambda: True,
    )
    assert result is None
    assert PROMPT in stderr.getvalue()


def test_tty_wrong_phrase_refuses() -> None:
    stderr = StringIO()
    result = confirm_account_kill(
        force=False,
        stdin=StringIO("yes\n"),
        stderr=stderr,
        isatty=lambda: True,
    )
    assert result == 1
    assert WRONG_PHRASE_ERROR in stderr.getvalue()


def test_tty_trailing_space_is_not_flatten() -> None:
    stderr = StringIO()
    result = confirm_account_kill(
        force=False,
        stdin=StringIO("FLATTEN \n"),
        stderr=stderr,
        isatty=lambda: True,
    )
    assert result == 1
    assert WRONG_PHRASE_ERROR in stderr.getvalue()


def test_tty_empty_line_refuses() -> None:
    stderr = StringIO()
    result = confirm_account_kill(
        force=False,
        stdin=StringIO("\n"),
        stderr=stderr,
        isatty=lambda: True,
    )
    assert result == 1
    assert WRONG_PHRASE_ERROR in stderr.getvalue()


def test_phrase_constant_matches_web() -> None:
    assert ACCOUNT_KILL_PHRASE == "FLATTEN"
