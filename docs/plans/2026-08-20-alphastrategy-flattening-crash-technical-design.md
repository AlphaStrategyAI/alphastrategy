# Flattening Crash Recovery Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans (this cycle chose executing-plans). Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** If the host dies while the snapshot is `flattening`, finish cancel + `close_all` on the next Supervisor load instead of parking there forever.

**Architecture:** `_recover_interrupted_flatten` on `__init__` and `reload_from_disk` (after rebalancing recovery). `tick` retries `_flatten_account` when state is still `FLATTENING`. Same flatten success/halt matrix as account kill. Help names interrupted flattening.

**Tech Stack:** Python supervisor, Quiet cockpit help copy, pytest with FakeBroker.

**Requirements:** [`docs/requirements/2026-08-20-alphastrategy-flattening-crash-requirements.md`](../requirements/2026-08-20-alphastrategy-flattening-crash-requirements.md)

## Global Constraints

- Paper only. Five `#nav` screens. Locked tokens. No `window.confirm`. No live. No WebSockets. No charts.
- Resume does not catch up. Do not flatten a `REBALANCING` snapshot.
- JS must not contain `Gross cap`. Do not label a tile Live.
- Tests: `PYTHONPATH=src python3 -m pytest tests/alphastrategy/ -q`. Never hit a real broker.

## File map

- Modify: `src/alphastrategy/supervisor/loop.py`, `src/alphastrategy/helptext.py`
- Test: `tests/alphastrategy/test_halt_flatten.py`, `tests/alphastrategy/test_helptext.py`

---

### Task 1: Failing tests

- [ ] **Step 1: FakeBroker close_all crash + supervisor tests**

In `tests/alphastrategy/test_halt_flatten.py` `FakeBroker.__init__`, add `self.crash_on_close_all = False`.

In `close_all`, **before** clearing positions:

```python
        if self.crash_on_close_all:
            raise SimulatedCrash("host killed during close_all")
```

Add:

```python
def test_restart_during_flattening_finishes_flatten(tmp_path: Path):
    broker = FakeBroker(is_open=True)
    broker.positions["AAPL"] = 10.0
    supervisor = _make_supervisor(tmp_path, broker)
    supervisor.start_sleeve("asb_test", 0.15)
    supervisor.snapshot.last_combined = {"AAPL": 0.15}
    supervisor.snapshot.last_got = {"AAPL": 0.10}
    supervisor._snapshot.state = SupervisorState.FLATTENING
    supervisor._persist()

    restarted = _make_supervisor(tmp_path, broker)
    assert restarted.state == SupervisorState.STOPPED
    assert broker.close_all_called is True
    assert broker.positions == {}
    assert restarted.snapshot.last_combined == {}
    assert restarted.snapshot.last_got == {}
    assert restarted.snapshot.sleeves.get("asb_test", 0) == 0.0
    assert "asb_test" in restarted.snapshot.stopped
    events = [
        json.loads(line)
        for line in (tmp_path / "audit.jsonl").read_text(encoding="utf-8").splitlines()
    ]
    assert any(event["event"] == "flatten" for event in events)


def test_kill_account_host_crash_then_restart_finishes_flatten(tmp_path: Path):
    broker = FakeBroker(is_open=True)
    broker.positions["AAPL"] = 10.0
    supervisor = _make_supervisor(tmp_path, broker)
    supervisor.start_sleeve("asb_test", 0.15)
    broker.crash_on_close_all = True
    with pytest.raises(SimulatedCrash):
        supervisor.kill_account()
    inflight = _read_state(tmp_path)
    assert inflight["state"] == "flattening"
    assert broker.positions.get("AAPL", 0.0) == 10.0
    broker.crash_on_close_all = False
    restarted = _make_supervisor(tmp_path, broker)
    assert restarted.state == SupervisorState.STOPPED
    assert broker.close_all_called is True
    assert broker.positions == {}
    assert broker.close_all_count == 1
```

`REQUIRED_PHRASES` add `"interrupted flattening"`.

- [ ] **Step 2: Run — FAIL.** Commit tests.

Run: `PYTHONPATH=src python3 -m pytest tests/alphastrategy/test_halt_flatten.py::test_restart_during_flattening_finishes_flatten tests/alphastrategy/test_halt_flatten.py::test_kill_account_host_crash_then_restart_finishes_flatten tests/alphastrategy/test_helptext.py::test_help_text_contains_required_phrases -q`

Expected: restart tests fail (`state` stays `flattening`, `close_all` not called). Help phrase missing.

---

### Task 2: Recover flatten, tick retry, help

- [ ] **Step 3: loop.py**

Add:

```python
    def _recover_interrupted_flatten(self) -> None:
        if self._snapshot.state != SupervisorState.FLATTENING:
            return
        self._flatten_account()
```

Call it immediately after `_recover_interrupted_rebalance()` in `__init__` and `reload_from_disk`.

In `tick`, replace the combined STOPPED/FLATTENING early return:

```python
            if self._snapshot.state == SupervisorState.STOPPED:
                self._persist()
                return
            if self._snapshot.state == SupervisorState.FLATTENING:
                self._flatten_account()
                self._persist()
                return
```

- [ ] **Step 4: helptext.py** — In the `halt_flatten` section body, after “Halt is not flatten.”, add: `If the host dies while flattening, the desk treats that as interrupted flattening: it retries cancel and close_all. If the broker is unreachable it health-halts.`

- [ ] **Step 5: Full suite PASS. Commit.**

Run: `PYTHONPATH=src python3 -m pytest tests/alphastrategy/ -q`

Expected: all pass. `test_flatten_clears_last_book_and_zeros_sleeves` and `test_restart_during_rebalancing_halts_without_duplicate_orders` still pass.

---

## Spec coverage

Load of `FLATTENING` finishes flatten, tick does not park, unreachable still halts, help — tasked. Rebalancing-crash halt unchanged. No placeholders.
