# Caps LIMIT live-book Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans (this cycle chose executing-plans). Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Caps LIMIT / Clock Next flatten / CLI LIMIT `check_book` the same priced live blotter flatten-now uses, not only persisted `last_got`.

**Architecture:** Extract `_priced_live_weights`. `live_cap_weights` is priced else `last_got` (never `last_combined`). `from_supervisor(live=True)` passes that into `summarize`.

**Tech Stack:** Python 3.9+, pytest, helptext, README. No JS paint change.

**Requirements:** [`docs/requirements/2026-08-20-alphastrategy-caps-limit-book-requirements.md`](../requirements/2026-08-20-alphastrategy-caps-limit-book-requirements.md)

## Global Constraints

- Paper only. Five `#nav` screens. Locked tokens. No live.
- `"Gross cap"` must not appear in assembled JS.
- Heartbeat does not flatten. GET status/risk must not flatten.
- Do not feed `plan_orders` from `live_book()`.
- Do not use `last_combined` for `live_limit`.
- Do not overwrite Cash composition subs.
- Tests: `PYTHONPATH=src python3 -m pytest tests/alphastrategy/ -q`.
- Fixture: 15 AAPL × $150 / $10k = 0.225 vs default 20% name cap.

## File map

- Modify: `src/alphastrategy/supervisor/loop.py`, `src/alphastrategy/risk/utilization.py`, `src/alphastrategy/helptext.py`, `README.md`
- Test: `tests/alphastrategy/test_api.py`, `tests/alphastrategy/test_risk.py`, `tests/alphastrategy/test_helptext.py`

---

### Task 1: Failing tests

- [ ] **Step 1: Write the failing tests**

`REQUIRED_PHRASES` add:

```python
    "Caps LIMIT follows the same live book as Tighten",
```

In `tests/alphastrategy/test_api.py` after `test_status_live_limit_does_not_flatten`:

```python
def test_status_live_limit_without_last_got_uses_priced_book(api_stack):
    client, home, supervisor, broker = api_stack
    supervisor.snapshot.last_got = {}
    supervisor.snapshot.last_prices = {"AAPL": 150.0}
    save_state(home.state_path(), supervisor.snapshot)
    broker.positions = {"AAPL": 15.0}
    close_all_before = broker.close_all_count
    body = client.get("/api/status").json()
    assert body["utilization"]["live_limit"]["reason"] == "max_name_weight"
    risk = client.get("/api/risk").json()
    assert risk["utilization"]["live_limit"]["reason"] == "max_name_weight"
    assert broker.close_all_count == close_all_before
    assert supervisor.state.value != "stopped"


def test_status_live_limit_priced_book_wins_over_stale_last_got(api_stack):
    client, home, supervisor, broker = api_stack
    supervisor.snapshot.last_got = {"AAPL": 0.15}
    supervisor.snapshot.last_prices = {"AAPL": 150.0}
    save_state(home.state_path(), supervisor.snapshot)
    broker.positions = {"AAPL": 15.0}
    body = client.get("/api/status").json()
    assert body["utilization"]["live_limit"]["reason"] == "max_name_weight"
```

In `tests/alphastrategy/test_risk.py`:

```python
def test_from_supervisor_live_limit_ignores_last_combined() -> None:
    from alphastrategy.risk.utilization import from_supervisor

    class Snap:
        orders_today = 0
        last_combined = {"AAPL": 0.40}
        last_got = {}
        last_prices = {}

    class Fake:
        snapshot = Snap()

        def spoken_policy(self):
            return AccountPolicy.defaults()

        def live_book(self):
            return {"equity": 10_000.0, "cash": 10_000.0}, []

        def live_cap_weights(self, equity, positions):
            del equity, positions
            return {}

    out = from_supervisor(Fake(), live=True)
    assert out["live_limit"] is None
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
PYTHONPATH=src python3 -m pytest \
  tests/alphastrategy/test_helptext.py::test_help_text_contains_required_phrases \
  tests/alphastrategy/test_api.py::test_status_live_limit_without_last_got_uses_priced_book \
  tests/alphastrategy/test_api.py::test_status_live_limit_priced_book_wins_over_stale_last_got \
  tests/alphastrategy/test_risk.py::test_from_supervisor_live_limit_ignores_last_combined \
  -q
```

