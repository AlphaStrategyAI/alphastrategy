# Empty-Desk Band and Paint Rails Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans (this cycle chose executing-plans). Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Put Start this paper desk on empty Portfolio as a glance band, and extract utilization painters into `js/paint-rails.js`.

**Architecture:** HTML move of `#first-run` into `#screen-portfolio`. New IIFE fragment `paint-rails.js` after `core.js`. Function names unchanged so `renderPortfolio` / `renderRisk` keep calling them. Do not revive `static/app.js`.

**Tech Stack:** Static HTML/CSS, cockpit JS parts, `helptext.py`, pytest.

**Requirements:** [`docs/requirements/2026-08-20-alphastrategy-empty-desk-requirements.md`](../requirements/2026-08-20-alphastrategy-empty-desk-requirements.md)

## Global Constraints

- Paper only. Five `#nav` screens. Locked tokens. No `window.confirm`. No live. No ghost positions.
- Keep `#first-run` id and `data-go-screen` buttons. Each JS part ≤ 400 lines.
- Tests: `PYTHONPATH=src python3 -m pytest tests/alphastrategy/ -q`.

## File map

- Create: `src/alphastrategy/web/static/js/paint-rails.js`
- Modify: `cockpit.py` `JS_PARTS`, `index.html`, `styles.css`, `js/paint-portfolio.js`, `helptext.py`, `README.md`
- Test: `tests/alphastrategy/test_web_tokens.py`, `test_helptext.py`, `test_e2e_mocked.py`

---

### Task 1: Failing tests

- [ ] **Step 1: Replace `test_html_first_run_and_book_column` location asserts**

In `tests/alphastrategy/test_web_tokens.py`, change `test_html_first_run_and_book_column` so first-run is **inside** Portfolio, before Book:

```python
def test_html_first_run_and_book_column(html_text: str) -> None:
    assert 'id="first-run"' in html_text
    port = html_text[
        html_text.find('id="screen-portfolio"') : html_text.find('id="screen-strategies"')
    ]
    assert 'id="first-run"' in port
    assert port.find('id="first-run"') < port.find('id="glance-book"')
    banners = html_text[
        html_text.find('id="desk-banners"') : html_text.find('id="screen-portfolio"')
    ]
    assert 'id="first-run"' not in banners
    assert '<h2 class="glance-heading">Start this paper desk</h2>' in port
    assert "Import is not permission to trade" in html_text
    assert 'data-go-screen="strategies"' in html_text
    assert 'data-go-screen="run"' in html_text
    assert ">Book<" in html_text
    assert 'id="metric-gross-bar"' in html_text
```

Append:

```python
def test_cockpit_js_includes_paint_rails() -> None:
    from alphastrategy.web.cockpit import JS_PARTS, STATIC_DIR, cockpit_js

    assert JS_PARTS[0] == "js/core.js"
    assert JS_PARTS[1] == "js/paint-rails.js"
    assert JS_PARTS[2] == "js/paint-portfolio.js"
    rails = (STATIC_DIR / "js/paint-rails.js").read_text(encoding="utf-8")
    port = (STATIC_DIR / "js/paint-portfolio.js").read_text(encoding="utf-8")
    assert "function renderRiskUtilization" in rails
    assert "function wantedGotBar" in rails
    assert "function renderRiskUtilization" not in port
    assert "function renderPortfolio" in port
    assert "function renderFirstRun" in port
    assert rails.count("\n") <= 400
    assert "window.state" not in cockpit_js()
```

Update `test_cockpit_js_assembled_from_parts` `JS_PARTS` tuple to insert `"js/paint-rails.js"` after core.

`REQUIRED_PHRASES` add `"empty Portfolio"`.

- [ ] **Step 2: Run — FAIL.** Commit tests.

---

### Task 2: HTML, CSS, rails part, help

- [ ] **Step 4: HTML** — delete the first-run block above `#screen-portfolio`. Insert the glance-band markup from the requirements as the first child of `#screen-portfolio`.

- [ ] **Step 5: CSS** — replace `.first-run { border-color: #10b981; margin-bottom: 0.75rem; }` with:

```css
.first-run {
  border-color: #10b981;
}

.first-run .glance-heading {
  color: #10b981;
}

.first-run .panel {
  border-color: #10b981;
}
```

Keep `.first-run.hidden` display:none.

- [ ] **Step 6: Create `paint-rails.js`**

Copy these functions verbatim from `paint-portfolio.js` (two-space indent, no extra wrapper): `wantedGotBar`, `paintUtilTrack`, `utilization`, `renderGrossUtilization`, `renderRemainingBudgets`, `renderCashComposition`, `renderRiskUtilization`, `nameCapBar`, `renderSleeveAllocBook`.

Delete those functions from `paint-portfolio.js`. Keep `renderFirstRun` through `renderDeskPulse` except the moved ones.

- [ ] **Step 7: `cockpit.py`**

```python
JS_PARTS: tuple[str, ...] = (
    "js/core.js",
    "js/paint-rails.js",
    "js/paint-portfolio.js",
    "js/paint-strategies.js",
    "js/paint-run.js",
    "js/paint-activity.js",
    "js/paint-risk.js",
    "js/boot.js",
)
```

- [ ] **Step 8: Help + README**

`how_portfolio` first sentence:

```python
            "Empty Portfolio starts with Start this paper desk, then "
            "three bands: Book / Flatten budgets / Clock. Equity is the hero. "
```

Cockpit, after empty-desk sentence:

```text
An empty Portfolio shows Start this paper desk as its first glance band, not a global panel.
```

README: empty Portfolio shows **Start this paper desk** as the first glance band, then Book / Flatten budgets / Clock.

- [ ] **Step 9: Full suite PASS. Commit.**

---

## Spec coverage

Empty band location, rails extract, JS_PARTS, help — tasked. No placeholders.
