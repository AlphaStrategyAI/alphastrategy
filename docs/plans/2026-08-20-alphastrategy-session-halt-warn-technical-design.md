# Session Halt Warn Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans (this cycle chose executing-plans). Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Keep Session as the RTH OPEN/CLOSED word, but stop painting it running-green while Supervisor is HALTED.

**Architecture:** One `applySessionChip` helper paints `#desk-session` and `#metric-session`. OPEN + halted uses class `warn` (`#f59e0b`). OPEN otherwise keeps `open` (`#10b981`).

**Tech Stack:** Quiet cockpit JS/CSS, helptext, pytest.

**Requirements:** [`docs/requirements/2026-08-20-alphastrategy-session-halt-warn-requirements.md`](../requirements/2026-08-20-alphastrategy-session-halt-warn-requirements.md)

## Global Constraints

- Paper only. Five `#nav` screens. Locked tokens. No `window.confirm`. No live.
- `"Gross cap"` must not appear in assembled JS.
- `renderBanners` keeps a **single** `const reason`.
- Pulse LIVE stays the 20s beat. Session still names RTH.
- Tests: `PYTHONPATH=src python3 -m pytest tests/alphastrategy/ -q`.

## File map

- Modify: `src/alphastrategy/web/static/js/paint-portfolio.js`, `src/alphastrategy/web/static/styles.css`, `src/alphastrategy/helptext.py`, `README.md`
- Test: `tests/alphastrategy/test_web_tokens.py`, `tests/alphastrategy/test_helptext.py`

---

### Task 1: Failing tests

- [ ] **Step 1: JS + CSS + help**

In `tests/alphastrategy/test_web_tokens.py` `test_js_paints_header_chips` add:

```python
    assert "function applySessionChip" in js_text
    assert "applySessionChip" in paint
```

Add:

```python
def test_js_session_chip_warns_when_halted_open(js_text: str) -> None:
    assert "function applySessionChip" in js_text
    body = js_text[
        js_text.find("function applySessionChip") : js_text.find("function renderSessionMetrics")
    ]
    assert "halted" in body
    assert '"warn"' in body
    assert '"open"' in body
    session = js_text[
        js_text.find("function renderSessionMetrics") : js_text.find("function pulseLabel")
    ]
    assert "applySessionChip" in session
    pulse = js_text[
        js_text.find("function renderDeskPulse") : js_text.find("function renderStrategies")
    ]
    assert "applySessionChip" in pulse
    assert "Gross cap" not in js_text
    assert "window.confirm" not in js_text


def test_css_session_warn_uses_halt_token(css_text: str) -> None:
    desk_warn = re.search(r"#desk-session\.warn\s*\{[^}]*\}", css_text)
    metric_warn = re.search(r"#metric-session\.warn\s*\{[^}]*\}", css_text)
    desk_open = re.search(r"#desk-session\.open\s*\{[^}]*\}", css_text)
    assert desk_warn is not None and "#f59e0b" in desk_warn.group(0).lower()
    assert metric_warn is not None and "#f59e0b" in metric_warn.group(0).lower()
    assert desk_open is not None and "#10b981" in desk_open.group(0).lower()
```

If `applySessionChip` is defined *after* `renderSessionMetrics`, slice from `function applySessionChip` to the next `function `. Keep the asserts: helper body mentions `halted`, `"warn"`, `"open"`; both painters call it.

`REQUIRED_PHRASES` add `"Session OPEN is halt color while Supervisor is HALTED"`.

- [ ] **Step 2: Run — FAIL.** Commit tests + docs.

Run: `PYTHONPATH=src python3 -m pytest tests/alphastrategy/test_web_tokens.py::test_js_paints_header_chips tests/alphastrategy/test_web_tokens.py::test_js_session_chip_warns_when_halted_open tests/alphastrategy/test_web_tokens.py::test_css_session_warn_uses_halt_token tests/alphastrategy/test_helptext.py::test_help_text_contains_required_phrases -q`

---

### Task 2: Implementation

- [ ] **Step 3: `applySessionChip`**

In `src/alphastrategy/web/static/js/paint-portfolio.js`, before `renderSessionMetrics`:

```javascript
  function applySessionChip(el) {
    if (!el) return;
    const clock = state.status && state.status.clock;
    const halted = (state.status && state.status.state) === "halted";
    el.classList.remove("open", "warn");
    if (!clock || clock.error) {
      el.textContent = "UNAVAILABLE";
      return;
    }
    if (clock.is_open) {
      el.textContent = "OPEN";
      el.classList.add(halted ? "warn" : "open");
      return;
    }
    el.textContent = "CLOSED";
  }
```

`renderSessionMetrics`: delete `sessionEl.classList.remove("open")` and the OPEN/CLOSED/UNAVAILABLE text/class assignments. Call `applySessionChip(sessionEl)` at the start of clock handling (still dash countdown/Now/Last on error). Keep countdown and Last spent paint.

`renderDeskPulse` session block:

```javascript
    const sessionEl = document.getElementById("desk-session");
    if (sessionEl) {
      sessionEl.title = "RTH session";
      applySessionChip(sessionEl);
    }
```

Keep `paint-portfolio.js` ≤ 400 lines. `"Gross cap"` stays out.

- [ ] **Step 4: CSS**

After `#desk-session.open`:

```css
#desk-session.warn {
  color: #f59e0b;
}
```

After `#metric-session.open`:

```css
#metric-session.warn {
  color: #f59e0b;
}
```

- [ ] **Step 5: help + README**

Cockpit and `how_portfolio`: `Session OPEN is halt color while Supervisor is HALTED.`

README Operator (header chips sentence): Session OPEN is not running-green while HALTED.

- [ ] **Step 6: Full suite PASS.** Commit.

Run: `PYTHONPATH=src python3 -m pytest tests/alphastrategy/ -q`