Expected: help phrase missing; first two API tests fail (`live_limit` None). The last_combined Fake may already pass if `from_supervisor` does not read `last_combined` for LIMIT — keep it as a lock.

- [ ] **Step 3: Commit failing tests and docs**

```bash
git add docs/requirements/2026-08-20-alphastrategy-caps-limit-book-requirements.md \
  docs/plans/2026-08-20-alphastrategy-caps-limit-book-technical-design.md \
  tests/alphastrategy/test_helptext.py tests/alphastrategy/test_api.py \
  tests/alphastrategy/test_risk.py
git commit -m "test: Caps LIMIT follows the same live book as Tighten"
```

---

### Task 2: Engine + help

- [ ] **Step 1: Priced weights + utilization**

In `loop.py`, split priced qty out of `_live_book_weights`:

```python
    def _priced_live_weights(
        self, equity: float, raw_positions: list[dict[str, Any]]
    ) -> dict[str, float]:
        positions = _positions_map(raw_positions)
        prices = dict(self._snapshot.last_prices)
        if equity > 0 and prices:
            got = {
                symbol: (qty * prices[symbol]) / equity
                for symbol, qty in positions.items()
                if symbol in prices
            }
            if got:
                return got
        return {}

    def _live_book_weights(
        self, equity: float, raw_positions: list[dict[str, Any]]
    ) -> dict[str, float]:
        priced = self._priced_live_weights(equity, raw_positions)
        if priced:
            return priced
        if self._snapshot.last_got:
            return dict(self._snapshot.last_got)
        return dict(self._snapshot.last_combined)

    def live_cap_weights(
        self, equity: float, raw_positions: list[dict[str, Any]]
    ) -> dict[str, float]:
        with self._lock:
            priced = self._priced_live_weights(equity, raw_positions)
            if priced:
                return priced
            if self._snapshot.last_got:
                return dict(self._snapshot.last_got)
            return {}
```

In `utilization.from_supervisor`:

```python
    live_weights = None
    if live:
        try:
            account, positions = supervisor.live_book()
            equity = float(account.get("equity", 0))
            cash = float(account.get("cash", equity))
            live_weights = supervisor.live_cap_weights(equity, positions)
        except Exception:
            equity = None
            cash = None
            positions = None
    return summarize(
        ...
        last_got=live_weights or snapshot.last_got,
    )
```

- [ ] **Step 2: Help and README**

Insert `Caps LIMIT follows the same live book as Tighten. ` after `Tighten and Start paper flatten the same live book as Book. ` in `execution`, `halt_flatten`, `how_risk`, and `task_tighten`. README Operator after that same sentence.

- [ ] **Step 3: Run the new tests plus existing LIMIT locks**

```bash
PYTHONPATH=src python3 -m pytest \
  tests/alphastrategy/test_helptext.py::test_help_text_contains_required_phrases \
  tests/alphastrategy/test_api.py::test_status_live_limit_does_not_flatten \
  tests/alphastrategy/test_api.py::test_status_live_limit_without_last_got_uses_priced_book \
  tests/alphastrategy/test_api.py::test_status_live_limit_priced_book_wins_over_stale_last_got \
  tests/alphastrategy/test_risk.py::test_summarize_live_limit_from_marked_name \
  tests/alphastrategy/test_risk.py::test_from_supervisor_live_limit_ignores_last_combined \
  tests/alphastrategy/test_cli.py::test_status_prints_limit_on_stderr \
  -q
```

Expected: PASS.

- [ ] **Step 4: Commit**

```bash
git add src/alphastrategy/supervisor/loop.py src/alphastrategy/risk/utilization.py \
  src/alphastrategy/helptext.py README.md
git commit -m "feat: Caps LIMIT follows the same live book as Tighten"
```

---

### Task 3: Full suite

- [ ] **Step 1: Run**

```bash
PYTHONPATH=src python3 -m pytest tests/alphastrategy/ -q
```

Expected: all passed.

## Spec coverage

| Requirement | Task |
| --- | --- |
| Empty last_got still LIMIT from priced book | 1–2 |
| Priced book wins over stale last_got | 1–2 |
| last_combined does not LIMIT | 1 |
| Offline last_got LIMIT unchanged | 2 (CLI lock) |
| Help phrase | 1–2 |
| GET does not flatten | 1–2 |
