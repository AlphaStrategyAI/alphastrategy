# Positions Day last close Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans (this cycle chose executing-plans). Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Positions rows show that name’s session change (`day_pnl`) as last close → mark, never lifetime `unrealized_pl`, never a fake `0.00`.

**Architecture:** `_position_day_pnl` during `_enrich_positions`. Cockpit adds a Day column after Notional. `formatDayPnlCell` in `paint-rails.js`.

**Tech Stack:** Python 3.9+, Quiet cockpit HTML/CSS/JS, pytest, helptext, README.

**Requirements:** [`docs/requirements/2026-08-20-alphastrategy-positions-day-requirements.md`](../requirements/2026-08-20-alphastrategy-positions-day-requirements.md)

## Global Constraints

- Paper only. Five `#nav` screens. Locked tokens. No `window.confirm`. No live.
- `"Gross cap"` must not appear in assembled JS.
- Heartbeat does not flatten. GET status/portfolio/risk must not flatten.
- Do not feed `plan_orders` from `live_book()`.
- Do not overwrite Cash composition subs. Do not paint Beat/Glance on Day.
- Do not sum row `day_pnl` into Book Day PnL.
- Do not use `unrealized_pl` for Positions Day.
- Positions glance stays Rows / Wanted / Got / At cap.
- Each file in `JS_PARTS` stays ≤ 400 newlines.
- Tests: `PYTHONPATH=src python3 -m pytest tests/alphastrategy/ -q`.

## File map

- Modify: `src/alphastrategy/api/handlers.py`, `src/alphastrategy/web/static/index.html`, `src/alphastrategy/web/static/styles.css`, `src/alphastrategy/web/static/js/paint-rails.js`, `src/alphastrategy/web/static/js/paint-portfolio.js`, `src/alphastrategy/helptext.py`, `README.md`
- Test: `tests/alphastrategy/test_api.py`, `tests/alphastrategy/test_web_tokens.py`, `tests/alphastrategy/test_helptext.py`

---

### Task 1: Failing tests

- [ ] **Step 1: Write the failing tests**

`REQUIRED_PHRASES` add:

```python
    "Positions Day is that name since last close",
```

In `tests/alphastrategy/test_api.py` after the portfolio Day PnL tests:

```python
def _by_symbol(positions: list[dict]) -> dict[str, dict]:
    return {str(row["symbol"]): row for row in positions}


def test_get_portfolio_position_day_pnl_null_without_last_close(api_stack):
    client, home, supervisor, broker = api_stack
    broker.positions = {"AAPL": 15.0}
    supervisor.snapshot.last_prices = {"AAPL": 100.0}
    save_state(home.state_path(), supervisor.snapshot)
    close_all_before = broker.close_all_count
    body = client.get("/api/portfolio").json()
    row = _by_symbol(body["positions"])["AAPL"]
    assert row["day_pnl"] is None
    assert broker.close_all_count == close_all_before


def test_get_portfolio_position_day_pnl_from_intraday(api_stack):
    client, _home, _supervisor, broker = api_stack
    orig = broker.list_positions

    def with_intraday():
        rows = orig()
        for row in rows:
            row["unrealized_intraday_pl"] = "12.5"
            row["unrealized_pl"] = "999"
        return rows

    broker.list_positions = with_intraday  # type: ignore[method-assign]
    broker.positions = {"AAPL": 15.0}
    body = client.get("/api/portfolio").json()
    assert _by_symbol(body["positions"])["AAPL"]["day_pnl"] == 12.5


def test_get_portfolio_position_day_pnl_ignores_unrealized_pl(api_stack):
    client, _home, _supervisor, broker = api_stack
    orig = broker.list_positions

    def with_lifetime():
        rows = orig()
        for row in rows:
            row["unrealized_pl"] = "999"
        return rows

    broker.list_positions = with_lifetime  # type: ignore[method-assign]
    broker.positions = {"AAPL": 15.0}
    body = client.get("/api/portfolio").json()
    assert _by_symbol(body["positions"])["AAPL"]["day_pnl"] is None


def test_get_portfolio_position_day_pnl_from_lastday_price(api_stack):
    client, home, supervisor, broker = api_stack
    orig = broker.list_positions

    def with_last_close():
        rows = orig()
        for row in rows:
            row["lastday_price"] = "100"
        return rows

    broker.list_positions = with_last_close  # type: ignore[method-assign]
    broker.positions = {"AAPL": 15.0}
    supervisor.snapshot.last_prices = {"AAPL": 110.0}
    save_state(home.state_path(), supervisor.snapshot)
    body = client.get("/api/portfolio").json()
    assert _by_symbol(body["positions"])["AAPL"]["day_pnl"] == 150.0
```

In `tests/alphastrategy/test_web_tokens.py`:

- `test_js_session_name_and_alloc_rails`: `colspan='8'`
- `test_html_positions_glance_bands`: `assert ">Day<" in pos` and the header order Notional then Day
- add:

