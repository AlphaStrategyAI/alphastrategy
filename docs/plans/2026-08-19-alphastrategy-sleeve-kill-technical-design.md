# Isolated Sleeve Kill Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** When last book and RTH clock make isolation clean, `kill_sleeve` reduces to `last_combined − that sleeve’s contribution` instead of flattening the whole paper account.

**Architecture:** Add a pure residual helper, then teach `Supervisor.kill_sleeve` to use last book + `plan_orders` or fall back to `_flatten_account`. No API/Web changes.

**Tech Stack:** Existing Supervisor, `plan_orders`, pytest FakeBroker.

**Requirements:** [`docs/requirements/2026-08-19-alphastrategy-sleeve-kill-requirements.md`](../requirements/2026-08-19-alphastrategy-sleeve-kill-requirements.md)

## Global Constraints

- Paper only. Supervisor is the only order placer.
- If isolation is not clean, whole-account flatten (existing `_flatten_account`).
- Account kill / SIGINT / limit breach unchanged.
- Tests never hit a real broker.

## File map

- Create: `src/alphastrategy/supervisor/residual.py` — `residual_book(combined, contribution) -> dict[str, float]`
- Modify: `src/alphastrategy/supervisor/loop.py` — `kill_sleeve`
- Test: `tests/alphastrategy/test_combine.py` or `tests/alphastrategy/test_residual.py`
- Test: `tests/alphastrategy/test_halt_flatten.py`
- Test: `tests/alphastrategy/test_e2e_mocked.py`

---

### Task 1: Residual book helper

**Files:**
- Create: `src/alphastrategy/supervisor/residual.py`
- Create: `tests/alphastrategy/test_residual.py`

**Interfaces:**
- Produces: `residual_book(combined: dict[str, float], contribution: dict[str, float]) -> dict[str, float]`

- [ ] **Step 1: Write the failing tests**

```python
from alphastrategy.supervisor.residual import residual_book


def test_residual_subtracts_killed_sleeve_and_drops_zeros():
    combined = {"AAPL": 0.15, "MSFT": 0.15}
    killed = {"AAPL": 0.15}
    assert residual_book(combined, killed) == {"MSFT": 0.15}


def test_residual_overlapping_name_keeps_other_sleeve_share():
    combined = {"AAPL": 0.20}
    killed = {"AAPL": 0.10}
    assert residual_book(combined, killed) == {"AAPL": 0.10}


def test_residual_drops_negative_noise():
    assert residual_book({"AAPL": 0.1}, {"AAPL": 0.1}) == {}
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `PYTHONPATH=src python3 -m pytest tests/alphastrategy/test_residual.py -v`

Expected: FAIL import.

- [ ] **Step 3: Minimal implementation**

```python
EPS = 1e-12


def residual_book(combined: dict[str, float], contribution: dict[str, float]) -> dict[str, float]:
    assets = set(combined) | set(contribution)
    out: dict[str, float] = {}
    for asset in assets:
        weight = combined.get(asset, 0.0) - contribution.get(asset, 0.0)
        if weight > EPS:
            out[asset] = weight
    return out
```

- [ ] **Step 4: Run tests — expect PASS**

- [ ] **Step 5: Commit** `feat: residual book after sleeve kill`

---

### Task 2: Supervisor isolated kill

**Files:**
- Modify: `src/alphastrategy/supervisor/loop.py`
- Test: `tests/alphastrategy/test_halt_flatten.py`

**Interfaces:**
- Consumes: `residual_book`, `plan_orders`, snapshot last book, `broker.get_clock`
- Produces: `kill_sleeve` isolates when spec §2 holds; else `_flatten_account`

- [ ] **Step 1: Write failing tests**

Keep `test_kill_sleeve_calls_close_all_once` (no last book → still close_all).

Add:

```python
def test_kill_sleeve_isolates_when_last_book_exists(tmp_path: Path):
    open_time = datetime(2024, 1, 31, 14, 30)
    session_close = datetime(2024, 1, 31, 21, 0)
    broker = FakeBroker(
        is_open=False,
        next_open=open_time,
        next_close=session_close,
        now=open_time,
    )
    evaluators = {"asb_a": {"AAPL": 1.0}, "asb_b": {"MSFT": 1.0}}
    supervisor = _make_supervisor(tmp_path, broker, evaluators=evaluators)
    supervisor.start_sleeve("asb_a", 0.15)
    supervisor.start_sleeve("asb_b", 0.15)
    broker.set_session_open(
        open_time=open_time,
        session_close=session_close,
        now=open_time + timedelta(minutes=3),
    )
    supervisor.tick()
    assert "AAPL" in broker.positions
    assert "MSFT" in broker.positions
    close_all_before = broker.close_all_count
    supervisor.kill_sleeve("asb_a")
    assert broker.close_all_count == close_all_before
    assert supervisor.state != SupervisorState.STOPPED
    assert supervisor.snapshot.sleeves["asb_a"] == 0.0
    assert supervisor.snapshot.sleeves["asb_b"] == 0.15
    assert broker.positions.get("AAPL", 0.0) == 0.0
    assert broker.positions.get("MSFT", 0.0) > 0
    assert "asb_a" in supervisor.snapshot.stopped
