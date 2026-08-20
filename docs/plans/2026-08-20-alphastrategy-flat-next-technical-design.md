# Flat Next Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans (this cycle chose executing-plans). Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Mark Clock Next flat (fail-red) while the paper account is flattened or flattening, without changing halted held/warn.

**Architecture:** Paint-only in `renderSessionMetrics`. Halted branch unchanged. Flattened branch uses class `fail` and sub `flat · {open|close}`. API `countdown` unchanged.

**Tech Stack:** Quiet cockpit JS/CSS, helptext, pytest.

**Requirements:** [`docs/requirements/2026-08-20-alphastrategy-flat-next-requirements.md`](../requirements/2026-08-20-alphastrategy-flat-next-requirements.md)

## Global Constraints

- Paper only. Five `#nav` screens. Locked tokens. No `window.confirm`. No live.
- `"Gross cap"` must not appear in assembled JS.
- `renderBanners` keeps a **single** `const reason`.
- Keep tutorial substring `Next rebalance`. Keep halted `held · `.
- Tests: `PYTHONPATH=src python3 -m pytest tests/alphastrategy/ -q`.

## File map

- Modify: `src/alphastrategy/web/static/js/paint-portfolio.js`, `src/alphastrategy/web/static/styles.css`, `src/alphastrategy/helptext.py`, `README.md`
- Test: `tests/alphastrategy/test_web_tokens.py`, `tests/alphastrategy/test_helptext.py`

---

### Task 1: Failing tests

- [ ] **Step 1: JS + CSS + help**

In `tests/alphastrategy/test_web_tokens.py` add:

```python
def test_js_clock_next_flat_while_flattened(js_text: str) -> None:
    session = js_text[
        js_text.find("function renderSessionMetrics") : js_text.find("function bookDrift")
    ]
    assert "flat · " in session
    assert 'countEl.classList.add("fail")' in session
    assert "held · " in session
    assert 'countEl.classList.add("warn")' in session
    assert "fmtCountdown" in session
    assert "flattened" in session
    assert "Gross cap" not in js_text
    assert "window.confirm" not in js_text


def test_css_countdown_fail_uses_kill_token(css_text: str) -> None:
    fail = re.search(r"#metric-countdown\.fail\s*\{[^}]*\}", css_text)
    warn = re.search(r"#metric-countdown\.warn\s*\{[^}]*\}", css_text)
    assert fail is not None and "#ef4444" in fail.group(0).lower()
    assert warn is not None and "#f59e0b" in warn.group(0).lower()
```

`REQUIRED_PHRASES` add `"Clock Next is flat while the paper account is flattened"`.

- [ ] **Step 2: Run — FAIL.** Commit tests + docs.

Run: `PYTHONPATH=src python3 -m pytest tests/alphastrategy/test_web_tokens.py::test_js_clock_next_flat_while_flattened tests/alphastrategy/test_web_tokens.py::test_css_countdown_fail_uses_kill_token tests/alphastrategy/test_web_tokens.py::test_js_clock_next_held_while_halted tests/alphastrategy/test_helptext.py::test_help_text_contains_required_phrases -q`

---

### Task 2: Implementation

- [ ] **Step 3: countdown fork**

`if (countEl) countEl.classList.remove("warn", "fail");`

Inside `if (countdown)` after computing `kind` and `halted`:

```javascript
      const flattened =
        Boolean(state.status && state.status.flattened) ||
        (state.status &&
          (state.status.state === "stopped" || state.status.state === "flattening"));
      if (halted) {
        countEl.classList.add("warn");
        kindEl.textContent = "held · " + kind;
      } else if (flattened) {
        countEl.classList.add("fail");
        kindEl.textContent = "flat · " + kind;
      } else {
        kindEl.textContent = kind;
      }
```

Keep `paint-portfolio.js` ≤ 400 lines. `renderBanners` still one `const reason`.

- [ ] **Step 4: CSS**

After `#metric-countdown.warn`:

```css
#metric-countdown.fail {
  color: #ef4444;
}
```

- [ ] **Step 5: help + README**

`how_portfolio` after the held sentence: `Clock Next is flat while the paper account is flattened.`

README Clock: Next is held while HALTED and flat while the paper account is flattened.

- [ ] **Step 6: Full suite PASS.** Commit.

Run: `PYTHONPATH=src python3 -m pytest tests/alphastrategy/ -q`
