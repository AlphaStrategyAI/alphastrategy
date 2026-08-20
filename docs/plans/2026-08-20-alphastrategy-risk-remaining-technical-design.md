# Remaining Flatten Budgets Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans (this cycle chose executing-plans). Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Expose name-count and daily-order remaining flatten budgets plus cash-versus-invested composition on status, CLI, Portfolio, and Risk from one shared `summarize` function.

**Architecture:** Pure `alphastrategy.risk.utilization.summarize` builds a JSON-ready dict. Handlers and offline CLI call it. The Quiet cockpit paints tiles from `status.utilization`. Supervisor flatten math does not change.

**Tech Stack:** Python 3.9+, stdlib HTTP, static HTML/CSS/JS, pytest.

**Requirements:** [`docs/requirements/2026-08-20-alphastrategy-risk-remaining-requirements.md`](../requirements/2026-08-20-alphastrategy-risk-remaining-requirements.md)

## Global Constraints

- Paper only. Five `#nav` screens. Locked tokens `#0b0e14` `#11151d` `#2a3142` `#e5e9f0` `#5c6573` `#9ba3b4` `#10b981` `#f59e0b` `#ef4444`.
- No `window.confirm`. No live. No WebSockets. No chart libraries.
- Tests: `PYTHONPATH=src python3 -m pytest tests/alphastrategy/ -q`. Never hit a real broker.
- Do not change `check_book` or `plan_orders` thresholds.

## File map

- Create: `src/alphastrategy/risk/utilization.py`
- Modify: `src/alphastrategy/risk/__init__.py`
- Modify: `src/alphastrategy/api/handlers.py`
- Modify: `src/alphastrategy/cli/main.py`
- Modify: `src/alphastrategy/web/static/index.html`, `styles.css`, `app.js`
- Modify: `src/alphastrategy/helptext.py`, `README.md`
- Test: `tests/alphastrategy/test_risk.py` (utilization cases)
- Test: `tests/alphastrategy/test_api.py`, `test_cli.py`, `test_web_tokens.py`, `test_helptext.py`, `test_e2e_mocked.py`

---

### Task 1: `summarize` pure function

**Files:**
- Create: `src/alphastrategy/risk/utilization.py`
- Modify: `src/alphastrategy/risk/__init__.py`
- Test: `tests/alphastrategy/test_risk.py`

**Interfaces:**
- Consumes: `AccountPolicy`
- Produces: `summarize(...) -> dict[str, Any]` with keys `names`, `max_names`, `orders_today`, `max_orders_per_day`, `cash_weight`, `invested_weight`, `target_cash_weight`, `max_gross`

- [ ] **Step 1: Write the failing tests** at the end of `tests/alphastrategy/test_risk.py`

