# Risk Headroom Glance Tiles Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans (this cycle chose executing-plans). Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Paint Risk Headroom as Names / Orders today / Cash / Target cash glance tiles with used/cap rails.

**Architecture:** Static metrics inside `#risk-utilization`. `renderRiskUtilization` in `js/paint-rails.js` fills mounts from existing `utilization()`. No `innerHTML` wipe. No API change.

**Tech Stack:** Quiet cockpit HTML/CSS/JS, `helptext.py`, pytest.

**Requirements:** [`docs/requirements/2026-08-20-alphastrategy-risk-headroom-requirements.md`](../requirements/2026-08-20-alphastrategy-risk-headroom-requirements.md)

## Global Constraints

- Paper only. Five `#nav` screens. Locked tokens. No `window.confirm`. No live. No WebSockets. No charts.
- Keep `#risk-headroom`, `#risk-utilization`. `renderRiskUtilization` stays in `paint-rails.js`. Each JS part ≤ 400 lines.
- JS must not contain `Gross cap`. Do not label a tile Live.
- Tests: `PYTHONPATH=src python3 -m pytest tests/alphastrategy/ -q`.

## File map

- Modify: `index.html`, `styles.css`, `js/paint-rails.js`, `helptext.py`, `README.md`
- Test: `test_web_tokens.py`, `test_helptext.py`, `test_e2e_mocked.py`

---

### Task 1: Failing tests

- [ ] **Step 1: HTML/JS/CSS**

In `test_html_risk_glance_bands`, after `assert 'id="risk-utilization"' in head`, add:

```python
    assert 'id="risk-head-names"' in head
    assert 'id="risk-head-orders"' in head
    assert 'id="risk-head-cash"' in head
    assert 'id="risk-head-target"' in head
    assert "metrics-4" in head
    assert "hero" in head
    assert ">Names<" in head
    assert ">Target cash<" in head
```

Add:

```python
def test_js_paints_risk_headroom_tiles(js_text: str) -> None:
    paint = js_text[
        js_text.find("function renderRiskUtilization") : js_text.find("function nameCapBar")
    ]
    assert "risk-head-names" in paint
    assert "risk-head-orders" in paint
    assert "risk-head-cash" in paint
    assert "risk-head-target" in paint
    assert "target_cash_weight" in paint
    assert "paintUtilTrack" in paint
    assert 'innerHTML = ""' not in paint
    assert "Gross cap" not in js_text
    assert "window.confirm" not in js_text
    assert "window.state" not in js_text


def test_css_risk_headroom_fail_tokens(css_text: str) -> None:
    names = re.search(r"#risk-head-names\.fail\s*\{[^}]*\}", css_text)
    orders = re.search(r"#risk-head-orders\.fail\s*\{[^}]*\}", css_text)
    assert names is not None and "#ef4444" in names.group(0).lower()
    assert orders is not None and "#ef4444" in orders.group(0).lower()
```

`REQUIRED_PHRASES` add `"Names / Orders today / Cash / Target cash"`.

e2e `test_control_plane_serves_help`: `assert 'id="risk-head-names"' in html`.

- [ ] **Step 2: Run — FAIL.** Commit tests.

---

### Task 2: HTML, CSS, JS, help

- [ ] **Step 3: HTML** — Headroom markup from the requirements.

- [ ] **Step 4: CSS** — separate `#risk-head-names.fail` and `#risk-head-orders.fail` blocks.

- [ ] **Step 5: JS** — Rewrite `renderRiskUtilization` to fill the mounts. Names/Orders: used, `of {cap}`, `paintUtilTrack`, `fail` when used ≥ cap. Cash: `fmtPct(cash_weight)`, invested sub, cash-track like Portfolio. Target cash: `fmtPct(target_cash_weight)`. No container wipe.

- [ ] **Step 6: Help + README** — `how_risk` Headroom is Names / Orders today / Cash / Target cash; Names is the hero. Cockpit/README the same.

- [ ] **Step 7: Full suite PASS. Commit.**

---

## Spec coverage

Headroom tiles, keep wrapper id, rails, no wipe, help — tasked. No placeholders.
