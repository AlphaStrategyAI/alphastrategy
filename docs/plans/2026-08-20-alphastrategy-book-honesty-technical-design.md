# Book Honesty Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans (this cycle chose executing-plans). Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Show wanted names with no fill on Positions, put Drift on Book, clear the last book on flatten, and let Start paper leave STOPPED without a catch-up rebalance.

**Architecture:** `_enrich_positions` unions `last_combined`. `_flatten_account` zeros last maps and sleeves. `start_sleeve` calls the same idle transition as halt resume when state is STOPPED. Book glance adds a Drift tile painted in `paint-portfolio.js`.

**Tech Stack:** Supervisor snapshot, control-plane JSON, Quiet cockpit HTML/CSS/JS, `helptext.py`, pytest.

**Requirements:** [`docs/requirements/2026-08-20-alphastrategy-book-honesty-requirements.md`](../requirements/2026-08-20-alphastrategy-book-honesty-requirements.md)

## Global Constraints

- Paper only. Five `#nav` screens. Locked tokens. No `window.confirm`. No live. No ghost fills.
- Resume stays halt-only. Do not leave `FLATTENING` via Start paper.
- Keep `#glance-book`, `#first-run`, `data-go-screen`. Each JS part ≤ 400 lines.
- Tests: `PYTHONPATH=src python3 -m pytest tests/alphastrategy/ -q`.

## File map

- Modify: `src/alphastrategy/api/handlers.py` (`_enrich_positions`)
- Modify: `src/alphastrategy/supervisor/loop.py` (`_flatten_account`, `start_sleeve`)
- Modify: `index.html`, `styles.css` (Drift tile; fail color on `#metric-drift`)
- Modify: `js/paint-portfolio.js` (`renderBookDrift`)
- Modify: `helptext.py`, `README.md`
- Test: `tests/alphastrategy/test_api.py`, `test_halt_flatten.py`, `test_web_tokens.py`, `test_helptext.py`, `test_e2e_mocked.py`

---

### Task 1: Failing tests

- [ ] **Step 1: API wanted-only row**

In `tests/alphastrategy/test_api.py`, after `test_portfolio_includes_contribution_and_position_weight`:

```python
def test_portfolio_includes_wanted_name_with_no_fill(api_stack):
    client, home, supervisor, broker = api_stack
    supervisor.snapshot.last_combined = {"AAPL": 0.4, "MSFT": 0.2}
    supervisor.snapshot.last_prices = {"AAPL": 100.0, "MSFT": 200.0}
    save_state(home.state_path(), supervisor.snapshot)
    broker.positions = {"AAPL": 10.0}
    broker.equity = 10_000.0
    body = client.get("/api/portfolio").json()
    msft = next(item for item in body["positions"] if item["symbol"] == "MSFT")
    assert float(msft["qty"]) == 0.0
    assert msft["wanted"] == pytest.approx(0.2)
    assert msft["weight"] == pytest.approx(0.0)
```

- [ ] **Step 2: Flatten clears last book; Start paper leaves STOPPED**

In `tests/alphastrategy/test_halt_flatten.py`:

```python
def test_flatten_clears_last_book_and_zeros_sleeves(tmp_path: Path):
    broker = FakeBroker(is_open=True)
    broker.positions["AAPL"] = 10.0
    supervisor = _make_supervisor(tmp_path, broker)
    supervisor.start_sleeve("asb_test", 0.15)
    supervisor.snapshot.last_combined = {"AAPL": 0.15}
    supervisor.snapshot.last_got = {"AAPL": 0.10}
    supervisor.kill_account()
    snap = supervisor.snapshot
    assert snap.state == SupervisorState.STOPPED
    assert snap.last_combined == {}
    assert snap.last_got == {}
    assert snap.last_sleeve_weights == {}
    assert snap.last_sleeve_contribution == {}
    assert snap.last_prices == {}
    assert snap.sleeves.get("asb_test", 0) == 0.0
    assert "asb_test" in snap.stopped


def test_start_sleeve_after_flatten_leaves_stopped_without_catchup(tmp_path: Path):
    open_time = datetime(2024, 1, 31, 14, 30)
    session_close = datetime(2024, 1, 31, 21, 0)
    broker = FakeBroker(
        is_open=True,
        next_open=open_time,
        next_close=session_close,
        now=open_time + timedelta(minutes=3),
    )
    supervisor = _make_supervisor(tmp_path, broker)
    supervisor.start_sleeve("asb_test", 0.15)
    supervisor.kill_account()
    assert supervisor.state == SupervisorState.STOPPED
    orders_after_kill = list(broker.orders)
    supervisor.start_sleeve("asb_test", 0.15)
    assert supervisor.state == SupervisorState.IDLE_IN_SESSION
    supervisor.tick()
    assert broker.orders == orders_after_kill
```

