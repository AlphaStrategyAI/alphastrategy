# Positions Next follows current allocations Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans (this cycle chose executing-plans). Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Portfolio Positions grow a Next column from `combine(current allocations, last sleeve weights)` so the home book matches Caps LIMIT / Headroom / Sleeves, while Wanted stays last combined.

**Architecture:** `next_send_combined_glance(snapshot)` returns None when not ready. `_enrich_positions` stamps `next` and unions next-only names. Cockpit paints Next after Wanted with halt-warn color when it differs from Wanted.

**Tech Stack:** Python 3.9+, pytest, cockpit HTML/CSS/JS, helptext, README.

**Requirements:** [`docs/requirements/2026-08-21-alphastrategy-positions-next-requirements.md`](../requirements/2026-08-21-alphastrategy-positions-next-requirements.md)

## Global Constraints

- Paper only. Five `#nav` screens. Locked tokens. No live.
- Do not evaluate DSL on GET. Do not flatten on GET. Do not place.
- Wanted stays last combined. Book Drift stays last wanted vs last fill.
- Positions glance stays Rows / Wanted / Got / At cap.
- Keep `Next rebalance`. Keep Cash composition labels.
- `paint-portfolio.js` and `paint-rails.js` stay ≤ 400 lines.
- Tests: `PYTHONPATH=src python3 -m pytest tests/alphastrategy/ -q`.

## File map

- Modify: `src/alphastrategy/risk/utilization.py`, `src/alphastrategy/api/handlers.py`, `src/alphastrategy/web/static/index.html`, `src/alphastrategy/web/static/styles.css`, `src/alphastrategy/web/static/js/paint-rails.js`, `src/alphastrategy/web/static/js/paint-portfolio.js`, `src/alphastrategy/helptext.py`, `README.md`
- Test: `tests/alphastrategy/test_api.py`, `tests/alphastrategy/test_helptext.py`, `tests/alphastrategy/test_web_tokens.py`

---

### Task 1: Failing tests

- [ ] **Step 1: Write the failing tests**

`REQUIRED_PHRASES` add:

```python
    "Positions Next follows current allocations on last sleeve weights",
```

In `test_api.py` after `test_portfolio_contribution_follows_current_allocation`:

```python
def test_portfolio_next_follows_current_allocation(api_stack):
    client, home, supervisor, broker = api_stack
    supervisor.snapshot.last_got = {}
    supervisor.snapshot.last_combined = {"AAPL": 0.10}
    supervisor.snapshot.last_sleeve_weights = {"asb_x": {"AAPL": 1.0}}
    supervisor.snapshot.sleeves = {"asb_x": 0.18}
    supervisor.snapshot.last_prices = {"AAPL": 100.0}
    save_state(home.state_path(), supervisor.snapshot)
    broker.positions = {}
    close_all_before = broker.close_all_count
    body = client.get("/api/portfolio").json()
    pos = next(item for item in body["positions"] if item["symbol"] == "AAPL")
    assert pos["wanted"] == pytest.approx(0.10)
    assert pos["next"] == pytest.approx(0.18)
    assert broker.close_all_count == close_all_before
    assert supervisor.state.value != "stopped"


def test_portfolio_omits_next_when_paper_sleeve_has_no_last_weights(api_stack):
    client, home, supervisor, broker = api_stack
    supervisor.snapshot.last_got = {}
    supervisor.snapshot.last_combined = {"AAPL": 0.18}
    supervisor.snapshot.last_sleeve_weights = {}
    supervisor.snapshot.sleeves = {"asb_y": 0.18}
    supervisor.snapshot.last_prices = {"AAPL": 100.0}
    save_state(home.state_path(), supervisor.snapshot)
    broker.positions = {}
    body = client.get("/api/portfolio").json()
    pos = next(item for item in body["positions"] if item["symbol"] == "AAPL")
    assert pos["wanted"] == pytest.approx(0.18)
    assert pos.get("next") is None
    assert broker.close_all_count == broker.close_all_count


def test_portfolio_includes_next_only_name(api_stack):
    client, home, supervisor, broker = api_stack
    supervisor.snapshot.last_got = {}
    supervisor.snapshot.last_combined = {"AAPL": 0.10}
    supervisor.snapshot.last_sleeve_weights = {"asb_x": {"AAPL": 0.5, "MSFT": 0.5}}
    supervisor.snapshot.sleeves = {"asb_x": 0.20}
    supervisor.snapshot.last_prices = {"AAPL": 100.0, "MSFT": 100.0}
    save_state(home.state_path(), supervisor.snapshot)
    broker.positions = {}
    close_all_before = broker.close_all_count
    body = client.get("/api/portfolio").json()
    msft = next(item for item in body["positions"] if item["symbol"] == "MSFT")
    assert float(msft["qty"]) == 0.0
    assert msft.get("wanted") is None
    assert msft["next"] == pytest.approx(0.10)
    aapl = next(item for item in body["positions"] if item["symbol"] == "AAPL")
    assert aapl["wanted"] == pytest.approx(0.10)
    assert aapl["next"] == pytest.approx(0.10)
    assert broker.close_all_count == close_all_before
    assert supervisor.state.value != "stopped"
```

