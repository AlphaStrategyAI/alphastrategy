# CLI Account-Kill Confirmation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task (this cycle explicitly chose executing-plans). Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make CLI account kill (`paper kill` without `--bundle`) fail-closed: TTY must type `FLATTEN`; non-TTY must pass `--force`; sleeve kill stays unattended.

**Architecture:** Extract a small `confirm_account_kill` helper. Call it at the start of `_cmd_paper_kill` only when `bundle_id` is omitted, before any control-plane POST or offline `kill_account`. Prompts and errors go to stderr so `--force` JSON stays on stdout.

**Tech Stack:** stdlib argparse/sys, existing Supervisor, pytest. Tests mock the broker. Never place a real order.

**Requirements:** [`docs/requirements/2026-08-20-alphastrategy-cli-kill-confirm-requirements.md`](../requirements/2026-08-20-alphastrategy-cli-kill-confirm-requirements.md)

## Global Constraints

- Package `alphastrategy`, paper-only walls unchanged.
- Do not grow `src/openstrategy/`.
- Do not change isolation math in `_isolation_ready` / `residual_book`.
- Five `#nav` screens. No `window.confirm`. Web account kill still requires `FLATTEN`.
- Sleeve CLI kill (`--bundle`) does not prompt and does not require `--force`.
- SIGINT `_shutdown_flatten` does not grow a confirm.
- Tests: `PYTHONPATH=src python3 -m pytest tests/alphastrategy/ -q`. Never place a real order.

## File map

- Create: `src/alphastrategy/cli/confirm.py` — `confirm_account_kill`
- Modify: `src/alphastrategy/cli/main.py` — `--force`, call confirm before kill
- Modify: `src/alphastrategy/helptext.py` — halt_flatten + cli sentences
- Modify: `README.md` — Operator account-kill bullet
- Modify: `docs/explanation/architecture.md` — one halt/flatten sentence
- Test: `tests/alphastrategy/test_cli_kill_confirm.py` (new)
- Test: `tests/alphastrategy/test_cli.py` — `--force` help; account kill `--force` JSON; non-TTY refuse
- Test: `tests/alphastrategy/test_helptext.py` — `--force` phrase

---

### Task 1: confirm_account_kill helper

**Files:**
- Create: `src/alphastrategy/cli/confirm.py`
- Test: `tests/alphastrategy/test_cli_kill_confirm.py`

**Interfaces:**
- Produces: `confirm_account_kill(*, force: bool, stdin=None, stderr=None, isatty=None) -> int | None`
- Produces: constants `NON_TTY_ERROR`, `WRONG_PHRASE_ERROR`, `PROMPT`, `ACCOUNT_KILL_PHRASE`
- Consumes: nothing from Supervisor

- [ ] **Step 1: Write the failing tests**

Create `tests/alphastrategy/test_cli_kill_confirm.py`:

```python
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
    stdin = StringIO("")
    result = confirm_account_kill(
        force=True, stdin=stdin, stderr=stderr, isatty=lambda: False
    )
    assert result is None
    assert stderr.getvalue() == ""
    assert stdin.read() == ""


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
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `PYTHONPATH=src python3 -m pytest tests/alphastrategy/test_cli_kill_confirm.py -q`

Expected: FAIL with `ModuleNotFoundError: No module named 'alphastrategy.cli.confirm'` (or import error for `confirm_account_kill`).

- [ ] **Step 3: Write minimal implementation**

Create `src/alphastrategy/cli/confirm.py`:

```python
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
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `PYTHONPATH=src python3 -m pytest tests/alphastrategy/test_cli_kill_confirm.py -q`

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/alphastrategy/cli/confirm.py tests/alphastrategy/test_cli_kill_confirm.py
git commit -m "feat: fail-closed confirm helper for CLI account kill"
```

---

### Task 2: Wire CLI paper kill; integration tests

**Files:**
- Modify: `src/alphastrategy/cli/main.py`
- Test: `tests/alphastrategy/test_cli.py`

**Interfaces:**
- Consumes: `confirm_account_kill` from Task 1
- Produces: `paper kill --force`; `_cmd_paper_kill(..., force: bool = False)`
- Produces: account kill without `--force` on non-TTY exits 1 and does not flatten

- [ ] **Step 1: Write the failing tests**

Append to `tests/alphastrategy/test_cli.py`:

```python
def test_paper_kill_help_mentions_force(capsys) -> None:
    with pytest.raises(SystemExit) as exc:
        main(["paper", "kill", "--help"])
    assert exc.value.code == 0
    out = capsys.readouterr().out.lower()
    assert "--force" in out
    assert "tty" in out


