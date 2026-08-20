# Header Session and Supervisor Chips Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans (this cycle chose executing-plans). Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Put Session and Supervisor chips in the Quiet cockpit header next to Pulse so RTH and runtime state are visible on every screen.

**Architecture:** HTML chips in `.brand`. Extend `renderDeskPulse` to paint Session from `status.clock` and Supervisor via `supervisorLabel`. Move `supervisorLabel` next to `pulseLabel` in `paint-portfolio.js`. No API change.

**Tech Stack:** Quiet cockpit HTML/CSS/JS, `helptext.py`, pytest.

**Requirements:** [`docs/requirements/2026-08-20-alphastrategy-header-chips-requirements.md`](../requirements/2026-08-20-alphastrategy-header-chips-requirements.md)

## Global Constraints

- Paper only. Five `#nav` screens. Locked tokens. No `window.confirm`. No live. No WebSockets. No charts.
- Keep `#desk-pulse`, `#desk-pulse-label`, `#metric-session`, `#act-beat-state`. Each JS part ≤ 400 lines.
- Tests: `PYTHONPATH=src python3 -m pytest tests/alphastrategy/ -q`.

## File map

- Modify: `index.html`, `styles.css`, `js/paint-portfolio.js`, `js/paint-activity.js`, `helptext.py`, `README.md`
- Test: `test_web_tokens.py`, `test_helptext.py`, `test_e2e_mocked.py`

---

### Task 1: Failing tests

- [ ] **Step 1: HTML/JS/CSS tests**

Add:

```python
def test_html_header_session_chips(html_text: str) -> None:
    header = html_text[html_text.find("<header>") : html_text.find("</header>")]
    assert 'id="desk-pulse"' in header
    assert 'id="desk-session"' in header
    assert 'id="desk-supervisor"' in header
    assert "desk-chip" in header
    port = html_text[
        html_text.find('id="screen-portfolio"') : html_text.find('id="screen-strategies"')
    ]
    assert 'id="desk-session"' not in port
    nav = re.search(r'<nav id="nav"[^>]*>(.*?)</nav>', html_text, re.DOTALL)
    screens = re.findall(r'data-screen="([^"]+)"', nav.group(1))
    assert screens == ["portfolio", "strategies", "run", "activity", "risk"]


def test_js_paints_header_chips(js_text: str) -> None:
    paint = js_text[
        js_text.find("function renderDeskPulse") : js_text.find("function renderStrategies")
    ]
    assert "desk-session" in paint
    assert "desk-supervisor" in paint
    assert "function supervisorLabel" in js_text
    assert "RTH session" in paint
    assert "window.confirm" not in js_text
    assert "window.state" not in js_text


def test_css_header_chip_tokens(css_text: str) -> None:
    session = re.search(r"#desk-session\.open\s*\{[^}]*\}", css_text)
    halt = re.search(r"#desk-supervisor\.halt\s*\{[^}]*\}", css_text)
    fail = re.search(r"#desk-supervisor\.fail\s*\{[^}]*\}", css_text)
    assert session is not None and "#10b981" in session.group(0).lower()
    assert halt is not None and "#f59e0b" in halt.group(0).lower()
    assert fail is not None and "#ef4444" in fail.group(0).lower()
```

`REQUIRED_PHRASES` add `"Pulse, Session, and Supervisor"`.

e2e `test_control_plane_serves_help`: `assert 'id="desk-session"' in html`.

- [ ] **Step 2: Run — FAIL.** Commit tests.

Run: `PYTHONPATH=src python3 -m pytest tests/alphastrategy/test_web_tokens.py::test_html_header_session_chips tests/alphastrategy/test_web_tokens.py::test_js_paints_header_chips tests/alphastrategy/test_web_tokens.py::test_css_header_chip_tokens tests/alphastrategy/test_helptext.py::test_help_text_contains_required_phrases tests/alphastrategy/test_e2e_mocked.py::test_control_plane_serves_help -q`

Expected: FAIL (missing ids / phrase).

---

### Task 2: HTML, CSS, JS, help

- [ ] **Step 3: HTML** — chips from the requirements, after `#desk-pulse`, before `alphastrategy · paper`.

- [ ] **Step 4: CSS** — `.desk-chip` and the three token blocks from the requirements. Separate blocks so the tests can regex each selector.

- [ ] **Step 5: JS** — Move `supervisorLabel` from `paint-activity.js` to `paint-portfolio.js` (next to `pulseLabel`). In `renderDeskPulse`, fill `#desk-session` and `#desk-supervisor`. Session: UNAVAILABLE / OPEN / CLOSED; toggle `open`. Supervisor: spoken label, `title` = raw state, `halt` / `fail` classes as on Activity Beat.

- [ ] **Step 6: Help + README** — Cockpit: Header shows Pulse, Session, and Supervisor; LIVE is still the beat, not Session. README Operator: OPEN / CLOSED is RTH; spoken Supervisor is runtime state.

- [ ] **Step 7: Full suite PASS. Commit.**

Run: `PYTHONPATH=src python3 -m pytest tests/alphastrategy/ -q`

Expected: PASS.

---

## Spec coverage

Header chips, keep Pulse, shared supervisorLabel, tokens, help — tasked. No placeholders.
