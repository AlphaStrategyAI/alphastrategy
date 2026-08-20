# Portfolio Positions Glance Tiles Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans (this cycle chose executing-plans). Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Paint Portfolio Positions as Rows / Wanted / Got / At cap glance tiles above the holdings table, and wrap Sleeves in a matching glance band.

**Architecture:** Static metrics inside `#glance-positions`. `renderPositionsGlance` in `js/paint-portfolio.js` counts the existing `portfolio.positions` array. No API change. Sleeves is chrome only (no Run tiles).

**Tech Stack:** Quiet cockpit HTML/CSS/JS, `helptext.py`, pytest.

**Requirements:** [`docs/requirements/2026-08-20-alphastrategy-positions-glance-requirements.md`](../requirements/2026-08-20-alphastrategy-positions-glance-requirements.md)

## Global Constraints

- Paper only. Five `#nav` screens. Locked tokens. No `window.confirm`. No live. No WebSockets. No charts.
- Keep `#positions-table`, `#sleeves-table`, `.book-grid`, `#metric-drift`. Each JS part ≤ 400 lines.
- JS must not contain `Gross cap`. Do not label a tile Live.
- Tests: `PYTHONPATH=src python3 -m pytest tests/alphastrategy/ -q`.

## File map

- Modify: `src/alphastrategy/web/static/index.html`, `src/alphastrategy/web/static/styles.css`, `src/alphastrategy/web/static/js/paint-portfolio.js`, `src/alphastrategy/helptext.py`, `README.md`
- Test: `tests/alphastrategy/test_web_tokens.py`, `tests/alphastrategy/test_helptext.py`, `tests/alphastrategy/test_e2e_mocked.py`

---

### Task 1: Failing tests

- [ ] **Step 1: HTML/JS/CSS**

Add to `test_web_tokens.py`:

```python
def test_html_positions_glance_bands(html_text: str) -> None:
    port = html_text[
        html_text.find('id="screen-portfolio"') : html_text.find('id="screen-strategies"')
    ]
    pos = port[port.find('id="glance-positions"') : port.find('id="glance-sleeves"')]
    sleeves = port[port.find('id="glance-sleeves"') :]
    assert 'id="pos-count-rows"' in pos
    assert 'id="pos-count-wanted"' in pos
    assert 'id="pos-count-got"' in pos
    assert 'id="pos-count-cap"' in pos
    assert "metrics-4" in pos
    assert "hero" in pos
    assert ">Wanted<" in pos
    assert ">At cap<" in pos
    assert 'id="positions-table"' in pos
    assert 'id="sleeves-table"' in sleeves
    assert 'id="sleeve-alloc-track"' in sleeves
    assert "book-grid" in port
    nav = re.search(r'<nav id="nav"[^>]*>(.*?)</nav>', html_text, re.DOTALL)
    screens = re.findall(r'data-screen="([^"]+)"', nav.group(1))
    assert screens == ["portfolio", "strategies", "run", "activity", "risk"]


def test_js_paints_positions_glance_tiles(js_text: str) -> None:
    paint = js_text[
        js_text.find("function renderPositionsGlance") : js_text.find("function renderDeskPulse")
    ]
    assert "pos-count-rows" in paint
    assert "pos-count-wanted" in paint
    assert "pos-count-got" in paint
    assert "pos-count-cap" in paint
    assert "max_name_weight" in paint
    assert "window.confirm" not in js_text
    assert "window.state" not in js_text
    assert "Gross cap" not in js_text


def test_css_positions_cap_fail_token(css_text: str) -> None:
    cap = re.search(r"#pos-count-cap\.fail\s*\{[^}]*\}", css_text)
    assert cap is not None and "#ef4444" in cap.group(0).lower()
```

`REQUIRED_PHRASES` add `"Rows / Wanted / Got / At cap"`.

e2e `test_control_plane_serves_help`: `assert 'id="pos-count-wanted"' in html`.

- [ ] **Step 2: Run — FAIL.** Commit tests.

