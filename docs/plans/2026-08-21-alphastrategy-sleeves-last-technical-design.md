# Sleeves Contribution names last against next Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans (this cycle chose executing-plans). Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Portfolio Sleeves Contribution keeps the next-send overlay as the number and names last send in a muted sub when it differs, matching Headroom Target cash.

**Architecture:** Expose persisted `last_sleeve_contribution` on GET `/api/portfolio`. Cockpit `formatContributionCell` appends `last {fmtContribution}` when that map differs. Overlay math and stop semantics unchanged.

**Tech Stack:** Python 3.9+, pytest, cockpit HTML/JS, helptext, README.

**Requirements:** [`docs/requirements/2026-08-21-alphastrategy-sleeves-last-requirements.md`](../requirements/2026-08-21-alphastrategy-sleeves-last-requirements.md)

## Global Constraints

- Paper only. Five `#nav` screens. Locked tokens. No live.
- Do not evaluate DSL on GET. Do not flatten on GET. Do not place.
- Wanted stays last combined. Book Drift stays last wanted vs last fill.
- Positions glance stays Rows / Wanted / Got / At cap. Sleeves glance stays chrome only.
- Keep `Next rebalance`. Keep Cash composition labels. Keep Positions `colspan='9'`.
- Keep `sleeve_contribution_glance` overlay. Stopped sleeves keep last contribution.
- `paint-portfolio.js` and `paint-rails.js` stay ≤ 400 lines.
- Tests: `PYTHONPATH=src python3 -m pytest tests/alphastrategy/ -q`.

## File map

- Modify: `src/alphastrategy/risk/utilization.py`, `src/alphastrategy/api/handlers.py`, `src/alphastrategy/web/static/js/core.js`, `src/alphastrategy/web/static/js/paint-portfolio.js`, `src/alphastrategy/helptext.py`, `README.md`
- Test: `tests/alphastrategy/test_api.py`, `tests/alphastrategy/test_helptext.py`, `tests/alphastrategy/test_web_tokens.py`

---

### Task 1: Failing tests

**Files:**
- Modify: `tests/alphastrategy/test_api.py`
- Modify: `tests/alphastrategy/test_helptext.py`
- Modify: `tests/alphastrategy/test_web_tokens.py`

**Interfaces:**
- Consumes: existing `sleeve_contribution_glance`; persisted `last_sleeve_contribution`
- Produces: GET key `last_sleeve_contribution`; JS `formatContributionCell`; help phrase `Sleeves Contribution names last against next`

- [ ] **Step 1: Write the failing tests**

`REQUIRED_PHRASES` add after `Sleeves contribution follows current allocations on last sleeve weights`:

```python
    "Sleeves Contribution names last against next",
```

In `test_api.py` after `test_portfolio_contribution_follows_current_allocation`:

```python
def test_portfolio_last_contribution_stays_last_send(api_stack):
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
    assert body["last_sleeve_contribution"]["asb_x"]["AAPL"] == pytest.approx(0.10)
    pos = next(item for item in body["positions"] if item["symbol"] == "AAPL")
    assert pos["wanted"] == pytest.approx(0.10)
    assert pos["next"] == pytest.approx(0.18)
    assert broker.close_all_count == close_all_before
    assert supervisor.state.value != "stopped"
```

After `test_js_wanted_got_bar_names_next`:

```python
def test_js_paints_sleeves_contribution_last(js_text: str) -> None:
    assert "function formatContributionCell" in js_text
    helper = js_text[
        js_text.find("function formatContributionCell") : js_text.find("async function api")
    ]
    assert "fmtContribution" in helper
    assert '"last "' in helper
    assert "metric-sub" in helper
    port = js_text[
        js_text.find("function renderPortfolio") : js_text.find("function pulseLabel")
    ]
    assert "formatContributionCell(contrib[id], lastContrib[id])" in port
    assert "last_sleeve_contribution" in port
    assert "colspan='9'" in port
    assert "Gross cap" not in js_text
    assert "Order size" not in js_text
    assert "window.confirm" not in js_text
    assert "window.state" not in js_text
```

Keep `test_portfolio_contribution_follows_current_allocation`. Keep `test_portfolio_next_follows_current_allocation`.

- [ ] **Step 2: Run the new tests and confirm they fail**

```bash
PYTHONPATH=src python3 -m pytest tests/alphastrategy/test_api.py::test_portfolio_last_contribution_stays_last_send tests/alphastrategy/test_api.py::test_portfolio_contribution_follows_current_allocation tests/alphastrategy/test_helptext.py::test_help_text_contains_required_phrases tests/alphastrategy/test_web_tokens.py::test_js_paints_sleeves_contribution_last tests/alphastrategy/test_web_tokens.py::test_js_wanted_got_bar_names_next -q
```

