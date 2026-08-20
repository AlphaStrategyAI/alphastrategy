# Sleeve-Isolate Crash Recovery Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans (this cycle chose executing-plans). Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** If the host dies during an isolated sleeve kill, flatten the whole paper account on the next Supervisor load rather than guess the residual.

**Architecture:** `SupervisorSnapshot.isolate_in_flight`. Persist it at the start of `_isolate_sleeve`. Clear it on isolate success and in `_flatten_account`. `__init__` / `reload_from_disk` call `_recover_interrupted_isolate` after rebalance/flatten recovery.

**Tech Stack:** Python supervisor, Quiet cockpit help copy, pytest with FakeBroker.

**Requirements:** [`docs/requirements/2026-08-20-alphastrategy-isolate-crash-requirements.md`](../requirements/2026-08-20-alphastrategy-isolate-crash-requirements.md)

## Global Constraints

- Paper only. Five `#nav` screens. Locked tokens. No `window.confirm`. No live. No WebSockets. No charts.
- Resume does not catch up. Do not retry remaining isolate orders. Do not halt-and-hold a torn isolate.
- Do not flatten a `REBALANCING` snapshot (that path still health-halts).
- JS must not contain `Gross cap`. Do not label a tile Live.
- Tests: `PYTHONPATH=src python3 -m pytest tests/alphastrategy/ -q`. Never hit a real broker.

## File map

- Modify: `src/alphastrategy/supervisor/state.py`, `src/alphastrategy/supervisor/loop.py`, `src/alphastrategy/helptext.py`
- Test: `tests/alphastrategy/test_halt_flatten.py`, `tests/alphastrategy/test_helptext.py`

---

### Task 1: Failing tests

- [ ] **Step 1: Supervisor + help tests**

Add to `tests/alphastrategy/test_halt_flatten.py` after `test_kill_sleeve_isolates_when_last_book_exists`:

```python
def test_restart_during_sleeve_isolate_flattens_account(tmp_path: Path):
    open_time = datetime(2024, 1, 31, 14, 30)
    session_close = datetime(2024, 1, 31, 21, 0)
    broker = FakeBroker(
        is_open=False,
        next_open=open_time,
        next_close=session_close,
        now=open_time,
    )
    evaluators = {
        "asb_a": {"AAPL": 0.5, "MSFT": 0.5},
        "asb_b": {"GOOG": 1.0},
    }
    supervisor = _make_supervisor(tmp_path, broker, evaluators=evaluators)
    supervisor.start_sleeve("asb_a", 0.15)
    supervisor.start_sleeve("asb_b", 0.15)
    broker.set_session_open(
        open_time=open_time,
        session_close=session_close,
        now=open_time + timedelta(minutes=3),
    )
    supervisor.tick()
    assert "GOOG" in broker.positions
    broker.crash_after_place = len(broker.orders) + 1
    with pytest.raises(SimulatedCrash):
        supervisor.kill_sleeve("asb_a")
    inflight = _read_state(tmp_path)
    assert inflight["isolate_in_flight"] == "asb_a"
    assert inflight["state"] != "stopped"
    assert broker.close_all_called is False
    broker.crash_after_place = None
    restarted = _make_supervisor(tmp_path, broker, evaluators=evaluators)
    assert restarted.state == SupervisorState.STOPPED
    assert broker.close_all_called is True
    assert broker.positions == {}
    assert restarted.snapshot.isolate_in_flight is None
    assert restarted.snapshot.last_kill["reason"] == "fallback_interrupted"
    assert restarted.snapshot.last_kill["flattened"] is True
    assert restarted.snapshot.sleeves.get("asb_b", 0) == 0.0
```

`REQUIRED_PHRASES` add `"interrupted sleeve isolate"`.

- [ ] **Step 2: Run — FAIL.** Commit tests.

Run: `PYTHONPATH=src python3 -m pytest tests/alphastrategy/test_halt_flatten.py::test_restart_during_sleeve_isolate_flattens_account tests/alphastrategy/test_helptext.py::test_help_text_contains_required_phrases -q`

Expected: restart test fails (`isolate_in_flight` missing / new Supervisor not `stopped`). Help phrase missing.

---

### Task 2: Snapshot, persist, recover, help

- [ ] **Step 3: state.py** — Add `isolate_in_flight: str | None = None`. In `from_dict`:

```python
            isolate_in_flight=(
                None
                if payload.get("isolate_in_flight") in (None, "")
                else str(payload.get("isolate_in_flight"))
            ),
```

- [ ] **Step 4: loop.py**

At the start of `_isolate_sleeve`, before `cancel_open_orders`:

```python
        self._snapshot.isolate_in_flight = bundle_id
        self._persist()
```

After a successful `_place_batch` (no `place_error`), set `self._snapshot.isolate_in_flight = None` before updating `last_combined`.

At the start of `_flatten_account`, `self._snapshot.isolate_in_flight = None`.

Add:

```python
    def _recover_interrupted_isolate(self) -> None:
        bundle_id = self._snapshot.isolate_in_flight
        if not bundle_id:
            return
        self._flatten_account()
        self._audit("kill", bundle_id=bundle_id, isolated=False)
        self._record_kill(
            KillOutcome(
                isolated=False,
                flattened=True,
                scope="account",
                reason="fallback_interrupted",
                bundle_id=bundle_id,
            )
        )
```

Call it immediately after `_recover_interrupted_flatten()` in `__init__` and `reload_from_disk`.

- [ ] **Step 5: helptext.py** — In the `halt_flatten` section, after the interrupted-flattening sentence, add: `If the host dies during a sleeve isolate, the desk treats that as interrupted sleeve isolate: it flattens the whole paper account rather than guess the residual.`

- [ ] **Step 6: Full suite PASS. Commit.**

Run: `PYTHONPATH=src python3 -m pytest tests/alphastrategy/ -q`

Expected: all pass. `test_kill_sleeve_isolates_when_last_book_exists` still does not call `close_all`.

---

## Spec coverage

Persist-before-isolate, load flatten, `fallback_interrupted`, help, happy isolate unchanged — tasked. Rebalancing halt and flattening retry unchanged. No placeholders.