Run: `PYTHONPATH=src python3 -m pytest tests/alphastrategy/test_web_tokens.py::test_html_positions_glance_bands tests/alphastrategy/test_web_tokens.py::test_js_paints_positions_glance_tiles tests/alphastrategy/test_web_tokens.py::test_css_positions_cap_fail_token tests/alphastrategy/test_helptext.py::test_help_text_contains_required_phrases tests/alphastrategy/test_e2e_mocked.py::test_control_plane_serves_help -q`

Expected: those new assertions fail (missing ids / phrase). Existing `test_js_risk_tighten_groups` is unchanged.

---

### Task 2: HTML, CSS, JS, help

- [ ] **Step 3: HTML** — replace the Positions / Sleeves `.panel` pair with the markup in the requirements. Keep `class="grid book-grid stack"`. Keep `#clock-line` above the grid. Keep the seven Positions columns and three Sleeves columns.

- [ ] **Step 4: CSS** — add a separate `#pos-count-cap.fail` block with `color: #ef4444`.

- [ ] **Step 5: JS** — add `renderPositionsGlance(positions)` in `paint-portfolio.js` (file must stay ≤ 400 lines). Place it **after** `renderPortfolio` and **before** `renderDeskPulse` so the test slice does not include the Positions table painter (that painter already mentions `max_name_weight`). Call it from `renderPortfolio` with `portfolio.positions || []` (function declarations in the cockpit IIFE hoist).

```javascript
  function renderPositionsGlance(positions) {
    const rowsEl = document.getElementById("pos-count-rows");
    const wantedEl = document.getElementById("pos-count-wanted");
    const gotEl = document.getElementById("pos-count-got");
    const capEl = document.getElementById("pos-count-cap");
    const rows = positions || [];
    const cap =
      Number(state.risk && state.risk.account && state.risk.account.max_name_weight) || 0.2;
    let wantedN = 0;
    let gotN = 0;
    let atCap = 0;
    for (const pos of rows) {
      if (pos.wanted != null && pos.wanted !== undefined && Number(pos.wanted) > 0) {
        wantedN += 1;
      }
      if (Number(pos.qty) !== 0) gotN += 1;
      if (cap > 0 && Number(pos.weight) >= cap) atCap += 1;
    }
    if (rowsEl) rowsEl.textContent = String(rows.length);
    if (wantedEl) wantedEl.textContent = String(wantedN);
    if (gotEl) gotEl.textContent = String(gotN);
    if (capEl) {
      capEl.textContent = String(atCap);
      capEl.classList.toggle("fail", atCap > 0);
    }
  }
```

Call `renderPositionsGlance(positions)` next to the existing `renderBookDrift(positions, equity)` line.

- [ ] **Step 6: Help + README** — `how_portfolio` Positions is Rows / Wanted / Got / At cap; Wanted is the hero. Cockpit/README the same phrase. Keep `Book / Flatten budgets / Clock`.

`how_portfolio` body becomes:

```python
            "Empty Portfolio starts with Start this paper desk, then "
            "Book / Flatten budgets / Clock, then Positions / Sleeves. Equity is the hero. "
            "Book Drift is names off the last combined target. "
            "Positions is four tiles Rows / Wanted / Got / At cap. Wanted is the hero. "
            "Positions include wanted names with no fill. "
            "The Positions Book column is wanted versus got. "
            "Header LIVE is the Supervisor beat, not Session OPEN."
```

Cockpit: replace “Portfolio home is three bands Book / Flatten budgets / Clock.” with “Portfolio home is Book / Flatten budgets / Clock, then Positions / Sleeves. Positions is Rows / Wanted / Got / At cap.”

README: after the Clock sentence, add that Positions is **Rows / Wanted / Got / At cap** (Wanted is the hero). Keep **Book / Flatten budgets / Clock**.

- [ ] **Step 7: Full suite PASS. Commit.**

Run: `PYTHONPATH=src python3 -m pytest tests/alphastrategy/ -q`

Expected: all pass.

---

## Spec coverage

Positions tiles, Sleeves band chrome, keep table ids, At cap fail token, help — tasked. No placeholders. Clock `#clock-line` left unchanged (out).
