# Headroom Target cash follows current allocations Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans (this cycle chose executing-plans). Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Headroom Target cash, Book cash-composition target, and Sleeves contribution follow `combine(current allocations, last sleeve weights)` when Caps LIMIT can dry-run that next send, while Positions Wanted stays last combined.

**Architecture:** `from_supervisor` keeps summarize’s last-combined residual as `last_target_cash_weight` and overlays `target_cash_weight` from `_next_send_combined` when `_next_send_ready`. `sleeve_contribution_glance(snapshot)` overwrites positive sleeves from last weights × current alloc. Headroom paints `last {fmtPct}` on `#risk-head-target-sub` when the two residuals differ.

**Tech Stack:** Python 3.9+, pytest, cockpit HTML/JS, helptext, README.

**Requirements:** [`docs/requirements/2026-08-21-alphastrategy-target-cash-requirements.md`](../requirements/2026-08-21-alphastrategy-target-cash-requirements.md)

## Global Constraints

- Paper only. Five `#nav` screens. Locked tokens. No live.
- Do not evaluate DSL on GET. Do not flatten on GET. Do not place.
- Keep Caps four tiles. Keep Headroom four tiles.
- Positions Wanted stays last combined. Keep `colspan='8'`.
- Cash composition labels stay `invested … · cash … · target cash …`.
- Keep wait-weights unknown / empty-prices last_combined 0.40 → `live_limit` null.
- `paint-portfolio.js` and `paint-rails.js` stay ≤ 400 lines.
- Tests: `PYTHONPATH=src python3 -m pytest tests/alphastrategy/ -q`.

## File map

- Modify: `src/alphastrategy/risk/utilization.py`, `src/alphastrategy/api/handlers.py`, `src/alphastrategy/web/static/index.html`, `src/alphastrategy/web/static/js/paint-rails.js`, `src/alphastrategy/helptext.py`, `README.md`
- Test: `tests/alphastrategy/test_api.py`, `tests/alphastrategy/test_risk.py`, `tests/alphastrategy/test_helptext.py`, `tests/alphastrategy/test_web_tokens.py`

---

### Task 1: Failing tests

- [ ] **Step 1: Write the failing tests**

`REQUIRED_PHRASES` add after the wait-weights Caps phrase:

```python
    "Headroom Target cash follows current allocations on last sleeve weights",
    "Sleeves contribution follows current allocations on last sleeve weights",
```

In `test_api.py` after `test_status_live_limit_next_send_follows_current_allocation`:

```python
def test_status_target_cash_follows_current_allocation(api_stack):
    client, home, supervisor, broker = api_stack
    supervisor.snapshot.last_got = {}
    supervisor.snapshot.last_combined = {"AAPL": 0.10}
    supervisor.snapshot.last_sleeve_weights = {"asb_x": {"AAPL": 1.0}}
    supervisor.snapshot.sleeves = {"asb_x": 0.18}
    supervisor.snapshot.last_prices = {"AAPL": 100.0}
    save_state(home.state_path(), supervisor.snapshot)
    broker.positions = {}
    close_all_before = broker.close_all_count
    body = client.get("/api/status").json()
    assert body["utilization"]["target_cash_weight"] == pytest.approx(0.82)
    assert body["utilization"]["last_target_cash_weight"] == pytest.approx(0.90)
    risk = client.get("/api/risk").json()
    assert risk["utilization"]["target_cash_weight"] == pytest.approx(0.82)
    assert risk["utilization"]["last_target_cash_weight"] == pytest.approx(0.90)
    assert broker.close_all_count == close_all_before
    assert supervisor.state.value != "stopped"


def test_portfolio_contribution_follows_current_allocation(api_stack):
    client, home, supervisor, broker = api_stack
    supervisor.snapshot.last_got = {}
    supervisor.snapshot.last_combined = {"AAPL": 0.10}
    supervisor.snapshot.last_sleeve_weights = {"asb_x": {"AAPL": 1.0}}
    supervisor.snapshot.last_sleeve_contribution = {"asb_x": {"AAPL": 0.10}}
    supervisor.snapshot.sleeves = {"asb_x": 0.18}
    supervisor.snapshot.last_prices = {"AAPL": 100.0}
    save_state(home.state_path(), supervisor.snapshot)
    broker.positions = {}
    close_all_before = broker.close_all_count
    body = client.get("/api/portfolio").json()
    assert body["sleeve_contribution"]["asb_x"]["AAPL"] == pytest.approx(0.18)
    pos = next(item for item in body["positions"] if item["symbol"] == "AAPL")
    assert pos["wanted"] == pytest.approx(0.10)
    assert broker.close_all_count == close_all_before
    assert supervisor.state.value != "stopped"
```

In `test_risk.py` after `test_from_supervisor_live_limit_next_send_follows_current_allocation`:

```python
def test_from_supervisor_target_cash_follows_current_allocation() -> None:
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
            return AccountPolicy.defaults()

        def live_book(self):
            return {"equity": 10_000.0, "cash": 10_000.0}, []

        def live_cap_weights(self, equity, positions):
            del equity, positions
            return {}

    out = from_supervisor(Fake(), live=True)
    assert out["target_cash_weight"] == pytest.approx(0.82)
    assert out["last_target_cash_weight"] == pytest.approx(0.90)
```