```python
from alphastrategy.risk.utilization import summarize


def test_summarize_counts_live_nonzero_positions() -> None:
    policy = AccountPolicy.defaults()
    out = summarize(
        policy=policy,
        orders_today=3,
        equity=10_000.0,
        cash=4_000.0,
        positions=[{"symbol": "AAPL", "qty": "10"}, {"symbol": "MSFT", "qty": "0"}],
        last_combined={"AAPL": 0.6},
        last_got={"AAPL": 0.55, "MSFT": 0.1},
    )
    assert out["names"] == 1
    assert out["max_names"] == 50
    assert out["orders_today"] == 3
    assert out["max_orders_per_day"] == 200
    assert out["cash_weight"] == pytest.approx(0.4)
    assert out["invested_weight"] == pytest.approx(0.6)
    assert out["target_cash_weight"] == pytest.approx(0.4)
    assert out["max_gross"] == 1.0


def test_summarize_falls_back_to_last_got_when_no_positions() -> None:
    out = summarize(
        policy=AccountPolicy.defaults(),
        orders_today=0,
        last_got={"AAPL": 0.2, "MSFT": 0.0, "GOOG": 0.1},
    )
    assert out["names"] == 2
    assert out["cash_weight"] is None
    assert out["invested_weight"] is None
    assert out["target_cash_weight"] is None


def test_summarize_falls_back_to_last_combined_when_got_empty() -> None:
    out = summarize(
        policy=AccountPolicy.defaults(),
        orders_today=0,
        last_combined={"AAPL": 0.25, "MSFT": 0.25},
    )
    assert out["names"] == 2
    assert out["target_cash_weight"] == pytest.approx(0.5)


def test_summarize_empty_book_is_zeros() -> None:
    out = summarize(policy=AccountPolicy.defaults(), orders_today=0)
    assert out["names"] == 0
    assert out["orders_today"] == 0
    assert out["cash_weight"] is None
    assert out["target_cash_weight"] is None


def test_summarize_zero_equity_cash_weight_is_zero() -> None:
    out = summarize(
        policy=AccountPolicy.defaults(),
        orders_today=0,
        equity=0.0,
        cash=0.0,
        positions=[],
    )
    assert out["cash_weight"] == 0.0
    assert out["invested_weight"] == 0.0
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `PYTHONPATH=src python3 -m pytest tests/alphastrategy/test_risk.py::test_summarize_counts_live_nonzero_positions tests/alphastrategy/test_risk.py::test_summarize_falls_back_to_last_got_when_no_positions tests/alphastrategy/test_risk.py::test_summarize_falls_back_to_last_combined_when_got_empty tests/alphastrategy/test_risk.py::test_summarize_empty_book_is_zeros tests/alphastrategy/test_risk.py::test_summarize_zero_equity_cash_weight_is_zero -q`

Expected: FAIL with `ModuleNotFoundError: No module named 'alphastrategy.risk.utilization'` (or import error for `summarize`).

- [ ] **Step 3: Write minimal implementation**

`src/alphastrategy/risk/utilization.py`:

```python
from __future__ import annotations

from typing import Any

from alphastrategy.risk.policy import AccountPolicy

_EPS = 1e-12


def _nonzero_weight_count(weights: dict[str, float] | None) -> int:
    if not weights:
        return 0
    return sum(1 for value in weights.values() if abs(float(value)) > _EPS)


def summarize(
    *,
    policy: AccountPolicy,
    orders_today: int,
    equity: float | None = None,
    cash: float | None = None,
    positions: list[dict[str, Any]] | None = None,
    last_combined: dict[str, float] | None = None,
    last_got: dict[str, float] | None = None,
) -> dict[str, Any]:
    names = 0
    if positions:
        names = sum(1 for pos in positions if abs(float(pos.get("qty") or 0)) > _EPS)
    elif last_got:
        names = _nonzero_weight_count(last_got)
    else:
        names = _nonzero_weight_count(last_combined)

    cash_weight: float | None
    invested_weight: float | None
    if equity is None or cash is None:
        cash_weight = None
        invested_weight = None
    elif equity > 0:
        cash_weight = float(cash) / float(equity)
        invested_weight = 1.0 - cash_weight
    else:
        cash_weight = 0.0
        invested_weight = 0.0

    target_cash_weight: float | None = None
    if last_combined:
        target_cash_weight = max(0.0, 1.0 - sum(float(v) for v in last_combined.values()))

    return {
        "names": int(names),
        "max_names": int(policy.max_names),
        "orders_today": int(orders_today),
        "max_orders_per_day": int(policy.max_orders_per_day),
        "cash_weight": cash_weight,
        "invested_weight": invested_weight,
        "target_cash_weight": target_cash_weight,
        "max_gross": float(policy.max_gross),
    }
