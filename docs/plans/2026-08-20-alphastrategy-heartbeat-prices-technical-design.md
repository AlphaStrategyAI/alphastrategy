# Heartbeat Marks and Rebalance Live Flatten Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans (this cycle chose executing-plans). Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Heartbeat refreshes `last_prices` / `last_got` without flattening; the next legal rebalance flattens a live book that already breaches the spoken cap, before any target batch.

**Architecture:** Expand `_heartbeat_health_check` to keep the bar fetch, merge marks, and recompute live Got without `_snapshot_got`. After `_rebalance` writes `last_prices`, call existing `_enforce_live_book()` and return if flattening or stopped.

**Tech Stack:** Supervisor loop, FakeBroker pytest, helptext, README.

**Requirements:** [`docs/requirements/2026-08-20-alphastrategy-heartbeat-prices-requirements.md`](../requirements/2026-08-20-alphastrategy-heartbeat-prices-requirements.md)

## Global Constraints

- Paper only. Five `#nav` screens. Locked tokens. No `window.confirm`. No live.
- `"Gross cap"` must not appear in assembled JS.
- `renderBanners` keeps a **single** `const reason`.
- Heartbeat does not flatten. Do not 409 start. Do not spend a session event on a heartbeat.
- Do not call `_snapshot_got` from the heartbeat (no `execution_deviation` flood).
- Do not retry leftover orders. Resume does not catch up.
- Tests: `PYTHONPATH=src python3 -m pytest tests/alphastrategy/ -q`.

## File map

- Modify: `src/alphastrategy/supervisor/loop.py`, `src/alphastrategy/helptext.py`, `README.md`
- Test: `tests/alphastrategy/test_halt_flatten.py`, `tests/alphastrategy/test_helptext.py`

---

### Task 1: Failing tests

**Files:**

- Modify: `tests/alphastrategy/test_halt_flatten.py`
- Modify: `tests/alphastrategy/test_helptext.py`

- [ ] **Step 1: Write the failing tests**

In `tests/alphastrategy/test_helptext.py` `REQUIRED_PHRASES` after `"Caps is the spoken book"` add:

```python
    "Heartbeat refreshes last prices and does not flatten",
    "Rebalance flattens a live book that already breaches the spoken cap",
```

In `tests/alphastrategy/test_halt_flatten.py` after `test_start_sleeve_without_overlay_does_not_flatten_live_book_inside_name_cap` add:

```python
def _open_then_idle(
    tmp_path: Path,
    *,
    allocation: float = 0.15,
) -> tuple[datetime, datetime, FakeBroker, Supervisor]:
    open_time = datetime(2024, 1, 31, 14, 30)
    session_close = datetime(2024, 1, 31, 21, 0)
    broker = FakeBroker(
        is_open=False,
        next_open=open_time,
        next_close=session_close,
        now=open_time,
        equity=10_000.0,
    )
    broker.bars["AAPL"] = {"bars": [{"c": 100.0, "t": "2024-01-31"}]}
    supervisor = _make_supervisor(tmp_path, broker)
    supervisor.start_sleeve("asb_test", allocation)
    broker.set_session_open(
        open_time=open_time,
        session_close=session_close,
        now=open_time + timedelta(minutes=3),
    )
    supervisor.tick()
    return open_time, session_close, broker, supervisor


def _audit_events(tmp_path: Path) -> list[dict]:
    path = tmp_path / "audit.jsonl"
    if not path.is_file():
        return []
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def test_heartbeat_refreshes_last_prices_without_flattening(tmp_path: Path) -> None:
    open_time, _session_close, broker, supervisor = _open_then_idle(tmp_path)
    assert broker.positions.get("AAPL") == pytest.approx(15.0)
    assert supervisor.snapshot.last_prices["AAPL"] == pytest.approx(100.0)
    broker.bars["AAPL"] = {"bars": [{"c": 150.0, "t": "2024-01-31"}]}
    before_dev = sum(
        1 for ev in _audit_events(tmp_path) if ev.get("event") == "execution_deviation"
    )
    close_all_before = broker.close_all_count
    orders_before = list(broker.orders)
    broker.advance_now(open_time + timedelta(minutes=10))
    supervisor.tick()
    assert supervisor.snapshot.last_prices["AAPL"] == pytest.approx(150.0)
    assert supervisor.snapshot.last_got["AAPL"] == pytest.approx(0.225)
    assert broker.close_all_count == close_all_before
    assert supervisor.state == SupervisorState.IDLE_IN_SESSION
    assert broker.orders == orders_before
    assert supervisor.snapshot.last_rebalance_event == "2024-01-31:open"
    after_dev = sum(
        1 for ev in _audit_events(tmp_path) if ev.get("event") == "execution_deviation"
    )
    assert after_dev == before_dev
    disk = _read_state(tmp_path)
    assert disk["last_prices"]["AAPL"] == pytest.approx(150.0)
    assert disk["last_got"]["AAPL"] == pytest.approx(0.225)


def test_heartbeat_prices_held_names_after_stop_without_flattening(
    tmp_path: Path,
) -> None:
    open_time, _session_close, broker, supervisor = _open_then_idle(tmp_path)
    supervisor.stop_sleeve("asb_test")
    assert supervisor.snapshot.sleeves["asb_test"] == 0.0
    assert broker.positions.get("AAPL") == pytest.approx(15.0)
    broker.bars["AAPL"] = {"bars": [{"c": 150.0, "t": "2024-01-31"}]}
    broker.advance_now(open_time + timedelta(minutes=10))
    supervisor.tick()
    assert supervisor.snapshot.last_prices["AAPL"] == pytest.approx(150.0)
    assert supervisor.snapshot.last_got["AAPL"] == pytest.approx(0.225)
    assert broker.close_all_count == 0
    assert supervisor.state == SupervisorState.IDLE_IN_SESSION
    assert supervisor.snapshot.last_rebalance_event == "2024-01-31:open"


def test_heartbeat_does_not_flatten_when_live_name_breaches_cap(
    tmp_path: Path,
) -> None:
    open_time, _session_close, broker, supervisor = _open_then_idle(tmp_path)
    broker.bars["AAPL"] = {"bars": [{"c": 150.0, "t": "2024-01-31"}]}
    broker.advance_now(open_time + timedelta(minutes=10))
    supervisor.tick()
    assert broker.close_all_count == 0
    assert supervisor.state != SupervisorState.STOPPED


def test_close_rebalance_flattens_live_book_after_price_rally(
    tmp_path: Path,
) -> None:
    open_time, session_close, broker, supervisor = _open_then_idle(tmp_path)
    orders_after_open = list(broker.orders)
    broker.bars["AAPL"] = {"bars": [{"c": 150.0, "t": "2024-01-31"}]}
    broker.advance_now(session_close - timedelta(minutes=10))
    supervisor.tick()
    assert broker.close_all_count == 1
    assert supervisor.state == SupervisorState.STOPPED
    assert broker.orders == orders_after_open
    assert supervisor.snapshot.last_kill is not None
    assert supervisor.snapshot.last_kill["reason"] == "max_name_weight"
    assert supervisor.snapshot.last_kill["flattened"] is True
    assert supervisor.snapshot.last_rebalance_event == "2024-01-31:open"
    events = _audit_events(tmp_path)
    flattens = [ev for ev in events if ev.get("event") == "flatten"]
    assert flattens
    assert flattens[-1]["reason"] == "max_name_weight"
    closes = [
        ev
        for ev in events
        if ev.get("event") == "rebalance" and ev.get("session_event") == "close"
    ]
    assert closes == []
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
PYTHONPATH=src python3 -m pytest \
  tests/alphastrategy/test_halt_flatten.py::test_heartbeat_refreshes_last_prices_without_flattening \
  tests/alphastrategy/test_halt_flatten.py::test_heartbeat_prices_held_names_after_stop_without_flattening \
  tests/alphastrategy/test_halt_flatten.py::test_heartbeat_does_not_flatten_when_live_name_breaches_cap \
  tests/alphastrategy/test_halt_flatten.py::test_close_rebalance_flattens_live_book_after_price_rally \
  tests/alphastrategy/test_helptext.py::test_help_text_contains_required_phrases -q
```

Expected: FAIL. Heartbeat still leaves `last_prices` at 100. Close rebalance sells toward 15% or stays running instead of flattening. Help phrases missing.

If `test_heartbeat_does_not_flatten_when_live_name_breaches_cap` PASSES on the RED run, that is correct (existing lock). Keep it.

- [ ] **Step 3: Commit failing tests + docs**

```bash
git add docs/requirements/2026-08-20-alphastrategy-heartbeat-prices-requirements.md \
  docs/plans/2026-08-20-alphastrategy-heartbeat-prices-technical-design.md \
  tests/alphastrategy/test_halt_flatten.py tests/alphastrategy/test_helptext.py
git commit -m "test: heartbeat marks and close flatten on live name rally"
```

---

### Task 2: Heartbeat marks

**Files:**

- Modify: `src/alphastrategy/supervisor/loop.py`

**Interfaces:**

- Consumes: existing `_fetch_prices`, `_positions_map`, `_equity`, `_sleeve_weights`
- Produces: `_heartbeat_health_check` writes `last_prices` / `last_got`; no flatten; no `_snapshot_got`

- [ ] **Step 1: Implement heartbeat reconciliation**

Replace `_heartbeat_health_check` with:

```python
    def _price_universe(self, positions: dict[str, float]) -> set[str]:
        symbols: set[str] = set()
        for bundle_id, allocation in self._snapshot.sleeves.items():
            if allocation <= 0:
                continue
            symbols.update(self._sleeve_weights(bundle_id).keys())
        symbols.update(self._snapshot.last_combined.keys())
        symbols.update(positions.keys())
        return {str(symbol).strip().upper() for symbol in symbols if str(symbol).strip()}

    def _heartbeat_health_check(self, cur: ClockSnapshot) -> None:
        try:
            positions = _positions_map(self._broker.list_positions())
        except Exception as exc:
            raise HaltRequested(f"heartbeat live book: {exc}") from exc
        symbols = self._price_universe(positions)
        if not symbols:
            return
        prices = self._fetch_prices(symbols, now=cur.now if cur.is_open else None)
        try:
            equity = self._equity()
        except Exception as exc:
            raise HaltRequested(f"heartbeat live book: {exc}") from exc
        self._snapshot.last_prices = {
            **self._snapshot.last_prices,
            **{symbol: float(price) for symbol, price in prices.items()},
        }
        if equity > 0:
            self._snapshot.last_got = {
                symbol: (qty * prices[symbol]) / equity
                for symbol, qty in positions.items()
                if symbol in prices and qty != 0.0
            }
```

Do not call `_enforce_live_book` or `_snapshot_got` here.

- [ ] **Step 2: Run the heartbeat tests**

```bash
PYTHONPATH=src python3 -m pytest \
  tests/alphastrategy/test_halt_flatten.py::test_heartbeat_refreshes_last_prices_without_flattening \
  tests/alphastrategy/test_halt_flatten.py::test_heartbeat_prices_held_names_after_stop_without_flattening \
  tests/alphastrategy/test_halt_flatten.py::test_heartbeat_does_not_flatten_when_live_name_breaches_cap -q
```

Expected: PASS. Close flatten test still FAIL.

- [ ] **Step 3: Commit**

```bash
git add src/alphastrategy/supervisor/loop.py
git commit -m "feat: heartbeat refreshes last prices without flattening"
```

---

### Task 3: Rebalance live-book flatten + help

**Files:**

- Modify: `src/alphastrategy/supervisor/loop.py`
- Modify: `src/alphastrategy/helptext.py`
- Modify: `README.md`

- [ ] **Step 1: Enforce live book after rebalance marks**

In `_rebalance`, after `self._snapshot.last_prices = dict(prices)` and before `plan_orders`:

```python
        self._enforce_live_book()
        if self._snapshot.state in (
            SupervisorState.FLATTENING,
            SupervisorState.STOPPED,
        ):
            return
```

Keep `check_book(combined, equity, rebalance_policy)` where it is (before fetch).

- [ ] **Step 2: Help and README**

In `helptext.py` execution body, after the heartbeat sentence, add:

`Heartbeat refreshes last prices and does not flatten. `

In halt_flatten, after overlay flatten, add:

`Rebalance flattens a live book that already breaches the spoken cap. `

In `how_risk` after the overlay flatten sentence, add the same rebalance sentence.

In `how_activity` after the Beat tiles sentence, add the heartbeat sentence.

In README Operator heartbeat bullet, after “does not place orders.”, add both sentences.

- [ ] **Step 3: Run targeted tests**

```bash
PYTHONPATH=src python3 -m pytest \
  tests/alphastrategy/test_halt_flatten.py::test_heartbeat_refreshes_last_prices_without_flattening \
  tests/alphastrategy/test_halt_flatten.py::test_heartbeat_prices_held_names_after_stop_without_flattening \
  tests/alphastrategy/test_halt_flatten.py::test_heartbeat_does_not_flatten_when_live_name_breaches_cap \
  tests/alphastrategy/test_halt_flatten.py::test_close_rebalance_flattens_live_book_after_price_rally \
  tests/alphastrategy/test_halt_flatten.py::test_stopping_last_sleeve_sells_existing_positions_at_next_rebalance \
  tests/alphastrategy/test_halt_flatten.py::test_limit_breach_flattens_account \
  tests/alphastrategy/test_helptext.py::test_help_text_contains_required_phrases \
  tests/alphastrategy/test_web_tokens.py::test_html_has_five_nav_screens \
  tests/alphastrategy/test_e2e_mocked.py::test_v1_done_path -q
```

Expected: PASS.

- [ ] **Step 4: Commit**

```bash
git add src/alphastrategy/supervisor/loop.py src/alphastrategy/helptext.py README.md
git commit -m "feat: flatten live spoken-cap breach at rebalance"
```

---

### Task 4: Full suite

- [ ] **Step 1: Run** `PYTHONPATH=src python3 -m pytest tests/alphastrategy/ -q`

Expected: all pass. No real broker.

- [ ] **Step 2: Commit any fixes, push, mark PR ready, ff-merge to main**