In `test_web_tokens.py` `test_js_paints_risk_headroom_tiles` add:

```python
    assert "risk-head-target-sub" in paint
    assert "last_target_cash_weight" in paint
```

And after that test, HTML lock — extend the existing Headroom HTML test that already asserts `id="risk-head-target"`:

```python
    assert 'id="risk-head-target-sub"' in head
```

Keep `test_summarize_falls_back_to_last_combined_when_got_empty`.
Keep `test_portfolio_includes_contribution_and_position_weight`.
Keep `test_status_live_limit_unknown_when_paper_sleeve_has_no_last_weights`.

- [ ] **Step 2: Run the new tests and confirm they fail**

```bash
PYTHONPATH=src python3 -m pytest tests/alphastrategy/test_api.py::test_status_target_cash_follows_current_allocation tests/alphastrategy/test_api.py::test_portfolio_contribution_follows_current_allocation tests/alphastrategy/test_risk.py::test_from_supervisor_target_cash_follows_current_allocation tests/alphastrategy/test_api.py::test_portfolio_includes_contribution_and_position_weight tests/alphastrategy/test_risk.py::test_summarize_falls_back_to_last_combined_when_got_empty tests/alphastrategy/test_helptext.py::test_help_text_contains_required_phrases tests/alphastrategy/test_web_tokens.py::test_js_paints_risk_headroom_tiles -q
```

Expected: new target/contribution tests fail (`target_cash_weight` 0.90 / contribution 0.10). Help phrases missing. Headroom sub missing. Existing summarize / last-contribution 0.4 tests still pass.

- [ ] **Step 3: Commit tests and docs**

---

### Task 2: Implement

- [ ] **Step 4: utilization.py**

After `_next_send_ready`:

```python
def _cash_residual(weights: dict[str, float] | None) -> float | None:
    if not weights:
        return None
    return max(0.0, 1.0 - sum(float(v) for v in weights.values()))


def sleeve_contribution_glance(snapshot: Any) -> dict[str, dict[str, float]]:
    last = getattr(snapshot, "last_sleeve_contribution", None) or {}
    out: dict[str, dict[str, float]] = {
        str(bundle_id): {str(asset): float(weight) for asset, weight in weights.items()}
        for bundle_id, weights in last.items()
        if isinstance(weights, dict)
    }
    if not _next_send_ready(snapshot):
        return out
    sleeve_weights = getattr(snapshot, "last_sleeve_weights", None) or {}
    sleeves = getattr(snapshot, "sleeves", None) or {}
    for bundle_id, raw_alloc in sleeves.items():
        try:
            alloc = float(raw_alloc or 0)
        except (TypeError, ValueError):
            continue
        if alloc <= 0:
            continue
        weights = sleeve_weights.get(bundle_id)
        if not isinstance(weights, dict) or not weights:
            continue
        out[str(bundle_id)] = {
            str(asset): alloc * float(weight) for asset, weight in weights.items()
        }
    return out
```

`from_supervisor` after `summarize(...)`:

```python
    out["last_target_cash_weight"] = out.get("target_cash_weight")
    if _next_send_ready(snapshot):
        nxt = _next_send_combined(snapshot)
        residual = _cash_residual(nxt)
        if residual is not None:
            out["target_cash_weight"] = residual
```

Do this for live and offline. Do not flatten. Do not call DSL.

- [ ] **Step 5: handlers.py**

```python
from alphastrategy.risk.utilization import from_supervisor, sleeve_contribution_glance
```

`handle_get_portfolio`:

```python
        "sleeve_contribution": sleeve_contribution_glance(snapshot),
```

- [ ] **Step 6: HTML + paint-rails.js**

`index.html` Target cash metric:

```html
            <div class="metric">
              <div class="metric-label">Target cash</div>
              <div id="risk-head-target" class="metric-value">—</div>
              <div id="risk-head-target-sub" class="metric-sub">—</div>
            </div>
```

`renderRiskUtilization` after setting `risk-head-target`:

```javascript
    const targetSub = document.getElementById("risk-head-target-sub");
    if (targetSub) {
      const lastTarget = util.last_target_cash_weight;
      const differs =
        lastTarget != null &&
        lastTarget !== undefined &&
        target != null &&
        target !== undefined &&
        Math.abs(Number(lastTarget) - Number(target)) > 1e-9;
      targetSub.textContent = differs ? "last " + fmtPct(lastTarget) : "—";
    }
```

Do not change Cash composition label words. File ≤ 400 lines.

- [ ] **Step 7: Help and README**

`helptext.py`: add `Headroom Target cash follows current allocations on last sleeve weights. ` to `execution` (after Caps LIMIT current allocations), `how_risk` (after Headroom four tiles). Add `Sleeves contribution follows current allocations on last sleeve weights. ` to `execution` (same block) and `how_portfolio` (after Positions Book column).

README Operator: both sentences after Caps LIMIT current allocations. Keep `Next rebalance`.

- [ ] **Step 8: Full suite**

```bash
PYTHONPATH=src python3 -m pytest tests/alphastrategy/ -q
```

- [ ] **Step 9: Commit, push, update PR**