```

Export `summarize` from `src/alphastrategy/risk/__init__.py`.

- [ ] **Step 4: Run tests to verify they pass**

Run: same pytest command as Step 2.

Expected: PASS

- [ ] **Step 5: Commit** after Task 1 is green (this cycle batches commits per the cloud loop: docs first, then implementation).

---

### Task 2: Status, Risk API, and offline CLI

**Files:**
- Modify: `src/alphastrategy/api/handlers.py`
- Modify: `src/alphastrategy/cli/main.py`
- Test: `tests/alphastrategy/test_api.py`, `tests/alphastrategy/test_cli.py`, `tests/alphastrategy/test_e2e_mocked.py`

**Interfaces:**
- Consumes: `summarize`, `Supervisor.snapshot`, `Supervisor.policy`, `broker.get_account` / `list_positions` when reachable
- Produces: `utilization` key on `GET /api/status`, `GET /api/risk`, and CLI `status` JSON

- [ ] **Step 1: Failing tests**

In `tests/alphastrategy/test_api.py`:

```python
def test_status_and_risk_include_utilization(api_stack) -> None:
    client, _home, supervisor, broker = api_stack
    broker.positions = {"AAPL": 4.0, "MSFT": 2.0}
    supervisor._snapshot.orders_today = 7
    status = client.get("/api/status").json()
    util = status["utilization"]
    assert util["names"] == 2
    assert util["orders_today"] == 7
    assert util["max_names"] == supervisor.policy.max_names
    assert util["max_orders_per_day"] == supervisor.policy.max_orders_per_day
    assert util["cash_weight"] == pytest.approx(1.0)
    risk = client.get("/api/risk").json()
    assert risk["utilization"]["names"] == 2
    assert risk["utilization"]["orders_today"] == 7
```

In `tests/alphastrategy/test_cli.py` inside `test_status_prints_json`, add:

```python
    assert "utilization" in payload
    assert payload["utilization"]["orders_today"] == 0
    assert payload["utilization"]["cash_weight"] is None
```

In `tests/alphastrategy/test_e2e_mocked.py` after the existing `/api/status` assertions in `test_e2e_operator_desk_countdown_and_stopped`, add:

```python
        assert "utilization" in status
        assert "names" in status["utilization"]
        assert "orders_today" in status["utilization"]
```

- [ ] **Step 2: Run those tests — FAIL** (`utilization` missing).

- [ ] **Step 3: Implementation**

Add `_utilization_payload(supervisor: Supervisor, *, live: bool) -> dict` in `handlers.py`:

```python
from alphastrategy.risk.utilization import summarize


def _utilization_payload(supervisor: Supervisor, *, live: bool) -> dict[str, Any]:
    snapshot = supervisor.snapshot
    equity = None
    cash = None
    positions = None
    if live:
        try:
            account = supervisor.broker.get_account()
            equity = float(account.get("equity", 0))
            cash = float(account.get("cash", equity))
            positions = supervisor.broker.list_positions()
        except Exception:
            equity = None
            cash = None
            positions = None
    return summarize(
        policy=supervisor.policy,
        orders_today=snapshot.orders_today,
        equity=equity,
        cash=cash,
        positions=positions,
        last_combined=snapshot.last_combined,
        last_got=snapshot.last_got,
    )
```

`handle_get_status`: add `"utilization": _utilization_payload(supervisor, live=True)`.

`handle_get_risk`: add `"utilization": _utilization_payload(supervisor, live=True)`.

`_cmd_status` offline branch: `"utilization": _utilization_payload(supervisor, live=False)`.

- [ ] **Step 4: Run tests — PASS**

- [ ] **Step 5: Commit** (batched with remaining tasks in this cycle).

---

### Task 3: Quiet cockpit tiles

**Files:**
- Modify: `src/alphastrategy/web/static/index.html`, `styles.css`, `app.js`
- Test: `tests/alphastrategy/test_web_tokens.py`

- [ ] **Step 1: Failing tests** in `test_web_tokens.py`

```python
def test_html_remaining_budget_mounts(html_text: str) -> None:
    assert 'id="metric-names"' in html_text
    assert 'id="metric-names-cap"' in html_text
    assert 'id="metric-names-bar"' in html_text
    assert 'id="metric-orders"' in html_text
    assert 'id="metric-orders-cap"' in html_text
    assert 'id="metric-orders-bar"' in html_text
    assert 'id="metric-cash-bar"' in html_text
    assert 'id="metric-cash-sub"' in html_text
    assert 'id="risk-utilization"' in html_text
    nav = re.search(r'<nav id="nav"[^>]*>(.*?)</nav>', html_text, re.DOTALL)
    screens = re.findall(r'data-screen="([^"]+)"', nav.group(1))
    assert screens == ["portfolio", "strategies", "run", "activity", "risk"]


