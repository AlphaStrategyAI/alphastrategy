# Rebalancing Crash Recovery Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans (this cycle chose executing-plans). Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Persist an in-flight paper rebalance before and after each send, and if the host dies in `REBALANCING`, health-halt with Wanted / Got instead of firing the same session event again.

**Architecture:** `SupervisorSnapshot.rebalance_placed` plus `_persist()` before a non-empty `_place_batch` and after each successful `place_order`. `Supervisor.__init__` and `reload_from_disk` call `_recover_interrupted_rebalance` when state is `REBALANCING`: snapshot got, audit incomplete rebalance, `_halt`. No API schema beyond the snapshot JSON and existing audit fields.

**Tech Stack:** Python supervisor, Quiet cockpit help copy, pytest with FakeBroker.

**Requirements:** [`docs/requirements/2026-08-20-alphastrategy-rebalancing-crash-requirements.md`](../requirements/2026-08-20-alphastrategy-rebalancing-crash-requirements.md)

## Global Constraints

- Paper only. Five `#nav` screens. Locked tokens. No `window.confirm`. No live. No WebSockets. No charts.
- Resume does not catch up. Do not retry remaining orders in the same `{date}:{open|close}` event.
- JS must not contain `Gross cap`. Do not label a tile Live.
- Tests: `PYTHONPATH=src python3 -m pytest tests/alphastrategy/ -q`. Never hit a real broker.

## File map

- Modify: `src/alphastrategy/supervisor/state.py`, `src/alphastrategy/supervisor/loop.py`, `src/alphastrategy/helptext.py`
- Test: `tests/alphastrategy/test_halt_flatten.py`, `tests/alphastrategy/test_helptext.py`

---

### Task 1: Failing tests

- [ ] **Step 1: FakeBroker crash hook + supervisor tests**

In `tests/alphastrategy/test_halt_flatten.py` `FakeBroker.__init__`, add `self.crash_after_place = None`.

Add this class next to `FakeBroker` (after `close_all` / before `_make_supervisor` is fine; keep it at module level):

```python
class SimulatedCrash(BaseException):
    """Host kill mid-tick: not `Exception`, so `tick` except-handlers do not convert it to halt."""
```

In `place_order`, **before** appending the order, after the existing `fail_place_after` check:

```python
        if self.crash_after_place is not None and len(self.orders) >= self.crash_after_place:
            raise SimulatedCrash("host killed during place_order")
```

Add:

```python
def test_rebalance_persists_inflight_before_first_place(tmp_path: Path):
    open_time = datetime(2024, 1, 31, 14, 30)
    session_close = datetime(2024, 1, 31, 21, 0)
    broker = FakeBroker(
        is_open=False,
        next_open=open_time,
        next_close=session_close,
        now=open_time,
    )

    class ProbeBroker(FakeBroker):
        def place_order(self, symbol: str, qty: float, side: str) -> dict:
            if not self.orders:
                self.before_first = _read_state(tmp_path)
            return super().place_order(symbol, qty, side)

    broker = ProbeBroker(
        is_open=False,
        next_open=open_time,
        next_close=session_close,
        now=open_time,
    )
    supervisor = _make_supervisor(
        tmp_path,
        broker,
        evaluators={"asb_test": {"AAPL": 0.5, "MSFT": 0.5}},
    )
    supervisor.start_sleeve("asb_test", 0.4)
    _trigger_open_rebalance(tmp_path, broker, supervisor)

    assert broker.before_first["state"] == "rebalancing"
    assert broker.before_first["last_rebalance_event"] == "2024-01-31:open"
    assert broker.before_first["orders_today"] == 0
    assert broker.before_first.get("rebalance_placed", 0) == 0
    finished = _read_state(tmp_path)
    assert finished["state"] == "idle_in_session"
    assert finished["last_rebalance_event"] == "2024-01-31:open"
    events = [
        json.loads(line)
        for line in (tmp_path / "audit.jsonl").read_text(encoding="utf-8").splitlines()
    ]
    rebalances = [event for event in events if event["event"] == "rebalance"]
    assert rebalances[-1]["complete"] is True


def test_restart_during_rebalancing_halts_without_duplicate_orders(tmp_path: Path):
    open_time = datetime(2024, 1, 31, 14, 30)
    session_close = datetime(2024, 1, 31, 21, 0)
    broker = FakeBroker(
        is_open=False,
        next_open=open_time,
        next_close=session_close,
        now=open_time,
    )
    broker.crash_after_place = 1
    supervisor = _make_supervisor(
        tmp_path,
        broker,
        evaluators={"asb_test": {"AAPL": 0.5, "MSFT": 0.5}},
    )
    supervisor.start_sleeve("asb_test", 0.4)
    with pytest.raises(SimulatedCrash):
        _trigger_open_rebalance(tmp_path, broker, supervisor)

    inflight = _read_state(tmp_path)
    assert inflight["state"] == "rebalancing"
    assert inflight["last_rebalance_event"] == "2024-01-31:open"
    assert inflight["orders_today"] == 1
    assert len(broker.orders) == 1

    restarted = _make_supervisor(
        tmp_path,
        broker,
        evaluators={"asb_test": {"AAPL": 0.5, "MSFT": 0.5}},
    )
    assert restarted.state == SupervisorState.HALTED
    assert broker.close_all_called is False
    assert restarted.snapshot.orders_today == 1
    assert restarted.snapshot.last_rebalance_event == "2024-01-31:open"
    assert restarted.snapshot.last_got
    assert "interrupted rebalancing" in (restarted.snapshot.halt_reason or "").lower()
    events = [
        json.loads(line)
        for line in (tmp_path / "audit.jsonl").read_text(encoding="utf-8").splitlines()
    ]
    rebalances = [event for event in events if event["event"] == "rebalance"]
    assert rebalances
    assert rebalances[-1]["complete"] is False
    assert rebalances[-1]["orders"] == 1
    assert "wanted" in rebalances[-1]
    assert "got" in rebalances[-1]
    first = list(broker.orders)
    broker.advance_now(open_time + timedelta(minutes=10))
    restarted.tick()
    assert broker.orders == first
    assert restarted.state == SupervisorState.HALTED
    assert broker.close_all_called is False
```

