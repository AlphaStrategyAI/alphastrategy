# Risk Overlay Cards Glance-Then-Action Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans (this cycle chose executing-plans). Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make each sleeve overlay card glance (rail + tighter count) then action (`<details> Tighten this sleeve`).

**Architecture:** In `renderRisk` card loop, keep heading / allocation / track / tighter line, wrap `buildRiskInputs` in `<details class="risk-sleeve-tighten">`. Warn token on `.tighter-line` when count > 0. No API change.

**Tech Stack:** Quiet cockpit HTML/CSS/JS, `helptext.py`, pytest.

**Requirements:** [`docs/requirements/2026-08-20-alphastrategy-overlay-cards-requirements.md`](../requirements/2026-08-20-alphastrategy-overlay-cards-requirements.md)

## Global Constraints

- Paper only. Five `#nav` screens. Locked tokens. No `window.confirm`. No live. No WebSockets. No charts.
- Keep `#risk-overlays`, `#risk-sleeves`, overlay glance tiles, PUT keys, `validateTighten`. Each JS part ≤ 400 lines.
- Do not clone account Tighten tiles or Run allocation inputs onto cards. Do not label a tile Live.
- Tests: `PYTHONPATH=src python3 -m pytest tests/alphastrategy/ -q`.

## File map

- Modify: `src/alphastrategy/web/static/js/paint-risk.js`, `src/alphastrategy/web/static/styles.css`, `src/alphastrategy/helptext.py`, `README.md`
- Test: `tests/alphastrategy/test_web_tokens.py`, `tests/alphastrategy/test_helptext.py`

---

### Task 1: Failing tests

- [ ] **Step 1: JS/CSS/help**

Extend `test_js_paints_risk_overlay_glance`:

```python
    assert "tighter-line" in paint
    assert "risk-sleeve-tighten" in paint
    assert "Tighten this sleeve" in paint
    assert "createElement(\"details\")" in paint or "createElement('details')" in paint
```

Add:

```python
def test_css_risk_overlay_card_tokens(css_text: str) -> None:
    tight = re.search(
        r"#risk-sleeves\s+\.tighter-line\.warn\s*\{[^}]*\}", css_text
    )
    summary = re.search(r"\.risk-sleeve-tighten\s+summary\s*\{[^}]*\}", css_text)
    assert tight is not None and "#f59e0b" in tight.group(0).lower()
    assert summary is not None and "#9ba3b4" in summary.group(0).lower()
```

`REQUIRED_PHRASES` add `"Tighten this sleeve"`.

- [ ] **Step 2: Run — FAIL.** Commit tests + docs.

Run: `PYTHONPATH=src python3 -m pytest tests/alphastrategy/test_web_tokens.py::test_js_paints_risk_overlay_glance tests/alphastrategy/test_web_tokens.py::test_css_risk_overlay_card_tokens tests/alphastrategy/test_helptext.py::test_help_text_contains_required_phrases -q`

Expected: FAIL (details / phrase / CSS missing).

---

### Task 2: JS, CSS, help

- [ ] **Step 3: JS** — tighter line `className = "nums tighter-line"`; `classList.add("warn")` when count > 0. Wrap form:

```javascript
      const details = document.createElement("details");
      details.className = "risk-sleeve-tighten";
      const summary = document.createElement("summary");
      summary.textContent = "Tighten this sleeve";
      details.appendChild(summary);
      details.appendChild(form);
      panel.appendChild(details);
```

Keep `createElement("details")` with double quotes so the test matches. File ≤ 400 lines.

- [ ] **Step 4: CSS** — separate `#risk-sleeves .tighter-line.warn` and `.risk-sleeve-tighten summary` blocks as in the requirements.

- [ ] **Step 5: Help + README** — `how_risk` and cockpit: each overlay card is allocation rail and tighter count; Tighten this sleeve holds the form.

- [ ] **Step 6: Full suite PASS. Commit.**

Run: `PYTHONPATH=src python3 -m pytest tests/alphastrategy/ -q`

Expected: PASS.

---

## Spec coverage

| Requirement | Task |
| --- | --- |
| details + summary copy | 1, 3 |
| tighter-line warn | 1, 3, 4 |
| summary token | 1, 4 |
| Help phrase | 1, 5 |