def test_js_remaining_budget_painters(js_text: str) -> None:
    assert "function renderRemainingBudgets" in js_text
    assert "function renderCashComposition" in js_text
    assert "function paintUtilTrack" in js_text
    assert "window.confirm" not in js_text
```

- [ ] **Step 2: Run those tests — FAIL** (missing ids / functions).

- [ ] **Step 3: Implementation**

HTML — after the Cash metric, keep dollar value and add sub + bar; after Gross (or Session), add Names and Orders cards. Place Names and Orders after Gross so flatten budgets sit together:

```html
        <div class="metric">
          <div class="metric-label">Cash</div>
          <div id="metric-cash" class="metric-value">—</div>
          <div id="metric-cash-sub" class="metric-sub">—</div>
          <div id="metric-cash-bar" class="cash-track hidden" aria-hidden="true"></div>
        </div>
```

(Keep existing Cash card; insert sub + bar inside it.)

After Gross:

```html
        <div class="metric">
          <div class="metric-label">Names</div>
          <div id="metric-names" class="metric-value">—</div>
          <div id="metric-names-cap" class="metric-sub">—</div>
          <div id="metric-names-bar" class="util-track hidden" aria-hidden="true"></div>
        </div>
        <div class="metric">
          <div class="metric-label">Orders today</div>
          <div id="metric-orders" class="metric-value">—</div>
          <div id="metric-orders-cap" class="metric-sub">—</div>
          <div id="metric-orders-bar" class="util-track hidden" aria-hidden="true"></div>
        </div>
```

Risk sticky bar:

```html
        <div id="risk-utilization" class="risk-caps nums"></div>
```

immediately after `#risk-account-caps`.

CSS: hide `#metric-cash-bar.hidden`; `.cash-track` same geometry as `.util-track`; `.cash-invested` fill `#10b981`. Reuse `.wg-wanted` for the target marker inside `.cash-track`.

JS — extract `paintUtilTrack(bar, used, cap, label)` from Gross (90% warn / 100% fail). `renderRemainingBudgets` reads `state.status.utilization`. `renderCashComposition` paints invested fill + optional marker. `renderRisk` fills `#risk-utilization` with Names / Orders / Cash rows (do not skip this when the tighten form is dirty; utilization is read-only).

Call `renderRemainingBudgets` and `renderCashComposition` from `renderPortfolio`.

- [ ] **Step 4: Run `test_web_tokens.py` — PASS**

---

### Task 4: Help, README, e2e GET `/`

**Files:**
- Modify: `src/alphastrategy/helptext.py`, `README.md`
- Test: `tests/alphastrategy/test_helptext.py`, `tests/alphastrategy/test_e2e_mocked.py`

- [ ] **Step 1: Failing tests**

Add `"utilization"` (or `"Orders today"`) to `REQUIRED_PHRASES` / cockpit body assertions.

In `test_e2e_mocked.py` GET `/` test, assert `metric-names` in the HTML body.

- [ ] **Step 2: FAIL**

- [ ] **Step 3:** Cockpit help sentence: Names and Orders today are remaining flatten budgets; Cash shows invested versus residual against the last combined target; `status` includes `utilization`. README Quiet cockpit / Operator: same, one sentence.

- [ ] **Step 4:** `PYTHONPATH=src python3 -m pytest tests/alphastrategy/ -q` — all pass.

---

## Spec coverage

| Requirement | Task |
| --- | --- |
| `summarize` fields and fallbacks | 1 |
| Status / Risk / CLI `utilization` | 2 |
| Names, Orders, Cash composition, Risk row | 3 |
| Help / README | 4 |
| e2e GET `/` and status keys | 2, 4 |
| Flatten math unchanged | no edits to `check.py` / `orders.py` |