```

- [ ] **Step 2: Run to verify FAIL** (`close_all_count` increments today).

- [ ] **Step 3: Implement `kill_sleeve`**

After zeroing allocation + stopped:

```python
def _isolation_ready(self, bundle_id: str) -> bool:
    contribution = self._snapshot.last_sleeve_contribution.get(bundle_id) or {}
    combined = self._snapshot.last_combined
    prices = self._snapshot.last_prices
    if not contribution or not combined or not prices:
        return False
    try:
        clock = self._broker.get_clock()
    except Exception:
        return False
    if not clock.get("is_open"):
        return False
    symbols = set(_positions_map(self._broker.list_positions())) | set(combined) | set(contribution)
    return all(symbol in prices for symbol in symbols)
```

If not ready: `_flatten_account(); audit kill isolated=false`.

If ready: `residual = residual_book(...)`; `cancel_open_orders`; `plan_orders`; `place_order` each; update last book; audit `isolated=true`. On exception, `_flatten_account` + `isolated=false`.

Do not set STOPPED on the success path.

- [ ] **Step 4: Run `test_halt_flatten.py` — expect PASS** (including existing `test_kill_sleeve_calls_close_all_once`).

- [ ] **Step 5: Commit** `feat: isolate sleeve kill when last book is clean`

---

### Task 3: E2E two-sleeve kill

**Files:**
- Modify: `tests/alphastrategy/test_e2e_mocked.py`

- [ ] **Step 1: Write test** using golden bundle as sleeve A (AAPL+MSFT 50/50) plus a second imported dir `asb_extra` with evaluator `{"TSLA": 1.0}` — actually e2e uses weight_fn from DSL. Simpler: use Supervisor evaluators in a dedicated e2e that still goes through HTTP kill.

Use FakeBroker + two bundle dirs + evaluators (same as unit test) then `POST /api/paper/kill` with `bundle_id`.

```python
def test_api_kill_sleeve_isolates(tmp_path):
    # two sleeves, open rebalance, POST /api/paper/kill {"bundle_id": "asb_a"}
    # close_all_count unchanged, GET /api/bundles asb_a in stopped, asb_b still paper
```

Can live in `test_api.py` as integration instead of e2e. Put it in `test_api.py` AND a short e2e in `test_e2e_mocked.py` that uses evaluators (not golden DSL) — one integration test in `test_api.py` is enough if e2e golden cannot easily be two strategies.

Prefer **`test_api.py`** integration: start two sleeves via API, persist last book on snapshot (or tick rebalance), POST kill.

Api_stack FakeBroker.tick needs session setup. Mirror halt_flatten test inside api_stack:

After `supervisor.start_sleeve` twice, set broker open, `supervisor.tick()`, then `client.post("/api/paper/kill", {"bundle_id": "asb_x"})`.

api_stack already has asb_x AAPL and asb_y MSFT evaluators.

- [ ] **Step 2–4:** TDD then `PYTHONPATH=src python3 -m pytest tests/alphastrategy/ -q` all pass.

- [ ] **Step 5: Commit** `test: API isolated sleeve kill`

---

## Self-review

§2 isolation gates → Task 2 `_isolation_ready`. Residual math → Task 1. Fallback flatten → existing test. Two-sleeve proof → Task 2+3. No Web/API schema change except existing kill route.