```python
def test_js_paints_positions_day_pnl(js_text: str) -> None:
    assert "function formatDayPnlCell" in js_text
    paint = js_text[
        js_text.find("function formatDayPnlCell") : js_text.find("function wantedGotBar")
    ]
    assert "pos.day_pnl" not in paint
    assert "day_pnl" in paint or "raw" in paint
    port = js_text[
        js_text.find("function renderPortfolio") : js_text.find("function pulseLabel")
    ]
    assert "formatDayPnlCell" in port
    assert "pos.day_pnl" in port
    assert "unrealized_pl" not in port
    assert "colspan='8'" in port
    assert "Gross cap" not in js_text
    assert "window.confirm" not in js_text
    assert "window.state" not in js_text


def test_css_positions_day_signed_tokens(css_text: str) -> None:
    pos = re.search(r"#positions-table td\.positive\s*\{[^}]*\}", css_text)
    neg = re.search(r"#positions-table td\.negative\s*\{[^}]*\}", css_text)
    assert pos is not None and "#10b981" in pos.group(0).lower()
    assert neg is not None and "#ef4444" in neg.group(0).lower()
```

Fix the JS test: `formatDayPnlCell` takes the raw value, `renderPortfolio` passes `pos.day_pnl`. The helper slice should not require `pos.day_pnl`.

- [ ] **Step 2: Run the new tests and confirm they fail**

```bash
PYTHONPATH=src python3 -m pytest tests/alphastrategy/test_api.py::test_get_portfolio_position_day_pnl_null_without_last_close tests/alphastrategy/test_api.py::test_get_portfolio_position_day_pnl_from_intraday tests/alphastrategy/test_api.py::test_get_portfolio_position_day_pnl_ignores_unrealized_pl tests/alphastrategy/test_api.py::test_get_portfolio_position_day_pnl_from_lastday_price tests/alphastrategy/test_web_tokens.py::test_js_session_name_and_alloc_rails tests/alphastrategy/test_web_tokens.py::test_html_positions_glance_bands tests/alphastrategy/test_web_tokens.py::test_js_paints_positions_day_pnl tests/alphastrategy/test_web_tokens.py::test_css_positions_day_signed_tokens tests/alphastrategy/test_helptext.py::test_help_text_contains_required_phrases -q
```

Expect failures on missing `day_pnl`, Day header, `formatDayPnlCell`, CSS, and the help phrase. Keep locks of existing behavior that still pass.

- [ ] **Step 3: Commit tests and docs**

---

### Task 2: Implement

- [ ] **Step 4: `_position_day_pnl` and enrich**

In `handlers.py` next to `_account_day_pnl`:

```python
def _position_day_pnl(
    item: dict[str, Any],
    *,
    qty: float,
    prices: dict[str, float],
) -> float | None:
    for key in ("unrealized_intraday_pl", "day_pnl"):
        if key not in item:
            continue
        parsed = _optional_float(item.get(key))
        if parsed is not None:
            return parsed
    if qty == 0:
        return None
    last_close = _optional_float(item.get("lastday_price"))
    symbol = str(item.get("symbol", ""))
    price = prices.get(symbol)
    if price is None:
        price = _optional_float(item.get("current_price"))
    if last_close is None or price is None:
        return None
    return qty * (price - last_close)
```

In `_enrich_positions`, after qty/notional/weight, set `item["day_pnl"] = _position_day_pnl(item, qty=qty, prices=prices)`. Wanted-only rows: `"day_pnl": None`. Do not flatten. Do not persist.

- [ ] **Step 5: Cockpit**

`index.html` Positions head: `<th>Symbol</th><th>Qty</th><th>Notional</th><th>Day</th><th>Wanted</th><th>Got</th><th>Book</th><th>Cap</th>`

`styles.css`:

```css
#positions-table td.positive {
  color: #10b981;
}
#positions-table td.negative {
  color: #ef4444;
}
```

`paint-rails.js` after `paintDayPnl`:

```javascript
  function formatDayPnlCell(raw) {
    const n = Number(raw);
    const has = raw != null && raw !== "" && Number.isFinite(n);
    const cls = has && n > 0 ? " positive" : has && n < 0 ? " negative" : "";
    return `<td class="nums${cls}">${has ? fmtNum(n, 2) : "—"}</td>`;
  }
```

`paint-portfolio.js`: empty `colspan='8'`; in the row template insert `formatDayPnlCell(pos.day_pnl)` after Notional. File ≤ 400 newlines.

- [ ] **Step 6: Help and README**

`helptext.py`: add `Positions Day is that name since last close. ` to `cockpit` (after Positions Book column), `how_portfolio` (after Positions four tiles), and `task_wanted`.

README Portfolio Positions sentence: same phrase. Keep `Day PnL is equity minus last close`. Keep `Next rebalance`. Keep `Rows / Wanted / Got / At cap`.

- [ ] **Step 7: Run the new tests green, then the full suite**

```bash
PYTHONPATH=src python3 -m pytest tests/alphastrategy/ -q
```

- [ ] **Step 8: Commit, push, update PR**