`REQUIRED_PHRASES` add `"interrupted rebalancing"`.

- [ ] **Step 2: Run — FAIL.** Commit tests.

Run: `PYTHONPATH=src python3 -m pytest tests/alphastrategy/test_halt_flatten.py::test_rebalance_persists_inflight_before_first_place tests/alphastrategy/test_halt_flatten.py::test_restart_during_rebalancing_halts_without_duplicate_orders tests/alphastrategy/test_helptext.py::test_help_text_contains_required_phrases -q`

Expected: persist test fails (`before_first["state"]` is not `rebalancing`). Restart test fails (disk not `rebalancing` and/or new Supervisor is not `halted`). Help phrase missing.

---

### Task 2: Snapshot, persist, recover, help

- [ ] **Step 3: state.py** — Add `rebalance_placed: int = 0` on `SupervisorSnapshot`. In `from_dict`, `rebalance_placed=int(payload.get("rebalance_placed") or 0)`.

- [ ] **Step 4: loop.py** — Persist in-flight; recover on load.

`_place_batch` after `orders_today = already + placed`:

```python
            if self._snapshot.state == SupervisorState.REBALANCING:
                self._snapshot.rebalance_placed = placed
            self._persist()
```

`_rebalance` after `plan_orders`, before `_place_batch`:

```python
        if plans:
            self._snapshot.last_rebalance_event = f"{session_date}:{event}"
            self._snapshot.rebalance_placed = 0
            self._persist()
        placed, place_error = self._place_batch(plans, already)
        got = self._snapshot_got(combined, prices, equity)
        self._snapshot.last_rebalance_event = f"{session_date}:{event}"
        self._audit(
            "rebalance",
            session_event=event,
            orders=placed,
            wanted=dict(combined),
            got=dict(got),
            complete=place_error is None,
        )
        if place_error is not None:
            raise HaltRequested(
                f"place_order failed after {placed} of {len(plans)}: {place_error}"
            ) from place_error
        self._snapshot.rebalance_placed = 0
        self._set_idle_state(cur)
```

Keep the existing `last_combined` / `last_prices` writes **before** this persist so recovery has prices.

Add:

```python
    def _recover_interrupted_rebalance(self) -> None:
        if self._snapshot.state != SupervisorState.REBALANCING:
            return
        combined = dict(self._snapshot.last_combined)
        prices = dict(self._snapshot.last_prices)
        try:
            equity = self._equity()
            self._snapshot_got(combined, prices, equity)
        except Exception:
            pass
        placed = int(self._snapshot.rebalance_placed or 0)
        event = "open"
        marker = self._snapshot.last_rebalance_event or ""
        if ":" in marker:
            event = marker.split(":", 1)[1]
        self._audit(
            "rebalance",
            session_event=event,
            orders=placed,
            wanted=dict(combined),
            got=dict(self._snapshot.last_got),
            complete=False,
        )
        self._halt(f"interrupted rebalancing after {placed} orders")
```

Call it at the end of `__init__` (after the `STARTING` → idle conversion) and at the end of `reload_from_disk` (same place).

- [ ] **Step 5: helptext.py** — In the `execution` section body, after the incomplete-rebalance sentence, add: `If the host dies mid-rebalance, the desk treats that as interrupted rebalancing: it writes Wanted / Got from the broker, health-halts, and does not flatten or retry that event.`

- [ ] **Step 6: Full suite PASS. Commit.**

Run: `PYTHONPATH=src python3 -m pytest tests/alphastrategy/ -q`

Expected: all pass. Existing `test_rebalance_partial_place_order_failure_halts_without_flatten` and `test_rebalance_counts_orders_today_and_audits_wanted_got` still pass.

---

## Spec coverage

Persist-before-send, persist-after-ack, `rebalance_placed`, load of `REBALANCING` → halt, no flatten, no retry, help — tasked. `FLATTENING` crash explicitly out. No placeholders.