def test_cli_account_kill_without_force_on_non_tty_does_not_flatten(
    cli_home: Path, patch_alpaca: mock.MagicMock, capsys
) -> None:
    _create_imported_bundle(cli_home)
    assert main(["paper", "start", "--bundle", "asb_test", "--allocation", "0.25"]) == 0
    rc = main(["paper", "kill"])
    err = capsys.readouterr().err
    assert rc == 1
    assert "pass --force" in err
    state = json.loads((cli_home / "supervisor-state.json").read_text(encoding="utf-8"))
    assert state["sleeves"]["asb_test"] == 0.25
    patch_alpaca.assert_not_called()


def test_cli_account_kill_with_force_prints_account_outcome(
    cli_home: Path, patch_alpaca: mock.MagicMock, capsys
) -> None:
    _create_imported_bundle(cli_home)
    assert main(["paper", "start", "--bundle", "asb_test", "--allocation", "0.25"]) == 0
    rc = main(["paper", "kill", "--force"])
    assert rc == 0
    payload = json.loads(capsys.readouterr().out.strip())
    assert payload["reason"] == "account"
    assert payload["flattened"] is True
    assert payload["isolated"] is False
    assert payload["scope"] == "account"


def test_cli_account_kill_tty_flatten_without_force(
    cli_home: Path, patch_alpaca: mock.MagicMock, monkeypatch, capsys
) -> None:
    from io import StringIO

    from alphastrategy.cli import confirm as confirm_mod

    _create_imported_bundle(cli_home)
    assert main(["paper", "start", "--bundle", "asb_test", "--allocation", "0.25"]) == 0

    stdin = StringIO("FLATTEN\n")
    stderr = StringIO()

    def _tty_confirm(*, force: bool, **_kwargs):
        return confirm_mod.confirm_account_kill(
            force=force, stdin=stdin, stderr=stderr, isatty=lambda: True
        )

    monkeypatch.setattr("alphastrategy.cli.main.confirm_account_kill", _tty_confirm)
    rc = main(["paper", "kill"])
    assert rc == 0
    payload = json.loads(capsys.readouterr().out.strip())
    assert payload["reason"] == "account"
    assert "Type FLATTEN" in stderr.getvalue()


def test_cli_account_kill_tty_wrong_phrase_does_not_flatten(
    cli_home: Path, patch_alpaca: mock.MagicMock, monkeypatch, capsys
) -> None:
    from io import StringIO

    from alphastrategy.cli import confirm as confirm_mod

    _create_imported_bundle(cli_home)
    assert main(["paper", "start", "--bundle", "asb_test", "--allocation", "0.25"]) == 0

    stdin = StringIO("yes\n")
    stderr = StringIO()

    def _tty_confirm(*, force: bool, **_kwargs):
        return confirm_mod.confirm_account_kill(
            force=force, stdin=stdin, stderr=stderr, isatty=lambda: True
        )

    monkeypatch.setattr("alphastrategy.cli.main.confirm_account_kill", _tty_confirm)
    rc = main(["paper", "kill"])
    assert rc == 1
    state = json.loads((cli_home / "supervisor-state.json").read_text(encoding="utf-8"))
    assert state["sleeves"]["asb_test"] == 0.25
    patch_alpaca.assert_not_called()


def test_cli_account_kill_control_plane_without_force_does_not_post(
    cli_home: Path, patch_alpaca: mock.MagicMock
) -> None:
    _create_imported_bundle(cli_home, "asb_test")
    home = AlphaStrategyHome.from_env()
    broker = FakeBroker()
    supervisor = Supervisor(
        home=home,
        broker=broker,
        policy=AccountPolicy.defaults(),
        evaluators={"asb_test": {"AAPL": 1.0}},
    )
    supervisor.start_sleeve("asb_test", 0.25)
    server = make_server(home, supervisor, bind="127.0.0.1", port=0)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        rc = main(["paper", "kill", "--port", str(server.server_port)])
    finally:
        server.shutdown()
        thread.join(timeout=2)
    assert rc == 1
    assert supervisor.snapshot.sleeves["asb_test"] == 0.25
    assert supervisor.snapshot.last_kill is None


