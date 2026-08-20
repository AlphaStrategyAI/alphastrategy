# Activity Beat Glance Tiles Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans (this cycle chose executing-plans). Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Paint Activity Beat as Pulse / Age / Interval / Supervisor glance tiles, keeping `#activity-heartbeat` as the Pulse hero.

**Architecture:** HTML metrics inside `#act-beat`. `renderActivity` fills four mounts from existing status/heartbeat. Spoken Supervisor labels live in `paint-activity.js`. No API change.

**Tech Stack:** Quiet cockpit HTML/CSS/JS, `helptext.py`, pytest.

**Requirements:** [`docs/requirements/2026-08-20-alphastrategy-activity-beat-requirements.md`](../requirements/2026-08-20-alphastrategy-activity-beat-requirements.md)

## Global Constraints

- Paper only. Five `#nav` screens. Locked tokens. No `window.confirm`. No live. No WebSockets. No charts.
- Keep `#act-beat`, `#activity-heartbeat`, `#activity-list`. Each JS part ≤ 400 lines.
- Tests: `PYTHONPATH=src python3 -m pytest tests/alphastrategy/ -q`.

## File map

- Modify: `index.html`, `styles.css`, `js/paint-activity.js`, `helptext.py`, `README.md`
- Test: `test_web_tokens.py`, `test_helptext.py`, `test_e2e_mocked.py`

---

### Task 1: Failing tests

- [ ] **Step 1: HTML/JS**

In `test_html_activity_tape_bands`, after `assert 'id="activity-heartbeat"' in beat`, add:

```python
    assert 'id="act-beat-age"' in beat
    assert 'id="act-beat-interval"' in beat
    assert 'id="act-beat-state"' in beat
    assert "metrics-4" in beat
    assert "hero" in beat
    assert ">Pulse<" in beat
```

Add:

```python
def test_js_paints_activity_beat(js_text: str) -> None:
    paint = js_text[
        js_text.find("function renderActivity") : js_text.find("RISK_TIGHTEN_GROUPS")
    ]
    assert "function supervisorLabel" in js_text
    assert "act-beat-age" in paint
    assert "act-beat-interval" in paint
    assert "act-beat-state" in paint
    assert "interval_seconds" in paint
    assert "IN SESSION" in js_text
    assert "window.confirm" not in js_text
```

```python
def test_css_activity_beat_pulse_tokens(css_text: str) -> None:
    live = re.search(r"#activity-heartbeat\.live\s*\{[^}]*\}", css_text)
    stale = re.search(r"#activity-heartbeat\.stale\s*\{[^}]*\}", css_text)
    dead = re.search(r"#activity-heartbeat\.dead\s*\{[^}]*\}", css_text)
    assert live is not None and "#10b981" in live.group(0).lower()
    assert stale is not None and "#f59e0b" in stale.group(0).lower()
    assert dead is not None and "#ef4444" in dead.group(0).lower()
```

`REQUIRED_PHRASES` add `"Pulse / Age / Interval / Supervisor"`.

e2e `test_control_plane_serves_help`: `assert 'id="act-beat-age"' in html`.

- [ ] **Step 2: Run — FAIL.** Commit tests.

---

### Task 2: HTML, CSS, JS, help

- [ ] **Step 3: HTML** — Beat markup from the requirements (Pulse hero = `#activity-heartbeat`).

- [ ] **Step 4: CSS**

```css
#activity-heartbeat.live {
  color: #10b981;
}

#activity-heartbeat.stale,
#act-beat-state.halt {
  color: #f59e0b;
}

#activity-heartbeat.dead,
#act-beat-state.fail {
  color: #ef4444;
}
```

- [ ] **Step 5: JS** — `supervisorLabel(state)` as in the requirements table. In `renderActivity`, fill Pulse/Age/Interval/Supervisor instead of the combined sentence. Toggle Pulse classes `live|stale|dead|missing`. Toggle Supervisor `halt` when halted, `fail` when flattening or stopped.

- [ ] **Step 6: Help + README** — `how_activity` Beat is Pulse / Age / Interval / Supervisor; Pulse is the hero. Cockpit/README Activity the same.

- [ ] **Step 7: Full suite PASS. Commit.**

---

## Spec coverage

Beat tiles, keep `#activity-heartbeat`, spoken Supervisor, tokens, help — tasked. No placeholders.
