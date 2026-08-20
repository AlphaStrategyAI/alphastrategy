# Halt Next Held Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans (this cycle chose executing-plans). Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Keep Clock Next as time-to-window, but mark it held (halt/warn) while Supervisor is HALTED so the hero cannot look like the next fire.

**Architecture:** Paint-only in `renderSessionMetrics`. API `countdown` unchanged. Sub becomes `held · {open|close}` and `#metric-countdown` takes class `warn` when halted.

**Tech Stack:** Quiet cockpit JS/CSS, helptext, pytest.

**Requirements:** [`docs/requirements/2026-08-20-alphastrategy-halt-next-held-requirements.md`](../requirements/2026-08-20-alphastrategy-halt-next-held-requirements.md)

## Global Constraints

- Paper only. Five `#nav` screens. Locked tokens. No `window.confirm`. No live.
- `"Gross cap"` must not appear in assembled JS.
- `renderBanners` keeps a **single** `const reason`.
- Keep tutorial substring `Next rebalance`.
- Tests: `PYTHONPATH=src python3 -m pytest tests/alphastrategy/ -q`.

## File map

- Modify: `src/alphastrategy/web/static/js/paint-portfolio.js`, `src/alphastrategy/web/static/styles.css`, `src/alphastrategy/helptext.py`, `README.md`
- Test: `tests/alphastrategy/test_web_tokens.py`, `tests/alphastrategy/test_helptext.py`

---

### Task 1: Failing tests

- [ ] **Step 1: JS + CSS + help**

In `tests/alphastrategy/test_web_tokens.py` add:

```python
def test_js_clock_next_held_while_halted(js_text: str) -> None:
    session = js_text[
        js_text.find("function renderSessionMetrics") : js_text.find("function bookDrift")
    ]
    assert "held · " in session
    assert 'countEl.classList.add("warn")' in session or 'classList.add("warn")' in session
    assert "fmtCountdown" in session
    assert "countdown.next_rebalance" in session
    assert "halted" in session
    assert "Gross cap" not in js_text
    assert "window.confirm" not in js_text


def test_css_countdown_warn_uses_halt_token(css_text: str) -> None:
    countdown = re.search(r"#metric-countdown\.warn\s*\{[^}]*\}", css_text)
    last = re.search(r"#metric-last-rebalance\.warn\s*\{[^}]*\}", css_text)
    assert countdown is not None and "#f59e0b" in countdown.group(0).lower()
    assert last is not None and "#f59e0b" in last.group(0).lower()
```

If `classList.add("warn")` also matches Last spent in that slice, require the countdown-specific add: `countEl.classList.add("warn")`.

`REQUIRED_PHRASES` add `"Clock Next is held while Supervisor is HALTED"`. Keep `"Next rebalance"`.

- [ ] **Step 2: Run — FAIL.** Commit tests + docs.

Run: `PYTHONPATH=src python3 -m pytest tests/alphastrategy/test_web_tokens.py::test_js_clock_next_held_while_halted tests/alphastrategy/test_web_tokens.py::test_css_countdown_warn_uses_halt_token tests/alphastrategy/test_helptext.py::test_help_text_contains_required_phrases tests/alphastrategy/test_helptext.py::test_tutorials_come_before_how_to_jobs -q`

---

### Task 2: Implementation

- [ ] **Step 3: `renderSessionMetrics` countdown**

Replace the countdown branch:

```javascript
    if (countEl) countEl.classList.remove("warn");
    if (countdown) {
      countEl.textContent = fmtCountdown(countdown.seconds);
      const kind = countdown.next_rebalance || "—";
      const halted =
        (state.status && state.status.state) === "halted" ||
        Boolean(state.status && state.status.halted);
      if (halted) {
        countEl.classList.add("warn");
        kindEl.textContent = "held · " + kind;
      } else {
        kindEl.textContent = kind;
      }
    } else {
      countEl.textContent = "—";
      kindEl.textContent = "—";
    }
```

On the clock-error path, also `countEl.classList.remove("warn")` (already at the top of the countdown block — call remove before the `if (!clock)` return, or in both branches). Put `if (countEl) countEl.classList.remove("warn");` immediately after `applySessionChip(sessionEl)` so UNAVAILABLE clears a leftover warn.

Keep `paint-portfolio.js` ≤ 400 lines.

- [ ] **Step 4: CSS**

After `#metric-session.warn`:

```css
#metric-countdown.warn {
  color: #f59e0b;
}
```

- [ ] **Step 5: help + README**

`how_portfolio` after Clock Last sentence: `Clock Next is held while Supervisor is HALTED.`

README Clock sentence: Next is the hero; it is held while Supervisor is HALTED.

- [ ] **Step 6: Full suite PASS.** Commit.

Run: `PYTHONPATH=src python3 -m pytest tests/alphastrategy/ -q`