def test_cli_account_kill_control_plane_with_force_flattens(
    cli_home: Path, patch_alpaca: mock.MagicMock, capsys
) -> None:
    _create_imported_bundle(cli_home, "asb_test")
    home = AlphaStrategyHome.from_env()
    broker = FakeBroker()
    supervisor = Supervisor(
        home=home,
        broker=broker,
        policy=AccountPolicy.defaults(),
        evaluators={"asb_test": {"AAPL": 1.0}},
    )
    supervisor.start_sleeve("asb_test", 0.25)
    server = make_server(home, supervisor, bind="127.0.0.1", port=0)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        rc = main(
            ["paper", "kill", "--force", "--port", str(server.server_port)]
        )
    finally:
        server.shutdown()
        thread.join(timeout=2)
    assert rc == 0
    payload = json.loads(capsys.readouterr().out.strip())
    assert payload["reason"] == "account"
    assert supervisor.snapshot.last_kill["reason"] == "account"
```

Keep `test_paper_kill_prints_outcome_json` unchanged (sleeve kill, no `--force`). The TTY-through-CLI tests monkeypatch `alphastrategy.cli.main.confirm_account_kill` so pytest's non-TTY stdin still exercises the real helper with `isatty=lambda: True`.

- [ ] **Step 2: Run the new tests to verify they fail**

Run: `PYTHONPATH=src python3 -m pytest tests/alphastrategy/test_cli.py::test_paper_kill_help_mentions_force tests/alphastrategy/test_cli.py::test_cli_account_kill_without_force_on_non_tty_does_not_flatten tests/alphastrategy/test_cli.py::test_cli_account_kill_with_force_prints_account_outcome tests/alphastrategy/test_cli.py::test_cli_account_kill_tty_flatten_without_force tests/alphastrategy/test_cli.py::test_cli_account_kill_tty_wrong_phrase_does_not_flatten tests/alphastrategy/test_cli.py::test_cli_account_kill_control_plane_without_force_does_not_post tests/alphastrategy/test_cli.py::test_cli_account_kill_control_plane_with_force_flattens -q`

Expected: FAIL — argparse unknown `--force` and/or account kill still flattens on non-TTY (rc 0 instead of 1).

- [ ] **Step 3: Write minimal implementation**

In `src/alphastrategy/cli/main.py`:

Add import:

```python
from alphastrategy.cli.confirm import confirm_account_kill
```

Change `_cmd_paper_kill` to take `force` and confirm **before** `_control_request`:

```python
def _cmd_paper_kill(
    home: AlphaStrategyHome,
    broker: Any | None,
    bundle_id: str | None,
    port: int = DEFAULT_PORT,
    force: bool = False,
) -> int:
    if not bundle_id:
        refused = confirm_account_kill(force=force)
        if refused is not None:
            return refused
    response = _control_request(
        "POST",
        "/api/paper/kill",
        port,
        {"bundle_id": bundle_id} if bundle_id else {},
    )
    if response is not None:
        return _control_json(response)
    if broker is None:
        broker = _make_paper_broker()
    supervisor = _make_supervisor(home, broker)
    if bundle_id:
        outcome = supervisor.kill_sleeve(bundle_id)
    else:
        outcome = supervisor.kill_account()
    print(json.dumps(outcome.to_dict(), separators=(",", ":")))
    return 0
```

In `create_parser`, after the existing `--bundle` / `--port` on `paper_kill`:

```python
    paper_kill.add_argument(
        "--force",
        action="store_true",
        help="skip account-kill confirmation (required when stdin is not a TTY)",
    )
```

In `main`, pass the flag:

```python
        if args.paper_command == "kill":
            return _cmd_paper_kill(
                home, None, args.bundle, args.port, args.force
            )
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `PYTHONPATH=src python3 -m pytest tests/alphastrategy/test_cli.py tests/alphastrategy/test_cli_kill_confirm.py -q`

Expected: PASS. Existing `test_paper_kill_prints_outcome_json` still passes without `--force`.

- [ ] **Step 5: Commit**

```bash
git add src/alphastrategy/cli/main.py tests/alphastrategy/test_cli.py
git commit -m "feat: require FLATTEN or --force for CLI account kill"
```

---

### Task 3: Help, README, architecture

**Files:**
- Modify: `src/alphastrategy/helptext.py`
- Modify: `README.md`
- Modify: `docs/explanation/architecture.md`
- Test: `tests/alphastrategy/test_helptext.py`
- Test: `tests/alphastrategy/test_cli.py` (`test_help_command_prints_operator_copy` already asserts `FLATTEN`)

