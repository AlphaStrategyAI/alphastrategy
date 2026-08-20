# Clock Session Continuity Tiles Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans (this cycle chose executing-plans). Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Paint Portfolio Clock as Session / Now / Next / Last glance tiles and remove the leftover `#clock-line`.

**Architecture:** Static metrics inside `#glance-clock`. `renderSessionMetrics` in `js/paint-portfolio.js` fills mounts from existing `status.clock`, `status.countdown`, and `status.last_rebalance_event`. No API change.

**Tech Stack:** Quiet cockpit HTML/CSS/JS, `helptext.py`, pytest.

**Requirements:** [`docs/requirements/2026-08-20-alphastrategy-clock-continuity-requirements.md`](../requirements/2026-08-20-alphastrategy-clock-continuity-requirements.md)

## Global Constraints

- Paper only. Five `#nav` screens. Locked tokens. No `window.confirm`. No live. No WebSockets. No charts.
- Keep `#metric-session`, `#metric-countdown`, `#metric-countdown-kind`, `#desk-session`. Each JS part ≤ 400 lines.
- JS must not contain `Gross cap`. Do not label a tile Live.
- Tests: `PYTHONPATH=src python3 -m pytest tests/alphastrategy/ -q`.

## File map

- Modify: `src/alphastrategy/web/static/index.html`, `src/alphastrategy/web/static/styles.css`, `src/alphastrategy/web/static/js/paint-portfolio.js`, `src/alphastrategy/helptext.py`, `README.md`, `tests/alphastrategy/test_web_tokens.py`
- Test: `tests/alphastrategy/test_web_tokens.py`, `tests/alphastrategy/test_helptext.py`, `tests/alphastrategy/test_e2e_mocked.py`

---

### Task 1: Failing tests

- [ ] **Step 1: HTML/JS**

In `test_html_glance_bands`, change the Clock slice delimiter from `#clock-line` to `#glance-positions`:

```python
    clock = html_text[html_text.find('id="glance-clock"') : html_text.find('id="glance-positions"')]
```

Add after `assert 'id="metric-countdown"' in clock`:

```python
    assert 'id="metric-clock-now"' in clock
    assert 'id="metric-last-rebalance"' in clock
    assert "metrics-4" in clock
    assert "hero" in clock
    assert ">Now<" in clock
    assert ">Last<" in clock
    assert 'id="clock-line"' not in html_text
```

Add:

```python
def test_js_paints_clock_continuity_tiles(js_text: str) -> None:
    paint = js_text[
        js_text.find("function renderSessionMetrics") : js_text.find("function renderBookDrift")
    ]
    assert "metric-clock-now" in paint
    assert "metric-last-rebalance" in paint
    assert "last_rebalance_event" in paint
    assert "clock-line" not in paint
    assert "Gross cap" not in js_text
    assert "window.confirm" not in js_text
    assert "window.state" not in js_text
```

`REQUIRED_PHRASES` add `"Session / Now / Next / Last"`.

e2e `test_control_plane_serves_help`: `assert 'id="metric-last-rebalance"' in html`.

- [ ] **Step 2: Run — FAIL.** Commit tests.

---

### Task 2: HTML, JS, help

- [ ] **Step 3: HTML** — Clock markup from the requirements. Delete `<p id="clock-line" …>`.

- [ ] **Step 4: CSS** — delete `.clock-line { … }` (unused). Keep `#metric-session.open` and `.metrics-2`.

- [ ] **Step 5: JS** — rewrite `renderSessionMetrics` to fill Now and Last. Drop every `clockLine` reference.

Now: if `clock.timestamp` or `clock.now` matches `^(\d{4}-\d{2}-\d{2})T(\d{2}:\d{2}(?::\d{2})?)`, value = time, sub = date; else value = raw or em dash.

Last: split `last_rebalance_event` on `:`. Value = `open`/`close`, sub = date. Missing: em dash.

Unavailable clock: Session `UNAVAILABLE`; Now / Next / Last and their subs em dash.

- [ ] **Step 6: Help + README** — Clock is Session / Now / Next / Last; Next is the hero. Keep `Book / Flatten budgets / Clock`.

- [ ] **Step 7: Full suite PASS. Commit.**

---

## Spec coverage

Clock tiles, remove clock-line, glance-bands slice, help — tasked. No placeholders.
