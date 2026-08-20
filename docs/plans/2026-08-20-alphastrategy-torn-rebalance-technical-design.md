# Torn Rebalance Honesty Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans (this cycle chose executing-plans). Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Count each successful paper `place_order`, and when a later call throws, record Wanted / Got, health-halt, and do not flatten or retry that session event.

**Architecture:** Shared `_place_batch` in `supervisor/loop.py`. Torn `_rebalance` snapshots `last_got`, audits deviations and `rebalance` with `complete: false`, raises `HaltRequested`. Activity paints `incomplete`. No API schema beyond the existing audit JSONL fields.

**Tech Stack:** Python supervisor, Quiet cockpit JS, pytest with FakeBroker.

**Requirements:** [`docs/requirements/2026-08-20-alphastrategy-torn-rebalance-requirements.md`](../requirements/2026-08-20-alphastrategy-torn-rebalance-requirements.md)

## Global Constraints

- Paper only. Five `#nav` screens. Locked tokens. No `window.confirm`. No live. No WebSockets. No charts.
- Resume does not catch up. Do not retry remaining orders in the same `{date}:{open|close}` event.
- JS must not contain `Gross cap`. Do not label a tile Live.
- Tests: `PYTHONPATH=src python3 -m pytest tests/alphastrategy/ -q`. Never hit a real broker.

## File map

- Modify: `src/alphastrategy/supervisor/loop.py`, `src/alphastrategy/web/static/js/paint-activity.js`, `src/alphastrategy/helptext.py`
- Test: `tests/alphastrategy/test_halt_flatten.py`, `tests/alphastrategy/test_web_tokens.py`, `tests/alphastrategy/test_helptext.py`

---

### Task 1: Failing tests

- [ ] **Step 1: FakeBroker + supervisor test**

In `tests/alphastrategy/test_halt_flatten.py` `FakeBroker.__init__`, add `self.fail_place_after = None`.

In `place_order`, **before** appending the order:

```python
        if self.fail_place_after is not None and len(self.orders) >= self.fail_place_after:
            raise RuntimeError("broker place_order failed")
```

Add:

```python
def test_rebalance_partial_place_order_failure_halts_without_flatten(tmp_path: Path):
    open_time = datetime(2024, 1, 31, 14, 30)
    session_close = datetime(2024, 1, 31, 21, 0)
    broker = FakeBroker(
        is_open=False,
        next_open=open_time,
        next_close=session_close,
        now=open_time,
    )
    broker.fail_place_after = 1
    supervisor = _make_supervisor(
        tmp_path,
        broker,
        evaluators={"asb_test": {"AAPL": 0.5, "MSFT": 0.5}},
    )
    supervisor.start_sleeve("asb_test", 0.4)
    _trigger_open_rebalance(tmp_path, broker, supervisor)

    assert supervisor.state == SupervisorState.HALTED
    assert broker.close_all_called is False
    assert len(broker.orders) == 1
    assert supervisor.snapshot.orders_today == 1
    assert supervisor.snapshot.last_rebalance_event == "2024-01-31:open"
    assert supervisor.snapshot.last_got
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
    assert any(event["event"] == "execution_deviation" for event in events)
    first = list(broker.orders)
    broker.advance_now(open_time + timedelta(minutes=10))
    supervisor.tick()
    assert broker.orders == first
    assert supervisor.state == SupervisorState.HALTED
```

`REQUIRED_PHRASES` add `"incomplete rebalance"`.

In `test_web_tokens.py`:

```python
def test_js_activity_incomplete_rebalance(js_text: str) -> None:
    paint = js_text[
        js_text.find("function eventSummary") : js_text.find("function renderActivity")
    ]
    assert "complete === false" in paint
    assert "incomplete" in paint
    assert "Complete" in paint
    assert "window.confirm" not in js_text
    assert "window.state" not in js_text
```

- [ ] **Step 2: Run — FAIL.** Commit tests.

Run: `PYTHONPATH=src python3 -m pytest tests/alphastrategy/test_halt_flatten.py::test_rebalance_partial_place_order_failure_halts_without_flatten tests/alphastrategy/test_helptext.py::test_help_text_contains_required_phrases tests/alphastrategy/test_web_tokens.py::test_js_activity_incomplete_rebalance -q`

Expected: supervisor test fails (`orders_today != 1` and/or no `rebalance` with `complete: false`). Help phrase missing. JS slice missing `incomplete`.

---

### Task 2: Supervisor, Activity, help

- [ ] **Step 3: loop.py** — Add `_place_batch` and `_snapshot_got`. Use them from `_rebalance` and `_isolate_sleeve`.

```python
    def _place_batch(
        self,
        plans: list,
        already: int,
        extra_audit: dict | None = None,
    ) -> int:
        placed = 0
        extra = extra_audit or {}
        for plan in plans:
            self._broker.place_order(plan.symbol, plan.qty, plan.side)
            self._audit(
                "order",
                symbol=plan.symbol,
                qty=plan.qty,
                side=plan.side,
                **extra,
            )
            placed += 1
            self._snapshot.orders_today = already + placed
        return placed

    def _snapshot_got(
        self,
        combined: dict[str, float],
        prices: dict[str, float],
        equity: float,
    ) -> dict[str, float]:
        positions_after = _positions_map(self._broker.list_positions())
        got = {
            symbol: (qty * prices[symbol]) / equity
            for symbol, qty in positions_after.items()
            if symbol in prices and equity > 0
        }
        self._snapshot.last_got = dict(got)
        for deviation in deviations_after(combined, got, equity, prices):
            self._audit("execution_deviation", **deviation)
        return got
```

`_rebalance` order loop becomes:

```python
        placed = 0
        place_error: Exception | None = None
        try:
            placed = self._place_batch(plans, already)
        except Exception as exc:
            place_error = exc
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
        self._set_idle_state(cur)
```

`_isolate_sleeve` replaces its for-loop with `self._place_batch(plans, already, extra_audit={"reason": "sleeve_kill"})` and drops `orders_today = already + len(plans)`.

Do not wrap `FlattenRequested` from `plan_orders` (that stays before `_place_batch`).

- [ ] **Step 4: paint-activity.js** — In `eventSummary` rebalance case, append `incomplete` when `ev.complete === false`. In `eventDetail` rebalance `detailList`, add `["Complete", ev.complete === false ? "no" : "yes"]`.

- [ ] **Step 5: helptext.py** — In the `execution` section body, add: `An incomplete rebalance still writes Wanted / Got, counts those orders, and health-halts. It does not flatten and does not retry that event.`

- [ ] **Step 6: Full suite PASS. Commit.**

Run: `PYTHONPATH=src python3 -m pytest tests/alphastrategy/ -q`

Expected: all pass. Existing `test_rebalance_counts_orders_today_and_audits_wanted_got` still passes.

---

## Spec coverage

Per-success count, torn halt, no flatten, no retry, Activity incomplete, help — tasked. Crash recovery of `REBALANCING` explicitly out. No placeholders.
