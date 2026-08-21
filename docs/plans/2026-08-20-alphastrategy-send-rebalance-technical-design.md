# Next-send Orders / rebalance Caps LIMIT Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans (this cycle chose executing-plans). Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Caps fail-color Orders / rebalance when a dry-run next send would flatten on that cap, and Clock Next says `flatten send` when `live_limit.kind` is send.

**Architecture:** Existing `_next_send_limit` already returns `max_orders_per_rebalance`. Add `#risk-cap-rebalance` like Order size. Clock Next branches on `kind === "send"`. GET does not flatten.

**Tech Stack:** Python 3.9+, Quiet cockpit HTML/CSS/JS, pytest, helptext, README.

**Requirements:** [`docs/requirements/2026-08-20-alphastrategy-send-rebalance-requirements.md`](../requirements/2026-08-20-alphastrategy-send-rebalance-requirements.md)

## Global Constraints

- Paper only. Five `#nav` screens. Locked tokens. No `window.confirm`. No live.
- `"Gross cap"` must not appear in assembled JS. Do not hardcode `Order size` or `Orders / rebalance` in JS.
- Caps stay four tiles. Keep `#risk-cap-order`.
- Heartbeat does not flatten. GET must not flatten.
- Keep `flatten · ` for book LIMIT. Keep `Next rebalance`.
- Tests: `PYTHONPATH=src python3 -m pytest tests/alphastrategy/ -q`.

## File map

- Modify: `src/alphastrategy/web/static/index.html`, `src/alphastrategy/web/static/styles.css`, `src/alphastrategy/web/static/js/paint-risk.js`, `src/alphastrategy/web/static/js/paint-portfolio.js`, `src/alphastrategy/helptext.py`, `README.md`
- Test: `tests/alphastrategy/test_api.py`, `tests/alphastrategy/test_risk.py`, `tests/alphastrategy/test_web_tokens.py`, `tests/alphastrategy/test_helptext.py`

---

### Task 1: Failing tests

- [ ] **Step 1: Write the failing tests**

`REQUIRED_PHRASES` add:

```python
    "Caps LIMIT follows a next send through Orders / rebalance",
    "Clock Next is flatten send while a next send will flatten",
```

In `test_api.py` after `test_status_live_limit_next_send_order_size`:

```python
def test_status_live_limit_next_send_orders_per_rebalance(api_stack):
    client, home, supervisor, broker = api_stack
    supervisor.set_policy({"max_orders_per_rebalance": 2})
    supervisor.snapshot.last_got = {}
    supervisor.snapshot.last_combined = {"AAA": 0.01, "BBB": 0.01, "CCC": 0.01}
    supervisor.snapshot.last_prices = {"AAA": 100.0, "BBB": 100.0, "CCC": 100.0}
    save_state(home.state_path(), supervisor.snapshot)
    broker.positions = {}
    close_all_before = broker.close_all_count
    body = client.get("/api/status").json()
    assert body["utilization"]["live_limit"]["reason"] == "max_orders_per_rebalance"
    assert body["utilization"]["live_limit"]["kind"] == "send"
    risk = client.get("/api/risk").json()
    assert risk["utilization"]["live_limit"]["reason"] == "max_orders_per_rebalance"
    assert broker.close_all_count == close_all_before
    assert supervisor.state.value != "stopped"
```

In `test_risk.py` after `test_from_supervisor_live_limit_next_send_order_size`:

```python
def test_from_supervisor_live_limit_next_send_orders_per_rebalance() -> None:
    from alphastrategy.risk.utilization import from_supervisor

    class Snap:
        orders_today = 0
        last_combined = {"AAA": 0.01, "BBB": 0.01, "CCC": 0.01}
        last_got = {}
        last_prices = {"AAA": 100.0, "BBB": 100.0, "CCC": 100.0}

    class Fake:
        snapshot = Snap()

        def spoken_policy(self):
            return replace(AccountPolicy.defaults(), max_orders_per_rebalance=2)

        def live_book(self):
            return {"equity": 10_000.0, "cash": 10_000.0}, []

        def live_cap_weights(self, equity, positions):
            del equity, positions
            return {}

    out = from_supervisor(Fake(), live=True)
    assert out["live_limit"]["reason"] == "max_orders_per_rebalance"
    assert out["live_limit"]["kind"] == "send"
```

