# Status Day PnL Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans (this cycle chose executing-plans). Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** GET `/api/status` and CLI `status` report the same Book Day PnL (equity minus last close), including a PNL stderr line.

**Architecture:** Reuse `_account_day_pnl` on the warm `live_book()` account after utilization. Offline status emits JSON null and does not fetch. `_print_status` prints BOOK, then PNL, then LIMIT on stderr.

**Tech Stack:** Python 3.9+, CLI, pytest, helptext, README. No JS paint change.

**Requirements:** [`docs/requirements/2026-08-20-alphastrategy-status-pnl-requirements.md`](../requirements/2026-08-20-alphastrategy-status-pnl-requirements.md)

## Global Constraints

- Paper only. Five `#nav` screens. Locked tokens. No live.
- `"Gross cap"` must not appear in assembled JS.
- Heartbeat does not flatten. GET status/portfolio/risk must not flatten.
- Do not feed `plan_orders` from `live_book()`.
- CLI stdout is one JSON object. BOOK, PNL, and LIMIT go to stderr.
- Offline status keeps `from_supervisor(..., live=False)` and does not call `live_book()`.
- Tests: `PYTHONPATH=src python3 -m pytest tests/alphastrategy/ -q`.

## File map

- Modify: `src/alphastrategy/api/handlers.py`, `src/alphastrategy/cli/main.py`, `src/alphastrategy/helptext.py`, `README.md`
- Test: `tests/alphastrategy/test_api.py`, `tests/alphastrategy/test_cli.py`, `tests/alphastrategy/test_helptext.py`

---

### Task 1: Failing tests

- [ ] **Step 1: Write the failing tests**

`REQUIRED_PHRASES` add:

```python
    "status names Day PnL",
```

In `tests/alphastrategy/test_api.py` after `test_status_returns_state_clock_and_halt`:

```python
def test_status_day_pnl_null_without_last_equity(api_stack):
    client, _home, supervisor, broker = api_stack
    close_all_before = broker.close_all_count
    body = client.get("/api/status").json()
    assert body["pnl"] is None
    assert body["pnl_source"] is None
    assert broker.close_all_count == close_all_before
    assert supervisor.state.value != "stopped"


def test_status_day_pnl_from_last_equity(api_stack):
    client, _home, _supervisor, broker = api_stack
    orig = broker.get_account

    def with_last():
        account = orig()
        account["last_equity"] = "9900"
        return account

    broker.get_account = with_last  # type: ignore[method-assign]
    close_all_before = broker.close_all_count
    body = client.get("/api/status").json()
    assert body["pnl"] == 100.0
    assert body["pnl_source"] == "last_close"
    assert broker.close_all_count == close_all_before
```

In `tests/alphastrategy/test_cli.py` after `test_status_prints_book_on_stderr`:

```python
def test_status_prints_pnl_on_stderr(
    cli_home: Path, patch_alpaca: mock.MagicMock, capsys, monkeypatch: pytest.MonkeyPatch
) -> None:
    payload = {
        "state": "idle_in_session",
        "clock": {},
        "halted": False,
        "flattened": False,
        "utilization": {"live_limit": {"reason": "max_name_weight"}},
        "heartbeat": {"age_seconds": 4, "pulse": "live", "interval_seconds": 20},
        "book": {"source": "heartbeat"},
        "pnl": 100.0,
        "pnl_source": "last_close",
    }
    monkeypatch.setattr(
        "alphastrategy.cli.main._control_request",
        lambda *args, **kwargs: (200, payload),
    )
    rc = main(["status"])
    assert rc == 0
    captured = capsys.readouterr()
    out = json.loads(captured.out.strip())
    assert out["pnl"] == 100.0
    assert captured.err.splitlines() == [
        "BOOK: heartbeat",
        "PNL: 100.00 vs last close",
        "LIMIT: live book through Name cap — next rebalance will flatten",
    ]
    patch_alpaca.assert_not_called()


def test_status_omits_pnl_when_null(
    cli_home: Path, patch_alpaca: mock.MagicMock, capsys, monkeypatch: pytest.MonkeyPatch
) -> None:
    payload = {
        "state": "idle_in_session",
        "clock": {},
        "halted": False,
        "flattened": False,
        "utilization": {},
        "book": {"source": "glance"},
        "pnl": None,
        "pnl_source": None,
    }
    monkeypatch.setattr(
        "alphastrategy.cli.main._control_request",
        lambda *args, **kwargs: (200, payload),
    )
    rc = main(["status"])
    assert rc == 0
    captured = capsys.readouterr()
    assert captured.err.splitlines() == ["BOOK: glance"]
    patch_alpaca.assert_not_called()
```

Extend `test_offline_status_includes_last_kill_after_account_kill` with:

```python
    assert payload["pnl"] is None
    assert payload["pnl_source"] is None
    assert "PNL:" not in capsys.readouterr().err
```

Wait: that test already consumed stderr via `capsys.readouterr()` for stdout. After `json.loads(captured.out.strip())`, assert `"PNL:" not in captured.err` on that same capture. Do not call `readouterr()` twice.

- [ ] **Step 2: Run the new tests and confirm they fail**

```bash
PYTHONPATH=src python3 -m pytest tests/alphastrategy/test_api.py::test_status_day_pnl_null_without_last_equity tests/alphastrategy/test_api.py::test_status_day_pnl_from_last_equity tests/alphastrategy/test_cli.py::test_status_prints_pnl_on_stderr tests/alphastrategy/test_cli.py::test_status_omits_pnl_when_null tests/alphastrategy/test_cli.py::test_offline_status_includes_last_kill_after_account_kill tests/alphastrategy/test_helptext.py::test_help_text_contains_required_phrases -q
```

Expect failures on missing status `pnl`, PNL stderr, and the help phrase. If `test_status_prints_book_on_stderr` still passes, keep it.

- [ ] **Step 3: Commit tests and docs**

---

### Task 2: Implement

- [ ] **Step 4: GET `/api/status`**

In `handle_get_status`, after building utilization via `from_supervisor(supervisor, live=True)`, derive PnL from the warm live book:

```python
    utilization = from_supervisor(supervisor, live=True)
    try:
        account, _positions = supervisor.live_book()
        pnl, pnl_source = _account_day_pnl(account)
    except Exception:
        pnl, pnl_source = None, None
```

Add `"pnl"` and `"pnl_source"` to the JSON next to `"book"`. Do not flatten.

- [ ] **Step 5: CLI**

`_status_pnl_line(payload)`: missing/null/non-finite `pnl` → `None`. Else `PNL: {value:.2f}` and append ` vs last close` when `pnl_source == "last_close"`.

`_print_status`: print BOOK, then PNL, then LIMIT.

Offline `_cmd_status` payload: `"pnl": None`, `"pnl_source": None`. Do not call `live_book()`.

- [ ] **Step 6: Help and README**

`helptext.py` `cli` body: `status names Day PnL. ` after `status names BOOK heartbeat or glance.`

README Operator: `status names Day PnL.` next to BOOK. Keep `Day PnL is equity minus last close`. Keep `Next rebalance`.

- [ ] **Step 7: Run the new tests green, then the full suite**

```bash
PYTHONPATH=src python3 -m pytest tests/alphastrategy/ -q
```

- [ ] **Step 8: Commit, push, update PR**
