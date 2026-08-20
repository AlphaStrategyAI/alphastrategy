# Run Sleeve Card State Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans (this cycle chose executing-plans). Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Each Run sleeve card names imported / paper / halted / stopped and shows allocation as a rail, using the same `sleeveState` helper as Strategies Roster.

**Architecture:** Paint-only in `renderRunSleeves`. Header row + `paintUtilTrack`. Existing forms and dirty skip stay. No API change.

**Tech Stack:** Quiet cockpit JS parts, CSS, pytest token tests.

**Requirements:** [`docs/requirements/2026-08-20-alphastrategy-run-sleeve-state-requirements.md`](../requirements/2026-08-20-alphastrategy-run-sleeve-state-requirements.md)

## Global Constraints

- Paper only. Five `#nav` screens. Locked tokens. No `window.confirm`. No live.
- `"Gross cap"` must not appear in assembled JS.
- Sleeve state words are `imported` / `paper` / `halted` / `stopped`. Never `Live`.
- Do not clone Risk tighten forms onto Run.
- Tests: `PYTHONPATH=src python3 -m pytest tests/alphastrategy/ -q`.

## File map

- Modify: `src/alphastrategy/web/static/js/paint-run.js`, `src/alphastrategy/web/static/styles.css`, `src/alphastrategy/helptext.py`, `README.md`
- Test: `tests/alphastrategy/test_web_tokens.py`, `tests/alphastrategy/test_helptext.py`

---

### Task 1: Failing tests

- [ ] **Step 1: Write the failing tests**

In `tests/alphastrategy/test_web_tokens.py` after `test_js_paints_run_capacity`:

```python
def test_js_run_sleeve_cards_name_state(js_text: str) -> None:
    paint = js_text[
        js_text.find("function renderRunSleeves") : js_text.find("function renderRunStartHint")
    ]
    assert "sleeveState" in paint
    assert "paintUtilTrack" in paint
    assert "status-running" in paint
    assert "status-halt" in paint
    assert "status-stopped" in paint
    assert "sleeve-state" in paint
    assert "util-track" in paint
    assert "allocation " in paint
    assert ">Live<" not in paint
    assert "Gross cap" not in js_text
    assert "window.confirm" not in js_text
    assert "window.state" not in js_text
    assert "sleeve-alloc-form" in paint
    assert "data-kill-confirm" in paint


def test_css_sleeve_head_row(css_text: str) -> None:
    assert ".sleeve-head" in css_text
    assert ".sleeve-card .util-track" in css_text
```

`REQUIRED_PHRASES` add `"Each sleeve card names imported, paper, halted, or stopped"`.

- [ ] **Step 2: Run tests to verify they fail**

```bash
PYTHONPATH=src python3 -m pytest tests/alphastrategy/test_web_tokens.py::test_js_run_sleeve_cards_name_state tests/alphastrategy/test_web_tokens.py::test_css_sleeve_head_row tests/alphastrategy/test_helptext.py::test_help_text_contains_required_phrases -q
```

Expected: FAIL (strings missing).

- [ ] **Step 3: Commit failing tests + docs**

```bash
git add docs/requirements/2026-08-20-alphastrategy-run-sleeve-state-requirements.md docs/plans/2026-08-20-alphastrategy-run-sleeve-state-technical-design.md tests/alphastrategy/test_web_tokens.py tests/alphastrategy/test_helptext.py
git commit -m "test: require Run sleeve cards to name state and show an allocation rail"
```

---

### Task 2: Paint, CSS, help

- [ ] **Step 1: `renderRunSleeves` card body**

Replace the card `innerHTML` head so that **before** the allocation form:

```javascript
      const st = sleeveState(id, bundles, state.status);
      const statusClass =
        st === "paper" ? "running" : st === "halted" ? "halt" : st === "stopped" ? "stopped" : "muted";
      card.innerHTML = `
        <div class="sleeve-head">
          <h3>${id}</h3>
          <span class="sleeve-state status-${statusClass}">${st}</span>
        </div>
        <div class="util-track" data-alloc-rail></div>
        <form class="inline sleeve-alloc-form" data-bundle="${id}">
```

Keep the rest of the form and kill row exactly.

After `container.appendChild(card);` (inside the `for` loop, before the querySelectorAll binding that currently runs once after the loop):

Either paint each rail inside the loop:

```javascript
      const track = card.querySelector("[data-alloc-rail]");
      paintUtilTrack(track, alloc, 1, "allocation " + fmtPct(alloc));
      container.appendChild(card);
```

Keep the existing `querySelectorAll` bindings **after** the loop (unchanged).

- [ ] **Step 2: CSS** after `.sleeve-card h3`:

```css
.sleeve-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.5rem;
  margin-bottom: 0.35rem;
}

.sleeve-head h3 {
  margin: 0;
}

.sleeve-card .util-track {
  margin: 0 0 0.6rem;
}

.status-muted {
  color: #5c6573;
}
```

`.sleeve-card h3 { margin: 0 0 0.5rem }` can stay; `.sleeve-head h3 { margin: 0 }` wins inside the head.

- [ ] **Step 3: Help / README**

`how_run` after the Sleeves tiles sentence:

`Each sleeve card names imported, paper, halted, or stopped. Allocation is a rail. `

README Run sentence after Active / Idle: sleeve cards name imported / paper / halted / stopped; allocation is a rail.

- [ ] **Step 4: Run tests**

```bash
PYTHONPATH=src python3 -m pytest tests/alphastrategy/test_web_tokens.py::test_js_run_sleeve_cards_name_state tests/alphastrategy/test_web_tokens.py::test_css_sleeve_head_row tests/alphastrategy/test_web_tokens.py::test_js_paints_run_capacity tests/alphastrategy/test_helptext.py::test_help_text_contains_required_phrases tests/alphastrategy/test_web_tokens.py::test_html_has_no_live_toggle_label tests/alphastrategy/test_web_tokens.py::test_cockpit_js_assembled_from_parts -q
```

Expected: PASS. `paint-run.js` ≤ 400 lines.

- [ ] **Step 5: Commit**

```bash
git add src/alphastrategy/web/static/js/paint-run.js src/alphastrategy/web/static/styles.css src/alphastrategy/helptext.py README.md
git commit -m "feat: name Run sleeve state and paint allocation as a rail"
```

---

### Task 3: Full suite

```bash
PYTHONPATH=src python3 -m pytest tests/alphastrategy/ -q
```

Expected: all passed.

---

## Spec coverage

| Requirement | Task |
| --- | --- |
| sleeveState + four words + classes | 1–2 |
| paintUtilTrack allocation rail | 1–2 |
| CSS head row | 2 |
| Help / README | 2 |
| No Live / Gross cap / API change | 1–3 |

No placeholders.
