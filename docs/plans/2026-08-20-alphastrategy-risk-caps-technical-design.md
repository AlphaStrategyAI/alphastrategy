# Risk Caps Glance Tiles Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans (this cycle chose executing-plans). Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Paint Risk Caps as Gross cap / Name cap / Names / Orders today glance tiles, with Long only as a line under the tiles.

**Architecture:** Static metrics inside `#risk-account-caps`. `renderRiskCaps` fills four mounts plus `#risk-cap-long` from existing `risk.account`. Spoken labels stay in HTML / `policyLabel`. No API change.

**Tech Stack:** Quiet cockpit HTML/JS, `helptext.py`, pytest.

**Requirements:** [`docs/requirements/2026-08-20-alphastrategy-risk-caps-requirements.md`](../requirements/2026-08-20-alphastrategy-risk-caps-requirements.md)

## Global Constraints

- Paper only. Five `#nav` screens. Locked tokens. No `window.confirm`. No live. No WebSockets. No charts.
- Keep `#risk-caps`, `#risk-account-caps`, `#risk-headroom`, `#risk-tighten`, `#risk-overlays`. Each JS part ≤ 400 lines.
- JS must not contain the string `Gross cap`. Do not label a tile Live.
- Tests: `PYTHONPATH=src python3 -m pytest tests/alphastrategy/ -q`.

## File map

- Modify: `index.html`, `js/paint-risk.js`, `helptext.py`, `README.md`
- Test: `test_web_tokens.py`, `test_helptext.py`, `test_e2e_mocked.py`

---

### Task 1: Failing tests

- [ ] **Step 1: HTML/JS**

In `test_html_risk_glance_bands`, after `assert 'id="risk-account-caps"' in caps`, add:

```python
    assert 'id="risk-cap-gross"' in caps
    assert 'id="risk-cap-name"' in caps
    assert 'id="risk-cap-names"' in caps
    assert 'id="risk-cap-orders"' in caps
    assert 'id="risk-cap-long"' in caps
    assert "metrics-4" in caps
    assert "hero" in caps
    assert ">Gross cap<" in caps
    assert ">Name cap<" in caps
```

Add:

```python
def test_js_paints_risk_caps_tiles(js_text: str) -> None:
    paint = js_text[
        js_text.find("function renderRiskCaps") : js_text.find("function buildRiskInputs")
    ]
    assert "risk-cap-gross" in paint
    assert "risk-cap-name" in paint
    assert "risk-cap-names" in paint
    assert "risk-cap-orders" in paint
    assert "risk-cap-long" in paint
    assert "max_gross" in paint
    assert "max_name_weight" in paint
    assert "max_orders_per_day" in paint
    assert "fmtPct" in paint
    assert "Gross cap" not in js_text
    assert "window.confirm" not in js_text
    assert "window.state" not in js_text
```

`REQUIRED_PHRASES` add `"Gross cap / Name cap / Names / Orders today"`.

e2e `test_control_plane_serves_help`: `assert 'id="risk-cap-gross"' in html`.

- [ ] **Step 2: Run — FAIL.** Commit tests.

---

### Task 2: HTML, JS, help

- [ ] **Step 3: HTML** — Caps markup from the requirements. `#risk-utilization` keeps `class="risk-caps nums"`.

- [ ] **Step 4: JS** — `renderRiskCaps` fills the four value mounts and `#risk-cap-long`. Do not loop `NUMERIC_CAPS` into rows. Do not write `Gross cap` in JS. Use `fmtPct` for gross and name cap; integers for names and orders today; `policyLabel("long_only")` for the line.

- [ ] **Step 5: Help + README** — `how_risk` Caps is Gross cap / Name cap / Names / Orders today; Gross cap is the hero. Cockpit/README the same.

- [ ] **Step 6: Full suite PASS. Commit.**

---

## Spec coverage

Caps tiles, keep wrapper id, no Gross cap in JS, Long only line, help — tasked. No placeholders.
