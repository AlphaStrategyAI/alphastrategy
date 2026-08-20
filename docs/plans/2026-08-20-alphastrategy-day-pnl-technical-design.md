# Day PnL last close Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans (this cycle chose executing-plans). Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Book Day PnL is equity minus Alpaca `last_equity` (or an explicit account PnL field), never a fake `0.00` when last close is missing.

**Architecture:** `_account_day_pnl` reads the `live_book()` account dict. Portfolio JSON uses `null` when unknown. Cockpit `paintDayPnl` paints `—` or `vs last close`. No second broker read.

**Tech Stack:** Python 3.9+, Quiet cockpit HTML/JS, pytest, helptext, README.

**Requirements:** [`docs/requirements/2026-08-20-alphastrategy-day-pnl-requirements.md`](../requirements/2026-08-20-alphastrategy-day-pnl-requirements.md)

## Global Constraints

- Paper only. Five `#nav` screens. Locked tokens. No `window.confirm`. No live.
- `"Gross cap"` must not appear in assembled JS.
- Heartbeat does not flatten. GET status/portfolio/risk must not flatten.
- Do not feed `plan_orders` from `live_book()`.
- Do not overwrite Cash / Headroom cash composition subs.
- Do not paint Beat/Glance on Day PnL.
- Each file in `JS_PARTS` stays ≤ 400 newlines.
- Tests: `PYTHONPATH=src python3 -m pytest tests/alphastrategy/ -q`.

## File map

- Modify: `src/alphastrategy/api/handlers.py`, `src/alphastrategy/web/static/index.html`, `src/alphastrategy/web/static/js/paint-rails.js`, `src/alphastrategy/web/static/js/paint-portfolio.js`, `src/alphastrategy/helptext.py`, `README.md`
- Test: `tests/alphastrategy/test_api.py`, `tests/alphastrategy/test_web_tokens.py`, `tests/alphastrategy/test_helptext.py`

---

### Task 1: Failing tests

- [ ] **Step 1: Write the failing tests**

`REQUIRED_PHRASES` add:

```python
    "Day PnL is equity minus last close",
```

In `tests/alphastrategy/test_api.py` update `test_get_portfolio_returns_account_fields` and add after it:

```python
def test_get_portfolio_returns_account_fields(api_client: ApiClient):
    response = api_client.get("/api/portfolio")
    assert response.status == 200
    body = response.json()
    assert body["equity"] == 10_000.0
    assert body["cash"] == 10_000.0
    assert body["pnl"] is None
    assert body["pnl_source"] is None
    assert "positions" in body
    assert "sleeves" in body


def test_get_portfolio_pnl_from_last_equity(api_stack):
    client, _home, _supervisor, broker = api_stack
    orig = broker.get_account

    def with_last():
        account = orig()
        account["last_equity"] = "9900"
        return account

    broker.get_account = with_last  # type: ignore[method-assign]
    close_all_before = broker.close_all_count
    body = client.get("/api/portfolio").json()
    assert body["pnl"] == 100.0
    assert body["pnl_source"] == "last_close"
    assert broker.close_all_count == close_all_before


def test_get_portfolio_pnl_prefers_account_field(api_stack):
    client, _home, _supervisor, broker = api_stack
    orig = broker.get_account

    def with_both():
        account = orig()
        account["pnl"] = "42.5"
        account["last_equity"] = "9900"
        return account

    broker.get_account = with_both  # type: ignore[method-assign]
    body = client.get("/api/portfolio").json()
    assert body["pnl"] == 42.5
    assert body["pnl_source"] == "account"


def test_get_portfolio_explicit_zero_pnl_is_not_null(api_stack):
    client, _home, _supervisor, broker = api_stack
    orig = broker.get_account

    def with_zero():
        account = orig()
        account["pnl"] = "0"
        return account

    broker.get_account = with_zero  # type: ignore[method-assign]
    body = client.get("/api/portfolio").json()
    assert body["pnl"] == 0.0
    assert body["pnl_source"] == "account"
```

In `tests/alphastrategy/test_web_tokens.py` `test_html_glance_bands` add `assert 'id="metric-pnl-sub"' in book`.

Add:

```python
def test_js_paints_day_pnl_last_close(js_text: str) -> None:
    assert "function paintDayPnl" in js_text
    paint = js_text[
        js_text.find("function paintDayPnl") : js_text.find("function wantedGotBar")
    ]
    assert "metric-pnl-sub" in paint
    assert "vs last close" in paint
    assert 'pnl_source === "last_close"' in paint
    port = js_text[
        js_text.find("function renderPortfolio") : js_text.find("function pulseLabel")
    ]
    assert "paintDayPnl(" in port
    assert "Gross cap" not in js_text
    assert "window.confirm" not in js_text
    assert "window.state" not in js_text
```

