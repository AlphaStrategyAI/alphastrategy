# Execution Honesty Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task (this cycle explicitly chose executing-plans). Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Enforce the daily paper-order budget, record wanted vs got on every rebalance, and make a flattened desk visually and in JSON unmistakably flat.

**Architecture:** Extend `plan_orders` with a daily budget check. Persist `orders_date` / `orders_today` / `last_got` on the snapshot. Always compute `got` after rebalance orders and audit it. Expose `flattened` on `/api/status` and a fail-red cockpit banner. Document halt ≠ flatten in README.

**Tech Stack:** Existing Supervisor, pytest, static Quiet cockpit. Tests mock the broker.

**Requirements:** [`docs/requirements/2026-08-20-alphastrategy-execution-honesty-requirements.md`](../requirements/2026-08-20-alphastrategy-execution-honesty-requirements.md)

## Global Constraints

- Package `alphastrategy`, paper-only walls unchanged.
- Do not grow `src/openstrategy/`.
- Limit breach still flattens the whole account.
- Halt banner stays amber; flatten banner is fail red `#ef4444`.
- Tests: `PYTHONPATH=src python3 -m pytest tests/alphastrategy/ -q`. Never place a real order.

## File map

- Modify: `src/alphastrategy/supervisor/orders.py` — daily budget in `plan_orders`
- Modify: `src/alphastrategy/supervisor/state.py` — `orders_date`, `orders_today`, `last_got`
- Modify: `src/alphastrategy/supervisor/loop.py` — count orders, persist `last_got`, audit wanted/got
- Modify: `src/alphastrategy/api/handlers.py` — `flattened`, position `wanted`
- Modify: `src/alphastrategy/cli/main.py` — offline status fields
- Modify: `src/alphastrategy/web/static/{index.html,app.js}`
- Modify: `README.md`
- Test: `tests/alphastrategy/test_orders.py`, `test_halt_flatten.py`, `test_api.py`, `test_web_tokens.py`, `test_e2e_mocked.py`, `test_cli.py`, `test_packaging.py`

---

### Task 1: Daily order budget in plan_orders

**Files:**
- Modify: `src/alphastrategy/supervisor/orders.py`
- Test: `tests/alphastrategy/test_orders.py`

**Interfaces:**
- Consumes: existing `plan_orders(combined, positions, prices, equity, policy)`
- Produces: `plan_orders(..., orders_already_today: int = 0)`. If `orders_already_today + len(plans) > policy.max_orders_per_day`, raise `FlattenRequested("account")` after the per-rebalance count check. Default `0` keeps current tests passing except the new one.

- [ ] **Step 1: Write the failing test**

Append to `tests/alphastrategy/test_orders.py`:

```python
def test_plan_orders_raises_flatten_on_daily_order_budget():
    combined = {"AAPL": 0.10, "MSFT": 0.10}
    positions = {}
    prices = {"AAPL": 100.0, "MSFT": 100.0}
    equity = 10_000.0
    policy = replace(AccountPolicy.defaults(), max_orders_per_day=1)

    with pytest.raises(FlattenRequested) as exc:
        plan_orders(
            combined,
            positions,
            prices,
            equity,
            policy,
            orders_already_today=0,
        )
    assert exc.value.scope == "account"


def test_plan_orders_daily_budget_allows_remaining_room():
    combined = {"AAPL": 0.10}
    positions = {}
    prices = {"AAPL": 100.0}
    equity = 10_000.0
    policy = replace(AccountPolicy.defaults(), max_orders_per_day=2)
    plans = plan_orders(
        combined, positions, prices, equity, policy, orders_already_today=1
    )
    assert plans == [OrderPlan(symbol="AAPL", qty=10, side="buy")]
```

- [ ] **Step 2: Run to verify FAIL**

Run: `PYTHONPATH=src python3 -m pytest tests/alphastrategy/test_orders.py::test_plan_orders_raises_flatten_on_daily_order_budget -v`

Expected: FAIL (`orders_already_today` unexpected keyword or no flatten).

- [ ] **Step 3: Minimal implementation**

In `plan_orders`, add `orders_already_today: int = 0`. After the `max_orders_per_rebalance` check:

```python
    if orders_already_today + len(plans) > policy.max_orders_per_day:
        raise FlattenRequested("account")
```