**Interfaces:**
- Consumes: locked error/prompt copy from Task 1
- Produces: help/README/architecture mention TTY `FLATTEN` and `--force`

- [ ] **Step 1: Write the failing test**

In `tests/alphastrategy/test_helptext.py`, add `"--force"` to `REQUIRED_PHRASES` and handle it like other lowercase phrases (it is case-sensitive as a flag; assert `"--force"` in `text`).

```python
REQUIRED_PHRASES = (
    "halt is not flatten",
    "paper only",
    "sole order placer",
    "does not catch up",
    "FLATTEN",
    "--force",
    "Wanted",
    "Got",
)


def test_help_text_contains_required_phrases() -> None:
    text = help_text()
    lower = text.lower()
    assert "halt is not flatten" in lower
    for phrase in REQUIRED_PHRASES:
        if phrase == "FLATTEN":
            assert "FLATTEN" in text
        elif phrase == "--force":
            assert "--force" in text
        elif phrase in ("Wanted", "Got"):
            assert phrase in text
        else:
            assert phrase.lower() in lower
```

Also extend `test_help_command_prints_operator_copy` in `test_cli.py`:

```python
    assert "--force" in out
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `PYTHONPATH=src python3 -m pytest tests/alphastrategy/test_helptext.py::test_help_text_contains_required_phrases tests/alphastrategy/test_cli.py::test_help_command_prints_operator_copy -q`

Expected: FAIL — `--force` not in helptext.

- [ ] **Step 3: Write minimal copy**

In `helptext.py` `halt_flatten` body, replace the account-kill sentence with:

```text
Account kill on the Web requires typing FLATTEN. CLI account kill requires typing FLATTEN on a TTY, or --force when stdin is not a TTY.
```

In the `cli` body, after “paper kill without --bundle flattens the whole paper account.”, add:

```text
 That CLI account kill prompts for FLATTEN on a TTY and refuses on a non-TTY unless --force is passed.
```

In `README.md` Operator account-kill bullet, replace the CLI sentence with:

```markdown
- **Account kill** flattens the whole paper account. On the Web, type
  `FLATTEN` and confirm. CLI: `alphastrategy paper kill` (omit
  `--bundle`) types `FLATTEN` on a TTY, or pass `--force` when stdin
  is not a TTY.
```

In `docs/explanation/architecture.md`, after “Manual account kill, SIGINT/SIGTERM, and limit breaches **flatten** when the broker is reachable.”, add:

```text
CLI account kill (no `--bundle`) is fail-closed: type `FLATTEN` on a TTY, or pass `--force` when stdin is not a TTY. SIGINT flatten does not prompt.
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `PYTHONPATH=src python3 -m pytest tests/alphastrategy/test_helptext.py tests/alphastrategy/test_cli.py tests/alphastrategy/test_cli_kill_confirm.py -q`

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/alphastrategy/helptext.py README.md docs/explanation/architecture.md tests/alphastrategy/test_helptext.py tests/alphastrategy/test_cli.py
git commit -m "docs: CLI account kill needs FLATTEN or --force"
```

---

### Task 4: Full suite

**Files:** none beyond verification

- [ ] **Step 1: Run the product suite**

Run: `PYTHONPATH=src python3 -m pytest tests/alphastrategy/ -q`

Expected: all pass. No real broker.

- [ ] **Step 2: Commit only if anything was fixed**

If the suite is already green, do not add an empty commit.

---

## Self-review

| Spec item | Task |
| --- | --- |
| `--force` skips prompt | 1, 2 |
| Non-TTY without `--force` exits 1, stderr `--force`, no flatten | 1, 2 |
| Piped `FLATTEN` on non-TTY is still refuse (helper ignores stdin when not TTY) | 1 |
| TTY + exact `FLATTEN` proceeds | 1, 2 |
| TTY + `yes` / empty / trailing space refuses | 1, 2 |
| Sleeve `--bundle` unchanged without `--force` | 2 (existing test) |
| Confirm before HTTP POST | 2 control-plane tests |
| SIGINT unchanged | 2 does not touch `_shutdown_flatten`; existing test remains |
| Help/README/architecture | 3 |
| No `--yes`, no sleeve CLI confirm, no isolation math change | Out of file map |

No TBD placeholders. `--force` argparse dest is `force`. Helper return `None` vs `1` is the only gate code.
