# Risk Sleeve Overlay Glance Tiles Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans (this cycle chose executing-plans). Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Paint Risk Sleeve overlays as Spoken / Overlays / Tighter / Idle glance tiles, with allocation as a rail on each card.

**Architecture:** HTML metrics inside `#risk-overlays`. `renderRisk` fills four mounts from existing `state.risk.sleeves` and `bundles.paper`. `overlayTighterCount` compares effective sleeve policy to account. No API change.

**Tech Stack:** Quiet cockpit HTML/CSS/JS, `helptext.py`, pytest.

**Requirements:** [`docs/requirements/2026-08-20-alphastrategy-risk-overlays-requirements.md`](../requirements/2026-08-20-alphastrategy-risk-overlays-requirements.md)

## Global Constraints

- Paper only. Five `#nav` screens. Locked tokens. No `window.confirm`. No live. No WebSockets. No charts.
- Keep `#risk-caps`, `#risk-headroom`, `#risk-tighten`, `#risk-overlays`, `#risk-sleeves`. Each JS part ≤ 400 lines.
- Do not clone Run allocation forms onto Risk. Do not label a tile Live.
- Tests: `PYTHONPATH=src python3 -m pytest tests/alphastrategy/ -q`.

## File map

- Modify: `index.html`, `styles.css`, `js/paint-risk.js`, `helptext.py`, `README.md`
- Test: `test_web_tokens.py`, `test_helptext.py`, `test_e2e_mocked.py`

---

### Task 1: Failing tests

- [ ] **Step 1: HTML/JS/CSS**

In `test_html_risk_glance_bands`, after `assert 'id="risk-sleeves"' in overlays`, add:

```python
    assert 'id="risk-overlay-spoken"' in overlays
    assert 'id="risk-overlay-count"' in overlays
    assert 'id="risk-overlay-tighter"' in overlays
    assert 'id="risk-overlay-idle"' in overlays
    assert "metrics-4" in overlays
    assert "hero" in overlays
    assert ">Spoken<" in overlays
```

Add:

```python
def test_js_paints_risk_overlay_glance(js_text: str) -> None:
    paint = js_text[js_text.find("function overlayTighterCount") :]
    assert "function overlayTighterCount" in js_text
    assert "risk-overlay-spoken" in paint
    assert "risk-overlay-count" in paint
    assert "risk-overlay-tighter" in paint
    assert "risk-overlay-idle" in paint
    assert "paintUtilTrack" in paint
    assert "No sleeve overlays" in paint
    assert "tighter than account" in paint
    assert "window.confirm" not in js_text
    assert "window.state" not in js_text


def test_css_risk_overlay_tokens(css_text: str) -> None:
    warn = re.search(r"#risk-overlay-spoken\.warn\s*\{[^}]*\}", css_text)
    fail = re.search(r"#risk-overlay-spoken\.fail\s*\{[^}]*\}", css_text)
    tight = re.search(r"#risk-overlay-tighter\.warn\s*\{[^}]*\}", css_text)
    assert warn is not None and "#f59e0b" in warn.group(0).lower()
    assert fail is not None and "#ef4444" in fail.group(0).lower()
    assert tight is not None and "#f59e0b" in tight.group(0).lower()
```

`REQUIRED_PHRASES` add `"Spoken / Overlays / Tighter / Idle"`.

e2e `test_control_plane_serves_help`: `assert 'id="risk-overlay-spoken"' in html`.

- [ ] **Step 2: Run — FAIL.** Commit tests.

Run: `PYTHONPATH=src python3 -m pytest tests/alphastrategy/test_web_tokens.py::test_html_risk_glance_bands tests/alphastrategy/test_web_tokens.py::test_js_paints_risk_overlay_glance tests/alphastrategy/test_web_tokens.py::test_css_risk_overlay_tokens tests/alphastrategy/test_helptext.py::test_help_text_contains_required_phrases tests/alphastrategy/test_e2e_mocked.py::test_control_plane_serves_help -q`

Expected: FAIL (missing ids / phrase).

---

### Task 2: HTML, CSS, JS, help

- [ ] **Step 3: HTML** — overlay metrics from the requirements, before `#risk-sleeves`.

- [ ] **Step 4: CSS** — separate `#risk-overlay-spoken.warn`, `#risk-overlay-spoken.fail`, `#risk-overlay-tighter.warn` blocks.

- [ ] **Step 5: JS** — `overlayTighterCount(overlay, account)`. `renderOverlayGlance` fills the four tiles (even when the form is dirty). Each sleeve card: allocation + `paintUtilTrack`, tighter line, then the existing tighten form. Empty copy exact.

- [ ] **Step 6: Help + README** — `how_risk` Spoken / Overlays / Tighter / Idle; Spoken is the hero; allocation is a rail, not only text. Cockpit/README the same. Drop “allocation as text.”

- [ ] **Step 7: Full suite PASS. Commit.**

Run: `PYTHONPATH=src python3 -m pytest tests/alphastrategy/ -q`

Expected: PASS.

---

## Spec coverage

Overlay tiles, allocation rail, tighter count, empty copy, tokens, help — tasked. No placeholders.