- [ ] **Step 3: HTML Drift + help phrases**

In `test_web_tokens.py` `test_html_first_run_and_book_column` (or append):

```python
    assert 'id="metric-drift"' in html_text
    book = html_text[
        html_text.find('id="glance-book"') : html_text.find('id="glance-risk"')
    ]
    assert 'id="metric-drift"' in book
    assert "metrics-4" in book
```

Add `test_js_renders_book_drift`:

```python
def test_js_renders_book_drift(js_text: str) -> None:
    assert "function renderBookDrift" in js_text
    assert "metric-drift" in js_text
    assert "window.confirm" not in js_text
```

`REQUIRED_PHRASES` add `"Book Drift"` and `"Start paper after flatten"`.

e2e `test_control_plane_serves_help`: `assert 'id="metric-drift"' in html`.
e2e flatten test: after kill, GET `/api/portfolio` `last_combined == {}`.

- [ ] **Step 4: Run — FAIL.** Commit tests.

---

### Task 2: Implementation

- [ ] **Step 5: `_enrich_positions`**

After existing rows, for each `symbol, weight` in sorted `combined` not already in the list, if `abs(weight) > 0`, append `{symbol, qty: 0, notional: 0, weight: 0, wanted: float(weight)}`.

- [ ] **Step 6: `_flatten_account` success path** (after `STOPPED`):

```python
        self._snapshot.last_combined = {}
        self._snapshot.last_got = {}
        self._snapshot.last_sleeve_weights = {}
        self._snapshot.last_sleeve_contribution = {}
        self._snapshot.last_prices = {}
        for bundle_id in list(self._snapshot.sleeves):
            self._snapshot.sleeves[bundle_id] = 0.0
            if bundle_id not in self._snapshot.stopped:
                self._snapshot.stopped.append(bundle_id)
```

- [ ] **Step 7: `start_sleeve`** at the start of the locked body, after validation of allocation, **before** writing the sleeve:

If `self._snapshot.state == SupervisorState.STOPPED`, set `prime_clock_after_resume = True` and enter idle from clock (copy the try/except from `resume`). Do not do this for `HALTED` or `FLATTENING`.

- [ ] **Step 8: HTML/CSS/JS**

Inside `#glance-book`, change `metrics-3` to `metrics-4` and append:

```html
          <div class="metric">
            <div class="metric-label">Drift</div>
            <div id="metric-drift" class="metric-value">—</div>
            <div id="metric-drift-sub" class="metric-sub">—</div>
            <div id="metric-drift-bar" class="util-track hidden" aria-hidden="true"></div>
          </div>
```

CSS: `#metric-drift.fail { color: #ef4444; }`

`renderBookDrift(positions, equity)` in `paint-portfolio.js`: count names whose `|wanted−weight| * equity >= max(1, 0.001 * equity)` when wanted is a number. Paint count, max gap via `fmtPct`, `paintUtilTrack`. Call from `renderPortfolio`.

- [ ] **Step 9: Help + README** as requirements §6.

- [ ] **Step 10: Full suite PASS. Commit.**

---

## Spec coverage

Wanted-only rows, flatten clears book, Start paper leaves STOPPED, Book Drift, help — tasked. No placeholders.
