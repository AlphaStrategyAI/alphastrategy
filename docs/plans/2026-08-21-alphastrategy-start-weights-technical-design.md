# Start paper seeds last sleeve weights Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans (this cycle chose executing-plans). Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Start paper evaluates DSL on the write path and persists `last_sleeve_weights` for that sleeve when missing, so Caps / Positions Next / Headroom can dry-run the next send without waiting for the next RTH rebalance.

**Architecture:** `start_sleeve` calls `_seed_last_sleeve_weights` after the `paper_start` audit. Same `_sleeve_weights` as rebalance. Skip when weights already exist, allocation is 0, or broker is None. Halt (do not flatten) on eval failure. Do not place. Do not rewrite last combined.

**Tech Stack:** Python 3.9+, pytest, helptext, README.

**Requirements:** [`docs/requirements/2026-08-21-alphastrategy-start-weights-requirements.md`](../requirements/2026-08-21-alphastrategy-start-weights-requirements.md)

## Global Constraints

- Paper only. Five `#nav` screens. Locked tokens. No live.
- Do not evaluate DSL on GET. Do not flatten on GET. Do not place on Start (except existing live-book flatten).
- Wanted stays last combined. Book Drift stays last wanted vs last fill.
- Keep `Caps LIMIT waits when a paper sleeve has no last weights` for injected incomplete state.
- Keep `Next rebalance`. Keep Cash composition labels.
- Tests: `PYTHONPATH=src python3 -m pytest tests/alphastrategy/ -q`.

## File map

- Modify: `src/alphastrategy/supervisor/loop.py`, `src/alphastrategy/helptext.py`, `README.md`
- Test: `tests/alphastrategy/test_api.py`, `tests/alphastrategy/test_halt_flatten.py`, `tests/alphastrategy/test_helptext.py`

---

### Task 1: Failing tests

**Files:**
- Modify: `tests/alphastrategy/test_api.py`
- Modify: `tests/alphastrategy/test_halt_flatten.py`
- Modify: `tests/alphastrategy/test_helptext.py`

**Interfaces:**
- Consumes: `Supervisor.start_sleeve`; `_sleeve_weights`; existing evaluators
- Produces: `last_sleeve_weights[id]` after Start when missing; help phrase `Start paper seeds last sleeve weights`

- [ ] **Step 1: Write the failing tests**

`REQUIRED_PHRASES` add after `Caps LIMIT waits when a paper sleeve has no last weights`:

```python
    "Start paper seeds last sleeve weights",
```

In `test_halt_flatten.py` after `test_start_sleeve_clears_stopped`:

```python
def test_start_sleeve_seeds_last_sleeve_weights(tmp_path: Path):
    broker = FakeBroker()
    supervisor = _make_supervisor(tmp_path, broker)
    close_all_before = broker.close_all_count
    orders_before = list(broker.orders)
    held = supervisor.start_sleeve("asb_test", 0.18)
    assert held is False
    assert supervisor.snapshot.last_sleeve_weights["asb_test"]["AAPL"] == pytest.approx(1.0)
    assert supervisor.snapshot.last_combined == {}
    assert broker.close_all_count == close_all_before
    assert broker.orders == orders_before
    assert supervisor.state.value != "stopped"


def test_start_sleeve_does_not_reseed_existing_last_weights(tmp_path: Path):
    calls = {"n": 0}

    def weight_fn(bundle_id: str) -> dict[str, float]:
        calls["n"] += 1
        return {"MSFT": 1.0}

    home = AlphaStrategyHome(root=tmp_path)
    home.bundle_dir("asb_test").mkdir(parents=True, exist_ok=True)
    broker = FakeBroker()
    supervisor = Supervisor(
        home=home,
        broker=broker,
        evaluators={"asb_test": {"AAPL": 1.0}},
        weight_fn=weight_fn,
    )
    supervisor.snapshot.last_sleeve_weights = {"asb_test": {"AAPL": 1.0}}
    supervisor.start_sleeve("asb_test", 0.18)
    assert calls["n"] == 0
    assert supervisor.snapshot.last_sleeve_weights["asb_test"]["AAPL"] == pytest.approx(1.0)
    assert broker.close_all_count == 0


def test_start_sleeve_halts_when_sleeve_has_no_evaluator(tmp_path: Path):
    home = AlphaStrategyHome(root=tmp_path)
    home.bundle_dir("asb_x").mkdir(parents=True, exist_ok=True)
    broker = FakeBroker()
    supervisor = Supervisor(home=home, broker=broker, evaluators={})
    close_all_before = broker.close_all_count
    held = supervisor.start_sleeve("asb_x", 0.18)
    assert held is True
    assert supervisor.state == SupervisorState.HALTED
    assert not (supervisor.snapshot.last_sleeve_weights.get("asb_x") or {})
    assert broker.close_all_count == close_all_before
    assert supervisor.snapshot.sleeves["asb_x"] == pytest.approx(0.18)
```

Need `Supervisor` imported in `test_halt_flatten.py` if not already.

In `test_api.py` after `test_status_live_limit_unknown_when_paper_sleeve_has_no_last_weights`:

```python
def test_start_paper_seeds_last_sleeve_weights_for_next_send(api_stack):
    client, home, supervisor, broker = api_stack
    supervisor.set_policy({"max_order_notional_frac": 0.10})
    supervisor.snapshot.last_got = {}
    supervisor.snapshot.last_combined = {"AAPL": 0.18}
    supervisor.snapshot.last_sleeve_weights = {}
    supervisor.snapshot.sleeves = {}
    supervisor.snapshot.last_prices = {"AAPL": 100.0, "MSFT": 100.0}
    save_state(home.state_path(), supervisor.snapshot)
    broker.positions = {}
    close_all_before = broker.close_all_count
    started = client.post("/api/paper/start", json={"bundle_id": "asb_y", "allocation": 0.18})
    assert started.status == 200
    body = client.get("/api/status").json()
    assert body["utilization"]["live_limit"]["kind"] == "send"
    assert body["utilization"]["live_limit"]["reason"] == "max_order_notional_frac"
    portfolio = client.get("/api/portfolio").json()
    msft = next(item for item in portfolio["positions"] if item["symbol"] == "MSFT")
    assert msft["next"] == pytest.approx(0.18)
    aapl = next(item for item in portfolio["positions"] if item["symbol"] == "AAPL")
    assert aapl["wanted"] == pytest.approx(0.18)
    assert aapl.get("next") is None
    assert supervisor.snapshot.last_sleeve_weights["asb_y"]["MSFT"] == pytest.approx(1.0)
    assert supervisor.snapshot.last_combined == {"AAPL": 0.18}
    assert broker.close_all_count == close_all_before
    assert supervisor.state.value != "stopped"
```

Keep the unknown inject tests. They must still pass (no Start).

- [ ] **Step 2: Run the new tests and confirm they fail**

```bash
PYTHONPATH=src python3 -m pytest tests/alphastrategy/test_halt_flatten.py::test_start_sleeve_seeds_last_sleeve_weights tests/alphastrategy/test_halt_flatten.py::test_start_sleeve_does_not_reseed_existing_last_weights tests/alphastrategy/test_halt_flatten.py::test_start_sleeve_halts_when_sleeve_has_no_evaluator tests/alphastrategy/test_api.py::test_start_paper_seeds_last_sleeve_weights_for_next_send tests/alphastrategy/test_api.py::test_status_live_limit_unknown_when_paper_sleeve_has_no_last_weights tests/alphastrategy/test_helptext.py::test_help_text_contains_required_phrases -q
```

Expected: seed / reseed / halt-no-evaluator / POST-start / help fail. Unknown inject lock still passes.

- [ ] **Step 3: Commit tests and docs**

```bash
git add docs/requirements/2026-08-21-alphastrategy-start-weights-requirements.md docs/plans/2026-08-21-alphastrategy-start-weights-technical-design.md tests/alphastrategy/test_api.py tests/alphastrategy/test_halt_flatten.py tests/alphastrategy/test_helptext.py
git commit -m "test: Start paper seeds last sleeve weights"
```

---

### Task 2: Implement

**Files:**
- Modify: `src/alphastrategy/supervisor/loop.py`
- Modify: `src/alphastrategy/helptext.py`
- Modify: `README.md`

**Interfaces:**
- Consumes: `_sleeve_weights(bundle_id) -> dict[str, float]`; `_validate_weights`; `_halt`
- Produces: `_seed_last_sleeve_weights(bundle_id: str, allocation: float) -> None`

- [ ] **Step 4: Supervisor**

In `start_sleeve`, after the `paper_start` audit and **before** `_persist()` / `_enforce_live_book()`:

```python
            self._audit("paper_start", bundle_id=bundle_id, allocation=allocation)
            self._seed_last_sleeve_weights(bundle_id, allocation)
            self._persist()
            self._enforce_live_book()
            return self._snapshot.state == SupervisorState.HALTED
```

Add next to `_sleeve_weights`:

```python
    def _seed_last_sleeve_weights(self, bundle_id: str, allocation: float) -> None:
        if allocation <= 0 or self._broker is None:
            return
        stored = self._snapshot.last_sleeve_weights.get(bundle_id)
        if isinstance(stored, dict) and stored:
            return
        try:
            weights = self._sleeve_weights(bundle_id)
            self._validate_weights(weights)
        except (HaltRequested, IllegalWeights) as exc:
            self._halt(str(exc))
            return
        self._snapshot.last_sleeve_weights[bundle_id] = dict(weights)
```

Do not update `last_combined`. Do not call `_place_batch`. Do not `check_book` the next send. Do not catch `FlattenRequested` here.

- [ ] **Step 5: Help and README**

`helptext.py`: add `Start paper seeds last sleeve weights. ` to `execution` (after Caps LIMIT waits), `halt_flatten` (after Caps LIMIT waits), `how_run` (after Start paper is a second explicit action).

README Operator: after `Caps LIMIT waits when a paper sleeve has no last weights.`, add `Start paper seeds last sleeve weights.` Keep wait-weights Clock Next sentence. Keep `Next rebalance`.

- [ ] **Step 6: Full suite**

```bash
PYTHONPATH=src python3 -m pytest tests/alphastrategy/ -q
```

- [ ] **Step 7: Commit, push, update PR**

```bash
git add src/alphastrategy/supervisor/loop.py src/alphastrategy/helptext.py README.md
git commit -m "feat: Start paper seeds last sleeve weights"
```
