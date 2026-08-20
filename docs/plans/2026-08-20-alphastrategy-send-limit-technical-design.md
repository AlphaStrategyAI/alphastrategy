# Next-send Caps LIMIT Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans (this cycle chose executing-plans). Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Caps LIMIT / Clock Next flatten / CLI LIMIT warn when a dry-run of `plan_orders` against last combined would flatten through Order size, without flattening on GET.

**Architecture:** `from_supervisor(live=True)` keeps book `check_book`. If that is null, `_next_send_limit` calls `plan_orders` with last combined, live qty, last prices. `#risk-cap-order` is a Caps line beside Long only.

**Tech Stack:** Python 3.9+, Quiet cockpit HTML/CSS/JS, pytest, helptext, README.

**Requirements:** [`docs/requirements/2026-08-20-alphastrategy-send-limit-requirements.md`](../requirements/2026-08-20-alphastrategy-send-limit-requirements.md)

## Global Constraints

- Paper only. Five `#nav` screens. Locked tokens. No `window.confirm`. No live.
- `"Gross cap"` must not appear in assembled JS.
- Caps stay four tiles. Order size is not a fifth tile.
- Heartbeat does not flatten. GET status/portfolio/risk must not flatten.
- Do not feed `_place_batch` from `live_book()`.
- Do not use `last_combined` for **book** `check_book`.
- Tests: `PYTHONPATH=src python3 -m pytest tests/alphastrategy/ -q`.

## File map

- Modify: `src/alphastrategy/risk/utilization.py`, `src/alphastrategy/web/static/index.html`, `src/alphastrategy/web/static/styles.css`, `src/alphastrategy/web/static/js/paint-risk.js`, `src/alphastrategy/helptext.py`, `README.md`
- Test: `tests/alphastrategy/test_api.py`, `tests/alphastrategy/test_risk.py`, `tests/alphastrategy/test_web_tokens.py`, `tests/alphastrategy/test_helptext.py`

---

### Task 1: Failing tests

- [ ] **Step 1: Write the failing tests**

`REQUIRED_PHRASES` add:

```python
    "Caps LIMIT follows a next send through Order size",
```

In `tests/alphastrategy/test_api.py` after `test_status_live_limit_priced_book_wins_over_stale_last_got`:

```python
def test_status_live_limit_next_send_order_size(api_stack):
    client, home, supervisor, broker = api_stack
    supervisor.set_policy({"max_order_notional_frac": 0.10})
    supervisor.snapshot.last_got = {}
    supervisor.snapshot.last_combined = {"AAPL": 0.18}
    supervisor.snapshot.last_prices = {"AAPL": 100.0}
    save_state(home.state_path(), supervisor.snapshot)
    broker.positions = {}
    close_all_before = broker.close_all_count
    body = client.get("/api/status").json()
    assert body["utilization"]["live_limit"]["reason"] == "max_order_notional_frac"
    risk = client.get("/api/risk").json()
    assert risk["utilization"]["live_limit"]["reason"] == "max_order_notional_frac"
    assert broker.close_all_count == close_all_before
    assert supervisor.state.value != "stopped"
```

In `tests/alphastrategy/test_risk.py` after `test_from_supervisor_live_limit_ignores_last_combined`:

```python
def test_from_supervisor_live_limit_next_send_order_size() -> None:
    from alphastrategy.risk.utilization import from_supervisor

    class Snap:
        orders_today = 0
        last_combined = {"AAPL": 0.18}
        last_got = {}
        last_prices = {"AAPL": 100.0}

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
```

Keep `test_from_supervisor_live_limit_ignores_last_combined` (empty `last_prices` must stay null).

Web: `test_html_risk_glance_bands` assert `'id="risk-cap-order"' in caps`. `test_js_paints_risk_caps_tiles` assert `risk-cap-order` and `max_order_notional_frac`. `test_js_paints_risk_caps_live_limit` assert `markLimit` path includes `max_order_notional_frac`. Add `#risk-cap-order.fail` to `test_css_risk_cap_live_limit_fail_token`. Add `#risk-cap-order.warn` CSS test or fold into an existing warn test.

- [ ] **Step 2: Run the new tests and confirm they fail**

```bash
PYTHONPATH=src python3 -m pytest tests/alphastrategy/test_api.py::test_status_live_limit_next_send_order_size tests/alphastrategy/test_risk.py::test_from_supervisor_live_limit_next_send_order_size tests/alphastrategy/test_risk.py::test_from_supervisor_live_limit_ignores_last_combined tests/alphastrategy/test_web_tokens.py::test_html_risk_glance_bands tests/alphastrategy/test_web_tokens.py::test_js_paints_risk_caps_tiles tests/alphastrategy/test_web_tokens.py::test_js_paints_risk_caps_live_limit tests/alphastrategy/test_web_tokens.py::test_css_risk_cap_live_limit_fail_token tests/alphastrategy/test_helptext.py::test_help_text_contains_required_phrases -q
```

- [ ] **Step 3: Commit tests and docs**

---

### Task 2: Implement

- [ ] **Step 4: `_next_send_limit` in utilization.py**

Import `plan_orders`. Implement `_next_send_limit` as in the requirements. `from_supervisor`:

```python
    out = summarize(...)
    if live and out.get("live_limit") is None:
        out["live_limit"] = _next_send_limit(
            policy=supervisor.spoken_policy(),
            combined=snapshot.last_combined,
            prices=getattr(snapshot, "last_prices", None),
            positions=positions,
            equity=equity,
            orders_today=snapshot.orders_today,
        )
    return out
```

Do not flatten. Catch only `FlattenRequested` inside `_next_send_limit`; let other errors return None.

- [ ] **Step 5: Cockpit**

`index.html` Caps, after `#risk-cap-long`:

```html
          <p id="risk-cap-order" class="muted nums"></p>
```

`styles.css`: `#risk-cap-order.warn { color: #f59e0b; }` and `#risk-cap-order.fail { color: #ef4444; }`

`paint-risk.js` `renderRiskCaps`: read `#risk-cap-order`; paint `policyLabel("max_order_notional_frac") + " " + fmtPct(...)`; `markTighter`; `markLimit(orderEl, "max_order_notional_frac")`. Do not put `Gross cap` or the letters `Order size` in JS. File ≤ 400 newlines.

- [ ] **Step 6: Help and README**

`helptext.py`: add `Caps LIMIT follows a next send through Order size. ` to `halt_flatten`, `how_risk` (after Caps LIMIT same live book), `task_tighten`.

README Operator: same sentence after Caps LIMIT same live book. Keep `Next rebalance`. Keep four Caps tiles.

- [ ] **Step 7: Full suite**

```bash
PYTHONPATH=src python3 -m pytest tests/alphastrategy/ -q
```

- [ ] **Step 8: Commit, push, update PR**
