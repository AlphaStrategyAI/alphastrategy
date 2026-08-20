# Overlay Details Survive Refresh Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans (this cycle chose executing-plans). Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Keep an open **Tighten this sleeve** disclosure across the 5s refresh so overlay cards stay glance-then-action.

**Architecture:** `riskFormIsDirty` returns true when `#screen-risk details[open]` exists. Glance painters stay above the dirty return. No API change.

**Tech Stack:** Quiet cockpit JS, `helptext.py`, pytest.

**Requirements:** [`docs/requirements/2026-08-20-alphastrategy-overlay-details-poll-requirements.md`](../requirements/2026-08-20-alphastrategy-overlay-details-poll-requirements.md)

## Global Constraints

- Paper only. Five `#nav` screens. Locked tokens. No `window.confirm`. No live. `"Gross cap"` not in JS.
- Tests: `PYTHONPATH=src python3 -m pytest tests/alphastrategy/ -q`.

## File map

- Modify: `src/alphastrategy/web/static/js/paint-risk.js`, `src/alphastrategy/helptext.py`, `README.md`
- Test: `tests/alphastrategy/test_web_tokens.py`, `tests/alphastrategy/test_helptext.py`

---

### Task 1: Failing tests

- [ ] **Step 1**

Add:

```python
def test_js_risk_form_dirty_includes_open_details(js_text: str) -> None:
    fn = js_text.split("function riskFormIsDirty")[1].split("function renderRisk")[0]
    assert 'details[open]' in fn
    assert "#screen-risk" in fn
    risk_fn = js_text[js_text.find("function renderRisk") :]
    glance = risk_fn.find("renderTightenGlance")
    overlay = risk_fn.find("renderOverlayGlance")
    dirty = risk_fn.find("if (riskFormIsDirty())")
    assert glance != -1 and overlay != -1 and dirty != -1
    assert glance < dirty and overlay < dirty
    assert "window.confirm" not in js_text
    assert "window.state" not in js_text
```

`REQUIRED_PHRASES` add `"Tighten this sleeve stays open across the refresh"`.

- [ ] **Step 2: Run — FAIL.** Commit tests + docs.

Run: `PYTHONPATH=src python3 -m pytest tests/alphastrategy/test_web_tokens.py::test_js_risk_form_dirty_includes_open_details tests/alphastrategy/test_helptext.py::test_help_text_contains_required_phrases -q`

---

### Task 2: JS + help

- [ ] **Step 3:** At the top of `riskFormIsDirty`:

```javascript
    if (document.querySelector("#screen-risk details[open]")) return true;
```

- [ ] **Step 4:** `how_risk` + cockpit + README with the exact phrase.

- [ ] **Step 5:** Full suite PASS. Commit.

Run: `PYTHONPATH=src python3 -m pytest tests/alphastrategy/ -q`

---

## Spec coverage

| Requirement | Task |
| --- | --- |
| details[open] dirty | 1, 3 |
| glance still paints | 1 |
| Help phrase | 1, 4 |