- [ ] **Step 4: Run `tests/alphastrategy/test_orders.py -q` — PASS**

- [ ] **Step 5: Commit** `feat: enforce daily paper order budget in plan_orders`

---

### Task 2: Persist counters, last_got, and audit wanted/got

**Files:**
- Modify: `src/alphastrategy/supervisor/state.py`
- Modify: `src/alphastrategy/supervisor/loop.py`
- Test: `tests/alphastrategy/test_halt_flatten.py`

**Interfaces:**
- Produces: snapshot fields `orders_date: str | None`, `orders_today: int`, `last_got: dict[str, float]`
- `_rebalance` and `_isolate_sleeve` pass `orders_already_today` (reset if session date ≠ `orders_date`) into `plan_orders`, then add `len(plans)` to `orders_today`
- Always compute `got` after the rebalance order loop; set `last_got`; audit `rebalance` with `wanted` and `got`; run `deviations_after` without the all-filled gate

- [ ] **Step 1: Write failing tests**

```python
def test_rebalance_counts_orders_today_and_audits_wanted_got(tmp_path: Path):
    open_time = datetime(2024, 1, 31, 14, 30)
    session_close = datetime(2024, 1, 31, 21, 0)
    broker = FakeBroker(
        is_open=False,
        next_open=open_time,
        next_close=session_close,
        now=open_time,
    )
    supervisor = _make_supervisor(tmp_path, broker)
    supervisor.start_sleeve("asb_test", 0.15)
    _trigger_open_rebalance(tmp_path, broker, supervisor)
    assert supervisor.snapshot.orders_today == len(broker.orders)
    assert supervisor.snapshot.orders_date == "2024-01-31"
    assert "AAPL" in supervisor.snapshot.last_got
    events = [
        json.loads(line)
        for line in (tmp_path / "audit.jsonl").read_text(encoding="utf-8").splitlines()
    ]
    rebalances = [e for e in events if e["event"] == "rebalance"]
    assert rebalances
    assert "wanted" in rebalances[-1]
    assert "got" in rebalances[-1]


def test_daily_order_budget_flattens_without_overflow_batch(tmp_path: Path):
    open_time = datetime(2024, 1, 31, 14, 30)
    session_close = datetime(2024, 1, 31, 21, 0)
    broker = FakeBroker(
        is_open=False,
        next_open=open_time,
        next_close=session_close,
        now=open_time,
    )
    policy = replace(AccountPolicy.defaults(), max_orders_per_day=0)
    supervisor = _make_supervisor(tmp_path, broker, policy=policy)
    supervisor.start_sleeve("asb_test", 0.15)
    _trigger_open_rebalance(tmp_path, broker, supervisor)
    assert broker.close_all_called is True
    assert supervisor.state == SupervisorState.STOPPED
    assert broker.orders == []
```

Use the existing `_trigger_open_rebalance` helper in that file.

- [ ] **Step 2: Run to verify FAIL** (`orders_today` missing).

- [ ] **Step 3: Implementation**

`SupervisorSnapshot` + `from_dict` defaults: `orders_date=None`, `orders_today=0`, `last_got={}`.

Add `_session_order_budget(self, session_date: str) -> int` that resets the counter when the date changes and returns `orders_today`.

`_rebalance`: `session_date = cur.next_close.date().isoformat()` before `plan_orders`; `already = self._session_order_budget(session_date)`; pass into `plan_orders`. After placing, `self._snapshot.orders_today += len(plans)`.

Replace the `if all_orders_filled:` block with always:

```python
        positions_after = _positions_map(self._broker.list_positions())
        got = {
            symbol: (qty * prices[symbol]) / equity
            for symbol, qty in positions_after.items()
            if symbol in prices and equity > 0
        }
        self._snapshot.last_got = dict(got)
        for deviation in deviations_after(combined, got, equity, prices):
            self._audit("execution_deviation", **deviation)
        ...
        self._audit(
            "rebalance",
            session_event=event,
            orders=len(plans),
            wanted=dict(combined),
            got=dict(got),
        )
```

`_isolate_sleeve`: same budget check via `plan_orders(..., orders_already_today=...)` using clock `next_close` date from `get_clock()`. Increment after placing.

- [ ] **Step 4: Run `test_halt_flatten.py` + `test_e2e_mocked.py` — PASS** (partial-fill deviation test still finds execution_deviation).

