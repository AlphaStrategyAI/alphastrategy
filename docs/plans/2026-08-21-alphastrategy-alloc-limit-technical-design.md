# Caps LIMIT follows current allocations Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans (this cycle chose executing-plans). Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Next-send Caps LIMIT dry-runs `combine(current allocations, last sleeve weights)` so an allocation raise that would flatten through Order size warns before the window, without evaluating DSL on GET.

**Architecture:** `_next_send_combined(snapshot)` builds `combine` pairs from `last_sleeve_weights` and positive `sleeves`. If none, use `last_combined`. `_next_send_limit` keeps taking that dict. Book `check_book` unchanged.

**Tech Stack:** Python 3.9+, pytest, helptext, README.

**Requirements:** [`docs/requirements/2026-08-21-alphastrategy-alloc-limit-requirements.md`](../requirements/2026-08-21-alphastrategy-alloc-limit-requirements.md)

## Global Constraints

- Paper only. Five `#nav` screens. Locked tokens. No live.
- Do not evaluate DSL on GET. Do not flatten on GET. Do not place.
- Keep Caps four tiles. Keep `#risk-cap-order`.
- Keep empty-`last_prices` last_combined 0.40 → `live_limit` null.
- Tests: `PYTHONPATH=src python3 -m pytest tests/alphastrategy/ -q`.

## File map

- Modify: `src/alphastrategy/risk/utilization.py`, `src/alphastrategy/helptext.py`, `README.md`
- Test: `tests/alphastrategy/test_api.py`, `tests/alphastrategy/test_risk.py`, `tests/alphastrategy/test_helptext.py`

---

### Task 1: Failing tests

- [ ] **Step 1: Write the failing tests**

`REQUIRED_PHRASES` add:

```python
    "Caps LIMIT follows current allocations on last sleeve weights",
```

In `test_api.py` after `test_status_live_limit_next_send_order_size`:

```python
def test_status_live_limit_next_send_follows_current_allocation(api_stack):
    client, home, supervisor, broker = api_stack
    supervisor.set_policy({"max_order_notional_frac": 0.10})
    supervisor.snapshot.last_got = {}
    supervisor.snapshot.last_combined = {"AAPL": 0.10}
    supervisor.snapshot.last_sleeve_weights = {"asb_x": {"AAPL": 1.0}}
    supervisor.snapshot.sleeves = {"asb_x": 0.18}
    supervisor.snapshot.last_prices = {"AAPL": 100.0}
    save_state(home.state_path(), supervisor.snapshot)
    broker.positions = {}
    close_all_before = broker.close_all_count
    body = client.get("/api/status").json()
    assert body["utilization"]["live_limit"]["reason"] == "max_order_notional_frac"
    assert body["utilization"]["live_limit"]["kind"] == "send"
    risk = client.get("/api/risk").json()
    assert risk["utilization"]["live_limit"]["reason"] == "max_order_notional_frac"
    assert broker.close_all_count == close_all_before
    assert supervisor.state.value != "stopped"
```

In `test_risk.py` after `test_from_supervisor_live_limit_next_send_order_size`:

```python
def test_from_supervisor_live_limit_next_send_follows_current_allocation() -> None:
    from alphastrategy.risk.utilization import from_supervisor

    class Snap:
        orders_today = 0
        last_combined = {"AAPL": 0.10}
        last_got = {}
        last_prices = {"AAPL": 100.0}
        last_sleeve_weights = {"asb_x": {"AAPL": 1.0}}
        sleeves = {"asb_x": 0.18}

    class Fake:
        snapshot = Snap()

        def spoken_policy(self):
            return replace(AccountPolicy.defaults(), max_order_notional_frac=0.10)

        def live_book(self):
            return {"equity": 10_000.0, "cash": 10_000.0}, []

        def live_cap_weights(self, equity, positions):
            del equity, positions
            return {}

    out = from_supervisor(Fake(), live=True)
    assert out["live_limit"]["reason"] == "max_order_notional_frac"
    assert out["live_limit"]["kind"] == "send"
```

Keep `test_status_live_limit_next_send_order_size`.
Keep `test_from_supervisor_live_limit_ignores_last_combined`.

- [ ] **Step 2: Run the new tests and confirm they fail**

```bash
PYTHONPATH=src python3 -m pytest tests/alphastrategy/test_api.py::test_status_live_limit_next_send_follows_current_allocation tests/alphastrategy/test_risk.py::test_from_supervisor_live_limit_next_send_follows_current_allocation tests/alphastrategy/test_api.py::test_status_live_limit_next_send_order_size tests/alphastrategy/test_risk.py::test_from_supervisor_live_limit_ignores_last_combined tests/alphastrategy/test_helptext.py::test_help_text_contains_required_phrases -q
```

Expected: the two new live_limit tests fail (`live_limit` null — last combined 0.10 does not exceed Order size). Help phrase missing. Existing Order size / empty-prices tests still pass.

- [ ] **Step 3: Commit tests and docs**

---

### Task 2: Implement

- [ ] **Step 4: `_next_send_combined` in utilization.py**

```python
from alphastrategy.supervisor.combine import combine
```

```python
def _next_send_combined(snapshot: Any) -> dict[str, float] | None:
    weights = getattr(snapshot, "last_sleeve_weights", None) or {}
    sleeves = getattr(snapshot, "sleeves", None) or {}
    pairs: list[tuple[float, dict[str, float]]] = []
    for bundle_id, sleeve_weights in weights.items():
        if not isinstance(sleeve_weights, dict) or not sleeve_weights:
            continue
        try:
            alloc = float(sleeves.get(bundle_id) or 0)
        except (TypeError, ValueError):
            continue
        if alloc <= 0:
            continue
        pairs.append((alloc, dict(sleeve_weights)))
    if pairs:
        try:
            return combine(pairs)
        except Exception:
            return None
    combined = getattr(snapshot, "last_combined", None)
    if not combined:
        return None
    return dict(combined)
```

`from_supervisor` dry-run:

```python
            combined=_next_send_combined(snapshot),
```

Do not flatten. Do not call DSL.

- [ ] **Step 5: Help and README**

`helptext.py`: add `Caps LIMIT follows current allocations on last sleeve weights. ` to `execution` (after Caps LIMIT same live book), `halt_flatten` (after Caps LIMIT Order size), `how_risk` (same).

README Operator: same sentence after Caps LIMIT Order size. Keep `Next rebalance`.

- [ ] **Step 6: Full suite**

```bash
PYTHONPATH=src python3 -m pytest tests/alphastrategy/ -q
```

- [ ] **Step 7: Commit, push, update PR**
