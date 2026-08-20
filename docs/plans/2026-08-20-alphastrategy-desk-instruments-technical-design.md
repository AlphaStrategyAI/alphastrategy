# Desk instruments Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans (this cycle chose executing-plans). Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Header Pulse / Session / Supervisor read as instruments, Book takes LIMIT warn/fail color, and hero numbers scale to 2.35rem, without new tokens or a sixth screen.

**Architecture:** CSS gives chips metric chrome and Book a reserved left rail. `paintBookLimitRail` in `paint-rails.js` colors the rail from flattened vs `live_limit`. `renderPortfolio` calls it. Help names the instruments and the Book LIMIT color.

**Tech Stack:** Quiet cockpit HTML/CSS/JS, pytest, helptext, README.

**Requirements:** [`docs/requirements/2026-08-20-alphastrategy-desk-instruments-requirements.md`](../requirements/2026-08-20-alphastrategy-desk-instruments-requirements.md)

## Global Constraints

- Paper only. Five `#nav` screens. Locked tokens. No `window.confirm`. No live.
- `"Gross cap"` must not appear in assembled JS. Do not hardcode `Order size` in JS.
- Caps stay four tiles. Keep `#risk-cap-order`.
- Heartbeat does not flatten. GET must not flatten.
- `paint-portfolio.js` stays ≤ 400 newlines. Prefer new JS in `paint-rails.js`.
- Tests: `PYTHONPATH=src python3 -m pytest tests/alphastrategy/ -q`.

## File map

- Modify: `src/alphastrategy/web/static/styles.css`, `src/alphastrategy/web/static/js/paint-rails.js`, `src/alphastrategy/web/static/js/paint-portfolio.js`, `src/alphastrategy/helptext.py`, `README.md`
- Test: `tests/alphastrategy/test_web_tokens.py`, `tests/alphastrategy/test_helptext.py`

---

### Task 1: Failing tests

- [ ] **Step 1: Write the failing tests**

`REQUIRED_PHRASES` add:

```python
    "Book takes LIMIT color while a next rebalance will flatten",
    "Header Pulse, Session, and Supervisor are instruments",
```

In `test_css_desk_pulse_tokens` after existing asserts:

```python
    live = re.search(r"\.desk-pulse\.live\s*\{[^}]*\}", css_text)
    assert live is not None and "#10b981" in live.group(0).lower()
    assert "border" in live.group(0).lower() or "border-color" in live.group(0).lower()
```

`test_css_glance_bands`: change `"1.85rem"` to `"2.35rem"`.

After `test_css_header_chip_tokens`:

```python
def test_css_glance_book_limit_rail(css_text: str) -> None:
    warn = re.search(r"#glance-book\.warn\s*\{[^}]*\}", css_text)
    fail = re.search(r"#glance-book\.fail\s*\{[^}]*\}", css_text)
    assert warn is not None and "#f59e0b" in warn.group(0).lower()
    assert fail is not None and "#ef4444" in fail.group(0).lower()
```

After `test_js_paints_live_limit_banner`:

```python
def test_js_paints_book_limit_rail(js_text: str) -> None:
    assert "function paintBookLimitRail" in js_text
    paint = js_text[
        js_text.find("function paintBookLimitRail") : js_text.find("function renderGrossUtilization")
    ]
    assert "glance-book" in paint
    assert "live_limit" in paint
    assert 'classList.add("warn")' in paint
    assert 'classList.add("fail")' in paint
    port = js_text[
        js_text.find("function renderPortfolio") : js_text.find("function pulseLabel")
    ]
    assert "paintBookLimitRail(" in port
    assert "Gross cap" not in js_text
    assert "window.confirm" not in js_text
    assert "window.state" not in js_text
```

- [ ] **Step 2: Run the new tests and confirm they fail**

```bash
PYTHONPATH=src python3 -m pytest tests/alphastrategy/test_web_tokens.py::test_css_desk_pulse_tokens tests/alphastrategy/test_web_tokens.py::test_css_glance_bands tests/alphastrategy/test_web_tokens.py::test_css_glance_book_limit_rail tests/alphastrategy/test_web_tokens.py::test_js_paints_book_limit_rail tests/alphastrategy/test_helptext.py::test_help_text_contains_required_phrases -q
```

- [ ] **Step 3: Commit tests and docs**

---

### Task 2: Implement

- [ ] **Step 4: CSS**

`.desk-pulse` and `.desk-chip`: add `border: 1px solid #2a3142`, `background: #0b0e14`, `border-radius: 4px`, padding `0.15rem 0.45rem`.

`.desk-pulse.live { color: #10b981; border-color: #10b981; }`
`.desk-pulse.stale { color: #f59e0b; border-color: #f59e0b; }`
`.desk-pulse.dead { color: #ef4444; border-color: #ef4444; }`
`#desk-session.warn { color: #f59e0b; border-color: #f59e0b; }`
`#desk-supervisor.halt { color: #f59e0b; border-color: #f59e0b; }`
`#desk-supervisor.fail { color: #ef4444; border-color: #ef4444; }`
`#desk-session.open` keep color `#10b981`; add `border-color: #10b981`.

```css
#glance-book {
  border-left: 2px solid transparent;
  padding-left: 0.65rem;
}

#glance-book.warn {
  border-left-color: #f59e0b;
}

#glance-book.fail {
  border-left-color: #ef4444;
}
```

`.metric.hero .metric-value { font-size: 2.35rem; }`

- [ ] **Step 5: JS**

In `paint-rails.js` after `renderLiveLimitBanner`:

```javascript
  function paintBookLimitRail() {
    const band = document.getElementById("glance-book");
    if (!band) return;
    band.classList.remove("warn", "fail");
    const flattened =
      Boolean(state.status && state.status.flattened) ||
      (state.status &&
        (state.status.state === "stopped" || state.status.state === "flattening"));
    if (flattened) {
      band.classList.add("fail");
      return;
    }
    const limit = utilization().live_limit;
    if (limit && limit.reason) band.classList.add("warn");
  }
```

In `renderPortfolio`, immediately before `renderBanners();`:

```javascript
    paintBookLimitRail();
```

`paint-rails.js` and `paint-portfolio.js` stay ≤ 400 newlines.

- [ ] **Step 6: Help and README**

Add `Book takes LIMIT color while a next rebalance will flatten. ` and `Header Pulse, Session, and Supervisor are instruments. ` to `cockpit` (after Header shows Pulse…), `how_portfolio` (after Clock Next flatten sentence), `halt_flatten` (after LIMIT names a next send).

README Operator: both sentences after the LIMIT send sentence. Keep `Next rebalance`.

- [ ] **Step 7: Full suite**

```bash
PYTHONPATH=src python3 -m pytest tests/alphastrategy/ -q
```

- [ ] **Step 8: Commit, push, update PR**
