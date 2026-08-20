# Activity Tape Spent Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans (this cycle chose executing-plans). Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Paint spent rebalances on Activity Tape and Blotter with the same word Clock Last already uses, and stop coloring a torn batch as running green.

**Architecture:** Count `event=rebalance` rows with `complete === false`. Rebalances hero keeps the total count; a new sub `#act-count-spent` shows `{n} spent`. Hero uses halt/warn when spent &gt; 0. Blotter suffix and detail say spent.

**Tech Stack:** Quiet cockpit HTML/CSS/JS, `helptext.py`, pytest.

**Requirements:** [`docs/requirements/2026-08-20-alphastrategy-tape-spent-requirements.md`](../requirements/2026-08-20-alphastrategy-tape-spent-requirements.md)

## Global Constraints

- Paper only. Five `#nav` screens. Locked tokens. No `window.confirm`. No live.
- `"Gross cap"` must not appear in assembled JS.
- `renderBanners` keeps a **single** `const reason`.
- Tests: `PYTHONPATH=src python3 -m pytest tests/alphastrategy/ -q`.

## File map

- Modify: `src/alphastrategy/web/static/index.html`, `src/alphastrategy/web/static/js/paint-activity.js`, `src/alphastrategy/web/static/styles.css`, `src/alphastrategy/helptext.py`, `README.md`
- Test: `tests/alphastrategy/test_web_tokens.py`, `tests/alphastrategy/test_helptext.py`

---

### Task 1: Failing tests

- [ ] **Step 1: HTML / JS / CSS / help**

In `test_html_activity_bands` tape asserts, add:

```python
    assert 'id="act-count-spent"' in tape
    assert ">Rebalances<" in tape
```

Replace `test_js_activity_incomplete_rebalance` with:

```python
def test_js_activity_spent_rebalance(js_text: str) -> None:
    summary = js_text[
        js_text.find("function eventSummary") : js_text.find("function renderActivity")
    ]
    paint = js_text[
        js_text.find("function renderActivity") : js_text.find("RISK_TIGHTEN_GROUPS")
    ]
    assert "complete === false" in summary
    assert "spent" in summary
    assert "incomplete" not in summary
    assert '["Spent"' in summary or '"Spent"' in summary
    assert "act-count-spent" in paint
    assert "warn" in paint
    assert "Gross cap" not in js_text
    assert "window.confirm" not in js_text
    assert "window.state" not in js_text
```

In `test_js_paints_activity_tape` add:

```python
    assert '"act-count-spent"' in paint
```

Add:

```python
def test_css_rebalance_spent_warn_token(css_text: str) -> None:
    reb = re.search(r"#act-count-rebalance\.warn\s*\{[^}]*\}", css_text)
    assert reb is not None and "#f59e0b" in reb.group(0).lower()
```

`REQUIRED_PHRASES` add `"Tape Rebalances sub names spent"`. Keep `"incomplete rebalance"`.

- [ ] **Step 2: Run — FAIL.** Commit tests + docs.

Run: `PYTHONPATH=src python3 -m pytest tests/alphastrategy/test_web_tokens.py::test_html_activity_bands tests/alphastrategy/test_web_tokens.py::test_js_activity_spent_rebalance tests/alphastrategy/test_web_tokens.py::test_js_paints_activity_tape tests/alphastrategy/test_web_tokens.py::test_css_rebalance_spent_warn_token tests/alphastrategy/test_helptext.py::test_help_text_contains_required_phrases -q`

---

### Task 2: Paint + help

- [ ] **Step 3: HTML**

In `src/alphastrategy/web/static/index.html` Rebalances hero, after `#act-count-rebalance`:

```html
            <div id="act-count-spent" class="metric-sub">—</div>
```

- [ ] **Step 4: JS**

`eventSummary` rebalance branch: `const spent = ev.complete === false ? "spent" : "";` and use `spent` in the return string. No `incomplete`.

`eventDetail` rebalance fields:

```javascript
          ["Session", ev.session_event],
          ["Orders", ev.orders],
          ["Spent", ev.complete === false ? "yes" : "no"],
```

In `renderActivity`, count `spent` when `ev.event === "rebalance" && ev.complete === false`. After `setTape` for rebalance, override classes:

```javascript
    setTape("act-count-rebalance", counts.rebalance, "status-running");
    const rebEl = document.getElementById("act-count-rebalance");
    const spentEl = document.getElementById("act-count-spent");
    if (rebEl) {
      rebEl.classList.toggle("status-running", counts.rebalance > 0 && spent === 0);
      rebEl.classList.toggle("warn", spent > 0);
    }
    if (spentEl) spentEl.textContent = spent ? spent + " spent" : "—";
```

Keep halt / deviation / kill `setTape` calls. Do not add a second `const reason` in `renderBanners`.

- [ ] **Step 5: CSS**

Next to `.status-halt`:

```css
#act-count-rebalance.warn {
  color: #f59e0b;
}
```

- [ ] **Step 6: help + README**

`how_activity` after `Rebalances is the hero count.`: `Tape Rebalances sub names spent. Blotter rebalance rows say spent when that event did not finish.`

README Operator Activity sentence: Tape Rebalances sub names spent rebalances.

Keep execution `incomplete rebalance`.

- [ ] **Step 7: Full suite PASS.** Commit.

Run: `PYTHONPATH=src python3 -m pytest tests/alphastrategy/ -q`

---