Expected: last-contribution / help / formatContributionCell tests fail. Existing contribution overlay and Book-next locks still pass.

- [ ] **Step 3: Commit tests and docs**

```bash
git add docs/requirements/2026-08-21-alphastrategy-sleeves-last-requirements.md docs/plans/2026-08-21-alphastrategy-sleeves-last-technical-design.md tests/alphastrategy/test_api.py tests/alphastrategy/test_helptext.py tests/alphastrategy/test_web_tokens.py
git commit -m "test: Sleeves Contribution names last against next"
```

---

### Task 2: Implement

**Files:**
- Modify: `src/alphastrategy/risk/utilization.py`
- Modify: `src/alphastrategy/api/handlers.py`
- Modify: `src/alphastrategy/web/static/js/core.js`
- Modify: `src/alphastrategy/web/static/js/paint-portfolio.js`
- Modify: `src/alphastrategy/helptext.py`
- Modify: `README.md`

**Interfaces:**
- Consumes: persisted `snapshot.last_sleeve_contribution`
- Produces: `last_sleeve_contribution_glance(snapshot) -> dict[str, dict[str, float]]`; GET key `last_sleeve_contribution`; `formatContributionCell(nextMap, lastMap)`

- [ ] **Step 4: utilization.py + handlers.py**

Extract the persisted copy from `sleeve_contribution_glance` into:

```python
def last_sleeve_contribution_glance(snapshot: Any) -> dict[str, dict[str, float]]:
    last = getattr(snapshot, "last_sleeve_contribution", None) or {}
    return {
        str(bundle_id): {str(asset): float(weight) for asset, weight in weights.items()}
        for bundle_id, weights in last.items()
        if isinstance(weights, dict)
    }
```

`sleeve_contribution_glance` starts with `out = last_sleeve_contribution_glance(snapshot)` then overlays positive sleeves when ready (same as today).

`handlers.py` import `last_sleeve_contribution_glance` and set:

```python
        "sleeve_contribution": sleeve_contribution_glance(snapshot),
        "last_sleeve_contribution": last_sleeve_contribution_glance(snapshot),
```

Do not flatten. Do not call DSL.

- [ ] **Step 5: JS**

`core.js` after `fmtContribution`:

```javascript
  function formatContributionCell(nextMap, lastMap) {
    const nextText = fmtContribution(nextMap);
    const lastText = fmtContribution(lastMap);
    const hasLast = lastMap && typeof lastMap === "object" && Object.keys(lastMap).length;
    const differs = Boolean(hasLast && lastText !== nextText);
    const sub = differs ? `<div class="metric-sub nums">last ${lastText}</div>` : "";
    return `<td class="nums">${nextText}${sub}</td>`;
  }
```

The test locks `"last "` as a quoted prefix. Use `"last "` concatenated, not only a template `last ${`:

```javascript
    const sub = differs ? `<div class="metric-sub nums">` + "last " + lastText + `</div>` : "";
```

`paint-portfolio.js` in `renderPortfolio` sleeves block:

```javascript
    const contrib = portfolio.sleeve_contribution || {};
    const lastContrib = portfolio.last_sleeve_contribution || {};
```

Row:

```javascript
        tr.innerHTML = `<td>${id}</td><td class="nums">${fmtPct(sleeves[id])}</td>` + formatContributionCell(contrib[id], lastContrib[id]);
```

File ≤ 400 lines. Do not grow `paint-rails.js`.

- [ ] **Step 6: Help and README**

`helptext.py`: add `Sleeves Contribution names last against next. ` to `cockpit` (after Positions Book names Next against Wanted), `how_portfolio` (after Sleeves contribution follows current allocations).

README Operator list: after `Sleeves contribution follows current allocations on last sleeve weights.`, add `Sleeves Contribution names last against next.` Keep `Next rebalance`. Keep `Rows / Wanted / Got / At cap`.

- [ ] **Step 7: Full suite**

```bash
PYTHONPATH=src python3 -m pytest tests/alphastrategy/ -q
```

- [ ] **Step 8: Commit, push, update PR**

```bash
git add src/alphastrategy/risk/utilization.py src/alphastrategy/api/handlers.py src/alphastrategy/web/static/js/core.js src/alphastrategy/web/static/js/paint-portfolio.js src/alphastrategy/helptext.py README.md
git commit -m "feat: Sleeves Contribution names last against next"
```