- [ ] **Step 5: Commit** `feat: persist daily order count and rebalance wanted vs got`

---

### Task 3: API flattened flag and position wanted

**Files:**
- Modify: `src/alphastrategy/api/handlers.py`
- Modify: `src/alphastrategy/cli/main.py`
- Test: `tests/alphastrategy/test_api.py`, `tests/alphastrategy/test_cli.py`

**Interfaces:**
- `GET /api/status` adds `flattened` bool
- `_enrich_positions` adds `wanted` from `snapshot.last_combined`
- CLI offline status includes `last_rebalance_event` and `flattened`

- [ ] **Step 1: Failing tests**

In `test_api.py`:

```python
def test_status_flattened_false_by_default(api_client):
    body = api_client.get("/api/status").json()
    assert body["flattened"] is False


def test_status_flattened_true_after_account_kill(api_stack):
    client, _home, supervisor, _broker = api_stack
    supervisor.kill_account()
    body = client.get("/api/status").json()
    assert body["state"] == "stopped"
    assert body["flattened"] is True


def test_portfolio_position_includes_wanted_weight(api_stack):
    client, home, supervisor, broker = api_stack
    supervisor.snapshot.last_combined = {"AAPL": 0.15}
    supervisor.snapshot.last_prices = {"AAPL": 100.0}
    save_state(home.state_path(), supervisor.snapshot)
    broker.positions = {"AAPL": 10.0}
    pos = next(p for p in client.get("/api/portfolio").json()["positions"] if p["symbol"] == "AAPL")
    assert pos["wanted"] == pytest.approx(0.15)
    assert pos["weight"] == pytest.approx(0.1)
```

CLI: read `tests/alphastrategy/test_cli.py` for the status helper and add that offline JSON includes `flattened` and `last_rebalance_event`.

- [ ] **Step 2: Run to FAIL**

- [ ] **Step 3: Implementation**

`handle_get_status`: `"flattened": snapshot.state in (SupervisorState.FLATTENING, SupervisorState.STOPPED)`.

`_enrich_positions(..., last_combined)`: if symbol in last_combined, `item["wanted"] = last_combined[symbol]`.

CLI `_cmd_status` offline payload add `last_rebalance_event` and `flattened`.

- [ ] **Step 4: PASS `test_api.py` `test_cli.py`**

- [ ] **Step 5: Commit** `feat: expose flattened status and wanted weights`

---

### Task 4: Quiet cockpit flatten banner + wanted column + README

**Files:**
- Modify: `src/alphastrategy/web/static/index.html`, `app.js`
- Modify: `README.md`
- Test: `tests/alphastrategy/test_web_tokens.py`, `test_packaging.py`, `test_e2e_mocked.py`

- [ ] **Step 1: Failing tests**

```python
def test_html_has_flatten_banner_and_wanted_column(html_text: str) -> None:
    assert 'id="flatten-banner"' in html_text
    assert "Wanted" in html_text
    assert "Got" in html_text


def test_js_renders_flatten_banner(js_text: str) -> None:
    assert "flatten-banner" in js_text
    assert "flattened" in js_text
    assert "pos.wanted" in js_text or "wanted" in js_text
```

`test_packaging.py`:

```python
    assert "halt" in lower
    assert "flatten" in lower
```

E2E after `kill_account` in a small test or extend `test_v1_done_path`: GET `/api/status` `flattened` is true; GET `/` contains `flatten-banner`.

- [ ] **Step 2: FAIL then implement**

HTML: `#flatten-banner` after halt banner. Positions thead: Symbol, Qty, Notional, Wanted, Got.

JS `renderBanners`: if flattened/stopped/flattening, show flatten banner `FLAT: paper account flattened`. Positions cells: wanted `fmtPct`, got uses `weight`. Empty colspan 5.

README **Operator** section with the five bullets from the spec.

Activity `eventSummary` for rebalance: include `wanted`/`got` key counts if present.

- [ ] **Step 3: Full suite** `PYTHONPATH=src python3 -m pytest tests/alphastrategy/ -q`

- [ ] **Step 4: Commit** `feat: flatten banner, wanted vs got column, README operator notes`

---

## Self-review

Daily cap §2 → Task 1–2. Wanted/got §3 → Task 2–4. Flatten banner §4 → Task 3–4. README §5 → Task 4. No VWAP/live.