Keep `test_from_supervisor_live_limit_ignores_last_combined`.

Web: `test_html_risk_glance_bands` assert `'id="risk-cap-rebalance"' in caps`. `test_js_paints_risk_caps_tiles` assert `risk-cap-rebalance` and `max_orders_per_rebalance`. `test_js_paints_risk_caps_live_limit` assert `markLimit` includes `max_orders_per_rebalance`. Add `#risk-cap-rebalance.fail` to `test_css_risk_cap_live_limit_fail_token` and `#risk-cap-rebalance.warn` to `test_css_risk_cap_spoken_warn_token`.

`test_js_clock_next_flatten_while_live_limit` add:

```python
    assert "flatten send · " in session
    assert 'kind === "send"' in session
```

Keep `assert "flatten · " in session`.

- [ ] **Step 2: Run the new tests and confirm they fail**

```bash
PYTHONPATH=src python3 -m pytest tests/alphastrategy/test_api.py::test_status_live_limit_next_send_orders_per_rebalance tests/alphastrategy/test_risk.py::test_from_supervisor_live_limit_next_send_orders_per_rebalance tests/alphastrategy/test_risk.py::test_from_supervisor_live_limit_ignores_last_combined tests/alphastrategy/test_web_tokens.py::test_html_risk_glance_bands tests/alphastrategy/test_web_tokens.py::test_js_paints_risk_caps_tiles tests/alphastrategy/test_web_tokens.py::test_js_paints_risk_caps_live_limit tests/alphastrategy/test_web_tokens.py::test_css_risk_cap_live_limit_fail_token tests/alphastrategy/test_web_tokens.py::test_css_risk_cap_spoken_warn_token tests/alphastrategy/test_web_tokens.py::test_js_clock_next_flatten_while_live_limit tests/alphastrategy/test_helptext.py::test_help_text_contains_required_phrases -q
```

- [ ] **Step 3: Commit tests and docs**

---

### Task 2: Implement

- [ ] **Step 4: Caps line**

`index.html` after `#risk-cap-order`:

```html
          <p id="risk-cap-rebalance" class="muted nums"></p>
```

`styles.css`: `#risk-cap-rebalance.warn` `#f59e0b`; `#risk-cap-rebalance.fail` `#ef4444`.

`paint-risk.js` `renderRiskCaps`: `#risk-cap-rebalance`; paint `policyLabel("max_orders_per_rebalance") + " " + String(...)`; `markTighter`; `markLimit(rebalanceEl, "max_orders_per_rebalance")`. Empty policy paints `—`. File ≤ 400 newlines. Do not put `Gross cap` or `Orders / rebalance` in JS.

- [ ] **Step 5: Clock Next**

In `renderSessionMetrics` live_limit branch:

```javascript
        const send = utilization().live_limit.kind === "send";
        kindEl.textContent = (send ? "flatten send · " : "flatten · ") + kind;
```

Keep `held · ` and `flat · `. `paint-portfolio.js` ≤ 400 newlines.

- [ ] **Step 6: Help and README**

`helptext.py`: add both phrases to `halt_flatten`, `how_risk`, `how_portfolio` (Clock Next after live-book flatten sentence).

README Operator: both after Caps LIMIT Order size. Keep `Next rebalance`. Keep four Caps tiles.

- [ ] **Step 7: Full suite**

```bash
PYTHONPATH=src python3 -m pytest tests/alphastrategy/ -q
```

- [ ] **Step 8: Commit, push, update PR**