- [ ] **Step 2: Run the new tests and confirm they fail**

```bash
PYTHONPATH=src python3 -m pytest tests/alphastrategy/test_api.py::test_get_portfolio_returns_account_fields tests/alphastrategy/test_api.py::test_get_portfolio_pnl_from_last_equity tests/alphastrategy/test_api.py::test_get_portfolio_pnl_prefers_account_field tests/alphastrategy/test_api.py::test_get_portfolio_explicit_zero_pnl_is_not_null tests/alphastrategy/test_web_tokens.py::test_html_glance_bands tests/alphastrategy/test_web_tokens.py::test_js_paints_day_pnl_last_close tests/alphastrategy/test_helptext.py::test_help_text_contains_required_phrases -q
```

Expect failures on `pnl is None`, `pnl_source`, `paintDayPnl`, `metric-pnl-sub`, and the help phrase. If a lock of **existing** behavior passes, keep it.

- [ ] **Step 3: Commit tests and docs**

---

### Task 2: Implement

- [ ] **Step 4: `_account_day_pnl` and portfolio payload**

In `src/alphastrategy/api/handlers.py`:

```python
def _optional_float(value: Any) -> float | None:
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _account_day_pnl(account: dict[str, Any]) -> tuple[float | None, str | None]:
    for key in ("pnl", "day_pnl"):
        if key not in account:
            continue
        parsed = _optional_float(account.get(key))
        if parsed is not None:
            return parsed, "account"
    last_equity = _optional_float(account.get("last_equity"))
    equity = _optional_float(account.get("equity"))
    if last_equity is None or equity is None:
        return None, None
    return equity - last_equity, "last_close"
```

In `handle_get_portfolio` replace the `pnl` line:

```python
    pnl, pnl_source = _account_day_pnl(account)
    payload: dict[str, Any] = {
        "equity": equity,
        "cash": cash,
        "pnl": pnl,
        "pnl_source": pnl_source,
        ...
    }
```

Do not call `_equity()`. Do not flatten. Do not persist.

- [ ] **Step 5: Cockpit paint**

`index.html` Day PnL tile:

```html
            <div class="metric-label">Day PnL</div>
            <div id="metric-pnl" class="metric-value">—</div>
            <div id="metric-pnl-sub" class="metric-sub">—</div>
```

In `paint-rails.js` after `paintBookSourceHeadings`:

```javascript
  function paintDayPnl(portfolio) {
    const pnlEl = document.getElementById("metric-pnl");
    if (!pnlEl) return;
    const pnlSub = document.getElementById("metric-pnl-sub");
    const raw = portfolio && portfolio.pnl;
    const pnl = Number(raw);
    const hasPnl = raw != null && raw !== "" && Number.isFinite(pnl);
    pnlEl.textContent = hasPnl ? fmtNum(pnl, 2) : "—";
    pnlEl.classList.toggle("positive", hasPnl && pnl > 0);
    pnlEl.classList.toggle("negative", hasPnl && pnl < 0);
    if (pnlSub) {
      pnlSub.textContent =
        hasPnl && portfolio.pnl_source === "last_close" ? "vs last close" : "—";
    }
  }
```

In `paint-portfolio.js` `renderPortfolio`, replace the inline Day PnL block with `paintDayPnl(portfolio);`. Keep `eqSub` as `bookSourceLabel()`. Keep `renderCashComposition()`. File must stay ≤ 400 newlines.

- [ ] **Step 6: Help and README**

`helptext.py`: add `Day PnL is equity minus last close. ` to `cockpit` (after Equity is the hero) and `how_portfolio` (after Book Equity names Beat or Glance).

`README.md`: in the Portfolio Book sentence and Operator heartbeat bullets, add the same phrase. Keep `Next rebalance`. Keep Caps LIMIT / flatten-now / Beat-Glance sentences.

- [ ] **Step 7: Run the new tests green, then the full suite**

```bash
PYTHONPATH=src python3 -m pytest tests/alphastrategy/test_api.py::test_get_portfolio_returns_account_fields tests/alphastrategy/test_api.py::test_get_portfolio_pnl_from_last_equity tests/alphastrategy/test_api.py::test_get_portfolio_pnl_prefers_account_field tests/alphastrategy/test_api.py::test_get_portfolio_explicit_zero_pnl_is_not_null tests/alphastrategy/test_web_tokens.py::test_html_glance_bands tests/alphastrategy/test_web_tokens.py::test_js_paints_day_pnl_last_close tests/alphastrategy/test_web_tokens.py::test_cockpit_js_assembled_from_parts tests/alphastrategy/test_helptext.py::test_help_text_contains_required_phrases -q
PYTHONPATH=src python3 -m pytest tests/alphastrategy/ -q
```

- [ ] **Step 8: Commit, push, update PR**
