# LIMIT names a next send Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans (this cycle chose executing-plans). Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Tag `live_limit.kind` as book vs send so the LIMIT banner and CLI say `next send through` for Order size dry-runs and keep `live book through` for `check_book`.

**Architecture:** `summarize` stamps `kind: "book"`. `_next_send_limit` stamps `kind: "send"`. Cockpit and CLI branch on `kind === "send"` only. Missing kind stays the book sentence.

**Tech Stack:** Python 3.9+, Quiet cockpit HTML/CSS/JS, pytest, helptext, README.

**Requirements:** [`docs/requirements/2026-08-20-alphastrategy-limit-send-requirements.md`](../requirements/2026-08-20-alphastrategy-limit-send-requirements.md)

## Global Constraints

- Paper only. Five `#nav` screens. Locked tokens. No `window.confirm`. No live.
- `"Gross cap"` must not appear in assembled JS. Do not hardcode `Order size` in JS.
- Caps stay four tiles. Keep `#risk-cap-order`.
- Heartbeat does not flatten. GET status/portfolio/risk must not flatten.
- Do not feed `_place_batch` from `live_book()`.
- Keep `LIMIT: live book through Name cap — next rebalance will flatten`.
- Tests: `PYTHONPATH=src python3 -m pytest tests/alphastrategy/ -q`.

## File map

- Modify: `src/alphastrategy/risk/utilization.py`, `src/alphastrategy/web/static/js/paint-rails.js`, `src/alphastrategy/cli/main.py`, `src/alphastrategy/helptext.py`, `README.md`
- Test: `tests/alphastrategy/test_api.py`, `tests/alphastrategy/test_risk.py`, `tests/alphastrategy/test_cli.py`, `tests/alphastrategy/test_web_tokens.py`, `tests/alphastrategy/test_helptext.py`

---

### Task 1: Failing tests

- [ ] **Step 1: Write the failing tests**

`REQUIRED_PHRASES` add:

```python
    "LIMIT names a next send through Order size",
```

In `test_status_live_limit_next_send_order_size` after the reason asserts:

```python
    assert body["utilization"]["live_limit"]["kind"] == "send"
    assert risk["utilization"]["live_limit"]["kind"] == "send"
```

In `test_status_live_limit_does_not_flatten` after the reason asserts:

```python
    assert body["utilization"]["live_limit"]["kind"] == "book"
```

In `test_from_supervisor_live_limit_next_send_order_size`:

```python
    assert out["live_limit"]["kind"] == "send"
```

In `test_summarize_live_limit_from_marked_name`:

```python
    assert out["live_limit"]["kind"] == "book"
```

`test_js_paints_live_limit_banner` add:

```python
    assert "next send through" in js_text
    assert "live book through" in js_text
```

In `tests/alphastrategy/test_cli.py` after `test_status_prints_pnl_on_stderr`:

```python
def test_status_prints_send_limit_on_stderr(
    cli_home: Path, patch_alpaca: mock.MagicMock, capsys, monkeypatch: pytest.MonkeyPatch
) -> None:
    payload = {
        "state": "idle_in_session",
        "clock": {},
        "halted": False,
        "flattened": False,
        "utilization": {
            "live_limit": {"reason": "max_order_notional_frac", "kind": "send"}
        },
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
    assert captured.err.splitlines() == [
        "BOOK: heartbeat",
        "PNL: 100.00 vs last close",
        "LIMIT: next send through Order size — next rebalance will flatten",
    ]
    patch_alpaca.assert_not_called()
```

Keep `test_status_prints_pnl_on_stderr` book sentence.

- [ ] **Step 2: Run the new tests and confirm they fail**

```bash
PYTHONPATH=src python3 -m pytest tests/alphastrategy/test_api.py::test_status_live_limit_next_send_order_size tests/alphastrategy/test_api.py::test_status_live_limit_does_not_flatten tests/alphastrategy/test_risk.py::test_from_supervisor_live_limit_next_send_order_size tests/alphastrategy/test_risk.py::test_summarize_live_limit_from_marked_name tests/alphastrategy/test_web_tokens.py::test_js_paints_live_limit_banner tests/alphastrategy/test_cli.py::test_status_prints_send_limit_on_stderr tests/alphastrategy/test_cli.py::test_status_prints_pnl_on_stderr tests/alphastrategy/test_helptext.py::test_help_text_contains_required_phrases -q
```

- [ ] **Step 3: Commit tests and docs**

---

### Task 2: Implement

- [ ] **Step 4: Stamp `kind` in utilization.py**

`summarize`:

```python
            live_limit = {"reason": str(exc.reason or "limit"), "kind": "book"}
```

`_next_send_limit`:

```python
        return {"reason": str(exc.reason or "limit"), "kind": "send"}
```

- [ ] **Step 5: Banner and CLI**

`paint-rails.js` `renderLiveLimitBanner`:

```javascript
    const through =
      limit.kind === "send" ? "next send through " : "live book through ";
    el.textContent =
      "LIMIT: " + through + policyLabel(limit.reason) + " — next rebalance will flatten";
```

File ≤ 400 newlines. Do not put `Order size` or `Gross cap` in JS. `renderBanners` keeps a single `const reason`.

`cli/main.py`:

```python
_LIMIT_STATUS = (
    "LIMIT: live book through {label} — next rebalance will flatten"
)
_LIMIT_SEND_STATUS = (
    "LIMIT: next send through {label} — next rebalance will flatten"
)
```

`_status_limit_line`: if `limit.get("kind") == "send"` use `_LIMIT_SEND_STATUS`, else `_LIMIT_STATUS`.

- [ ] **Step 6: Help and README**

`helptext.py`: add `LIMIT names a next send through Order size. ` to `halt_flatten`, `how_risk`, `cli` (after status names LIMIT).

README Operator: same sentence after `Caps LIMIT follows a next send through Order size.`

Keep `Next rebalance`. Keep the book LIMIT sentence.

- [ ] **Step 7: Full suite**

```bash
PYTHONPATH=src python3 -m pytest tests/alphastrategy/ -q
```

- [ ] **Step 8: Commit, push, update PR**
