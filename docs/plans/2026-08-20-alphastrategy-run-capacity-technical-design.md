# Run Sleeves Capacity Tiles Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans (this cycle chose executing-plans). Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Paint Run Sleeves as Remaining / Spoken / Active / Idle glance tiles and name the empty sleeve list.

**Architecture:** HTML metrics inside `#run-book`. `renderRunSleeves` fills four mounts from existing `state.bundles`. No API change. Kill-switch band order unchanged.

**Tech Stack:** Quiet cockpit HTML/CSS/JS, `helptext.py`, pytest.

**Requirements:** [`docs/requirements/2026-08-20-alphastrategy-run-capacity-requirements.md`](../requirements/2026-08-20-alphastrategy-run-capacity-requirements.md)

## Global Constraints

- Paper only. Five `#nav` screens. Locked tokens. No `window.confirm`. No live. No WebSockets. No charts.
- Keep `#run-promote`, `#run-book`, `#run-recover`, `#run-flatten`, `#run-sleeves`. Each JS part ≤ 400 lines.
- Tests: `PYTHONPATH=src python3 -m pytest tests/alphastrategy/ -q`.

## File map

- Modify: `index.html`, `styles.css`, `js/paint-run.js`, `helptext.py`, `README.md`
- Test: `test_web_tokens.py`, `test_helptext.py`, `test_e2e_mocked.py`

---

### Task 1: Failing tests

- [ ] **Step 1: HTML/JS/CSS**

In `test_html_run_kill_switch_zones`, after `assert 'id="run-sleeves"' in book`, add:

```python
    assert 'id="run-remaining"' in book
    assert 'id="run-spoken"' in book
    assert 'id="run-count-active"' in book
    assert 'id="run-count-idle"' in book
    assert "metrics-4" in book
    assert "hero" in book
    assert ">Remaining<" in book
```

Add:

```python
def test_js_paints_run_capacity(js_text: str) -> None:
    paint = js_text[
        js_text.find("function renderRunSleeves") : js_text.find("function eventSummary")
    ]
    assert "run-remaining" in paint
    assert "run-spoken" in paint
    assert "run-count-active" in paint
    assert "run-count-idle" in paint
    assert "No sleeves yet" in paint
    assert "window.confirm" not in js_text
    assert "window.state" not in js_text


def test_css_run_remaining_tokens(css_text: str) -> None:
    warn = re.search(r"#run-remaining\.warn\s*\{[^}]*\}", css_text)
    fail = re.search(r"#run-remaining\.fail\s*\{[^}]*\}", css_text)
    assert warn is not None and "#f59e0b" in warn.group(0).lower()
    assert fail is not None and "#ef4444" in fail.group(0).lower()
```

`REQUIRED_PHRASES` add `"Remaining / Spoken / Active / Idle"`.

e2e `test_control_plane_serves_help`: `assert 'id="run-remaining"' in html`.

- [ ] **Step 2: Run — FAIL.** Commit tests.

---

### Task 2: HTML, CSS, JS, help

- [ ] **Step 3: HTML** — Sleeves metrics from the requirements, before `#run-sleeve-error`.

- [ ] **Step 4: CSS** — separate `#run-remaining.warn` and `#run-remaining.fail` blocks.

- [ ] **Step 5: JS** — In `renderRunSleeves`, fill Remaining / Spoken / Active / Idle from `bundles`. Empty list copy exact. Keep dirty-form skip and sleeve card controls.

- [ ] **Step 6: Help + README** — `how_run` still four bands; Sleeves is Remaining / Spoken / Active / Idle; Remaining is the hero. Cockpit/README the same.

- [ ] **Step 7: Full suite PASS. Commit.**

---

## Spec coverage

Sleeves tiles, empty copy, tokens, keep four bands, help — tasked. No placeholders.