Fix the unknown-weights test `close_all` assert to capture `close_all_before` like the others (do not compare the count to itself).

In `test_web_tokens.py`:

- `test_html_positions_glance_bands`: after Day < Wanted, assert Wanted < Next < Got.
- `test_js_session_name_and_alloc_rails` and `test_js_paints_positions_day_pnl`: `colspan='9'`.
- After `test_js_paints_positions_day_pnl`:

```python
def test_js_paints_positions_next(js_text: str) -> None:
    assert "function formatNextCell" in js_text
    helper = js_text[
        js_text.find("function formatNextCell") : js_text.find("function wantedGotBar")
    ]
    assert "fmtPct" in helper
    assert "warn" in helper
    port = js_text[
        js_text.find("function renderPortfolio") : js_text.find("function pulseLabel")
    ]
    assert "formatNextCell(pos.next, pos.wanted)" in port
    assert "colspan='9'" in port
    assert "Gross cap" not in js_text
    assert "Order size" not in js_text
    assert "window.confirm" not in js_text
    assert "window.state" not in js_text


def test_css_positions_next_warn_token(css_text: str) -> None:
    warn = re.search(r"#positions-table td\.warn\s*\{[^}]*\}", css_text)
    assert warn is not None and "#f59e0b" in warn.group(0).lower()
```

Keep `test_portfolio_includes_wanted_name_with_no_fill`.
Keep `test_portfolio_contribution_follows_current_allocation`.

- [ ] **Step 2: Run the new tests and confirm they fail**

```bash
PYTHONPATH=src python3 -m pytest tests/alphastrategy/test_api.py::test_portfolio_next_follows_current_allocation tests/alphastrategy/test_api.py::test_portfolio_omits_next_when_paper_sleeve_has_no_last_weights tests/alphastrategy/test_api.py::test_portfolio_includes_next_only_name tests/alphastrategy/test_api.py::test_portfolio_contribution_follows_current_allocation tests/alphastrategy/test_helptext.py::test_help_text_contains_required_phrases tests/alphastrategy/test_web_tokens.py::test_html_positions_glance_bands tests/alphastrategy/test_web_tokens.py::test_js_paints_positions_next tests/alphastrategy/test_web_tokens.py::test_js_paints_positions_day_pnl -q
```

Expected: next tests fail (no `next` key / no Next header / colspan still 8). Contribution / wanted-only locks still pass.

- [ ] **Step 3: Commit tests and docs**

---

### Task 2: Implement

- [ ] **Step 4: utilization.py + handlers.py**

After `sleeve_contribution_glance`:

```python
def next_send_combined_glance(snapshot: Any) -> dict[str, float] | None:
    if not _next_send_ready(snapshot):
        return None
    return _next_send_combined(snapshot)
```

`_enrich_positions` add `next_combined: dict[str, float] | None = None`. After wanted/fill on live rows, if `symbol in (next_combined or {})`: `item["next"] = float(next_combined[symbol])`. After the last_combined union loop, union remaining next keys the same way with `qty` 0 and no `wanted`.

```python
from alphastrategy.risk.utilization import (
    from_supervisor,
    next_send_combined_glance,
    sleeve_contribution_glance,
)
```

```python
    positions = _enrich_positions(
        raw_positions,
        equity,
        snapshot.last_prices,
        snapshot.last_combined,
        snapshot.last_fill_got,
        next_send_combined_glance(snapshot),
    )
```

Do not flatten. Do not call DSL.

- [ ] **Step 5: HTML, CSS, JS**

`index.html` head:

```html
                <tr><th>Symbol</th><th>Qty</th><th>Notional</th><th>Day</th><th>Wanted</th><th>Next</th><th>Got</th><th>Book</th><th>Cap</th></tr>
```

`styles.css` after `#positions-table td.negative`:

```css
#positions-table td.warn {
  color: #f59e0b;
}
```

`paint-rails.js` after `formatDayPnlCell`:

```javascript
  function formatNextCell(next, wanted) {
    const n = Number(next);
    const has = next != null && next !== "" && Number.isFinite(n);
    const w = Number(wanted);
    const differs =
      has &&
      wanted != null &&
      wanted !== "" &&
      Number.isFinite(w) &&
      Math.abs(n - w) > 1e-9;
    const cls = differs ? " warn" : "";
    return `<td class="nums${cls}">${has ? fmtPct(n) : "—"}</td>`;
  }
```

`paint-portfolio.js`: `colspan='9'`; after `formatDayPnlCell(pos.day_pnl)` insert `formatNextCell(pos.next, pos.wanted)` after the Wanted `<td>`. File ≤ 400 lines.

- [ ] **Step 6: Help and README**

`helptext.py`: add `Positions Next follows current allocations on last sleeve weights. ` to `execution` (after Sleeves contribution), `cockpit` (after Wanted is last combined), `how_portfolio` (after Positions Book / Sleeves contribution), `task_wanted` (after Positions Day).

README Portfolio: after Wanted versus Got, same sentence. Keep `Next rebalance`. Keep `Rows / Wanted / Got / At cap`.

- [ ] **Step 7: Full suite**

```bash
PYTHONPATH=src python3 -m pytest tests/alphastrategy/ -q
```

- [ ] **Step 8: Commit, push, update PR**
